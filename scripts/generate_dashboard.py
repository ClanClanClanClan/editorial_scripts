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


def _freshness_class(age_days):
    if age_days is None:
        return "stale-grey"
    if age_days <= 7:
        return "fresh-green"
    if age_days <= 14:
        return "fresh-amber"
    return "fresh-red"


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
        parts = sorted(set(p for p in parts if len(p) > 2), key=len, reverse=True)
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
    if len(inst) > 35:
        inst = inst[:33] + "…"
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
                    "freshness_class": "stale-grey",
                    "freshness_label": "No data",
                    "age_days": None,
                    "extraction_date": None,
                }
            )

    action_items = compute_action_items()
    manuscript_summaries = compute_manuscript_summaries()
    recommendations = _load_recent_recommendations(limit=8)
    training = _load_training_metadata()

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

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "git_commit": _git_commit(),
        "journals": journal_stats,
        "totals": totals,
        "action_items": [asdict(a) for a in action_items],
        "manuscripts": [asdict(s) for s in manuscript_summaries],
        "recommendations": rec_summaries,
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
    --bg: #f8fafc; --surface: #fff; --surface2: #f1f5f9; --text: #1e293b;
    --text2: #64748b; --border: #e2e8f0; --accent: #3b82f6; --accent-bg: #eff6ff;
    --crit: #dc2626; --crit-bg: #fef2f2; --crit-border: #fca5a5;
    --high: #ea580c; --high-bg: #fff7ed; --high-border: #fdba74;
    --med: #b45309; --med-bg: #fffbeb; --med-border: #fcd34d;
    --low: #16a34a; --low-bg: #f0fdf4; --low-border: #86efac;
    --done: #059669; --done-bg: #ecfdf5;
    --muted: #94a3b8; --muted-bg: #f1f5f9;
    --radius: 8px; --shadow: 0 1px 2px rgba(0,0,0,.06);
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0c1222; --surface: #1a2332; --surface2: #243044; --text: #e2e8f0;
        --text2: #94a3b8; --border: #2d3d52; --accent: #60a5fa; --accent-bg: #1e3a5f;
        --crit: #f87171; --crit-bg: #2d1215; --crit-border: #7f1d1d;
        --high: #fb923c; --high-bg: #2d1a0a; --high-border: #7c2d12;
        --med: #fbbf24; --med-bg: #2d2305; --med-border: #78350f;
        --low: #4ade80; --low-bg: #0d2818; --low-border: #14532d;
        --done: #34d399; --done-bg: #0d2818;
        --muted: #64748b; --muted-bg: #1e293b;
        --shadow: 0 1px 2px rgba(0,0,0,.2);
    }
}
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
    background: var(--bg); color: var(--text); font-size: 13px; line-height: 1.4;
    padding: 16px 20px; max-width: 1200px; margin: 0 auto; }

.hdr { text-align: center; margin-bottom: 16px; }
.hdr h1 { font-size: 1.3rem; font-weight: 700; letter-spacing: -0.02em; }
.hdr .sub { color: var(--text2); font-size: 0.75rem; margin-top: 2px; }

.alert { padding: 10px 16px; border-radius: var(--radius); margin-bottom: 14px;
    font-weight: 600; font-size: 0.85rem; border: 1.5px solid; display: flex; align-items: center; gap: 8px; }
.alert-crit { background: var(--crit-bg); border-color: var(--crit-border); color: var(--crit); }
.alert-high { background: var(--high-bg); border-color: var(--high-border); color: var(--high); }
.alert-ok { background: var(--low-bg); border-color: var(--low-border); color: var(--low); }

.pills { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; margin-bottom: 16px; }
.pill { background: var(--surface); border: 1px solid var(--border); border-radius: 16px;
    padding: 4px 12px; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 4px; }
.pill b { font-size: 0.85rem; }

.sec { margin-bottom: 20px; }
.sec-title { font-size: 0.9rem; font-weight: 700; margin-bottom: 8px;
    padding-bottom: 4px; border-bottom: 2px solid var(--border); }

