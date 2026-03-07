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
        return "1 day ago"
    return f"{age_days} days ago"


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
                "title": (rec.get("title") or "")[:100],
                "journal": (rec.get("journal") or "").upper(),
                "generated_at": rec.get("generated_at", "")[:16],
                "desk_rejection": rec.get("desk_rejection", {}),
                "candidates": [
                    {
                        "name": c.get("name", ""),
                        "institution": (c.get("institution") or "")[:40],
                        "h_index": c.get("h_index"),
                        "score": c.get("relevance_score", 0),
                        "source": c.get("source", ""),
                    }
                    for c in candidates
                ],
            }
        )

    totals = {
        "active_journals": sum(1 for s in journal_stats if s.get("manuscripts", 0) > 0),
        "manuscripts": sum(s.get("manuscripts", 0) for s in journal_stats),
        "active_manuscripts": len(manuscript_summaries),
        "referees": sum(s.get("referees", 0) for s in journal_stats),
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
    --bg: #f8fafc; --surface: #ffffff; --text: #0f172a; --text-secondary: #64748b;
    --border: #e2e8f0; --accent: #3b82f6; --accent-light: #dbeafe;
    --critical: #dc2626; --critical-bg: #fef2f2;
    --high: #ea580c; --high-bg: #fff7ed;
    --medium: #ca8a04; --medium-bg: #fefce8;
    --low: #16a34a; --low-bg: #f0fdf4;
    --completed: #059669; --completed-bg: #ecfdf5;
    --declined: #94a3b8; --declined-bg: #f1f5f9;
    --shadow: 0 1px 3px rgba(0,0,0,.1); --shadow-lg: 0 4px 12px rgba(0,0,0,.1);
    --radius: 10px; --radius-sm: 6px;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0f172a; --surface: #1e293b; --text: #f1f5f9; --text-secondary: #94a3b8;
        --border: #334155; --accent: #60a5fa; --accent-light: #1e3a5f;
        --critical-bg: #450a0a; --high-bg: #431407; --medium-bg: #422006;
        --low-bg: #052e16; --completed-bg: #064e3b; --declined-bg: #1e293b;
        --shadow: 0 1px 3px rgba(0,0,0,.3); --shadow-lg: 0 4px 12px rgba(0,0,0,.4);
    }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.5; padding: 20px 24px; }
.header { text-align: center; margin-bottom: 24px; }
.header h1 { font-size: 1.6rem; font-weight: 700; }
.header .subtitle { color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; }
.alert-banner { padding: 14px 20px; border-radius: var(--radius); margin-bottom: 20px;
    display: flex; align-items: center; gap: 12px; font-weight: 600; font-size: 0.95rem; }
.alert-critical { background: var(--critical-bg); border: 2px solid var(--critical); color: var(--critical); }
.alert-high { background: var(--high-bg); border: 2px solid var(--high); color: var(--high); }
.alert-clear { background: var(--low-bg); border: 2px solid var(--low); color: var(--low); }
.stats-row { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin: 12px 0; }
.stat-pill { background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
    padding: 6px 14px; font-size: 0.8rem; display: flex; align-items: center; gap: 6px; }
.stat-pill .num { font-weight: 700; font-size: 0.95rem; }
.section { margin-bottom: 24px; }
.section-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 12px;
    padding-bottom: 6px; border-bottom: 2px solid var(--border); }
.action-list { display: flex; flex-direction: column; gap: 8px; }
.action-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px;
    background: var(--surface); border-radius: var(--radius-sm); border-left: 4px solid;
    box-shadow: var(--shadow); font-size: 0.87rem; }
