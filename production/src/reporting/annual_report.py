"""Generate annual editorial statistics report."""

import json
from datetime import date, datetime

from pipeline import JOURNALS, MODELS_DIR, OUTPUTS_DIR

from reporting.cross_journal_report import (
    JOURNAL_NAMES,
    PLATFORMS,
    compute_journal_stats,
    load_journal_data,
)

REPORTS_DIR = OUTPUTS_DIR / "reports"
FEEDBACK_DIR = MODELS_DIR / "feedback"


def generate_annual_report(start_date, end_date, journals=None):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    target_journals = journals or JOURNALS

    per_journal = {}
    total_manuscripts = 0
    total_accepted = 0
    total_decided = 0
    all_decision_days = []

    for journal in target_journals:
        data = load_journal_data(journal)
        if not data:
            continue

        manuscripts = data.get("manuscripts", [])
        filtered = _filter_manuscripts_by_date(manuscripts, start, end)
        if not filtered:
            per_journal[journal] = {
                "journal_name": JOURNAL_NAMES.get(journal, journal),
                "platform": PLATFORMS.get(journal, ""),
                "total_manuscripts": 0,
                "acceptance_rate": None,
                "avg_days_to_decision": None,
            }
            continue

        stats = compute_journal_stats(journal, data)
        accepted = 0
        decided = 0
        decision_days = []

        for ms in filtered:
            status = (ms.get("status") or "").lower()
            if status in ("accepted", "accept"):
                accepted += 1
                decided += 1
            elif status in ("rejected", "reject"):
                decided += 1

            sub_date = _parse_date(ms.get("submission_date"))
            dec_date = _parse_date(ms.get("decision_date"))
            if sub_date and dec_date:
                delta = (dec_date - sub_date).days
                if 0 < delta < 1000:
                    decision_days.append(delta)

        acceptance_rate = round(accepted / decided, 3) if decided > 0 else None
        avg_decision_days = (
            round(sum(decision_days) / len(decision_days), 1) if decision_days else None
        )

        per_journal[journal] = {
            "journal_name": JOURNAL_NAMES.get(journal, journal),
            "platform": PLATFORMS.get(journal, ""),
            "total_manuscripts": len(filtered),
            "accepted": accepted,
            "decided": decided,
            "acceptance_rate": acceptance_rate,
            "avg_days_to_decision": avg_decision_days,
            "avg_span_days": stats.get("avg_span_days"),
            "avg_response_days": stats.get("avg_response_days"),
        }

        total_manuscripts += len(filtered)
        total_accepted += accepted
        total_decided += decided
        all_decision_days.extend(decision_days)

    referee_pool = _compute_referee_pool_stats(start, end)
    decision_stats = _compute_decision_stats(start, end)

    summary = {
        "total_manuscripts": total_manuscripts,
        "total_decided": total_decided,
        "total_accepted": total_accepted,
        "overall_acceptance_rate": (
            round(total_accepted / total_decided, 3) if total_decided > 0 else None
        ),
        "avg_days_to_decision": (
            round(sum(all_decision_days) / len(all_decision_days), 1) if all_decision_days else None
        ),
        "journals_covered": len(per_journal),
    }

    return {
        "period": {"start": start_date, "end": end_date},
        "summary": summary,
        "per_journal": per_journal,
        "referee_pool": referee_pool,
        "decision_breakdown": decision_stats,
        "generated_at": datetime.now().isoformat(),
    }


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value if isinstance(value, date) else value.date()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(value)[:19], fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _filter_manuscripts_by_date(manuscripts, start, end):
    filtered = []
    for ms in manuscripts:
        sub_date = _parse_date(ms.get("submission_date"))
        if sub_date and start <= sub_date <= end:
            filtered.append(ms)
    return filtered


