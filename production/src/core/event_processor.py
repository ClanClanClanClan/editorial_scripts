"""Event processor — reads pending events and dispatches actions."""

import subprocess
import sys
from pathlib import Path

from core.event_dispatcher import get_pending_events, mark_processed


def _notify(title: str, message: str):
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}" sound name "Glass"',
            ],
            check=False,
            timeout=5,
        )
    except Exception as e:
        print(f"  ⚠️ Notification failed: {e}")


def _record_outcomes(events: list[dict]):
    try:
        from pipeline import normalize_name_orderless
        from pipeline.referee_db import RefereeDB
        from reporting.cross_journal_report import load_journal_data

        relevant = [e for e in events if e.get("type") in ("STATUS_CHANGED", "ALL_REPORTS_IN")]
        if not relevant:
            return

        db = RefereeDB()
        journals_loaded = {}

        for event in relevant:
            journal = event.get("journal", "")
            ms_id = event.get("manuscript_id", "")
            if not journal or not ms_id:
                continue

            if journal not in journals_loaded:
                journals_loaded[journal] = load_journal_data(journal)

            data = journals_loaded[journal]
            if not data:
                continue

            for ms in data.get("manuscripts", []):
                if ms.get("manuscript_id") != ms_id:
                    continue
                for ref in ms.get("referees", []):
                    name = ref.get("name", "")
                    if not name:
                        continue
                    status = (ref.get("status") or "").lower()
                    dates = ref.get("dates") or {}
                    returned_date = dates.get("returned")

                    if "decline" in status or "terminated" in status:
                        response = "declined"
                    elif returned_date or status in (
                        "report submitted",
                        "review complete",
                        "completed",
                    ):
                        response = "accepted"
                    else:
                        continue

                    try:
                        key = normalize_name_orderless(name)
                        db._update_assignment_outcome(key, journal, ms_id, response, returned_date)
                    except Exception as e:
                        print(f"  ⚠️ Outcome update failed for {name}: {e}", file=sys.stderr)
                break

        try:
            db.resolve_predictions()
        except Exception as e:
            print(f"  ⚠️ Prediction resolution failed: {e}", file=sys.stderr)

    except Exception as e:
        print(f"  ⚠️ Outcome recording failed (non-critical): {e}")


def process_all(provider: str = "claude") -> list[dict]:
    events = get_pending_events()
    if not events:
        print("No pending events.")
        return []

    print(f"\n📬 Processing {len(events)} pending event(s)...\n")
    processed = []

    ae_candidates = []
    new_manuscripts = []

    for event in events:
        event_type = event.get("type", "")
        journal = event.get("journal", "")
        ms_id = event.get("manuscript_id", "")
        source_file = event.get("source_file")

        if event_type == "ALL_REPORTS_IN":
            ae_candidates.append((journal, ms_id))
        elif event_type == "NEW_MANUSCRIPT":
            new_manuscripts.append((journal, ms_id, source_file))

        processed.append(event)

    if ae_candidates:
        from pipeline.ae_report import generate

        for journal, ms_id in ae_candidates:
            print(f"\n🔄 Generating AE report for {journal.upper()}/{ms_id}...")
            result = generate(journal, ms_id, provider=provider)
            if result and result.get("recommendation"):
                _notify(
                    "AE Report Ready",
                    f"{journal.upper()}/{ms_id}: {result['recommendation']}",
                )
                try:
                    from core.email_notifications import send_event_notification

                    send_event_notification(
                        {
                            "type": "ALL_REPORTS_IN",
                            "journal": journal,
                            "manuscript_id": ms_id,
                        }
                    )
                except Exception as e:
                    print(f"  ⚠️ Email notification failed: {e}", file=sys.stderr)

    if new_manuscripts:
        print(f"\n📝 {len(new_manuscripts)} new manuscript(s) detected:")
        for journal, ms_id, _sf in new_manuscripts:
            print(f"   {journal.upper()}/{ms_id}")

        try:
            from pipeline.referee_pipeline import RefereePipeline

            pipeline = RefereePipeline(use_llm=False)
            for journal, ms_id, source_file in new_manuscripts:
                print(f"\n🔍 Running referee pipeline for {journal.upper()}/{ms_id}...")
                try:
                    kwargs = {}
                    if source_file:
                        kwargs["extraction_path"] = source_file
                    pipeline.run_single(journal, ms_id, **kwargs)
                    try:
                        from pipeline.manuscript_similarity import (
                            find_similar_manuscripts,
                        )
                        from reporting.cross_journal_report import load_journal_data

                        ms_data = load_journal_data(journal)
                        if ms_data:
                            for ms in ms_data.get("manuscripts", []):
                                if ms.get("manuscript_id") == ms_id:
                                    similar = find_similar_manuscripts(
                                        ms.get("title", ""),
                                        ms.get("abstract", ""),
                                        top_k=3,
                                    )
                                    if similar:
                                        print(f"   Similar manuscripts: {len(similar)} found")
                                    break
                    except Exception as e:
                        print(f"  ⚠️ Similarity check failed: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"   Pipeline error for {journal.upper()}/{ms_id}: {e}")
        except ImportError:
            print("   (referee pipeline not available — skipping auto-pipeline)")

        for journal, ms_id, _sf in new_manuscripts:
            try:
                from core.email_notifications import send_event_notification

                send_event_notification(
                    {
                        "type": "NEW_MANUSCRIPT",
                        "journal": journal,
                        "manuscript_id": ms_id,
                    }
                )
            except Exception as e:
                print(f"  ⚠️ Email notification failed: {e}", file=sys.stderr)

        _notify(
            "New Manuscripts",
            f"{len(new_manuscripts)} new manuscript(s) processed",
        )

    mark_processed(processed)
    _record_outcomes(processed)
    print(f"\n✅ Processed {len(processed)} event(s)")
    return processed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process pending editorial events")
    parser.add_argument(
        "--provider",
        choices=["claude", "clipboard"],
        default="claude",
        help="LLM provider for AE reports (default: claude)",
    )
    args = parser.parse_args()
    process_all(provider=args.provider)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