/* Action items */
.acts { display: flex; flex-direction: column; gap: 4px; }
.act { display: grid; grid-template-columns: 60px 44px auto 1fr auto; align-items: center;
    gap: 8px; padding: 6px 10px; border-radius: 5px; border-left: 3px solid;
    font-size: 0.8rem; background: var(--surface); }
.act.crit { border-left-color: var(--crit); background: var(--crit-bg); }
.act.high { border-left-color: var(--high); background: var(--high-bg); }
.act.med { border-left-color: var(--med); background: var(--med-bg); }
.act.low { border-left-color: var(--low); background: var(--low-bg); }
.act-badge { font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    padding: 1px 6px; border-radius: 3px; text-align: center; color: #fff; white-space: nowrap; }
.act-badge.crit { background: var(--crit); }
.act-badge.high { background: var(--high); }
.act-badge.med { background: var(--med); }
.act-badge.low { background: var(--low); }
.act-j { font-size: 0.7rem; font-weight: 600; color: var(--accent);
    background: var(--accent-bg); padding: 1px 5px; border-radius: 3px; text-align: center; }
.act-ms { font-weight: 600; white-space: nowrap; font-size: 0.78rem; }
.act-msg { color: var(--text); }
.act-meta { color: var(--text2); font-size: 0.72rem; white-space: nowrap; text-align: right; }

.filter-row { display: flex; gap: 4px; margin-bottom: 8px; flex-wrap: wrap; }
.fbtn { border: 1px solid var(--border); background: var(--surface); color: var(--text);
    padding: 2px 10px; border-radius: 12px; font-size: 0.72rem; cursor: pointer; }
.fbtn.on { background: var(--accent); color: #fff; border-color: var(--accent); }

/* Manuscripts table */
.tw { overflow-x: auto; border-radius: var(--radius); box-shadow: var(--shadow);
    border: 1px solid var(--border); }
table { width: 100%; border-collapse: collapse; background: var(--surface); font-size: 0.78rem;
    table-layout: fixed; }
th { background: var(--surface2); border-bottom: 2px solid var(--border); padding: 6px 8px;
    text-align: left; font-weight: 600; font-size: 0.7rem; color: var(--text2);
    text-transform: uppercase; letter-spacing: 0.04em; cursor: pointer;
    user-select: none; white-space: nowrap; }
th:hover { color: var(--accent); }
td { padding: 5px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
tr:last-child td { border-bottom: none; }
.ms-row { cursor: pointer; }
.ms-row:hover td { background: var(--accent-bg); }
.ms-row td:first-child::before { content: "▸ "; color: var(--text2); font-size: 0.7rem; }
.ms-row.exp td:first-child::before { content: "▾ "; }
.td-title { overflow: hidden; text-overflow: ellipsis; }
.td-status { overflow: hidden; text-overflow: ellipsis; font-size: 0.73rem; }
.detail-row { display: none; }
.detail-row.show { display: table-row; }
.detail-row td { padding: 2px 8px 8px 24px; background: var(--bg); }

.rt { width: 100%; font-size: 0.75rem; background: var(--surface); border-radius: 5px;
    border: 1px solid var(--border); }
.rt th { font-size: 0.68rem; padding: 4px 6px; background: var(--surface2); }
.rt td { padding: 4px 6px; }

.badge { font-size: 0.68rem; padding: 1px 5px; border-radius: 3px; font-weight: 600; white-space: nowrap; }
.b-agreed { background: var(--med-bg); color: var(--med); border: 1px solid var(--med-border); }
.b-done { background: var(--done-bg); color: var(--done); }
.b-pending { background: var(--high-bg); color: var(--high); border: 1px solid var(--high-border); }
.b-declined { background: var(--muted-bg); color: var(--muted); }
.b-term { background: var(--muted-bg); color: var(--muted); }
.b-overdue { background: var(--crit-bg); color: var(--crit); border: 1px solid var(--crit-border); }
.b-flag { background: var(--accent-bg); color: var(--accent); font-size: 0.68rem;
    padding: 1px 5px; border-radius: 3px; font-weight: 600; }
.overdue { color: var(--crit); font-weight: 600; }
.due-soon { color: var(--med); font-weight: 600; }
.on-track { color: var(--done); }
.rpt { font-weight: 700; font-size: 0.82rem; }

/* Journal overview */
.jgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(135px, 1fr)); gap: 6px; }
.jcard { background: var(--surface); border-radius: 6px; padding: 8px 10px;
    box-shadow: var(--shadow); border: 1px solid var(--border); }
.jcard .jn { font-weight: 700; font-size: 0.85rem; display: flex; align-items: center; gap: 6px; }
.jcard .jm { font-size: 0.7rem; color: var(--text2); }
.jcard .js { font-size: 0.72rem; margin-top: 2px; }
.fresh-green { background: var(--low-bg); color: var(--low); }
.fresh-amber { background: var(--med-bg); color: var(--med); }
.fresh-red { background: var(--crit-bg); color: var(--crit); }
.stale-grey { background: var(--muted-bg); color: var(--muted); }

/* Recommendations */
.rgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 8px; }
.rcard { background: var(--surface); border-radius: 6px; padding: 10px 12px;
    box-shadow: var(--shadow); border: 1px solid var(--border); }
