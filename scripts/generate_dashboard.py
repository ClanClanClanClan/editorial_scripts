#!/usr/bin/env python3
"""Generate a self-contained HTML dashboard from editorial extraction data."""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "production" / "src"))

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


def _load_feedback_stats():
    try:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        return trainer.get_feedback_stats()
    except (ImportError, OSError):
        return None


def _load_recent_recommendations(limit=10):
    recs = []
    for journal in JOURNALS:
        rec_dir = OUTPUTS_DIR / journal / "recommendations"
        if not rec_dir.exists():
            continue
        for f in sorted(rec_dir.glob("rec_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
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


def _load_pending_manuscripts():
    pending = []
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if not data:
            continue
        for ms in data.get("manuscripts", []):
            status = ms.get("status") or ""
            stage = ms.get("platform_specific", {}).get("metadata", {}).get("current_stage") or ""
            n_refs = len(ms.get("referees", []))
            is_pending = False
            if "Waiting for Potential Referee" in stage:
                is_pending = True
            elif "Requiring Assignment" in status:
                is_pending = True
            elif status in ("Under Review", "New Submission") and n_refs == 0:
                is_pending = True
            if is_pending:
                pending.append(
                    {
                        "manuscript_id": ms.get("manuscript_id", "?"),
                        "title": ms.get("title", "?"),
                        "journal": journal.upper(),
                        "status": stage or status,
                        "authors": len(ms.get("authors", [])),
                    }
                )
    return pending


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


def _model_status_class(status):
    if status in ("trained", "built"):
        return "status-good"
    if status == "model_not_useful":
        return "status-warn"
    return "status-neutral"


def build_dashboard_data():
    journal_stats = []
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if data:
            stats = compute_journal_stats(journal, data)
        else:
            stats = {
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
        stats["freshness_class"] = _freshness_class(stats.get("age_days"))
        stats["freshness_label"] = _freshness_label(stats.get("age_days"))
        journal_stats.append(stats)

    training = _load_training_metadata()
    feedback = _load_feedback_stats()
    recommendations = _load_recent_recommendations(limit=10)
    pending = _load_pending_manuscripts()

    rec_summary = []
    for r in recommendations:
        candidates = r.get("referee_candidates", [])[:3]
        rec_summary.append(
            {
                "manuscript_id": r.get("manuscript_id", "?"),
                "journal": r.get("journal", "?"),
                "title": r.get("title", "?"),
                "desk_reject": r.get("desk_rejection", {}).get("should_desk_reject", False),
                "desk_confidence": r.get("desk_rejection", {}).get("confidence", 0),
                "generated_at": r.get("generated_at", "")[:16].replace("T", " "),
                "top_candidates": [
                    {
                        "name": c.get("name", "?"),
                        "score": round(c.get("relevance_score", 0), 2),
                        "h_index": c.get("h_index", 0),
                        "institution": (c.get("institution") or "")[:40],
                        "source": c.get("source", ""),
                    }
                    for c in candidates
                ],
            }
        )

    totals = {
        "manuscripts": sum(s["manuscripts"] for s in journal_stats),
        "referees": sum(s["referees"] for s in journal_stats),
        "authors": sum(s["authors"] for s in journal_stats),
        "active_journals": sum(1 for s in journal_stats if s["manuscripts"] > 0),
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "git_commit": _git_commit(),
        "journals": journal_stats,
        "totals": totals,
        "training": training,
        "feedback": feedback,
        "recommendations": rec_summary,
        "pending": pending,
    }


CSS = """
:root {
    --bg: #f8f9fa;
    --surface: #ffffff;
    --text: #1a1a2e;
    --text-secondary: #6c757d;
    --border: #e9ecef;
    --accent: #4361ee;
    --accent-light: #eef2ff;
    --green: #10b981;
    --green-bg: #ecfdf5;
    --amber: #f59e0b;
    --amber-bg: #fffbeb;
    --red: #ef4444;
    --red-bg: #fef2f2;
    --grey: #9ca3af;
    --grey-bg: #f3f4f6;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-lg: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
    --radius: 12px;
    --radius-sm: 8px;
}
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0f172a;
        --surface: #1e293b;
        --text: #e2e8f0;
        --text-secondary: #94a3b8;
        --border: #334155;
        --accent: #818cf8;
        --accent-light: #1e1b4b;
        --green-bg: #064e3b;
        --amber-bg: #451a03;
        --red-bg: #450a0a;
        --grey-bg: #1f2937;
        --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
        --shadow: 0 1px 3px rgba(0,0,0,0.4);
        --shadow-lg: 0 4px 6px rgba(0,0,0,0.4);
    }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}
.container { max-width: 1280px; margin: 0 auto; padding: 24px; }

/* Header */
.header {
    text-align: center;
    padding: 48px 24px 36px;
    margin-bottom: 32px;
}
.header h1 {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 8px;
}
.header .subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
}
.header .stats-row {
    display: flex;
    justify-content: center;
    gap: 32px;
    margin-top: 20px;
    flex-wrap: wrap;
}
.header .stat-pill {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 8px 20px;
    font-size: 0.9rem;
    box-shadow: var(--shadow-sm);
}
.header .stat-pill strong { color: var(--accent); font-weight: 600; }

/* Section */
.section { margin-bottom: 36px; }
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
}

/* Cards Grid */
.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
}
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
    transition: box-shadow 0.2s, transform 0.2s;
}
.card:hover {
    box-shadow: var(--shadow-lg);
    transform: translateY(-1px);
}
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.card-header h3 {
    font-size: 1rem;
    font-weight: 600;
}
.card-header .platform {
    font-size: 0.75rem;
    color: var(--text-secondary);
    background: var(--grey-bg);
    padding: 2px 8px;
    border-radius: 100px;
}
.card-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 12px;
}
.card-stat {
    text-align: center;
}
.card-stat .val {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--accent);
}
.card-stat .lbl {
    font-size: 0.7rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 8px;
    border-top: 1px solid var(--border);
    font-size: 0.8rem;
    color: var(--text-secondary);
}

/* Freshness badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 500;
}
.fresh-green { background: var(--green-bg); color: var(--green); }
.fresh-amber { background: var(--amber-bg); color: var(--amber); }
.fresh-red { background: var(--red-bg); color: var(--red); }
.stale-grey { background: var(--grey-bg); color: var(--grey); }
.status-good { background: var(--green-bg); color: var(--green); }
.status-warn { background: var(--amber-bg); color: var(--amber); }
.status-neutral { background: var(--grey-bg); color: var(--grey); }

/* Tables */
.table-wrapper {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow-x: auto;
    box-shadow: var(--shadow);
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
}
th {
    text-align: left;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-secondary);
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}
th:hover { color: var(--accent); }
th .sort-arrow { font-size: 0.65rem; margin-left: 4px; opacity: 0.4; }
th.sorted .sort-arrow { opacity: 1; }
td {
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--accent-light); }

/* Recommendation cards */
.rec-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
    margin-bottom: 12px;
}
.rec-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
    gap: 16px;
}
.rec-header .ms-info h4 { font-size: 0.95rem; font-weight: 600; }
.rec-header .ms-meta {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 2px;
}
.rec-header .desk-badge {
    flex-shrink: 0;
    padding: 4px 12px;
    border-radius: 100px;
    font-size: 0.78rem;
    font-weight: 500;
}
.desk-pass { background: var(--green-bg); color: var(--green); }
.desk-reject { background: var(--red-bg); color: var(--red); }
.candidates-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
}
.candidate {
    background: var(--bg);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    font-size: 0.85rem;
}
.candidate .c-name { font-weight: 600; }
.candidate .c-details {
    color: var(--text-secondary);
    font-size: 0.78rem;
    margin-top: 2px;
}
.candidate .c-score {
    display: inline-block;
    background: var(--accent-light);
    color: var(--accent);
    padding: 1px 8px;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-top: 4px;
}

/* Model cards */
.model-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
}
.model-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
}
.model-card h4 {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 12px;
}
.model-metric {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 0.85rem;
}
.model-metric .label { color: var(--text-secondary); }
.model-metric .value { font-weight: 600; }

/* Freshness bar chart */
.freshness-bars {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
}
.bar-row {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    gap: 12px;
}
.bar-label {
    width: 60px;
    font-size: 0.85rem;
    font-weight: 600;
    flex-shrink: 0;
}
.bar-track {
    flex: 1;
    height: 24px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}
.bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s;
    min-width: 2px;
}
.bar-value {
    width: 80px;
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-align: right;
    flex-shrink: 0;
}

/* Footer */
.footer {
    text-align: center;
    padding: 24px;
    color: var(--text-secondary);
    font-size: 0.8rem;
    border-top: 1px solid var(--border);
    margin-top: 24px;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
    font-size: 0.9rem;
}

/* Responsive */
@media (max-width: 768px) {
    .container { padding: 16px; }
    .header h1 { font-size: 1.5rem; }
    .header .stats-row { gap: 12px; }
    .cards-grid { grid-template-columns: 1fr; }
    .candidates-list { grid-template-columns: 1fr; }
    .model-cards { grid-template-columns: 1fr; }
    table { font-size: 0.8rem; }
    th, td { padding: 8px 10px; }
}
"""

JS = """
function sortTable(tableId, colIdx) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const th = table.querySelectorAll('th')[colIdx];
    const asc = !th.classList.contains('sorted-asc');

    table.querySelectorAll('th').forEach(h => {
        h.classList.remove('sorted', 'sorted-asc', 'sorted-desc');
    });
    th.classList.add('sorted', asc ? 'sorted-asc' : 'sorted-desc');

    rows.sort((a, b) => {
        let va = a.cells[colIdx].getAttribute('data-sort') || a.cells[colIdx].textContent.trim();
        let vb = b.cells[colIdx].getAttribute('data-sort') || b.cells[colIdx].textContent.trim();
        const na = parseFloat(va), nb = parseFloat(vb);
        if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
        return asc ? va.localeCompare(vb) : vb.localeCompare(va);
    });
    rows.forEach(r => tbody.appendChild(r));
}
"""


def _esc(s):
    if s is None:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_html(data):
    journals = data["journals"]
    totals = data["totals"]
    training = data["training"]
    feedback = data["feedback"]
    recs = data["recommendations"]
    pending = data["pending"]

    parts = []
    parts.append(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Editorial Dashboard</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
"""
    )

    # Header
    parts.append(
        f"""
<div class="header">
    <h1>Editorial Dashboard</h1>
    <div class="subtitle">Generated {_esc(data['generated_at'])}</div>
    <div class="stats-row">
        <span class="stat-pill"><strong>{totals['active_journals']}</strong> / {len(journals)} journals</span>
        <span class="stat-pill"><strong>{totals['manuscripts']}</strong> manuscripts</span>
        <span class="stat-pill"><strong>{totals['referees']}</strong> referees</span>
        <span class="stat-pill"><strong>{totals['authors']}</strong> authors</span>
    </div>
</div>
"""
    )

    # Journal status cards
    parts.append(
        '<div class="section"><div class="section-title">Journal Status</div><div class="cards-grid">'
    )
    for s in journals:
        enrich = f"{s['enrichment_pct']:.0f}%" if s["total_people"] > 0 else "--"
        parts.append(
            f"""
<div class="card">
    <div class="card-header">
        <h3>{_esc(s['journal_name'])}</h3>
        <span class="platform">{_esc(s['platform'])}</span>
    </div>
    <div class="card-stats">
        <div class="card-stat"><div class="val">{s['manuscripts']}</div><div class="lbl">Manuscripts</div></div>
        <div class="card-stat"><div class="val">{s['referees']}</div><div class="lbl">Referees</div></div>
        <div class="card-stat"><div class="val">{enrich}</div><div class="lbl">Enriched</div></div>
    </div>
    <div class="card-footer">
        <span>{_esc(s['extraction_date']) or 'No extraction'}</span>
        <span class="badge {s['freshness_class']}">{_esc(s['freshness_label'])}</span>
    </div>
</div>"""
        )
    parts.append("</div></div>")

    # Pending manuscripts
    parts.append(
        '<div class="section"><div class="section-title">Pending Manuscripts (Awaiting Referee Assignment)</div>'
    )
    if pending:
        parts.append(
            """<div class="table-wrapper"><table id="pending-table">
<thead><tr>
    <th onclick="sortTable('pending-table',0)">MS ID <span class="sort-arrow">&#9650;</span></th>
    <th onclick="sortTable('pending-table',1)">Title <span class="sort-arrow">&#9650;</span></th>
    <th onclick="sortTable('pending-table',2)">Journal <span class="sort-arrow">&#9650;</span></th>
    <th onclick="sortTable('pending-table',3)">Status <span class="sort-arrow">&#9650;</span></th>
</tr></thead><tbody>"""
        )
        for m in pending:
            title_short = m["title"][:80] + ("..." if len(m["title"]) > 80 else "")
            parts.append(
                f"""<tr>
    <td><strong>{_esc(m['manuscript_id'])}</strong></td>
    <td>{_esc(title_short)}</td>
    <td>{_esc(m['journal'])}</td>
    <td>{_esc(m['status'])}</td>
</tr>"""
            )
        parts.append("</tbody></table></div>")
    else:
        parts.append(
            '<div class="empty-state">No manuscripts currently awaiting referee assignment.</div>'
        )
    parts.append("</div>")

    # Recent recommendations
    parts.append(
        '<div class="section"><div class="section-title">Recent Pipeline Recommendations</div>'
    )
    if recs:
        for r in recs:
            desk_class = "desk-reject" if r["desk_reject"] else "desk-pass"
            desk_text = "Desk Reject" if r["desk_reject"] else "Pass"
            title_short = r["title"][:90] + ("..." if len(r["title"]) > 90 else "")
            parts.append(
                f"""
<div class="rec-card">
    <div class="rec-header">
        <div class="ms-info">
            <h4>{_esc(r['manuscript_id'])} &mdash; {_esc(title_short)}</h4>
            <div class="ms-meta">{_esc(r['journal'])} &middot; {_esc(r['generated_at'])}</div>
        </div>
        <span class="desk-badge {desk_class}">{desk_text}</span>
    </div>
    <div class="candidates-list">"""
            )
            for i, c in enumerate(r["top_candidates"]):
                parts.append(
                    f"""
        <div class="candidate">
            <div class="c-name">#{i+1} {_esc(c['name'])}</div>
            <div class="c-details">{_esc(c['institution'])} &middot; h={c['h_index']}</div>
            <span class="c-score">{c['score']:.2f} &middot; {_esc(c['source'])}</span>
        </div>"""
                )
            parts.append("</div></div>")
    else:
        parts.append(
            '<div class="empty-state">No recommendations generated yet. Run: python3 run_pipeline.py --journal sicon --pending</div>'
        )
    parts.append("</div>")

    # ML Model Training
    parts.append(
        '<div class="section"><div class="section-title">ML Model Training</div><div class="model-cards">'
    )
    if training:
        trained_at = training.get("trained_at", "?")[:16].replace("T", " ")
        commit = training.get("commit", "?")

        # Expertise Index
        ei = training.get("expertise_index", {})
        ei_status = ei.get("status", "unknown")
        parts.append(
            f"""
<div class="model-card">
    <h4>Expertise Index (FAISS)</h4>
    <div class="model-metric"><span class="label">Status</span><span class="badge {_model_status_class(ei_status)}">{_esc(ei_status)}</span></div>
    <div class="model-metric"><span class="label">Referees indexed</span><span class="value">{ei.get('n_referees', 0)}</span></div>
    <div class="model-metric"><span class="label">Trained</span><span class="value">{_esc(trained_at)}</span></div>
</div>"""
        )

        # Response Predictor
        rp = training.get("response_predictor", {})
        rp_status = rp.get("status", "unknown")
        cv_acc = f"{rp.get('cv_accuracy', 0):.1%}" if rp.get("cv_accuracy") else "--"
        parts.append(
            f"""
<div class="model-card">
    <h4>Response Predictor</h4>
    <div class="model-metric"><span class="label">Status</span><span class="badge {_model_status_class(rp_status)}">{_esc(rp_status)}</span></div>
    <div class="model-metric"><span class="label">CV Accuracy</span><span class="value">{cv_acc}</span></div>
    <div class="model-metric"><span class="label">Training samples</span><span class="value">{rp.get('n_samples', 0)}</span></div>
    <div class="model-metric"><span class="label">Positive rate</span><span class="value">{rp.get('positive_rate', 0):.1%}</span></div>
    <div class="model-metric"><span class="label">Completion accuracy</span><span class="value">{rp.get('completion_cv_accuracy', 0):.1%}</span></div>
</div>"""
        )

        # Outcome Predictor
        op = training.get("outcome_predictor", {})
        op_status = op.get("status", "unknown")
        op_acc = f"{op.get('cv_accuracy', 0):.1%}" if op.get("cv_accuracy") else "--"
        parts.append(
            f"""
<div class="model-card">
    <h4>Outcome Predictor</h4>
    <div class="model-metric"><span class="label">Status</span><span class="badge {_model_status_class(op_status)}">{_esc(op_status)}</span></div>
    <div class="model-metric"><span class="label">CV Accuracy</span><span class="value">{op_acc}</span></div>
    <div class="model-metric"><span class="label">Baseline accuracy</span><span class="value">{op.get('baseline_accuracy', 0):.1%}</span></div>
    <div class="model-metric"><span class="label">Training samples</span><span class="value">{op.get('n_samples', 0)}</span></div>
    <div class="model-metric"><span class="label">Commit</span><span class="value">{_esc(commit)}</span></div>
</div>"""
        )
    else:
        parts.append(
            '<div class="empty-state">No training metadata found. Run: python3 run_pipeline.py --train</div>'
        )
    parts.append("</div></div>")

    # Extraction Freshness
    parts.append(
        '<div class="section"><div class="section-title">Extraction Freshness</div><div class="freshness-bars">'
    )
    max_age = max((s.get("age_days") or 0) for s in journals) or 1
    for s in sorted(journals, key=lambda x: x.get("age_days") or 999):
        age = s.get("age_days")
        if age is None:
            pct = 0
            color = "var(--grey)"
        else:
            pct = min(100, (age / max(max_age, 1)) * 100)
            if age <= 7:
                color = "var(--green)"
            elif age <= 14:
                color = "var(--amber)"
            else:
                color = "var(--red)"
        parts.append(
            f"""
<div class="bar-row">
    <span class="bar-label">{_esc(s['journal'])}</span>
    <div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%;background:{color}"></div></div>
    <span class="bar-value">{_esc(s['freshness_label'])}</span>
</div>"""
        )
    parts.append("</div></div>")

    # Feedback Summary
    parts.append('<div class="section"><div class="section-title">Feedback Summary</div>')
    if feedback:
        total_fb = sum(s["total"] for s in feedback.values())
        parts.append(
            """<div class="table-wrapper"><table id="feedback-table">
<thead><tr>
    <th onclick="sortTable('feedback-table',0)">Journal <span class="sort-arrow">&#9650;</span></th>
    <th onclick="sortTable('feedback-table',1)">Total <span class="sort-arrow">&#9650;</span></th>
    <th>Decisions</th>
</tr></thead><tbody>"""
        )
        for journal, s in sorted(feedback.items()):
            decisions = ", ".join(f"{k}: {v}" for k, v in s["decisions"].items())
            parts.append(
                f"""<tr>
    <td><strong>{_esc(journal.upper())}</strong></td>
    <td data-sort="{s['total']}">{s['total']}</td>
    <td>{_esc(decisions)}</td>
</tr>"""
            )
        parts.append(
            f"""</tbody></table></div>
<div style="text-align:center;padding:12px;color:var(--text-secondary);font-size:0.85rem">{total_fb} outcomes recorded</div>"""
        )
    else:
        parts.append(
            '<div class="empty-state">No feedback recorded yet. Record decisions with: python3 run_pipeline.py --record-outcome -j sicon -m M178221 --decision accept</div>'
        )
    parts.append("</div>")

    # Footer
    parts.append(
        f"""
<div class="footer">
    Generated {_esc(data['generated_at'])} &middot; git {_esc(data['git_commit'])} &middot; editorial-scripts
</div>
</div>
<script>{JS}</script>
</body>
</html>"""
    )

    return "".join(parts)


def main():
    data = build_dashboard_data()
    html = generate_html(data)
    out_path = OUTPUTS_DIR / "dashboard.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {out_path}")
    print(f"  Journals: {data['totals']['active_journals']}/{len(data['journals'])}")
    print(f"  Manuscripts: {data['totals']['manuscripts']}")
    print(f"  Recommendations: {len(data['recommendations'])}")
    print(f"  Pending: {len(data['pending'])}")


if __name__ == "__main__":
    main()
