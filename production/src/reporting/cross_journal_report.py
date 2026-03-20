#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"

JOURNALS = ["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"]

JOURNAL_NAMES = {
    "mf": "Mathematical Finance",
    "mor": "Math. Operations Research",
    "fs": "Finance & Stochastics",
    "jota": "JOTA",
    "mafe": "MAFE",
    "sicon": "SICON",
    "sifin": "SIFIN",
    "naco": "NACO",
}

PLATFORMS = {
    "mf": "ScholarOne",
    "mor": "ScholarOne",
    "fs": "Gmail",
    "jota": "Editorial Mgr",
    "mafe": "Editorial Mgr",
    "sicon": "SIAM",
    "sifin": "SIAM",
    "naco": "EditFlow",
}


def _list_extraction_files(journal: str) -> list[Path]:
    journal_dir = OUTPUTS_DIR / journal
    if not journal_dir.exists():
        return []
    skip = ("BASELINE", "debug", "rec_", "partial")
    return sorted(
        [f for f in journal_dir.glob("*.json") if not any(s in f.name for s in skip)],
        key=lambda f: f.name,
        reverse=True,
    )


def find_latest_output(journal: str) -> Optional[Path]:
    files = _list_extraction_files(journal)
    return files[0] if files else None


def _load_json(path: Path) -> Optional[dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_journal_data(journal: str) -> Optional[dict]:
    files = _list_extraction_files(journal)
    if not files:
        return None

    latest = _load_json(files[0])
    if not latest:
        return None

    latest["_source_file"] = files[0].name
    latest["_source_path"] = str(files[0])

    manifest = latest.get("dashboard_manifest")
    if not manifest or not manifest.get("scanned"):
        return latest

    discovered_ids = set()
    for ids in manifest["scanned"].values():
        discovered_ids.update(ids)
    failed_categories = set(manifest.get("failed", []))

    latest_ids = {m.get("manuscript_id") for m in latest.get("manuscripts", [])}
    ms_by_id = {m.get("manuscript_id"): m for m in latest.get("manuscripts", [])}

    need_from_older = discovered_ids - latest_ids
    if need_from_older or failed_categories:
        for older_path in files[1:]:
            older = _load_json(older_path)
            if not older:
                continue
            for m in older.get("manuscripts", []):
                ms_id = m.get("manuscript_id")
                if not ms_id or ms_id in ms_by_id:
                    continue
                if ms_id in need_from_older:
                    ms_by_id[ms_id] = m
                    need_from_older.discard(ms_id)
                elif failed_categories:
                    ms_cat = (m.get("category") or "").strip()
                    if ms_cat in failed_categories:
                        ms_by_id[ms_id] = m
            if not need_from_older:
                break

    latest["manuscripts"] = list(ms_by_id.values())
    return latest


INACTIVE_REFEREE_STATUSES = {
    "Reviewer Declined",
    "Declined",
    "Un-invited Before Agreeing to Review",
    "Un-assigned After Agreeing to Review",
    "Terminated After Agreeing to Review",
    "No Response",
    "No response",
    "Un-invited",
    "Un-assigned",
    "Terminated",
}

_INACTIVE_LOWER = {s.lower() for s in INACTIVE_REFEREE_STATUSES}


def _dedup_referees(referees: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for ref in referees:
        name = (ref.get("name") or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(ref)
    return unique


def _is_active_referee(ref: dict) -> bool:
    status = ref.get("platform_specific", {}).get("status") or ref.get("status") or ""
    return status.strip().lower() not in _INACTIVE_LOWER


def compute_journal_stats(journal: str, data: dict) -> dict:
    manuscripts = data.get("manuscripts", [])
    ms_count = len(manuscripts)

    ms_deduped = {m.get("manuscript_id", id(m)): m for m in manuscripts}
    manuscripts = list(ms_deduped.values())
    ms_count = len(manuscripts)

    total_refs = 0
    active_refs = 0
    total_authors = 0
    enriched = 0

    for m in manuscripts:
        refs = _dedup_referees(m.get("referees", []))
        authors = m.get("authors", [])
        total_refs += len(refs)
        active_refs += sum(1 for r in refs if _is_active_referee(r))
        total_authors += len(authors)
        enriched += sum(1 for p in refs + authors if p.get("web_profile"))

    total_people = total_refs + total_authors

    span_days = []
    response_days = []
    for m in manuscripts:
        ta = m.get("timeline_analytics", {})
        if ta.get("communication_span_days"):
            span_days.append(ta["communication_span_days"])
        rta = ta.get("response_time_analysis", {})
        if rta.get("average_response_days"):
            response_days.append(rta["average_response_days"])

    avg_span = round(sum(span_days) / len(span_days), 1) if span_days else None
    avg_response = round(sum(response_days) / len(response_days), 1) if response_days else None

    ts = data.get("extraction_timestamp", "")
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age_days = (
                (datetime.now(dt.tzinfo) - dt).days if dt.tzinfo else (datetime.now() - dt).days
            )
        except Exception:
            age_days = None
    else:
        age_days = None

    return {
        "journal": journal.upper(),
        "journal_name": JOURNAL_NAMES.get(journal, journal),
        "platform": PLATFORMS.get(journal, ""),
        "manuscripts": ms_count,
        "referees": active_refs,
        "referees_all": total_refs,
        "authors": total_authors,
        "enriched": enriched,
        "total_people": total_people,
        "enrichment_pct": round(100 * enriched / total_people, 1) if total_people > 0 else 0,
        "avg_span_days": avg_span,
        "avg_response_days": avg_response,
        "extraction_date": ts[:10] if len(ts) >= 10 else "",
        "age_days": age_days,
        "source_file": data.get("_source_file", ""),
        "schema_version": data.get("schema_version", ""),
    }


def print_terminal_report(all_stats: list[dict]):
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════════╗")
    print("║                       CROSS-JOURNAL EXTRACTION REPORT                          ║")
    print(
        f"║  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}                                                  ║"
    )
    print("╚══════════════════════════════════════════════════════════════════════════════════╝")
    print()

    header = f"{'Journal':<8} {'Platform':<14} {'MSS':>4} {'Refs':>5} {'Auth':>5} {'Enrich':>7} {'Span':>6} {'Resp':>6} {'Extracted':>11}"
    print(header)
    print("─" * len(header))

    tot_ms = tot_refs = tot_auth = tot_enriched = 0
    active_journals = 0

    for s in all_stats:
        if s is None:
            continue

        ms_str = str(s["manuscripts"]) if s["manuscripts"] > 0 else "—"
        refs_str = str(s["referees"]) if s["referees"] > 0 else "—"
        auth_str = str(s["authors"]) if s["authors"] > 0 else "—"
        enrich_str = f"{s['enrichment_pct']:.0f}%" if s["total_people"] > 0 else "—"
        span_str = f"{s['avg_span_days']:.0f}d" if s["avg_span_days"] else "—"
        resp_str = f"{s['avg_response_days']:.0f}d" if s["avg_response_days"] else "—"
        date_str = s["extraction_date"] if s["extraction_date"] else "—"

        print(
            f"{s['journal']:<8} {s['platform']:<14} {ms_str:>4} {refs_str:>5} {auth_str:>5} {enrich_str:>7} {span_str:>6} {resp_str:>6} {date_str:>11}"
        )

        tot_ms += s["manuscripts"]
        tot_refs += s["referees"]
        tot_auth += s["authors"]
        tot_enriched += s["enriched"]
        if s["manuscripts"] > 0:
            active_journals += 1

    print("─" * len(header))
    tot_people = tot_refs + tot_auth
    enrich_pct = f"{100 * tot_enriched / tot_people:.0f}%" if tot_people > 0 else "—"
    print(
        f"{'TOTAL':<8} {'':<14} {tot_ms:>4} {tot_refs:>5} {tot_auth:>5} {enrich_pct:>7} {'':>6} {'':>6} {'':>11}"
    )

    print()
    print(f"  📊 {active_journals}/{len(all_stats)} journals active, {tot_ms} manuscripts tracked")
    print(f"  👥 {tot_refs} referees, {tot_auth} authors ({tot_enriched}/{tot_people} enriched)")
    stale = [s for s in all_stats if s and s.get("age_days") and s["age_days"] > 7]
    if stale:
        stale_names = ", ".join(s["journal"] for s in stale)
        print(f"  ⚠️  Stale data (>7 days): {stale_names}")
    print()


def generate_json_report(all_stats: list[dict]) -> dict:
    return {
        "report_type": "cross_journal",
        "generated_at": datetime.now().isoformat(),
        "schema_version": "1.0.0",
        "journals": all_stats,
        "totals": {
            "journals_active": sum(1 for s in all_stats if s and s["manuscripts"] > 0),
            "journals_total": len(all_stats),
            "manuscripts": sum(s["manuscripts"] for s in all_stats if s),
            "referees": sum(s["referees"] for s in all_stats if s),
            "authors": sum(s["authors"] for s in all_stats if s),
            "enriched_people": sum(s["enriched"] for s in all_stats if s),
        },
    }


def _get_feedback_summary() -> dict | None:
    try:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        stats = trainer.get_feedback_stats()
        if not stats:
            return None
        total = sum(s["total"] for s in stats.values())
        return {"total": total, "journals": stats}
    except (ImportError, OSError):
        return None


def _print_feedback_summary(feedback: dict):
    print(f"  Feedback: {feedback['total']} outcomes recorded")
    for journal, s in sorted(feedback["journals"].items()):
        decisions = ", ".join(f"{k}: {v}" for k, v in s["decisions"].items())
        print(f"    {journal.upper()}: {s['total']} — {decisions}")
    print()


def run_report(save_json: bool = False, output_dir: Optional[Path] = None) -> dict:
    all_stats = []
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if data:
            stats = compute_journal_stats(journal, data)
            all_stats.append(stats)
        else:
            all_stats.append(
                {
                    "journal": journal.upper(),
                    "journal_name": JOURNAL_NAMES.get(journal, journal),
                    "platform": PLATFORMS.get(journal, ""),
                    "manuscripts": 0,
                    "referees": 0,
                    "authors": 0,
                    "enriched": 0,
                    "total_people": 0,
                    "enrichment_pct": 0,
                    "avg_span_days": None,
                    "avg_response_days": None,
                    "extraction_date": "",
                    "age_days": None,
                    "source_file": "",
                    "schema_version": "",
                }
            )

    print_terminal_report(all_stats)

    feedback = _get_feedback_summary()
    if feedback:
        _print_feedback_summary(feedback)

    report = generate_json_report(all_stats)
    if feedback:
        report["feedback"] = feedback

    if save_json:
        out_dir = output_dir or OUTPUTS_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"cross_journal_report_{timestamp}.json"
        with open(out_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  💾 JSON report saved: {out_file}")

    return report


if __name__ == "__main__":
    save = "--json" in sys.argv
    run_report(save_json=save)
