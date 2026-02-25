#!/usr/bin/env python3
"""Referee recommendation pipeline: orchestrator.

Loads extraction JSON, assesses desk rejection, finds referee candidates,
checks conflicts, and produces a recommendation report.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from core.academic_apis import AcademicProfileEnricher
from core.output_schema import JOURNAL_NAME_MAP, PLATFORM_MAP
from pipeline.conflict_checker import check_conflicts
from pipeline.desk_rejection import assess_desk_rejection
from pipeline.referee_finder import find_referees

PIPELINE_VERSION = "0.1.0"

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
JOURNALS = ["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"]

AWAITING_REFEREE_CONFIG = {
    "ScholarOne": {
        "category_contains": ["Requiring Assignment to a Reviewer"],
        "status_contains": ["Awaiting Reviewer"],
    },
    "SIAM": {
        "stage_values": [
            "Waiting for Potential Referee Assignment",
            "Contacting Potential Referees",
            "Potential Referees Assigned",
        ],
    },
    "Editorial Manager": {
        "status_needs_referee_check": ["Under Review", "With Referees", "Submitted to Journal"],
    },
    "EditFlow (MSP)": {
        "status_needs_referee_check": ["Under Review"],
    },
    "Email (Gmail)": {
        "status_values": ["Under Review", "New Submission"],
    },
}


def is_awaiting_referee(manuscript: dict, platform: str) -> bool:
    config = AWAITING_REFEREE_CONFIG.get(platform, {})
    status = (manuscript.get("status") or "").strip()
    category = (manuscript.get("category") or "").strip()
    ps = manuscript.get("platform_specific", {})

    for pattern in config.get("category_contains", []):
        if pattern.lower() in category.lower():
            return True
        cat_name = (ps.get("category_name") or "").strip()
        if pattern.lower() in cat_name.lower():
            return True

    for pattern in config.get("status_contains", []):
        if pattern.lower() in status.lower():
            return True
        main_status = (ps.get("status_details", {}).get("main_status") or "").strip()
        if pattern.lower() in main_status.lower():
            return True

    current_stage = (ps.get("metadata", {}).get("current_stage") or "").strip()
    for val in config.get("stage_values", []):
        if val.lower() == current_stage.lower():
            return True
        if val.lower() == status.lower():
            return True

    for val in config.get("status_values", []):
        if val.lower() == status.lower():
            return True

    referee_check_statuses = config.get("status_needs_referee_check", [])
    if referee_check_statuses:
        for val in referee_check_statuses:
            if val.lower() == status.lower():
                referees = manuscript.get("referees", [])
                active = [
                    r
                    for r in referees
                    if (r.get("status") or "").lower() not in ("", "declined", "cancelled")
                ]
                if len(active) == 0:
                    return True
                break

    return False


def find_latest_output(journal: str) -> Optional[Path]:
    journal_dir = OUTPUTS_DIR / journal.lower()
    if not journal_dir.exists():
        return None
    files = sorted(journal_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        if "BASELINE" in f.name or "debug" in str(f) or "recommendation" in str(f):
            continue
        return f
    return None


def load_journal_data(journal: str) -> Optional[dict]:
    path = find_latest_output(journal)
    if not path:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


class RefereePipeline:
    def __init__(self, use_llm: bool = False, max_candidates: int = 15):
        self.use_llm = use_llm
        self.max_candidates = max_candidates
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Editorial-Scripts/1.0 (mailto:dylansmb@gmail.com)"}
        )
        self.enricher = AcademicProfileEnricher(self.session)
        self.expertise_index = None
        self.response_predictor = None
        self.outcome_predictor = None
        self._load_models()

    def _load_models(self):
        try:
            from pipeline.models.expertise_index import ExpertiseIndex

            idx = ExpertiseIndex()
            if idx.load():
                self.expertise_index = idx
                print(f"   Loaded expertise index ({len(idx.referees)} referees)")
        except Exception:
            pass
        try:
            from pipeline.models.response_predictor import RefereeResponsePredictor

            rp = RefereeResponsePredictor()
            if rp.load():
                self.response_predictor = rp
                print("   Loaded response predictor")
        except Exception:
            pass
        try:
            from pipeline.models.outcome_predictor import ManuscriptOutcomePredictor

            op = ManuscriptOutcomePredictor()
            if op.load():
                self.outcome_predictor = op
                print("   Loaded outcome predictor")
        except Exception:
            pass

    def run_single(self, journal_code: str, manuscript_id: str) -> dict:
        jc = journal_code.upper()
        print(f"\n{'='*60}")
        print(f"Pipeline: {jc} / {manuscript_id}")
        print(f"{'='*60}")

        data = load_journal_data(journal_code)
        if not data:
            print(f"   No extraction data found for {jc}")
            return {}

        manuscript = None
        for ms in data.get("manuscripts", []):
            if ms.get("manuscript_id") == manuscript_id:
                manuscript = ms
                break
        if not manuscript:
            print(f"   Manuscript {manuscript_id} not found in latest {jc} extraction")
            return {}

        return self._process_manuscript(manuscript, jc)

    def run_pending(self, journal_code: str) -> list:
        jc = journal_code.upper()
        platform = PLATFORM_MAP.get(jc, "")

        data = load_journal_data(journal_code)
        if not data:
            print(f"No extraction data found for {jc}")
            return []

        pending = []
        for ms in data.get("manuscripts", []):
            if is_awaiting_referee(ms, platform):
                pending.append(ms)

        if not pending:
            print(f"No manuscripts awaiting referee assignment in {jc}")
            return []

        print(f"Found {len(pending)} manuscript(s) awaiting referee assignment in {jc}")
        reports = []
        for ms in pending:
            report = self._process_manuscript(ms, jc)
            if report:
                reports.append(report)
        return reports

    def _process_manuscript(self, manuscript: dict, journal_code: str) -> dict:
        ms_id = manuscript.get("manuscript_id", "?")
        title = manuscript.get("title", "?")
        print(f"\n   Processing: {ms_id}")
        print(f"   Title: {title[:80]}{'...' if len(title) > 80 else ''}")

        all_journals = {}
        for j in JOURNALS:
            jd = load_journal_data(j)
            if jd:
                all_journals[j] = jd

        from pipeline.report_quality import assess_report_quality

        print("   [1/5] Report quality assessment...")
        rq = assess_report_quality(manuscript)
        if rq["n_reports"] > 0:
            print(f"   >> {rq['n_reports']} reports, quality={rq['overall_quality']:.2f}")
        else:
            print("   >> No reports available")

        print("   [2/5] Desk rejection assessment...")
        desk = assess_desk_rejection(
            manuscript,
            journal_code,
            all_journals,
            use_llm=self.use_llm,
            outcome_predictor=self.outcome_predictor,
            report_quality=rq,
        )
        if desk["should_desk_reject"]:
            print(f"   >> DESK REJECT (confidence={desk['confidence']}): {desk['summary']}")
        else:
            print(f"   >> Pass (confidence={desk['confidence']})")

        candidates = []
        if not desk["should_desk_reject"] or desk["confidence"] < 0.8:
            print("   [3/5] Searching for referee candidates...")
            candidates = find_referees(
                manuscript,
                journal_code,
                self.enricher,
                self.session,
                self.max_candidates,
                expertise_index=self.expertise_index,
                response_predictor=self.response_predictor,
            )
            print(f"   >> Found {len(candidates)} candidates")

            rec = manuscript.get("referee_recommendations", {})
            if not rec:
                rec = manuscript.get("platform_specific", {}).get("referee_recommendations", {})
            opposed = rec.get("opposed_referees", [])

            print("   [4/5] Checking conflicts...")
            for c in candidates:
                conflicts = check_conflicts(
                    c,
                    manuscript.get("authors", []),
                    opposed,
                    manuscript.get("editors", []),
                    self.enricher,
                )
                c["conflicts"] = conflicts
                c["is_conflicted"] = len(conflicts) > 0

                opp_names = {_norm(o.get("name", "")) for o in opposed if o.get("name")}
                opp_emails = {(o.get("email") or "").lower() for o in opposed if o.get("email")}
                c["author_opposed"] = (c.get("email") or "").lower() in opp_emails or _norm(
                    c.get("name", "")
                ) in opp_names

            conflicted_count = sum(1 for c in candidates if c["is_conflicted"])
            print(
                f"   >> {conflicted_count} conflicted, {len(candidates) - conflicted_count} clean"
            )
        else:
            print("   [3/5] Skipping referee search (desk rejection recommended)")
            print("   [4/5] Skipping conflict check")

        print("   [5/5] Building report...")
        report = self._build_report(manuscript, journal_code, desk, candidates, rq)
        self._save_report(report, journal_code)
        self._print_summary(report)
        return report

    def _build_report(
        self,
        manuscript: dict,
        journal_code: str,
        desk: dict,
        candidates: list,
        report_quality: dict = None,
    ) -> dict:
        clean = [c for c in candidates if not c["is_conflicted"]]
        conflicted = [c for c in candidates if c["is_conflicted"]]

        clean.sort(key=lambda x: -x["relevance_score"])
        top = clean[: self.max_candidates]
        for i, c in enumerate(top, 1):
            c["rank"] = i

        rec = manuscript.get("referee_recommendations", {})
        if not rec:
            rec = manuscript.get("platform_specific", {}).get("referee_recommendations", {})
        suggested_status = {}
        for r in rec.get("recommended_referees", []):
            name = r.get("name", "?")
            matched = any(self.enricher._name_match(c.get("name", ""), name) for c in top)
            if matched:
                suggested_status[name] = "recommended"
            else:
                in_conflicted = any(
                    self.enricher._name_match(c.get("name", ""), name) for c in conflicted
                )
                suggested_status[name] = "conflict" if in_conflicted else "not_found"

        return {
            "pipeline_version": PIPELINE_VERSION,
            "generated_at": datetime.now().isoformat(),
            "journal": journal_code.upper(),
            "journal_name": JOURNAL_NAME_MAP.get(journal_code.upper(), ""),
            "manuscript_id": manuscript.get("manuscript_id", ""),
            "title": manuscript.get("title", ""),
            "desk_rejection": desk,
            "referee_candidates": _sanitize_candidates(top),
            "conflicted_candidates": _sanitize_candidates(conflicted[:10]),
            "author_suggested_status": suggested_status,
            "report_quality": report_quality or {},
            "metadata": {
                "candidates_found": len(candidates),
                "candidates_clean": len(clean),
                "candidates_conflicted": len(conflicted),
                "top_returned": len(top),
                "models_loaded": {
                    "expertise_index": self.expertise_index is not None,
                    "response_predictor": self.response_predictor is not None,
                    "outcome_predictor": self.outcome_predictor is not None,
                },
            },
        }

    def _save_report(self, report: dict, journal_code: str) -> Path:
        rec_dir = OUTPUTS_DIR / journal_code.lower() / "recommendations"
        rec_dir.mkdir(parents=True, exist_ok=True)
        ms_id = report.get("manuscript_id", "unknown")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = rec_dir / f"rec_{ms_id}_{ts}.json"
        with open(path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"   Saved: {path}")
        return path

    def _print_summary(self, report: dict):
        print(f"\n{'─'*60}")
        print(f"  {report['journal']} / {report['manuscript_id']}")
        print(f"  {report['title'][:70]}")
        print(f"{'─'*60}")

        desk = report["desk_rejection"]
        if desk["should_desk_reject"]:
            print(f"  DESK REJECT ({desk['method']}, confidence={desk['confidence']})")
            print(f"  {desk['summary']}")
        else:
            print(f"  Pass desk rejection ({desk['method']}, confidence={desk['confidence']})")

        candidates = report.get("referee_candidates", [])
        if candidates:
            print(f"\n  Top {len(candidates)} referee candidates:")
            print(f"  {'#':>3}  {'Score':>5}  {'Source':<20}  {'Name':<30}  {'H':>3}  Topics")
            print(f"  {'─'*3}  {'─'*5}  {'─'*20}  {'─'*30}  {'─'*3}  {'─'*20}")
            for c in candidates:
                topics = ", ".join(c.get("topic_overlap", [])[:3]) or "-"
                h = c.get("h_index") or "-"
                suggested = " *" if c.get("author_suggested") else ""
                print(
                    f"  {c.get('rank', '?'):>3}  "
                    f"{c.get('relevance_score', 0):>5.3f}  "
                    f"{c.get('source', '?'):<20}  "
                    f"{(c.get('name', '?')[:28] + suggested):<30}  "
                    f"{str(h):>3}  "
                    f"{topics[:40]}"
                )

        conflicted = report.get("conflicted_candidates", [])
        if conflicted:
            print(f"\n  Conflicted ({len(conflicted)}):")
            for c in conflicted:
                reasons = "; ".join(c.get("conflicts", []))
                print(f"    {c.get('name', '?')}: {reasons}")

        suggested = report.get("author_suggested_status", {})
        if suggested:
            print(f"\n  Author-suggested referees:")
            for name, status in suggested.items():
                print(f"    {name}: {status}")

        print()


def _norm(s: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _sanitize_candidates(candidates: list) -> list:
    clean = []
    skip_keys = {"web_profile", "_hist_journal", "_hist_ms", "_hist_overlap"}
    for c in candidates:
        out = {k: v for k, v in c.items() if k not in skip_keys}
        clean.append(out)
    return clean