.action-item.critical { border-left-color: var(--critical); background: var(--critical-bg); }
.action-item.high { border-left-color: var(--high); background: var(--high-bg); }
.action-item.medium { border-left-color: var(--medium); background: var(--medium-bg); }
.action-item.low { border-left-color: var(--low); background: var(--low-bg); }
.action-badge { font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    padding: 2px 8px; border-radius: 4px; white-space: nowrap; min-width: 60px; text-align: center; }
.action-badge.critical { background: var(--critical); color: white; }
.action-badge.high { background: var(--high); color: white; }
.action-badge.medium { background: var(--medium); color: white; }
.action-badge.low { background: var(--low); color: white; }
.action-ms { font-weight: 600; white-space: nowrap; min-width: 80px; }
.action-journal { font-size: 0.75rem; font-weight: 600; color: var(--accent);
    background: var(--accent-light); padding: 1px 6px; border-radius: 3px; }
.action-msg { flex: 1; }
.action-meta { color: var(--text-secondary); font-size: 0.78rem; white-space: nowrap; }
.table-wrapper { overflow-x: auto; border-radius: var(--radius); box-shadow: var(--shadow); }
table { width: 100%; border-collapse: collapse; background: var(--surface); font-size: 0.83rem; }
th { background: var(--surface); border-bottom: 2px solid var(--border); padding: 8px 10px;
    text-align: left; font-weight: 600; font-size: 0.78rem; color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.03em; cursor: pointer; user-select: none;
    white-space: nowrap; }
th:hover { color: var(--accent); }
td { padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--accent-light); }
.ms-row { cursor: pointer; }
.ms-row td:first-child::before { content: "▸ "; color: var(--text-secondary); }
.ms-row.expanded td:first-child::before { content: "▾ "; }
.detail-row { display: none; }
.detail-row.show { display: table-row; }
.detail-row td { padding: 0 10px 8px 30px; background: var(--bg); }
.ref-table { width: 100%; font-size: 0.8rem; background: var(--surface);
    border-radius: var(--radius-sm); }
.ref-table th { font-size: 0.72rem; padding: 5px 8px; }
.ref-table td { padding: 5px 8px; }
.status-badge { font-size: 0.72rem; padding: 2px 6px; border-radius: 3px; font-weight: 600; }
.status-agreed { background: var(--medium-bg); color: var(--medium); }
.status-completed { background: var(--completed-bg); color: var(--completed); }
.status-pending { background: var(--high-bg); color: var(--high); }
.status-declined { background: var(--declined-bg); color: var(--declined); }
.status-terminated { background: var(--declined-bg); color: var(--declined); }
.status-overdue { background: var(--critical-bg); color: var(--critical); }
.overdue-text { color: var(--critical); font-weight: 600; }
.due-soon-text { color: var(--medium); font-weight: 600; }
.on-track-text { color: var(--completed); }
.reports-fmt { font-weight: 600; }
.journal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px; }
.journal-mini { background: var(--surface); border-radius: var(--radius-sm); padding: 10px 12px;
    box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 4px; }
.journal-mini .jname { font-weight: 700; font-size: 0.9rem; }
.journal-mini .jmeta { font-size: 0.75rem; color: var(--text-secondary); }
.journal-mini .jstats { font-size: 0.78rem; display: flex; gap: 8px; }
.badge { font-size: 0.7rem; padding: 2px 6px; border-radius: 3px; font-weight: 600; }
.fresh-green { background: var(--low-bg); color: var(--low); }
.fresh-amber { background: var(--medium-bg); color: var(--medium); }
.fresh-red { background: var(--critical-bg); color: var(--critical); }
.stale-grey { background: var(--declined-bg); color: var(--declined); }
.rec-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.rec-card { background: var(--surface); border-radius: var(--radius-sm); padding: 12px;
    box-shadow: var(--shadow); }
.rec-card h4 { font-size: 0.85rem; margin-bottom: 4px; }
.rec-card .rec-meta { font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 8px; }
.rec-card .cand { font-size: 0.8rem; padding: 3px 0;
    display: flex; justify-content: space-between; align-items: center; }
