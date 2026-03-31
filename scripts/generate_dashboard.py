#!/usr/bin/env python3
"""Generate a self-contained HTML editorial command center."""

import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "production" / "src"))

from reporting.action_items import (  # noqa: E402
    compute_action_items,
    compute_manuscript_summaries,
)
from reporting.cross_journal_report import (  # noqa: E402
    JOURNAL_NAMES,
    JOURNALS,
    PLATFORMS,
    compute_journal_stats,
    load_journal_data,
)

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "production" / "outputs"
MODELS_DIR = Path(__file__).resolve().parent.parent / "production" / "models"


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _load_training_metadata():
    path = MODELS_DIR / "training_metadata.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _load_recent_recommendations(limit=10):
    recs = []
    for journal in JOURNALS:
        rec_dir = OUTPUTS_DIR / journal / "recommendations"
        if not rec_dir.exists():
            continue
        for f in sorted(rec_dir.glob("rec_*.json"), key=lambda p: p.name, reverse=True):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                recs.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    recs.sort(key=lambda r: r.get("generated_at", ""), reverse=True)
    seen = set()
    unique = []
    for r in recs:
        key = (r.get("journal", ""), r.get("manuscript_id", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)
            if len(unique) >= limit:
                break
    return unique


def _load_referee_intelligence():
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        return {
            "top": db.get_top_referees(min_invitations=2, limit=15),
            "decliners": db.get_chronic_decliners(min_invitations=2),
            "overdue": db.get_overdue_repeat_offenders(min_overdue=2),
        }
    except Exception:
        return {"top": [], "decliners": [], "overdue": []}


def _freshness_class(age_days):
    if age_days is None:
        return "stale"
    if age_days <= 7:
        return "fresh"
    if age_days <= 14:
        return "aging"
    return "stale"


def _freshness_label(age_days):
    if age_days is None:
        return "No data"
    if age_days == 0:
        return "Today"
    if age_days == 1:
        return "1d ago"
    return f"{age_days}d ago"


def _clean_institution(name, inst):
    import re

    if not inst:
        return ""
    inst = re.sub(r":?\d{4}-\d{4}-\d{4}-\d{3}[\dXx].*", "", inst)
    inst = re.sub(r"0000-\d{4}-\d{4}-\d{3}[\dXx].*", "", inst)
    garbage = [
        "GeneralInformationAddress",
        "GeneralInformationAd",
        "GeneralInformation",
        "dressHistoryNotes",
        "dressHistory",
        "HistoryNotes",
        "History",
        "Keywords",
        "ORCID",
        "Address",
        "Notes",
    ]
    for g in garbage:
        inst = inst.replace(g, "").strip()
    prefixes = ["Prof. ", "Dr. ", "Professor ", "Prof ", "Dr "]
    for p in prefixes:
        if inst.startswith(p):
            inst = inst[len(p) :].strip()
    if name:
        parts = [name, name.split(",")[0].strip()]
        parts += name.split()
        parts = sorted({p for p in parts if len(p) > 2}, key=len, reverse=True)
        for n in parts:
            if inst.startswith(n):
                inst = inst[len(n) :].strip()
                break
    inst = inst.lstrip(":,. ").rstrip(",.").strip()
    if not inst or len(inst) < 4:
        return ""
    if name:
        name_norm = name.lower().replace(",", "").strip()
        inst_norm = inst.lower().replace(",", "").strip()
        if inst_norm == name_norm or inst_norm in name_norm or name_norm in inst_norm:
            return ""
        name_words = set(name_norm.split())
        inst_words = set(inst_norm.split())
        if name_words and inst_words and inst_words.issubset(name_words):
            return ""
    if inst.isupper():
        return ""
    if len(inst) > 40:
        inst = inst[:38] + "…"
    return inst


def build_dashboard_data():
    journal_stats = []
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if data:
            stats = compute_journal_stats(journal, data)
            stats["freshness_class"] = _freshness_class(stats.get("age_days"))
            stats["freshness_label"] = _freshness_label(stats.get("age_days"))
            journal_stats.append(stats)
        else:
            journal_stats.append(
                {
                    "journal": journal,
                    "journal_name": JOURNAL_NAMES.get(journal, journal.upper()),
                    "platform": PLATFORMS.get(journal, ""),
                    "manuscripts": 0,
                    "referees": 0,
                    "authors": 0,
                    "freshness_class": "stale",
                    "freshness_label": "No data",
                    "age_days": None,
                    "extraction_date": None,
                }
            )

    action_items = compute_action_items()
    manuscript_summaries = compute_manuscript_summaries()
    recommendations = _load_recent_recommendations(limit=8)
    training = _load_training_metadata()

    manuscripts_by_journal = {}
    for ms in manuscript_summaries:
        j = ms.journal
        if j not in manuscripts_by_journal:
            manuscripts_by_journal[j] = []
        manuscripts_by_journal[j].append(ms)

    rec_summaries = []
    for rec in recommendations:
        candidates = rec.get("referee_candidates", [])[:3]
        rec_summaries.append(
            {
                "manuscript_id": rec.get("manuscript_id", ""),
                "title": (rec.get("title") or "")[:80],
                "journal": (rec.get("journal") or "").upper(),
                "generated_at": rec.get("generated_at", "")[:10],
                "desk_rejection": rec.get("desk_rejection", {}),
                "candidates": [
                    {
                        "name": c.get("name", ""),
                        "institution": _clean_institution(
                            c.get("name", ""), c.get("institution") or ""
                        ),
                        "h_index": c.get("h_index"),
                        "score": c.get("relevance_score", 0),
                        "source": c.get("source", ""),
                    }
                    for c in candidates
                ],
            }
        )

    active_refs = sum(s.get("referees", 0) for s in journal_stats)

    totals = {
        "active_journals": sum(1 for s in journal_stats if s.get("manuscripts", 0) > 0),
        "manuscripts": sum(s.get("manuscripts", 0) for s in journal_stats),
        "active_manuscripts": len(manuscript_summaries),
        "referees": active_refs,
        "action_items": len(action_items),
        "critical": sum(1 for a in action_items if a.priority == "critical"),
        "high": sum(1 for a in action_items if a.priority == "high"),
    }

    referee_intelligence = _load_referee_intelligence()

    rec_by_ms = {}
    for rec in rec_summaries:
        key = (rec["journal"].lower(), rec["manuscript_id"])
        rec_by_ms[key] = rec

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "git_commit": _git_commit(),
        "journals": journal_stats,
        "totals": totals,
        "action_items": [asdict(a) for a in action_items],
        "manuscripts": [asdict(s) for s in manuscript_summaries],
        "manuscripts_by_journal": {
            k: [asdict(m) for m in v] for k, v in manuscripts_by_journal.items()
        },
        "recommendations": rec_summaries,
        "rec_by_ms": rec_by_ms,
        "referee_intelligence": referee_intelligence,
        "training": training,
    }


def _esc(s):
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