.rcard h4 { font-size: 0.8rem; margin-bottom: 2px; }
.rcard .rmeta { font-size: 0.7rem; color: var(--text2); margin-bottom: 6px; }
.rcard .cand { font-size: 0.75rem; padding: 2px 0;
    display: flex; justify-content: space-between; gap: 8px; }
.rcard .cn { font-weight: 600; white-space: nowrap; }
.rcard .ci { font-size: 0.68rem; color: var(--text2); text-align: right; }

.collap-hdr { cursor: pointer; display: flex; align-items: center; gap: 6px; }
.collap-hdr::before { content: "▸"; font-size: 0.7rem; color: var(--text2); }
.collap-hdr.open::before { content: "▾"; }
.collap-body { display: none; margin-top: 6px; }
.collap-body.show { display: block; }

.footer { text-align: center; color: var(--text2); font-size: 0.7rem;
    margin-top: 20px; padding-top: 8px; border-top: 1px solid var(--border); }
.empty { text-align: center; padding: 16px; color: var(--text2); font-style: italic; font-size: 0.8rem; }

@media (max-width: 768px) {
    body { padding: 8px; font-size: 12px; }
    .act { grid-template-columns: 50px 36px auto 1fr; }
    .act-meta { display: none; }
    .rgrid { grid-template-columns: 1fr; }
    .jgrid { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
}
"""

JS = """
function sortTable(tid, ci) {
    var t = document.getElementById(tid);
    if (!t) return;
    var tb = t.querySelector('tbody');
    var rows = Array.from(tb.querySelectorAll('tr.ms-row'));
    var h = t.querySelectorAll('th')[ci];
    var asc = !h.classList.contains('sa');
    t.querySelectorAll('th').forEach(function(x) { x.classList.remove('sa','sd'); });
    h.classList.add(asc ? 'sa' : 'sd');
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
    if (r && d) { r.classList.toggle('exp'); d.classList.toggle('show'); }
}
function filterActs(lvl) {
    document.querySelectorAll('.fbtn').forEach(function(b) { b.classList.remove('on'); });
    event.target.classList.add('on');
    document.querySelectorAll('.act').forEach(function(a) {
        a.style.display = (lvl === 'all' || a.classList.contains(lvl)) ? '' : 'none';
    });
}
function toggleC(id) {
    var h = document.querySelector('[data-c="' + id + '"]');
    var b = document.getElementById(id);
    if (h && b) { h.classList.toggle('open'); b.classList.toggle('show'); }
}
"""


def generate_html(data):
    totals = data["totals"]
    items = data["action_items"]
    manuscripts = data["manuscripts"]
    journals = data["journals"]
    recommendations = data["recommendations"]
    training = data.get("training")

    h = []
    h.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    h.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    h.append("<title>Editorial Command Center</title>")
    h.append(f"<style>{CSS}</style></head><body>")

    h.append("<div class='hdr'>")
    h.append("<h1>Editorial Command Center</h1>")
    h.append(f"<div class='sub'>{_esc(data['generated_at'])}</div>")
    h.append("</div>")

    if totals["critical"] > 0:
        ac, ai = "alert-crit", "🔴"
        am = f"{totals['critical']} critical + {totals['high']} high priority items"
    elif totals["high"] > 0:
        ac, ai = "alert-high", "🟠"
        am = f"{totals['high']} high priority items"
    else:
        ac, ai = "alert-ok", "✅"
        am = "All clear"
    h.append(f"<div class='alert {ac}'>{ai} {am}</div>")

    h.append("<div class='pills'>")
    h.append(f"<span class='pill'><b>{totals['active_manuscripts']}</b> manuscripts</span>")
    h.append(f"<span class='pill'><b>{totals['action_items']}</b> actions</span>")
    h.append(f"<span class='pill'><b>{totals['active_journals']}</b> journals</span>")
    h.append(f"<span class='pill'><b>{totals['referees']}</b> active refs</span>")
    h.append("</div>")

    # --- Action Items ---
    h.append("<div class='sec'>")
    h.append("<div class='sec-title'>Action Items</div>")

    if items:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for it in items:
            counts[it["priority"]] = counts.get(it["priority"], 0) + 1

        h.append("<div class='filter-row'>")
        h.append("<button class='fbtn on' onclick='filterActs(\"all\")'>All</button>")
        for lvl, cls in [("critical", "crit"), ("high", "high"), ("medium", "med"), ("low", "low")]:
            if counts[lvl]:
                h.append(
                    f"<button class='fbtn' onclick='filterActs(\"{cls}\")'>"
                    f"{lvl.title()} ({counts[lvl]})</button>"
                )
        h.append("</div>")

        type_labels = {
            "overdue_report": "Overdue",
            "needs_ae_decision": "Decision",
            "pending_invitation": "No Reply",
            "needs_more_referees": "Few Refs",
            "due_soon": "Due Soon",
            "needs_assignment": "Assign",
        }
        pmap = {"critical": "crit", "high": "high", "medium": "med", "low": "low"}

        h.append("<div class='acts'>")
        for it in items:
            p = pmap.get(it["priority"], it["priority"])
            tl = type_labels.get(it["action_type"], it["action_type"])

            meta_parts = []
            if it.get("due_date"):
                meta_parts.append(f"due {it['due_date']}")
            if it.get("reminders_sent"):
                meta_parts.append(f"{it['reminders_sent']}r")
            meta = " · ".join(meta_parts)

            h.append(f"<div class='act {p}'>")
            h.append(f"<span class='act-badge {p}'>{tl}</span>")
            h.append(f"<span class='act-j'>{_esc(it['journal'])}</span>")
            h.append(f"<span class='act-ms'>{_esc(it['manuscript_id'])}</span>")
            h.append(f"<span class='act-msg'>{_esc(it['message'])}</span>")
            if meta:
                h.append(f"<span class='act-meta'>{_esc(meta)}</span>")
            h.append("</div>")
        h.append("</div>")
    else:
        h.append("<div class='empty'>No action items — all clear</div>")
    h.append("</div>")

    # --- Active Manuscripts ---
    h.append("<div class='sec'>")
    h.append("<div class='sec-title'>Active Manuscripts</div>")

    if manuscripts:
        h.append("<div class='tw'>")
        cols = ["Journal", "MS ID", "Title", "Status", "Rpts", "Due", "Days"]
        col_widths = ["54px", "105px", "auto", "140px", "42px", "62px", "38px"]
        h.append("<table id='mt'>")
        h.append("<colgroup>")
        for w in col_widths:
            h.append(f"<col style='width:{w}'>")
        h.append("</colgroup>")
        h.append("<thead><tr>")
        for i, col in enumerate(cols):
            h.append(f"<th onclick=\"sortTable('mt',{i})\">{col}</th>")
        h.append("</tr></thead><tbody>")

        for ms in manuscripts:
            safe_id = ms["manuscript_id"].replace(".", "_").replace("-", "_")

            completed = ms["reports_received"]
            reviewing = ms["reports_pending"]
            total_active = completed + reviewing
            rpt_str = f"{completed}/{total_active}" if total_active > 0 else "—"

            if ms.get("days_until_next_due") is not None:
                dd = ms["days_until_next_due"]
                if dd < 0:
                    dc, ds = "overdue", f"{abs(dd)}d over"
                elif dd <= 14:
                    dc, ds = "due-soon", f"{dd}d"
                else:
                    dc, ds = "on-track", f"{dd}d"
            else:
                dc, ds = "", "—"

            ndd = ds if ms.get("next_due_date") else "—"
            din = ms.get("days_in_system") or "—"

            flags = []
            if ms["needs_ae_decision"]:
                flags.append("<span class='b-flag'>Decision</span>")
            if ms["needs_referee_assignment"]:
                flags.append("<span class='b-flag'>Assign</span>")
            flag_str = " ".join(flags)

            status_display = ms["status"]
            status_abbrevs = {
                "All Referees Assigned": "Refs Assigned",
                "Awaiting Reviewer Scores": "Awaiting Scores",
                "Awaiting Reviewer Reports": "Awaiting Reports",
                "Overdue Reviewer Reports": "Overdue Reports",
                "Potential Referees Assigned": "Potential Refs",
                "Revision R1 Under Review": "R1 Under Review",
            }
            status_display = status_abbrevs.get(status_display, status_display)

            h.append(
                f"<tr class='ms-row' data-detail='d-{safe_id}' "
                f"onclick=\"toggleDetail('{safe_id}')\">"
            )
            h.append(f"<td><span class='act-j'>{_esc(ms['journal'])}</span></td>")
            h.append(f"<td>{_esc(ms['manuscript_id'])}</td>")
            title_display = ms["title"][:70] + ("…" if len(ms["title"]) > 70 else "")
            h.append(f"<td class='td-title'>{_esc(title_display)}</td>")
            h.append(f"<td class='td-status'>{_esc(status_display)} {flag_str}</td>")
            h.append(f"<td class='rpt' data-sort='{completed}'>{rpt_str}</td>")
            sort_due = (
                ms.get("days_until_next_due") if ms.get("days_until_next_due") is not None else 9999
            )
            h.append(f"<td data-sort='{sort_due}'><span class='{dc}'>{ndd}</span></td>")
            h.append(f"<td data-sort='{ms.get('days_in_system', 0)}'>{din}</td>")
            h.append("</tr>")

            ref_details = ms.get("referee_details", [])
            h.append(f"<tr class='detail-row' id='d-{safe_id}'><td colspan='{len(cols)}'>")
            if ref_details:
                h.append("<table class='rt'><thead><tr>")
                h.append(
                    "<th>Referee</th><th>Status</th><th>Invited</th>"
                    "<th>Agreed</th><th>Due</th><th>Returned</th>"
                    "<th>Rem.</th><th>Timeline</th>"
                )
                h.append("</tr></thead><tbody>")
                for rd in ref_details:
                    st = rd["normalized_status"]
                    bc = f"b-{st}" if st in ("agreed", "pending", "declined") else ""
                    if st == "completed":
                        bc = "b-done"
                    elif st == "terminated":
                        bc = "b-term"
                    if rd.get("days_overdue"):
                        bc = "b-overdue"

                    tl = ""
                    if rd.get("days_overdue"):
                        tl = f"<span class='overdue'>{rd['days_overdue']}d overdue</span>"
                    elif rd.get("days_remaining") is not None:
                        d = rd["days_remaining"]
                        tl = f"<span class='{'due-soon' if d <= 14 else 'on-track'}'>{d}d</span>"
                    elif st == "completed":
                        tl = "✓"
                    elif st in ("declined", "terminated"):
                        tl = "—"

                    h.append("<tr>")
                    h.append(f"<td>{_esc(rd['name'])}</td>")
                    h.append(f"<td><span class='badge {bc}'>{_esc(st)}</span></td>")
                    h.append(f"<td>{_esc(rd.get('invited') or '—')}</td>")
                    h.append(f"<td>{_esc(rd.get('agreed') or '—')}</td>")
                    h.append(f"<td>{_esc(rd.get('due') or '—')}</td>")
                    h.append(f"<td>{_esc(rd.get('returned') or '—')}</td>")
                    h.append(f"<td>{rd['reminders']}</td>")
                    h.append(f"<td>{tl}</td>")
                    h.append("</tr>")
                h.append("</tbody></table>")
            else:
                h.append("<div class='empty' style='padding:6px'>No referees assigned</div>")
            h.append("</td></tr>")

        h.append("</tbody></table></div>")
    else:
        h.append("<div class='empty'>No active manuscripts</div>")
    h.append("</div>")

    # --- Journal Overview ---
    h.append("<div class='sec'>")
    h.append("<div class='sec-title'>Journal Overview</div>")
    h.append("<div class='jgrid'>")
    for js in journals:
        j = js["journal"].upper()
        n_ms = js.get("manuscripts", 0)
        n_ref = js.get("referees", 0)
        fc = js.get("freshness_class", "stale-grey")
        fl = js.get("freshness_label", "No data")
        h.append("<div class='jcard'>")
        h.append(f"<div class='jn'>{_esc(j)} <span class='badge {fc}'>{_esc(fl)}</span></div>")
        h.append(f"<div class='jm'>{_esc(js.get('platform', ''))}</div>")
        h.append(f"<div class='js'>{n_ms} mss · {n_ref} refs</div>")
        h.append("</div>")
    h.append("</div></div>")

    # --- Pipeline Recommendations ---
    if recommendations:
        h.append("<div class='sec'>")
        h.append("<div class='sec-title'>Pipeline Recommendations</div>")
        h.append("<div class='rgrid'>")
        for rec in recommendations:
            h.append("<div class='rcard'>")
            h.append(f"<h4>{_esc(rec['journal'])} / {_esc(rec['manuscript_id'])}</h4>")
            h.append(f"<div class='rmeta'>{_esc(rec['title'])} · {_esc(rec['generated_at'])}</div>")
            for i, c in enumerate(rec.get("candidates", [])):
                hi = c.get("h_index") or "?"
                inst = c.get("institution") or ""
                score = c.get("score", 0)
                h.append(
                    f"<div class='cand'><span class='cn'>#{i+1} {_esc(c['name'])}</span>"
                    f"<span class='ci'>{_esc(inst)} · h={hi} · {score:.2f}</span></div>"
                )
            h.append("</div>")
        h.append("</div></div>")

    # --- Model Health ---
    if training:
        h.append("<div class='sec'>")
        h.append(
            "<div class='collap-hdr' data-c='mh' onclick=\"toggleC('mh')\">"
            "<span class='sec-title' style='border:none;margin:0;padding:0'>Model Health</span></div>"
        )
        h.append("<div class='collap-body' id='mh'>")
        h.append("<div class='jgrid'>")
        for mk, ml in [
            ("expertise_index", "Expertise Index"),
            ("response_predictor", "Response Predictor"),
            ("outcome_predictor", "Outcome Predictor"),
        ]:
            m = training.get(mk, {})
            st = m.get("status", "not_trained")
            h.append("<div class='jcard'>")
            h.append(f"<div class='jn'>{_esc(ml)}</div>")
            h.append(f"<div class='jm'>Status: {_esc(st)}</div>")
            if m.get("cv_accuracy"):
                h.append(f"<div class='js'>CV: {m['cv_accuracy']:.1%}</div>")
            if m.get("n_referees"):
                h.append(f"<div class='js'>{m['n_referees']} refs</div>")
            if m.get("n_samples"):
                h.append(f"<div class='js'>{m['n_samples']} samples</div>")
            h.append("</div>")
        h.append("</div></div></div>")

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
        f"  Action items: {totals['action_items']} ({totals['critical']} critical, {totals['high']} high)"
    )
    print(f"  Active manuscripts: {totals['active_manuscripts']}")
    print(f"  Journals: {totals['active_journals']}/8")
    if data["recommendations"]:
        print(f"  Recommendations: {len(data['recommendations'])}")


if __name__ == "__main__":
    main()