def _compute_referee_pool_stats(start, end):
    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        with db._lock:
            with db._connection() as conn:
                total = conn.execute("SELECT COUNT(*) FROM referee_profiles").fetchone()[0]

                new_referees = conn.execute(
                    "SELECT COUNT(*) FROM referee_profiles WHERE first_seen >= ? AND first_seen <= ?",
                    (start.isoformat(), end.isoformat()),
                ).fetchone()[0]

                row = conn.execute(
                    "SELECT AVG(avg_review_days), AVG(CASE WHEN total_invitations > 0 "
                    "THEN CAST(total_accepted AS REAL) / total_invitations END) "
                    "FROM referee_profiles WHERE total_invitations > 0"
                ).fetchone()
                avg_review_days = round(row[0], 1) if row[0] else None
                avg_acceptance_rate = round(row[1], 3) if row[1] else None

                most_active = []
                rows = conn.execute(
                    "SELECT display_name, total_completed FROM referee_profiles "
                    "ORDER BY total_completed DESC LIMIT 10"
                ).fetchall()
                for r in rows:
                    most_active.append(
                        {"name": r["display_name"], "completed_reviews": r["total_completed"]}
                    )

        return {
            "total_referees": total,
            "new_referees_in_period": new_referees,
            "avg_acceptance_rate": avg_acceptance_rate,
            "avg_review_days": avg_review_days,
            "most_active": most_active,
        }
    except Exception:
        return {
            "total_referees": None,
            "new_referees_in_period": None,
            "avg_acceptance_rate": None,
            "avg_review_days": None,
            "most_active": [],
        }


def _compute_decision_stats(start, end):
    decisions = {}
    for f in FEEDBACK_DIR.glob("*_outcomes.jsonl"):
        try:
            with open(f) as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                        ts = rec.get("timestamp", "")
                        rec_date = _parse_date(ts)
                        if rec_date and start <= rec_date <= end:
                            d = rec.get("decision", "unknown")
                            decisions[d] = decisions.get(d, 0) + 1
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            continue
    return decisions


def save_annual_report(report):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    period = report["period"]
    tag = f"{period['start']}_to_{period['end']}"

    json_path = REPORTS_DIR / f"annual_report_{tag}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    md_lines = [
        "# Annual Editorial Report",
        "",
        f"**Period**: {period['start']} to {period['end']}",
        f"**Generated**: {report['generated_at']}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]
    s = report["summary"]
    md_lines.append(f"| Total Manuscripts | {s['total_manuscripts']} |")
    md_lines.append(f"| Decided | {s['total_decided']} |")
    md_lines.append(f"| Accepted | {s['total_accepted']} |")
    rate = f"{s['overall_acceptance_rate']:.1%}" if s["overall_acceptance_rate"] else "N/A"
    md_lines.append(f"| Acceptance Rate | {rate} |")
    days = f"{s['avg_days_to_decision']}d" if s["avg_days_to_decision"] else "N/A"
    md_lines.append(f"| Avg Days to Decision | {days} |")
    md_lines.append(f"| Journals Covered | {s['journals_covered']} |")

    md_lines.extend(["", "## Per-Journal Breakdown", ""])
    md_lines.append("| Journal | Manuscripts | Acceptance Rate | Avg Decision Days |")
    md_lines.append("|---------|-------------|-----------------|-------------------|")
    for _journal, js in report["per_journal"].items():
        name = js["journal_name"]
        total = js["total_manuscripts"]
        ar = f"{js['acceptance_rate']:.1%}" if js["acceptance_rate"] is not None else "N/A"
        ad = f"{js['avg_days_to_decision']}d" if js["avg_days_to_decision"] else "N/A"
        md_lines.append(f"| {name} | {total} | {ar} | {ad} |")

    rp = report.get("referee_pool", {})
    if rp.get("total_referees"):
        md_lines.extend(["", "## Referee Pool", ""])
        md_lines.append(f"- Total referees: {rp['total_referees']}")
        md_lines.append(f"- New in period: {rp.get('new_referees_in_period', 'N/A')}")
        if rp.get("avg_acceptance_rate"):
            md_lines.append(f"- Avg invitation acceptance rate: {rp['avg_acceptance_rate']:.1%}")
        if rp.get("avg_review_days"):
            md_lines.append(f"- Avg review turnaround: {rp['avg_review_days']}d")
        if rp.get("most_active"):
            md_lines.extend(["", "### Most Active Reviewers", ""])
            for r in rp["most_active"][:5]:
                md_lines.append(f"- {r['name']}: {r['completed_reviews']} reviews")

    dd = report.get("decision_breakdown", {})
    if dd:
        md_lines.extend(["", "## Decision Breakdown", ""])
        for decision, count in sorted(dd.items(), key=lambda x: -x[1]):
            md_lines.append(f"- {decision}: {count}")

    md_path = REPORTS_DIR / f"annual_report_{tag}.md"
    md_path.write_text("\n".join(md_lines) + "\n")

    return json_path, md_path