CSS = """
:root {
    --bg: #f8fafc; --surface: #ffffff; --surface2: #f1f5f9;
    --text: #1e293b; --text2: #64748b; --text3: #94a3b8;
    --border: #e2e8f0; --border2: #cbd5e1;
    --accent: #3b82f6; --accent-bg: #eff6ff;
    --crit: #dc2626; --crit-bg: #fef2f2; --crit-border: #fecaca;
    --high: #ea580c; --high-bg: #fff7ed; --high-border: #fed7aa;
    --med: #b45309; --med-bg: #fffbeb; --med-border: #fde68a;
    --low: #16a34a; --low-bg: #f0fdf4; --low-border: #bbf7d0;
    --done: #059669; --done-bg: #ecfdf5;
    --muted: #94a3b8; --muted-bg: #f1f5f9;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0f172a; --surface: #1e293b; --surface2: #334155;
        --text: #f1f5f9; --text2: #94a3b8; --text3: #64748b;
        --border: #334155; --border2: #475569;
        --accent: #60a5fa; --accent-bg: #1e3a5f;
        --crit: #f87171; --crit-bg: #450a0a; --crit-border: #7f1d1d;
        --high: #fb923c; --high-bg: #431407; --high-border: #7c2d12;
        --med: #fbbf24; --med-bg: #422006; --med-border: #78350f;
        --low: #4ade80; --low-bg: #052e16; --low-border: #14532d;
        --done: #34d399; --done-bg: #052e16;
        --muted: #64748b; --muted-bg: #1e293b;
    }
}
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
    background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.5;
    padding: 24px; max-width: 1100px; margin: 0 auto;
}
h1 { font-size: 1.5rem; font-weight: 700; text-align: center; margin-bottom: 4px; }
.subtitle { text-align: center; color: var(--text2); font-size: 0.8rem; margin-bottom: 16px; }

/* Alert bar */
.alert {
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;
    font-weight: 600; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;
    border: 1px solid;
}
.alert-crit { background: var(--crit-bg); border-color: var(--crit-border); color: var(--crit); }
.alert-high { background: var(--high-bg); border-color: var(--high-border); color: var(--high); }
.alert-ok { background: var(--low-bg); border-color: var(--low-border); color: var(--low); }

/* Stats pills */
.stats { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px; }
.stat {
    background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
    padding: 5px 14px; font-size: 0.8rem;
}
.stat b { font-size: 0.9rem; }

/* Section */
.section { margin-bottom: 28px; }
.section-hdr {
    font-size: 1rem; font-weight: 700; margin-bottom: 10px;
    padding-bottom: 6px; border-bottom: 2px solid var(--border);
}

/* Filters */
.filters { display: flex; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
.fbtn {
    border: 1px solid var(--border); background: var(--surface); color: var(--text2);
    padding: 3px 12px; border-radius: 14px; font-size: 0.75rem; cursor: pointer;
}
.fbtn:hover { border-color: var(--accent); color: var(--accent); }
.fbtn.active { background: var(--accent); color: #fff; border-color: var(--accent); }

/* Action items */
.action-list { display: flex; flex-direction: column; gap: 6px; }
.action-item {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 12px; border-radius: 6px;
    border-left: 4px solid; background: var(--surface); font-size: 0.85rem;
}
.action-item.p-crit { border-left-color: var(--crit); background: var(--crit-bg); }
.action-item.p-high { border-left-color: var(--high); background: var(--high-bg); }
.action-item.p-med { border-left-color: var(--med); background: var(--med-bg); }
.action-item.p-low { border-left-color: var(--low); background: var(--low-bg); }
.action-type {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    padding: 2px 8px; border-radius: 3px; color: #fff; white-space: nowrap;
    min-width: 62px; text-align: center;
}
.action-type.t-crit { background: var(--crit); }
.action-type.t-high { background: var(--high); }
.action-type.t-med { background: var(--med); }
.action-type.t-low { background: var(--low); }
.action-journal {
    font-size: 0.72rem; font-weight: 700; color: var(--accent);
    background: var(--accent-bg); padding: 2px 6px; border-radius: 3px;
    white-space: nowrap;
}
.action-msid { font-weight: 700; white-space: nowrap; }
.action-msg { flex: 1; min-width: 0; }
.action-extra { color: var(--text2); font-size: 0.75rem; white-space: nowrap; }
.btn-ae { padding: 3px 10px; font-size: 0.75rem; border-radius: 4px; border: 1px solid var(--accent); background: var(--accent); color: #fff; cursor: pointer; white-space: nowrap; }
.btn-ae:hover { opacity: 0.85; }
.btn-ae:disabled { opacity: 0.5; cursor: wait; }
.btn-ae.btn-view { background: transparent; color: var(--accent); }
.btn-ae.btn-done { background: #22c55e; border-color: #22c55e; }

/* Table */
.table-wrap {
    overflow-x: auto; border-radius: 8px;
    border: 1px solid var(--border);
}
table {
    width: 100%; border-collapse: collapse; background: var(--surface);
    font-size: 0.82rem; table-layout: fixed;
}
thead th {
    background: var(--surface2); padding: 8px 10px; text-align: left;
    font-weight: 600; font-size: 0.72rem; color: var(--text2);
    text-transform: uppercase; letter-spacing: 0.03em;
    border-bottom: 2px solid var(--border); cursor: pointer;
    white-space: nowrap; user-select: none;
}
thead th:hover { color: var(--accent); }
td {
    padding: 7px 10px; border-bottom: 1px solid var(--border);
    vertical-align: middle;
}
tr:last-child td { border-bottom: none; }
.ms-row { cursor: pointer; transition: background 0.1s; }
.ms-row:hover td { background: var(--accent-bg); }
.ms-row td:first-child { padding-left: 20px; position: relative; }
.ms-row td:first-child::before {
    content: "\\25B8"; position: absolute; left: 6px; top: 50%;
    transform: translateY(-50%); color: var(--text3); font-size: 0.65rem;
}
.ms-row.expanded td:first-child::before { content: "\\25BE"; }
.td-title {
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.td-id { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.td-status { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.td-reports { text-align: center; font-weight: 700; }
.td-due { white-space: nowrap; text-align: right; }
.td-days { text-align: right; white-space: nowrap; }

.overdue { color: var(--crit); font-weight: 600; }
.due-soon { color: var(--med); font-weight: 600; }
.on-track { color: var(--done); }

.flag {
    display: inline-block; font-size: 0.68rem; font-weight: 600;
    padding: 1px 6px; border-radius: 3px; margin-left: 4px;
    background: var(--crit-bg); color: var(--crit); border: 1px solid var(--crit-border);
}

/* Detail rows */
.detail-row { display: none; }
.detail-row.show { display: table-row; }
.detail-row td { background: var(--bg); padding: 4px 10px 10px 20px; }
.ref-table {
    width: 100%; font-size: 0.78rem; border-collapse: collapse;
    background: var(--surface); border-radius: 6px; border: 1px solid var(--border);
}
.ref-table th {
    font-size: 0.68rem; padding: 5px 8px; background: var(--surface2);
    border-bottom: 1px solid var(--border);
}
.ref-table td { padding: 5px 8px; border-bottom: 1px solid var(--border); }
.ref-table tr:last-child td { border-bottom: none; }

.badge {
    display: inline-block; font-size: 0.68rem; padding: 1px 6px;
    border-radius: 3px; font-weight: 600;
}
.b-agreed { background: var(--med-bg); color: var(--med); border: 1px solid var(--med-border); }
.b-completed { background: var(--done-bg); color: var(--done); }
.b-pending { background: var(--high-bg); color: var(--high); border: 1px solid var(--high-border); }
.b-declined { background: var(--muted-bg); color: var(--muted); }
.b-terminated { background: var(--muted-bg); color: var(--muted); }
.b-overdue { background: var(--crit-bg); color: var(--crit); border: 1px solid var(--crit-border); }

/* Journal grid */
.journal-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px;
}
.jcard {
    background: var(--surface); border-radius: 6px; padding: 10px;
    border: 1px solid var(--border);
}
.jcard-name { font-weight: 700; font-size: 0.9rem; margin-bottom: 2px; }
.jcard-platform { font-size: 0.72rem; color: var(--text2); }
.jcard-stats { font-size: 0.78rem; margin-top: 4px; }
.jcard-fresh {
    display: inline-block; font-size: 0.68rem; padding: 1px 6px;
    border-radius: 3px; font-weight: 600; margin-top: 4px;
}
.jcard-fresh.fresh { background: var(--low-bg); color: var(--low); }
.jcard-fresh.aging { background: var(--med-bg); color: var(--med); }
.jcard-fresh.stale { background: var(--crit-bg); color: var(--crit); }

/* Recommendations */
.rec-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; }
.rec-card {
    background: var(--surface); border-radius: 6px; padding: 12px;
    border: 1px solid var(--border);
}
.rec-card h4 { font-size: 0.85rem; margin-bottom: 2px; }
.rec-meta { font-size: 0.72rem; color: var(--text2); margin-bottom: 8px; }
.rec-cand {
    font-size: 0.78rem; padding: 3px 0;
    display: flex; justify-content: space-between; gap: 8px;
}
.rec-name { font-weight: 600; }
.rec-info { font-size: 0.72rem; color: var(--text2); text-align: right; white-space: nowrap; }

/* Collapsible */
.collapsible-hdr {
    cursor: pointer; display: flex; align-items: center; gap: 6px;
}
.collapsible-hdr::before { content: "\\25B8"; font-size: 0.7rem; color: var(--text2); }
.collapsible-hdr.open::before { content: "\\25BE"; }
.collapsible-body { display: none; margin-top: 8px; }
.collapsible-body.show { display: block; }

.footer {
    text-align: center; color: var(--text3); font-size: 0.72rem;
    margin-top: 24px; padding-top: 10px; border-top: 1px solid var(--border);
}
.empty {
    text-align: center; padding: 20px; color: var(--text2);
    font-style: italic; font-size: 0.85rem;
}

/* Journal sections */
.journal-sections { display: flex; flex-direction: column; gap: 14px; }
.jsec {
    border: 1px solid var(--border); border-radius: 8px;
    overflow: hidden; background: var(--surface);
}
.jsec-hdr {
    cursor: pointer; display: flex; align-items: center; gap: 8px;
    padding: 10px 14px; background: var(--surface2);
    border-bottom: 1px solid var(--border);
    font-weight: 700; font-size: 0.9rem; user-select: none;
}
.jsec-hdr::before { content: "\\25BE"; font-size: 0.7rem; color: var(--text2); }
.jsec-hdr.collapsed::before { content: "\\25B8"; }
.jsec-badge {
    font-size: 0.72rem; font-weight: 500; color: var(--accent);
    background: var(--accent-bg); padding: 1px 7px; border-radius: 3px;
    margin-left: auto;
}
.jsec-body { display: block; }
.jsec-body.hidden { display: none; }
.jsec .table-wrap { border: none; border-radius: 0; }

/* Search */
.ms-search {
    width: 100%; padding: 6px 12px; border: 1px solid var(--border);
    border-radius: 6px; font-size: 0.85rem; margin-bottom: 10px;
    background: var(--surface); color: var(--text);
}
.ms-search:focus { outline: none; border-color: var(--accent); }

/* AE Panel (inline) */
.ae-panel {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 20px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;
    z-index: 1000; box-shadow: 0 4px 24px rgba(0,0,0,0.15);
}
.ae-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 999;
}
.ae-panel h3 { font-size: 1rem; margin-bottom: 8px; }
.ae-rec-badge {
    display: inline-block; padding: 3px 10px; border-radius: 4px;
    font-weight: 700; font-size: 0.85rem; margin-bottom: 8px;
}
.ae-accept { background: var(--low-bg); color: var(--low); border: 1px solid var(--low-border); }
.ae-reject { background: var(--crit-bg); color: var(--crit); border: 1px solid var(--crit-border); }
.ae-revise { background: var(--med-bg); color: var(--med); border: 1px solid var(--med-border); }
.ae-panel .ae-summary { color: var(--text2); font-size: 0.85rem; margin: 8px 0; }
.ae-panel ol { margin: 8px 0 8px 20px; font-size: 0.82rem; }
.ae-panel .ae-close {
    position: absolute; top: 10px; right: 14px; cursor: pointer;
    font-size: 1.2rem; color: var(--text2); border: none; background: none;
}

/* Referee card overlay */
.ref-card-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 999; }
.ref-card {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 20px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto;
    z-index: 1000; box-shadow: 0 4px 24px rgba(0,0,0,0.15);
}
.ref-card h3 { font-size: 1rem; margin-bottom: 4px; }
.ref-card .ref-meta { font-size: 0.78rem; color: var(--text2); margin-bottom: 10px; }
.ref-card .ref-stat-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px;
}
.ref-card .ref-stat {
    background: var(--surface2); padding: 6px 10px; border-radius: 4px; font-size: 0.78rem;
}
.ref-card .ref-stat b { display: block; font-size: 0.85rem; }
.ref-card .ref-close {
    position: absolute; top: 10px; right: 14px; cursor: pointer;
    font-size: 1.2rem; color: var(--text2); border: none; background: none;
}
.ref-clickable { cursor: pointer; color: var(--accent); text-decoration: underline; }
.ref-clickable:hover { opacity: 0.8; }

/* Detail sub-sections */
.detail-subsection {
    margin-top: 8px; padding: 8px 10px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 6px; font-size: 0.78rem;
}
.detail-subsection h5 { font-size: 0.75rem; font-weight: 700; margin-bottom: 4px; color: var(--text2); text-transform: uppercase; }

/* Referee intelligence tables */
.ri-table {
    width: 100%; font-size: 0.78rem; border-collapse: collapse;
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
}
.ri-table th {
    font-size: 0.68rem; padding: 5px 8px; background: var(--surface2);
    border-bottom: 1px solid var(--border); text-align: left;
}
.ri-table td { padding: 5px 8px; border-bottom: 1px solid var(--border); }
.ri-table tr:last-child td { border-bottom: none; }

@media (max-width: 768px) {
    body { padding: 12px; font-size: 13px; }
    .action-item { flex-wrap: wrap; }
    .action-extra { display: none; }
    .td-title { max-width: 180px; }
    .rec-grid { grid-template-columns: 1fr; }
}
"""