.rec-card .cand-name { font-weight: 600; }
.rec-card .cand-score { font-size: 0.72rem; color: var(--text-secondary); }
.collapsible-header { cursor: pointer; display: flex; align-items: center; gap: 8px; }
.collapsible-header::before { content: "▸"; font-size: 0.8rem; color: var(--text-secondary); }
.collapsible-header.open::before { content: "▾"; }
.collapsible-body { display: none; margin-top: 8px; }
.collapsible-body.show { display: block; }
.footer { text-align: center; color: var(--text-secondary); font-size: 0.75rem;
    margin-top: 24px; padding-top: 12px; border-top: 1px solid var(--border); }
.filter-row { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
.filter-btn { border: 1px solid var(--border); background: var(--surface); color: var(--text);
    padding: 4px 12px; border-radius: 16px; font-size: 0.78rem; cursor: pointer; }
.filter-btn.active { background: var(--accent); color: white; border-color: var(--accent); }
.empty-state { text-align: center; padding: 24px; color: var(--text-secondary); font-style: italic; }
@media (max-width: 768px) {
    body { padding: 12px; }
    .action-item { flex-wrap: wrap; gap: 6px; }
    .rec-grid { grid-template-columns: 1fr; }
    .journal-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
}
"""

JS = """
function sortTable(tableId, colIdx) {
    var table = document.getElementById(tableId);
    if (!table) return;
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr.ms-row'));
    var header = table.querySelectorAll('th')[colIdx];
    var asc = !header.classList.contains('sorted-asc');
    table.querySelectorAll('th').forEach(function(h) {
        h.classList.remove('sorted', 'sorted-asc', 'sorted-desc');
    });
    header.classList.add('sorted', asc ? 'sorted-asc' : 'sorted-desc');
    rows.sort(function(a, b) {
        var aVal = a.cells[colIdx].getAttribute('data-sort') || a.cells[colIdx].textContent.trim();
        var bVal = b.cells[colIdx].getAttribute('data-sort') || b.cells[colIdx].textContent.trim();
        var aNum = parseFloat(aVal), bNum = parseFloat(bVal);
        if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
        return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    rows.forEach(function(row) {
        var detailId = row.getAttribute('data-detail');
        tbody.appendChild(row);
        if (detailId) {
            var detail = document.getElementById(detailId);
            if (detail) tbody.appendChild(detail);
        }
    });
}

function toggleDetail(msId) {
    var row = document.querySelector('tr[data-detail="detail-' + msId + '"]');
    var detail = document.getElementById('detail-' + msId);
    if (row && detail) {
        row.classList.toggle('expanded');
        detail.classList.toggle('show');
    }
}

function filterActions(level) {
    var btns = document.querySelectorAll('.filter-btn');
    btns.forEach(function(b) { b.classList.remove('active'); });
    event.target.classList.add('active');
    var items = document.querySelectorAll('.action-item');
    items.forEach(function(item) {
        if (level === 'all') { item.style.display = ''; }
        else { item.style.display = item.classList.contains(level) ? '' : 'none'; }
    });
}

function toggleCollapsible(id) {
    var header = document.querySelector('[data-collapse="' + id + '"]');
    var body = document.getElementById(id);
    if (header && body) {
        header.classList.toggle('open');
        body.classList.toggle('show');
    }
}
"""


def generate_html(data):
    totals = data["totals"]
    items = data["action_items"]
    manuscripts = data["manuscripts"]
    journals = data["journals"]
    recommendations = data["recommendations"]
    training = data.get("training")

    html = []
    html.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    html.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    html.append("<title>Editorial Command Center</title>")
    html.append(f"<style>{CSS}</style></head><body>")

    html.append("<div class='header'>")
    html.append("<h1>Editorial Command Center</h1>")
    html.append(f"<div class='subtitle'>Updated {_esc(data['generated_at'])}</div>")
    html.append("</div>")

    if totals["critical"] > 0:
        alert_class = "alert-critical"
        alert_icon = "🔴"
        alert_msg = (
            f"{totals['critical']} critical + {totals['high']} high priority items need attention"
        )
    elif totals["high"] > 0:
        alert_class = "alert-high"
        alert_icon = "🟠"
        alert_msg = f"{totals['high']} items need attention"
    else:
        alert_class = "alert-clear"
        alert_icon = "✅"
        alert_msg = "All clear — no urgent items"
    html.append(f"<div class='alert-banner {alert_class}'>{alert_icon} {alert_msg}</div>")

    html.append("<div class='stats-row'>")
    html.append(
        f"<span class='stat-pill'><span class='num'>{totals['active_manuscripts']}</span> active manuscripts</span>"
    )
    html.append(
        f"<span class='stat-pill'><span class='num'>{totals['action_items']}</span> action items</span>"
    )
    html.append(
        f"<span class='stat-pill'><span class='num'>{totals['active_journals']}</span> journals</span>"
    )
    html.append(
        f"<span class='stat-pill'><span class='num'>{totals['referees']}</span> referees</span>"
    )
    html.append("</div>")

    # --- Section 1: Action Items ---
    html.append("<div class='section'>")
    html.append("<div class='section-title'>Action Items</div>")

    if items:
        priorities = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for it in items:
            priorities[it["priority"]] = priorities.get(it["priority"], 0) + 1

        html.append("<div class='filter-row'>")
        html.append(
            "<button class='filter-btn active' onclick='filterActions(\"all\")'>All</button>"
        )
        if priorities["critical"]:
            html.append(
                f"<button class='filter-btn' onclick='filterActions(\"critical\")'>Critical ({priorities['critical']})</button>"
            )
        if priorities["high"]:
            html.append(
                f"<button class='filter-btn' onclick='filterActions(\"high\")'>High ({priorities['high']})</button>"
            )
        if priorities["medium"]:
            html.append(
                f"<button class='filter-btn' onclick='filterActions(\"medium\")'>Medium ({priorities['medium']})</button>"
            )
        if priorities["low"]:
            html.append(
                f"<button class='filter-btn' onclick='filterActions(\"low\")'>Low ({priorities['low']})</button>"
            )
        html.append("</div>")

        html.append("<div class='action-list'>")
        for it in items:
            p = it["priority"]
            type_labels = {
                "overdue_report": "Overdue",
                "needs_ae_decision": "Decision",
                "pending_invitation": "No Reply",
                "needs_more_referees": "Few Refs",
                "due_soon": "Due Soon",
                "needs_assignment": "Assign",
            }
            type_label = type_labels.get(it["action_type"], it["action_type"])

            meta_parts = []
            if it.get("due_date"):
                meta_parts.append(f"due {it['due_date']}")
            if it.get("reminders_sent"):
                meta_parts.append(f"{it['reminders_sent']} reminders")
            meta = " · ".join(meta_parts)

            html.append(f"<div class='action-item {p}'>")
            html.append(f"<span class='action-badge {p}'>{type_label}</span>")
            html.append(f"<span class='action-journal'>{_esc(it['journal'])}</span>")
            html.append(f"<span class='action-ms'>{_esc(it['manuscript_id'])}</span>")
            html.append(f"<span class='action-msg'>{_esc(it['message'])}</span>")
            if meta:
                html.append(f"<span class='action-meta'>{_esc(meta)}</span>")
            html.append("</div>")
        html.append("</div>")
    else:
        html.append("<div class='empty-state'>No action items — everything is on track!</div>")
    html.append("</div>")

    # --- Section 2: Active Manuscripts ---
    html.append("<div class='section'>")
    html.append("<div class='section-title'>Active Manuscripts</div>")

    if manuscripts:
        html.append("<div class='table-wrapper'>")
        cols = ["Journal", "Manuscript", "Title", "Status", "Reports", "Next Due", "Days", "Refs"]
        html.append("<table id='ms-table'><thead><tr>")
        for i, col in enumerate(cols):
            html.append(f"<th onclick=\"sortTable('ms-table',{i})\">{col}</th>")
        html.append("</tr></thead><tbody>")

        for ms in manuscripts:
            safe_id = ms["manuscript_id"].replace(".", "_").replace("-", "_")
            reports_str = (
                f"{ms['reports_received']}/{ms['reports_received'] + ms['reports_pending']}"
            )

            if ms.get("days_until_next_due") is not None:
                days = ms["days_until_next_due"]
                if days < 0:
                    due_class = "overdue-text"
                    due_str = f"{abs(days)}d overdue"
                elif days <= 14:
                    due_class = "due-soon-text"
                    due_str = f"{days}d left"
                else:
                    due_class = "on-track-text"
                    due_str = f"{days}d left"
            else:
                due_class = ""
                due_str = "—"

            next_due_display = due_str if ms.get("next_due_date") else "—"
            days_in = ms.get("days_in_system") or "—"

            flags = []
            if ms["needs_ae_decision"]:
                flags.append("<span class='status-badge status-completed'>AE Decision</span>")
            if ms["needs_referee_assignment"]:
                flags.append("<span class='status-badge status-pending'>Assign Refs</span>")

            flag_str = " ".join(flags)

            total_refs = (
                ms["referees_agreed"] + ms["referees_completed"] + ms["referees_pending_response"]
            )

            html.append(
                f"<tr class='ms-row' data-detail='detail-{safe_id}' onclick=\"toggleDetail('{safe_id}')\">"
            )
            html.append(f"<td><span class='action-journal'>{_esc(ms['journal'])}</span></td>")
            html.append(f"<td>{_esc(ms['manuscript_id'])}</td>")
            html.append(f"<td>{_esc(ms['title'][:60])}{'…' if len(ms['title']) > 60 else ''}</td>")
            html.append(f"<td>{_esc(ms['status'])} {flag_str}</td>")
            html.append(
                f"<td class='reports-fmt' data-sort='{ms['reports_received']}'>{reports_str}</td>"
            )
            html.append(
                f"<td data-sort='{ms.get('days_until_next_due', 9999)}'><span class='{due_class}'>{next_due_display}</span></td>"
            )
            html.append(f"<td data-sort='{ms.get('days_in_system', 0)}'>{days_in}</td>")
            html.append(f"<td>{total_refs}</td>")
            html.append("</tr>")

            ref_details = ms.get("referee_details", [])
            html.append(f"<tr class='detail-row' id='detail-{safe_id}'><td colspan='{len(cols)}'>")
            if ref_details:
                html.append("<table class='ref-table'><thead><tr>")
                html.append(
                    "<th>Referee</th><th>Status</th><th>Invited</th><th>Agreed</th><th>Due</th><th>Returned</th><th>Reminders</th><th>Timeline</th>"
                )
                html.append("</tr></thead><tbody>")
                for rd in ref_details:
                    st = rd["normalized_status"]
                    badge_class = f"status-{st}"

                    timeline = ""
                    if rd.get("days_overdue"):
                        timeline = (
                            f"<span class='overdue-text'>{rd['days_overdue']}d overdue</span>"
                        )
                        badge_class = "status-overdue"
                    elif rd.get("days_remaining") is not None:
                        d = rd["days_remaining"]
                        if d <= 14:
                            timeline = f"<span class='due-soon-text'>{d}d left</span>"
                        else:
                            timeline = f"<span class='on-track-text'>{d}d left</span>"
                    elif st == "completed":
                        timeline = "✓"
                    elif st in ("declined", "terminated"):
                        timeline = "—"

                    html.append("<tr>")
                    html.append(f"<td>{_esc(rd['name'])}</td>")
                    html.append(
                        f"<td><span class='status-badge {badge_class}'>{_esc(st)}</span></td>"
                    )
                    html.append(f"<td>{_esc(rd.get('invited') or '—')}</td>")
                    html.append(f"<td>{_esc(rd.get('agreed') or '—')}</td>")
                    html.append(f"<td>{_esc(rd.get('due') or '—')}</td>")
                    html.append(f"<td>{_esc(rd.get('returned') or '—')}</td>")
                    html.append(f"<td>{rd['reminders']}</td>")
                    html.append(f"<td>{timeline}</td>")
                    html.append("</tr>")
                html.append("</tbody></table>")
            else:
                html.append(
                    "<div class='empty-state' style='padding:8px'>No referees assigned</div>"
                )
            html.append("</td></tr>")

        html.append("</tbody></table></div>")
    else:
        html.append("<div class='empty-state'>No active manuscripts</div>")
    html.append("</div>")

    # --- Section 3: Journal Overview ---
    html.append("<div class='section'>")
    html.append("<div class='section-title'>Journal Overview</div>")
    html.append("<div class='journal-grid'>")
    for js in journals:
        j = js["journal"].upper()
        n_ms = js.get("manuscripts", 0)
        n_ref = js.get("referees", 0)
        fc = js.get("freshness_class", "stale-grey")
        fl = js.get("freshness_label", "No data")
        html.append("<div class='journal-mini'>")
        html.append(
            f"<div class='jname'>{_esc(j)} <span class='badge {fc}'>{_esc(fl)}</span></div>"
        )
        html.append(f"<div class='jmeta'>{_esc(js.get('platform', ''))}</div>")
        html.append(f"<div class='jstats'><span>{n_ms} mss</span><span>{n_ref} refs</span></div>")
        html.append("</div>")
    html.append("</div></div>")

    # --- Section 4: Pipeline Recommendations ---
    if recommendations:
        html.append("<div class='section'>")
        html.append("<div class='section-title'>Pipeline Recommendations</div>")
        html.append("<div class='rec-grid'>")
        for rec in recommendations:
            html.append("<div class='rec-card'>")
            html.append(f"<h4>{_esc(rec['journal'])} / {_esc(rec['manuscript_id'])}</h4>")
            html.append(
                f"<div class='rec-meta'>{_esc(rec['title'])} · {_esc(rec['generated_at'])}</div>"
            )
            for i, c in enumerate(rec.get("candidates", [])):
                h = c.get("h_index") or "?"
                inst = c.get("institution") or ""
                html.append(
                    f"<div class='cand'><span class='cand-name'>#{i+1} {_esc(c['name'])}</span>"
                )
                html.append(
                    f"<span class='cand-score'>{inst} · h={h} · {c['score']:.2f}</span></div>"
                )
            html.append("</div>")
        html.append("</div></div>")

    # --- Section 5: Model Health (collapsible) ---
    if training:
        html.append("<div class='section'>")
        html.append(
            "<div class='collapsible-header' data-collapse='model-health' onclick=\"toggleCollapsible('model-health')\">"
        )
        html.append(
            "<span class='section-title' style='border:none;margin:0;padding:0'>Model Health</span></div>"
        )
        html.append("<div class='collapsible-body' id='model-health'>")
        html.append("<div class='journal-grid'>")
        for model_key, label in [
            ("expertise_index", "Expertise Index"),
            ("response_predictor", "Response Predictor"),
            ("outcome_predictor", "Outcome Predictor"),
        ]:
            m = training.get(model_key, {})
            status = m.get("status", "not_trained")
            html.append("<div class='journal-mini'>")
            html.append(f"<div class='jname'>{_esc(label)}</div>")
            html.append(f"<div class='jmeta'>Status: {_esc(status)}</div>")
            if m.get("cv_accuracy"):
                html.append(f"<div class='jstats'>CV: {m['cv_accuracy']:.1%}</div>")
            if m.get("n_referees"):
                html.append(f"<div class='jstats'>{m['n_referees']} referees</div>")
            if m.get("n_samples"):
                html.append(f"<div class='jstats'>{m['n_samples']} samples</div>")
            html.append("</div>")
        html.append("</div></div></div>")

    # --- Footer ---
    html.append("<div class='footer'>")
    html.append(
        f"Generated {_esc(data['generated_at'])} · commit {_esc(data['git_commit'])} · Editorial Scripts"
    )
    html.append("</div>")

    html.append(f"<script>{JS}</script></body></html>")
    return "\n".join(html)


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
