"""Backfill referee performance database from historical extraction data."""

import json
import sys
from pathlib import Path

from pipeline import JOURNALS, OUTPUTS_DIR
from pipeline.referee_db import RefereeDB
from pipeline.report_quality import assess_report_quality


def _effective_dates(ref: dict) -> dict:
    dates = ref.get("dates") or {}
    ps = ref.get("platform_specific") or {}
    sd = ref.get("status_details") or {}
    return {
        "invited": dates.get("invited") or ps.get("invited_date") or sd.get("invited_date"),
        "agreed": dates.get("agreed") or ps.get("agreed_date") or sd.get("agreed_date"),
        "due": dates.get("due") or ps.get("due_date") or sd.get("due_date"),
        "returned": dates.get("returned") or ps.get("returned_date") or sd.get("returned_date"),
        "response_date": dates.get("responded") or dates.get("agreed") or dates.get("declined"),
    }


def backfill(incremental: bool = False):
    db = RefereeDB()
    total_refs = 0
    total_assignments = 0

    for journal in JOURNALS:
        journal_dir = OUTPUTS_DIR / journal
        if not journal_dir.exists():
            continue

        files = sorted(journal_dir.glob(f"{journal}_extraction_*.json"))
        if not files:
            continue

        if incremental:
            files = files[-1:]

        seen = set()
        for filepath in files:
            try:
                with open(filepath) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            for ms in data.get("manuscripts", []):
                ms_id = ms.get("manuscript_id", "")
                if not ms_id:
                    continue

                rq = assess_report_quality(ms)
                quality_map = {}
                for rpt in rq.get("reports", []):
                    reviewer = rpt.get("reviewer", "").lower()
                    if reviewer:
                        quality_map[reviewer] = rpt.get("overall")

                for ref in ms.get("referees", []):
                    name = ref.get("name", "")
                    if not name:
                        continue

                    dedup_key = (name.lower(), journal, ms_id)
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    dates = _effective_dates(ref)
                    status = ref.get("status", "")
                    rec = ref.get("recommendation", "")
                    report = ref.get("report") or {}
                    if not rec:
                        rec = report.get("recommendation", "")

                    wp = ref.get("web_profile") or {}
                    h_index = wp.get("h_index")
                    topics = wp.get("research_topics", [])

                    quality_score = quality_map.get(name.lower())

                    word_count = None
                    if report.get("comments_to_author"):
                        word_count = len(report["comments_to_author"].split())

                    stats = ref.get("statistics") or {}
                    reminders = stats.get("reminders_received", 0)

                    db.record_assignment(
                        referee_name=name,
                        email=ref.get("email"),
                        journal=journal,
                        manuscript_id=ms_id,
                        dates=dates,
                        status=status,
                        recommendation=(
                            rec if rec and rec.lower() not in ("unknown", "n/a") else None
                        ),
                        institution=ref.get("institution"),
                        orcid=ref.get("orcid"),
                        h_index=h_index,
                        report_quality_score=quality_score,
                        report_word_count=word_count,
                        reminders=reminders,
                        research_topics=topics,
                    )
                    total_assignments += 1

        total_refs_journal = len({k for k in seen if k[1] == journal})
        if total_refs_journal:
            print(
                f"  {journal.upper()}: {total_refs_journal} referee assignments from {len(files)} file(s)"
            )
        total_refs += total_refs_journal

    print(
        f"\n✅ Backfill complete: {total_assignments} assignments, {total_refs} unique referee-journal pairs"
    )
    return total_assignments


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backfill referee performance database")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only process latest extraction per journal",
    )
    args = parser.parse_args()
    backfill(incremental=args.incremental)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