JS = """
function sortTable(tid, ci) {
    var t = document.getElementById(tid);
    if (!t) return;
    var tb = t.querySelector('tbody');
    var rows = Array.from(tb.querySelectorAll('tr.ms-row'));
    var h = t.querySelectorAll('thead th')[ci];
    var asc = !h.classList.contains('sort-asc');
    t.querySelectorAll('thead th').forEach(function(x) {
        x.classList.remove('sort-asc', 'sort-desc');
    });
    h.classList.add(asc ? 'sort-asc' : 'sort-desc');
    rows.sort(function(a, b) {
        var av = a.cells[ci].getAttribute('data-sort') || a.cells[ci].textContent.trim();
        var bv = b.cells[ci].getAttribute('data-sort') || b.cells[ci].textContent.trim();
        var an = parseFloat(av), bn = parseFloat(bv);
        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    rows.forEach(function(r) {
        var did = r.getAttribute('data-detail');
        tb.appendChild(r);
        if (did) { var d = document.getElementById(did); if (d) tb.appendChild(d); }
    });
}
function toggleDetail(id) {
    var r = document.querySelector('tr[data-detail="d-' + id + '"]');
    var d = document.getElementById('d-' + id);
    if (r && d) { r.classList.toggle('expanded'); d.classList.toggle('show'); }
}
function filterActs(lvl) {
    document.querySelectorAll('.fbtn-priority').forEach(function(b) { b.classList.remove('active'); });
    event.target.classList.add('active');
    document.querySelectorAll('.fbtn-journal').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.action-item').forEach(function(a) {
        a.style.display = (lvl === 'all' || a.classList.contains(lvl)) ? '' : 'none';
    });
}
function filterActsJournal(j) {
    document.querySelectorAll('.fbtn-journal').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.fbtn-priority').forEach(function(b) { b.classList.remove('active'); });
    event.target.classList.add('active');
    document.querySelectorAll('.action-item').forEach(function(a) {
        var aj = a.querySelector('.action-journal');
        a.style.display = (j === 'all' || (aj && aj.textContent.trim() === j)) ? '' : 'none';
    });
}
function searchManuscripts(q) {
    q = q.toLowerCase();
    document.querySelectorAll('.ms-row').forEach(function(r) {
        var id = (r.querySelector('.td-id') || {}).textContent || '';
        var title = (r.querySelector('.td-title') || {}).textContent || '';
        var show = !q || id.toLowerCase().indexOf(q) >= 0 || title.toLowerCase().indexOf(q) >= 0;
        r.style.display = show ? '' : 'none';
        var did = r.getAttribute('data-detail');
        if (did) {
            var d = document.getElementById(did);
            if (d && !show) d.classList.remove('show');
        }
    });
}
function toggleJsec(id) {
    var h = document.getElementById('jh-' + id);
    var b = document.getElementById('jb-' + id);
    if (h && b) { h.classList.toggle('collapsed'); b.classList.toggle('hidden'); }
}
function toggleCollapsible(id) {
    var h = document.querySelector('[data-collapse="' + id + '"]');
    var b = document.getElementById(id);
    if (h && b) { h.classList.toggle('open'); b.classList.toggle('show'); }
}
var API = window.location.origin + '/api';
function _showAEPanel(d) {
    _closeOverlays();
    var rec = (d.recommendation || '').toLowerCase();
    var cls = 'ae-revise';
    if (rec.indexOf('accept') >= 0) cls = 'ae-accept';
    else if (rec.indexOf('reject') >= 0) cls = 'ae-reject';
    var html = '<div class="ae-overlay" onclick="_closeOverlays()"></div>';
    html += '<div class="ae-panel">';
    html += '<button class="ae-close" onclick="_closeOverlays()">&times;</button>';
    html += '<h3>AE Report: ' + (d.manuscript_id || '') + '</h3>';
    html += '<div class="ae-rec-badge ' + cls + '">' + (d.recommendation || 'N/A') + '</div>';
    if (d.confidence) html += ' <span style="font-size:0.78rem;color:var(--text2)">Confidence: ' + d.confidence + '</span>';
    if (d.summary) html += '<div class="ae-summary">' + d.summary + '</div>';
    if (d.revision_points && d.revision_points.length) {
        html += '<ol>';
        d.revision_points.forEach(function(p) { html += '<li>' + p + '</li>'; });
        html += '</ol>';
    }
    if (d.referee_recommendations && d.referee_recommendations.length) {
        html += '<h5 style="margin-top:10px;font-size:0.75rem;color:var(--text2)">REFEREE CONSENSUS</h5>';
        d.referee_recommendations.forEach(function(r) {
            html += '<div style="font-size:0.78rem">' + r.name + ': <b>' + r.recommendation + '</b></div>';
        });
    }
    html += '</div>';
    document.body.insertAdjacentHTML('beforeend', html);
}
function _showAEPastePanel(d, j, m) {
    _closeOverlays();
    var html = '<div class="ae-overlay" onclick="_closeOverlays()"></div>';
    html += '<div class="ae-panel" style="max-width:800px">';
    html += '<button class="ae-close" onclick="_closeOverlays()">&times;</button>';
    html += '<h3>AE Report: ' + _escHtml(d.manuscript_id || m) + '</h3>';
    if (d.referee_recommendations && d.referee_recommendations.length) {
        html += '<h5 style="font-size:0.75rem;color:var(--text2);margin:4px 0">REFEREE CONSENSUS</h5>';
        d.referee_recommendations.forEach(function(r) {
            html += '<div style="font-size:0.78rem">' + _escHtml(r.name) + ': <b>' + _escHtml(r.recommendation) + '</b></div>';
        });
    }
    html += '<div style="margin-top:12px">';
    html += '<p style="font-size:0.78rem;color:var(--text2)"><b>Step 1:</b> Copy the prompt below and paste into ChatGPT Pro</p>';
    html += '<textarea id="ae-prompt-text" style="width:100%;height:120px;font-size:0.72rem;border:1px solid var(--border);border-radius:4px;padding:6px;font-family:monospace" readonly>' + _escHtml(d.prompt || '') + '</textarea>';
    html += '<button class="btn-ae" style="margin-top:4px" onclick="document.getElementById(\'ae-prompt-text\').select();document.execCommand(\'copy\');this.textContent=\'Copied!\'">Copy Prompt</button>';
    html += '</div>';
    html += '<div style="margin-top:12px">';
    html += '<p style="font-size:0.78rem;color:var(--text2)"><b>Step 2:</b> Paste the ChatGPT response below and click Save</p>';
    html += '<textarea id="ae-response-text" style="width:100%;height:150px;font-size:0.78rem;border:1px solid var(--border);border-radius:4px;padding:6px" placeholder="Paste ChatGPT response here..."></textarea>';
    html += '<button class="btn-ae" style="margin-top:4px" onclick="_saveAEResponse(\'' + _escHtml(j) + '\',\'' + _escHtml(m) + '\')">Save Response</button>';
    html += ' <span id="ae-save-status" style="font-size:0.78rem"></span>';
    html += '</div>';
    html += '</div>';
    document.body.insertAdjacentHTML('beforeend', html);
}
function _saveAEResponse(j, m) {
    var responseText = document.getElementById('ae-response-text').value;
    if (!responseText.trim()) { alert('Paste the response first'); return; }
    var status = document.getElementById('ae-save-status');
    status.textContent = 'Saving...';
    fetch(API + '/ae-report/paste', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({journal: j, manuscript_id: m, response: responseText})
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.recommendation) {
            status.textContent = 'Saved: ' + d.recommendation;
            status.style.color = '#22c55e';
            setTimeout(function() { _closeOverlays(); _showAEPanel(d); }, 1000);
        } else {
            status.textContent = 'Saved (paste a structured response for better results)';
        }
    }).catch(function() { status.textContent = 'Error saving'; status.style.color = '#ef4444'; });
}
function _closeOverlays() {
    document.querySelectorAll('.ae-overlay,.ae-panel,.ref-card-overlay,.ref-card').forEach(function(e) { e.remove(); });
}
function generateAE(j, m) {
    var btn = (event && event.target) || this;
    btn.textContent = 'Generating...';
    btn.disabled = true;
    fetch(API + '/ae-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({journal: j, manuscript_id: m})
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.recommendation && d.status !== 'awaiting_paste') {
            btn.textContent = d.recommendation;
            btn.classList.add('btn-done');
            _showAEPanel(d);
        } else if (d.status === 'awaiting_paste' || d.prompt) {
            btn.textContent = 'Paste Response';
            btn.classList.add('btn-view');
            _showAEPastePanel(d, j, m);
        } else {
            btn.textContent = 'Error';
        }
    }).catch(function() {
        btn.textContent = 'Server offline';
        btn.disabled = false;
    });
}
function viewAE(j, m) {
    fetch(API + '/ae-reports/' + j + '/' + m)
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.error) return;
        if (d.status === 'awaiting_paste' || (!d.recommendation && d.prompt)) {
            _showAEPastePanel(d, j, m);
        } else {
            _showAEPanel(d);
        }
    }).catch(function() {});
}
function showRefereeCard(name) {
    fetch(API + '/referee/' + encodeURIComponent(name))
    .then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.error) return;
        _closeOverlays();
        var html = '<div class="ref-card-overlay" onclick="_closeOverlays()"></div>';
        html += '<div class="ref-card">';
        html += '<button class="ref-close" onclick="_closeOverlays()">&times;</button>';
        html += '<h3>' + (d.display_name || name) + '</h3>';
        var meta = [];
        if (d.email) meta.push(d.email);
        if (d.institution) meta.push(d.institution);
        if (d.orcid) meta.push('ORCID: ' + d.orcid);
        html += '<div class="ref-meta">' + meta.join(' · ') + '</div>';
        var total = d.total_invitations || 0;
        var acc = total ? ((d.total_accepted || 0) / total * 100).toFixed(0) : '—';
        var comp = d.total_accepted ? ((d.total_completed || 0) / d.total_accepted * 100).toFixed(0) : '—';
        html += '<div class="ref-stat-grid">';
        html += '<div class="ref-stat"><b>' + total + '</b>Invitations</div>';
        html += '<div class="ref-stat"><b>' + acc + '%</b>Accept rate</div>';
        html += '<div class="ref-stat"><b>' + comp + '%</b>Completion</div>';
        html += '<div class="ref-stat"><b>' + (d.avg_review_days ? d.avg_review_days.toFixed(0) + 'd' : '—') + '</b>Avg review</div>';
        html += '<div class="ref-stat"><b>' + (d.overdue_rate ? (d.overdue_rate * 100).toFixed(0) + '%' : '0%') + '</b>Overdue rate</div>';
        html += '<div class="ref-stat"><b>' + ((d.journals_served || []).join(', ') || '—') + '</b>Journals</div>';
        html += '</div>';
        if (d.assignments && d.assignments.length) {
            html += '<h5 style="font-size:0.72rem;color:var(--text2);margin:8px 0 4px">RECENT ASSIGNMENTS</h5>';
            html += '<table class="ri-table"><thead><tr><th>Journal</th><th>Manuscript</th><th>Response</th><th>Days</th></tr></thead><tbody>';
            d.assignments.slice(0, 8).forEach(function(a) {
                html += '<tr><td>' + (a.journal||'').toUpperCase() + '</td><td>' + (a.manuscript_id||'') + '</td>';
                html += '<td>' + (a.response||'') + '</td><td>' + (a.days_to_complete || '—') + '</td></tr>';
            });
            html += '</tbody></table>';
        }
        html += '<div style="margin-top:8px"><b>Notes:</b><br>';
        var noteId = 'ref-note-' + name.replace(/[^a-zA-Z0-9]/g, '_');
        html += '<textarea id="' + noteId + '" style="width:100%;height:60px;font-size:0.78rem;border:1px solid var(--border);border-radius:4px;padding:4px">' + _escHtml(d.notes || '') + '</textarea>';
        html += '<button class="btn-ae" style="margin-top:4px" onclick="saveRefereeNote(\'' + name.replace(/'/g, "\\\\'") + '\')">Save Note</button></div>';
        html += '</div>';
        document.body.insertAdjacentHTML('beforeend', html);
    }).catch(function() {});
}
function runPipeline(j, m) {
    var btn = event.target;
    btn.textContent = 'Running...';
    btn.disabled = true;
    fetch(API + '/pipeline/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({journal: j, manuscript_id: m})
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        btn.textContent = d.status === 'started' ? 'Started' : 'Error';
    }).catch(function() {
        btn.textContent = 'Offline';
        btn.disabled = false;
    });
}
function _escHtml(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.appendChild(document.createTextNode(s));
    return d.innerHTML;
}
function recordDecision(j, m) {
    var sel = document.getElementById('dec-' + m);
    if (!sel || !sel.value) { alert('Select a decision first'); return; }
    var btn = (event && event.target) || this;
    if (btn) { btn.disabled = true; btn.textContent = 'Submitting...'; }
    fetch(API + '/record-decision', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({journal: j, manuscript_id: m, decision: sel.value})
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        if (btn) { btn.textContent = d.status === 'ok' ? 'Recorded' : 'Error'; if (d.status === 'ok') btn.classList.add('btn-done'); }
    });
}
function checkAuthorHistory(msId) {
    var div = document.getElementById('author-hist-' + msId);
    if (!div) return;
    div.style.display = 'block';
    div.innerHTML = 'Loading...';
    fetch(API + '/manuscripts/search?q=' + encodeURIComponent(msId))
    .then(function(r) { return r.json(); })
    .then(function(results) {
        if (results.length > 0 && results[0].authors && results[0].authors.length > 0) {
            return fetch(API + '/author-history/' + encodeURIComponent(results[0].authors[0]));
        }
        div.innerHTML = 'No author data available';
        return null;
    })
    .then(function(r) { return r ? r.json() : []; })
    .then(function(hist) {
        if (!hist || hist.length === 0) { div.innerHTML = 'No cross-journal submissions found'; return; }
        var html = '<b>Author submissions across journals:</b><ul style="margin:4px 0;padding-left:16px">';
        hist.forEach(function(h) { html += '<li>' + _escHtml(h.journal) + '/' + _escHtml(h.manuscript_id) + ' - ' + _escHtml((h.title||'').substr(0,60)) + ' [' + _escHtml(h.status||'') + ']</li>'; });
        html += '</ul>';
        div.innerHTML = html;
    });
}
function sendAllReminders() {
    if (!confirm('Send reminder emails to all overdue referees?')) return;
    var btn = (event && event.target) || this;
    if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }
    fetch(API + '/send-reminders', { method: 'POST' })
    .then(function(r) { return r.json(); })
    .then(function(d) {
        alert('Sent: ' + (d.reminders_sent || 0) + ' reminders');
        if (btn) { btn.textContent = 'Done'; btn.classList.add('btn-done'); }
    });
}
function saveRefereeNote(name) {
    var ta = document.getElementById('ref-note-' + name.replace(/[^a-zA-Z0-9]/g, '_'));
    if (!ta) return;
    fetch(API + '/referee/' + encodeURIComponent(name) + '/note', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({note: ta.value})
    }).then(function(r) { return r.json(); })
    .then(function(d) { if (d.status === 'ok') alert('Note saved'); });
}
function generateAnnualReport() {
    var s = document.getElementById('report-start').value;
    var e = document.getElementById('report-end').value;
    if (!s || !e) { alert('Select date range'); return; }
    var out = document.getElementById('annual-report-output');
    out.innerHTML = 'Generating...';
    fetch(API + '/annual-report', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({start_date: s, end_date: e})
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.error) { out.innerHTML = 'Error: ' + _escHtml(d.error); return; }
        var html = '<b>Report: ' + _escHtml(s) + ' to ' + _escHtml(e) + '</b><br>';
        if (d.summary) {
            html += 'Total manuscripts: ' + (d.summary.total_manuscripts || 0) + '<br>';
            html += 'Journals active: ' + (d.summary.journals_active || 0) + '<br>';
        }
        out.innerHTML = html;
    });
}
"""


def generate_html(data):
    totals = data["totals"]
    items = data["action_items"]
    journals = data["journals"]
    recommendations = data["recommendations"]
    training = data.get("training")

    h = []

    h.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    h.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    h.append("<title>Editorial Command Center</title>")
    h.append(f"<style>{CSS}</style></head><body>")

    h.append("<h1>Editorial Command Center</h1>")
    h.append(f"<div class='subtitle'>{_esc(data['generated_at'])}</div>")

    try:
        from reporting.action_items import get_seasonal_mode

        seasonal = get_seasonal_mode()
    except Exception:
        seasonal = None

    if totals["critical"] > 0:
        cls = "alert-crit"
        msg = f"🔴 {totals['critical']} critical + {totals['high']} high priority items"
    elif totals["high"] > 0:
        cls = "alert-high"
        msg = f"🟠 {totals['high']} high priority items"
    else:
        cls = "alert-ok"
        msg = "✅ All clear — no action needed"
    if seasonal:
        msg += f" · {seasonal['label']}"
    h.append(f"<div class='alert {cls}'>{msg}</div>")

    h.append("<div class='stats'>")
    h.append(f"<span class='stat'><b>{totals['active_manuscripts']}</b> manuscripts</span>")
    h.append(f"<span class='stat'><b>{totals['action_items']}</b> actions</span>")
    h.append(f"<span class='stat'><b>{totals['active_journals']}</b> journals</span>")
    h.append(f"<span class='stat'><b>{totals['referees']}</b> active refs</span>")
    h.append("</div>")

    # ── Action Items ──────────────────────────────────────────────
    h.append("<div class='section'>")
    h.append("<div class='section-hdr'>Action Items</div>")

    if items:
        counts = {}
        for it in items:
            counts[it["priority"]] = counts.get(it["priority"], 0) + 1

        h.append("<div class='filters'>")
        h.append(
            "<button class='fbtn fbtn-priority active' onclick='filterActs(\"all\")'>All</button>"
        )
        for lvl, css in [
            ("critical", "p-crit"),
            ("high", "p-high"),
            ("medium", "p-med"),
            ("low", "p-low"),
        ]:
            if counts.get(lvl, 0):
                h.append(
                    f"<button class='fbtn fbtn-priority' onclick='filterActs(\"{css}\")'>"
                    f"{lvl.title()} ({counts[lvl]})</button>"
                )
        journals_in_items = sorted({it["journal"] for it in items})
        if len(journals_in_items) > 1:
            h.append("<span style='border-left:1px solid var(--border);margin:0 4px'></span>")
            for j in journals_in_items:
                h.append(
                    f"<button class='fbtn fbtn-journal' "
                    f"onclick='filterActsJournal(\"{_esc(j)}\")'>{_esc(j)}</button>"
                )
        h.append("</div>")

        type_labels = {
            "overdue_report": "OVERDUE",
            "needs_ae_decision": "DECISION",
            "ae_report_ready": "AE READY",
            "pending_invitation": "NO REPLY",
            "needs_more_referees": "FEW REFS",
            "due_soon": "DUE SOON",
            "needs_assignment": "ASSIGN",
        }
        pmap = {"critical": "crit", "high": "high", "medium": "med", "low": "low"}

        h.append("<div class='action-list'>")
        for it in items:
            p = pmap.get(it["priority"], "low")
            label = type_labels.get(it["action_type"], it["action_type"])

            extra_parts = []
            if it.get("due_date"):
                extra_parts.append(f"due {it['due_date']}")
            if it.get("reminders_sent"):
                extra_parts.append(f"{it['reminders_sent']} rem")
            extra = " · ".join(extra_parts)

            h.append(f"<div class='action-item p-{p} {p}'>")
            h.append(f"<span class='action-type t-{p}'>{label}</span>")
            h.append(f"<span class='action-journal'>{_esc(it['journal'])}</span>")
            h.append(f"<span class='action-msid'>{_esc(it['manuscript_id'])}</span>")
            h.append(f"<span class='action-msg'>{_esc(it['message'])}</span>")
            if extra:
                h.append(f"<span class='action-extra'>{_esc(extra)}</span>")
            if it["action_type"] == "needs_ae_decision":
                j = it["journal"].lower()
                m = _esc(it["manuscript_id"])
                h.append(
                    f"<button class='btn-ae' onclick=\"generateAE('{j}','{m}')\">"
                    f"Generate AE Report</button>"
                )
            elif it["action_type"] == "ae_report_ready":
                j = it["journal"].lower()
                m = _esc(it["manuscript_id"])
                h.append(
                    f"<button class='btn-ae btn-view' onclick=\"viewAE('{j}','{m}')\">"
                    f"View Report</button>"
                )
            h.append("</div>")
        h.append(
            "<button class='btn-ae' style='margin-top:6px' onclick='sendAllReminders()'>Send All Reminders</button>"
        )
        h.append("</div>")
    else:
        h.append("<div class='empty'>No action items — all clear</div>")
    h.append("</div>")

    # ── Active Manuscripts ────────────────────────────────────────
    h.append("<div class='section'>")
    h.append("<div class='section-hdr'>Active Manuscripts</div>")
    h.append(
        "<input type='text' class='ms-search' placeholder='Search by manuscript ID or title...' "
        "oninput='searchManuscripts(this.value)'>"
    )

    ms_by_journal = data.get("manuscripts_by_journal", {})
    if ms_by_journal:
        h.append("<div class='journal-sections'>")
        for journal_code in sorted(ms_by_journal.keys()):
            j_manuscripts = ms_by_journal[journal_code]
            j_name = JOURNAL_NAMES.get(journal_code.lower(), journal_code)
            j_slug = journal_code.lower().replace(" ", "")
            tid = f"ms-table-{j_slug}"

            h.append("<div class='jsec'>")
            h.append(
                f"<div class='jsec-hdr' id='jh-{j_slug}' onclick=\"toggleJsec('{j_slug}')\">"
                f"{_esc(journal_code)} — {_esc(j_name)}"
                f"<span class='jsec-badge'>{len(j_manuscripts)}</span></div>"
            )
            h.append(f"<div class='jsec-body' id='jb-{j_slug}'>")
            h.append("<div class='table-wrap'>")
            h.append(f"<table id='{tid}'>")
            h.append("<colgroup>")
            h.append("<col style='width:28%'>")
            h.append("<col style='width:30%'>")
            h.append("<col style='width:18%'>")
            h.append("<col style='width:8%'>")
            h.append("<col style='width:10%'>")
            h.append("<col style='width:6%'>")
            h.append("</colgroup>")
            h.append("<thead><tr>")
            for i, col in enumerate(["Manuscript", "Title", "Status", "Rpts", "Due", "Days"]):
                h.append(f"<th onclick=\"sortTable('{tid}',{i})\">{col}</th>")
            h.append("</tr></thead><tbody>")

            for ms in j_manuscripts:
                safe_id = ms["manuscript_id"].replace(".", "_").replace("-", "_")

                completed = ms["referees_completed"]
                agreed = ms["referees_agreed"]
                pending = ms["referees_pending_response"]
                total_assigned = completed + agreed + pending
                rpt_str = f"{completed}/{total_assigned}" if total_assigned > 0 else "—"

                if ms.get("days_until_next_due") is not None:
                    dd = ms["days_until_next_due"]
                    if dd < 0:
                        due_cls = "overdue"
                        due_str = f"{abs(dd)}d overdue"
                    elif dd <= 14:
                        due_cls = "due-soon"
                        due_str = f"{dd}d"
                    else:
                        due_cls = "on-track"
                        due_str = f"{dd}d"
                else:
                    due_cls = ""
                    due_str = "—"

                din = ms.get("days_in_system") or "—"

                flags_html = ""
                if ms["needs_ae_decision"]:
                    flags_html += " <span class='flag'>Decision</span>"

                status_display = ms["status"]

                sort_due = (
                    ms.get("days_until_next_due")
                    if ms.get("days_until_next_due") is not None
                    else 9999
                )

                h.append(
                    f"<tr class='ms-row' data-detail='d-{safe_id}' "
                    f"onclick=\"toggleDetail('{safe_id}')\">"
                )
                h.append(
                    f"<td class='td-id' data-sort='{_esc(ms['manuscript_id'])}'>"
                    f"{_esc(ms['manuscript_id'])}</td>"
                )
                h.append(
                    f"<td class='td-title' title='{_esc(ms['title'])}'>{_esc(ms['title'])}</td>"
                )
                h.append(f"<td class='td-status'>{_esc(status_display)}{flags_html}</td>")
                h.append(f"<td class='td-reports' data-sort='{completed}'>{rpt_str}</td>")
                h.append(
                    f"<td class='td-due' data-sort='{sort_due}'>"
                    f"<span class='{due_cls}'>{due_str}</span></td>"
                )
                h.append(
                    f"<td class='td-days' data-sort='{ms.get('days_in_system', 0)}'>{din}</td>"
                )
                h.append("</tr>")

                ref_details = ms.get("referee_details", [])
                h.append(f"<tr class='detail-row' id='d-{safe_id}'><td colspan='6'>")
                if ref_details:
                    h.append("<table class='ref-table'><thead><tr>")
                    h.append(
                        "<th>Referee</th><th>Status</th><th>Invited</th>"
                        "<th>Agreed</th><th>Due</th><th>Returned</th>"
                        "<th>Rem</th><th>Timeline</th>"
                    )
                    h.append("</tr></thead><tbody>")
                    for rd in ref_details:
                        st = rd["normalized_status"]
                        if rd.get("days_overdue"):
                            badge_cls = "b-overdue"
                        elif st == "completed":
                            badge_cls = "b-completed"
                        elif st == "agreed":
                            badge_cls = "b-agreed"
                        elif st == "pending":
                            badge_cls = "b-pending"
                        elif st in ("declined", "terminated"):
                            badge_cls = "b-" + st
                        else:
                            badge_cls = ""

                        timeline = ""
                        if rd.get("days_overdue"):
                            timeline = f"<span class='overdue'>{rd['days_overdue']}d overdue</span>"
                        elif rd.get("days_remaining") is not None:
                            d = rd["days_remaining"]
                            cls = "due-soon" if d <= 14 else "on-track"
                            timeline = f"<span class='{cls}'>{d}d left</span>"
                        elif st == "completed":
                            timeline = "✓ done"
                        elif st in ("declined", "terminated"):
                            timeline = "—"

                        ref_name_esc = _esc(rd["name"])
                        h.append("<tr>")
                        h.append(
                            f"<td><span class='ref-clickable' "
                            f"onclick=\"showRefereeCard('{ref_name_esc}')\">"
                            f"{ref_name_esc}</span></td>"
                        )
                        h.append(f"<td><span class='badge {badge_cls}'>{_esc(st)}</span></td>")
                        h.append(f"<td>{_esc(rd.get('invited') or '—')}</td>")
                        h.append(f"<td>{_esc(rd.get('agreed') or '—')}</td>")
                        h.append(f"<td>{_esc(rd.get('due') or '—')}</td>")
                        h.append(f"<td>{_esc(rd.get('returned') or '—')}</td>")
                        h.append(f"<td>{rd.get('reminders', 0)}</td>")
                        h.append(f"<td>{timeline}</td>")
                        h.append("</tr>")
                    h.append("</tbody></table>")
                else:
                    h.append("<div class='empty' style='padding:8px'>No referees assigned</div>")

                rec_by_ms = data.get("rec_by_ms", {})
                rec_key = (journal_code.lower(), ms["manuscript_id"])
                rec_data = rec_by_ms.get(rec_key)
                if rec_data:
                    dr = rec_data.get("desk_rejection", {})
                    candidates = rec_data.get("candidates", [])
                    if dr:
                        verdict = dr.get("verdict", "")
                        conf = dr.get("confidence", "")
                        h.append("<div class='detail-subsection'>")
                        h.append("<h5>Desk Rejection Assessment</h5>")
                        h.append(
                            f"<span class='badge {'b-completed' if verdict == 'no' else 'b-overdue'}'>"
                            f"{_esc(verdict or 'N/A')}</span> "
                            f"<span style='font-size:0.72rem;color:var(--text2)'>"
                            f"Confidence: {_esc(str(conf))}</span>"
                        )
                        h.append("</div>")
                    if candidates:
                        h.append("<div class='detail-subsection'>")
                        h.append("<h5>Recommended Referees</h5>")
                        for i, c in enumerate(candidates[:3]):
                            hi = c.get("h_index") or "?"
                            inst = c.get("institution") or ""
                            sc = c.get("score", 0)
                            h.append(
                                f"<div class='rec-cand'>"
                                f"<span class='rec-name'>#{i + 1} {_esc(c['name'])}</span>"
                                f"<span class='rec-info'>"
                                f"{_esc(inst)}{' · ' if inst else ''}h={hi} · {sc:.2f}</span></div>"
                            )
                        h.append("</div>")
                elif ms.get("needs_referee_assignment"):
                    j_lower = journal_code.lower()
                    ms_id_esc = _esc(ms["manuscript_id"])
                    h.append("<div class='detail-subsection'>")
                    h.append(
                        f"<button class='btn-ae' onclick=\"runPipeline('{j_lower}','{ms_id_esc}')\">"
                        f"Find Referees</button>"
                    )
                    h.append("</div>")

                h.append("<div class='detail-subsection'>")
                h.append("<h5>Record Decision</h5>")
                j_esc = _esc(journal_code.lower())
                ms_esc = _esc(ms["manuscript_id"])
                h.append(
                    f"<select id='dec-{ms_esc}' class='rate-select' style='width:auto;font-size:0.78rem'>"
                    f"<option value=''>Select...</option>"
                    f"<option value='accept'>Accept</option>"
                    f"<option value='minor_revision'>Minor Revision</option>"
                    f"<option value='major_revision'>Major Revision</option>"
                    f"<option value='reject'>Reject</option>"
                    f"</select> "
                    f"<button class='btn-ae' onclick=\"recordDecision('{j_esc}','{ms_esc}')\">Submit</button>"
                )
                h.append("</div>")

                h.append("<div class='detail-subsection'>")
                h.append(
                    f"<button class='btn-ae btn-view' onclick=\"checkAuthorHistory('{ms_esc}')\">Check Author History</button>"
                )
                h.append(
                    f"<div id='author-hist-{ms_esc}' style='display:none;font-size:0.78rem;margin-top:4px'></div>"
                )
                h.append("</div>")

                h.append("</td></tr>")

            h.append("</tbody></table></div>")
            h.append("</div></div>")
        h.append("</div>")
    else:
        h.append("<div class='empty'>No active manuscripts</div>")
    h.append("</div>")

    # ── Journal Overview ──────────────────────────────────────────
    h.append("<div class='section'>")
    h.append("<div class='section-hdr'>Journal Overview</div>")
    h.append("<div class='journal-grid'>")
    for js in journals:
        j = js["journal"].upper()
        n_ms = js.get("manuscripts", 0)
        n_ref = js.get("referees", 0)
        fc = js.get("freshness_class", "stale")
        fl = js.get("freshness_label", "No data")
        h.append("<div class='jcard'>")
        h.append(f"<div class='jcard-name'>{_esc(j)}</div>")
        h.append(f"<div class='jcard-platform'>{_esc(js.get('platform', ''))}</div>")
        h.append(f"<div class='jcard-stats'>{n_ms} mss · {n_ref} refs</div>")
        h.append(f"<span class='jcard-fresh {fc}'>{_esc(fl)}</span>")
        h.append("</div>")
    h.append("</div></div>")

    # ── Pipeline Recommendations ──────────────────────────────────
    if recommendations:
        h.append("<div class='section'>")
        h.append("<div class='section-hdr'>Pipeline Recommendations</div>")
        h.append("<div class='rec-grid'>")
        for rec in recommendations:
            h.append("<div class='rec-card'>")
            h.append(f"<h4>{_esc(rec['journal'])} / {_esc(rec['manuscript_id'])}</h4>")
            h.append(
                f"<div class='rec-meta'>{_esc(rec['title'])} · {_esc(rec['generated_at'])}</div>"
            )
            for i, c in enumerate(rec.get("candidates", [])):
                hi = c.get("h_index") or "?"
                inst = c.get("institution") or ""
                score = c.get("score") or 0
                info_parts = []
                if inst:
                    info_parts.append(inst)
                info_parts.append(f"h={hi}")
                info_parts.append(f"{score:.2f}")
                info_str = " · ".join(info_parts)
                h.append(
                    f"<div class='rec-cand'>"
                    f"<span class='rec-name'>#{i + 1} {_esc(c['name'])}</span>"
                    f"<span class='rec-info'>{_esc(info_str)}</span></div>"
                )
            h.append("</div>")
        h.append("</div></div>")

    # ── Referee Intelligence ────────────────────────────────────────
    ri = data.get("referee_intelligence", {})
    ri_top = ri.get("top", [])
    ri_decl = ri.get("decliners", [])
    ri_overdue = ri.get("overdue", [])
    if ri_top or ri_decl or ri_overdue:
        h.append("<div class='section'>")
        h.append(
            "<div class='collapsible-hdr' data-collapse='ref-intel' "
            "onclick=\"toggleCollapsible('ref-intel')\">"
            "<span class='section-hdr' style='border:none;margin:0;padding:0'>"
            "Referee Intelligence</span></div>"
        )
        h.append("<div class='collapsible-body' id='ref-intel'>")

        if ri_top:
            h.append(
                "<h5 style='font-size:0.75rem;color:var(--text2);margin:8px 0 4px'>TOP PERFORMERS</h5>"
            )
            h.append("<div class='table-wrap'><table class='ri-table'>")
            h.append(
                "<thead><tr><th>Name</th><th>Institution</th><th>Inv</th>"
                "<th>Accept%</th><th>Avg Days</th><th>Quality</th><th>Journals</th></tr></thead><tbody>"
            )
            for r in ri_top[:10]:
                total = r.get("total_invitations", 0)
                acc = f"{r['total_accepted'] / total * 100:.0f}%" if total else "—"
                avg_d = f"{r['avg_review_days']:.0f}" if r.get("avg_review_days") else "—"
                qual = f"{r['avg_report_quality']:.2f}" if r.get("avg_report_quality") else "—"
                journals = ", ".join(
                    j.upper()
                    for j in (
                        json.loads(r["journals_served"])
                        if isinstance(r.get("journals_served"), str)
                        else (r.get("journals_served") or [])
                    )
                )
                name_esc = _esc(r.get("display_name", ""))
                h.append(
                    f"<tr><td><span class='ref-clickable' onclick=\"showRefereeCard('{name_esc}')\">"
                    f"{name_esc}</span></td>"
                    f"<td>{_esc(r.get('institution') or '')}</td>"
                    f"<td>{total}</td><td>{acc}</td><td>{avg_d}</td><td>{qual}</td>"
                    f"<td>{_esc(journals)}</td></tr>"
                )
            h.append("</tbody></table></div>")

        if ri_decl:
            h.append(
                "<h5 style='font-size:0.75rem;color:var(--text2);margin:12px 0 4px'>CHRONIC DECLINERS</h5>"
            )
            h.append("<div class='table-wrap'><table class='ri-table'>")
            h.append(
                "<thead><tr><th>Name</th><th>Institution</th><th>Inv</th>"
                "<th>Declined</th><th>Decline%</th></tr></thead><tbody>"
            )
            for r in ri_decl[:10]:
                total = r.get("total_invitations", 0)
                decl = r.get("total_declined", 0)
                pct = f"{decl / total * 100:.0f}%" if total else "—"
                name_esc = _esc(r.get("display_name", ""))
                h.append(
                    f"<tr><td>{name_esc}</td>"
                    f"<td>{_esc(r.get('institution') or '')}</td>"
                    f"<td>{total}</td><td>{decl}</td><td>{pct}</td></tr>"
                )
            h.append("</tbody></table></div>")

        if ri_overdue:
            h.append(
                "<h5 style='font-size:0.75rem;color:var(--text2);margin:12px 0 4px'>OVERDUE REPEAT OFFENDERS</h5>"
            )
            h.append("<div class='table-wrap'><table class='ri-table'>")
            h.append(
                "<thead><tr><th>Name</th><th>Institution</th><th>Overdue</th>"
                "<th>Overdue%</th><th>Avg Days</th></tr></thead><tbody>"
            )
            for r in ri_overdue[:10]:
                rate = f"{r['overdue_rate'] * 100:.0f}%" if r.get("overdue_rate") else "—"
                avg_d = f"{r['avg_review_days']:.0f}" if r.get("avg_review_days") else "—"
                name_esc = _esc(r.get("display_name", ""))
                h.append(
                    f"<tr><td>{name_esc}</td>"
                    f"<td>{_esc(r.get('institution') or '')}</td>"
                    f"<td>{r.get('overdue_count', 0)}</td><td>{rate}</td><td>{avg_d}</td></tr>"
                )
            h.append("</tbody></table></div>")

        h.append("</div></div>")

    # ── Model Health (collapsed) ──────────────────────────────────
    if training:
        h.append("<div class='section'>")
        h.append(
            "<div class='collapsible-hdr' data-collapse='model-health' "
            "onclick=\"toggleCollapsible('model-health')\">"
            "<span class='section-hdr' style='border:none;margin:0;padding:0'>"
            "Model Health</span></div>"
        )
        h.append("<div class='collapsible-body' id='model-health'>")
        h.append("<div class='journal-grid'>")
        for mk, ml in [
            ("expertise_index", "Expertise Index"),
            ("response_predictor", "Response Predictor"),
            ("outcome_predictor", "Outcome Predictor"),
        ]:
            m = training.get(mk, {})
            st = m.get("status", "not_trained")
            h.append("<div class='jcard'>")
            h.append(f"<div class='jcard-name'>{_esc(ml)}</div>")
            h.append(f"<div class='jcard-platform'>Status: {_esc(st)}</div>")
            if m.get("cv_accuracy"):
                h.append(f"<div class='jcard-stats'>CV: {m['cv_accuracy']:.1%}</div>")
            if m.get("n_referees"):
                h.append(f"<div class='jcard-stats'>{m['n_referees']} refs</div>")
            if m.get("n_samples"):
                h.append(f"<div class='jcard-stats'>{m['n_samples']} samples</div>")
            h.append("</div>")
        h.append("</div></div></div>")

    h.append("<div class='section'>")
    h.append(
        "<div class='collapsible-hdr' data-collapse='reports' onclick=\"toggleCollapsible('reports')\"><span class='section-hdr' style='border:none;margin:0;padding:0'>Reports</span></div>"
    )
    h.append("<div class='collapsible-body' id='reports'>")
    h.append("<div style='display:flex;gap:8px;align-items:center;margin-bottom:8px'>")
    h.append(
        "<input type='date' id='report-start' style='font-size:0.78rem;padding:4px;border:1px solid var(--border);border-radius:4px'>"
    )
    h.append(" to ")
    h.append(
        "<input type='date' id='report-end' style='font-size:0.78rem;padding:4px;border:1px solid var(--border);border-radius:4px'>"
    )
    h.append(" <button class='btn-ae' onclick='generateAnnualReport()'>Generate Report</button>")
    h.append("</div>")
    h.append("<div id='annual-report-output' style='font-size:0.78rem'></div>")
    h.append("</div></div>")

    h.append("<div class='footer'>")
    h.append(f"{_esc(data['generated_at'])} · {_esc(data['git_commit'])} · Editorial Scripts")
    h.append("</div>")

    h.append(f"<script>{JS}</script></body></html>")
    return "\n".join(h)


def main():
    data = build_dashboard_data()
    html = generate_html(data)
    out_path = OUTPUTS_DIR / "dashboard.html"
    with open(out_path, "w") as f:
        f.write(html)

    totals = data["totals"]
    print(f"Dashboard generated: {out_path}")
    print(
        f"  Action items: {totals['action_items']} "
        f"({totals['critical']} critical, {totals['high']} high)"
    )
    print(f"  Active manuscripts: {totals['active_manuscripts']}")
    print(f"  Journals: {totals['active_journals']}/8")
    if data["recommendations"]:
        print(f"  Recommendations: {len(data['recommendations'])}")


if __name__ == "__main__":
    main()
