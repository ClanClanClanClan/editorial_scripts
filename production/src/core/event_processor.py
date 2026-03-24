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
    except Exception:
        pass


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

        if event_type == "ALL_REPORTS_IN":
            ae_candidates.append((journal, ms_id))
        elif event_type == "NEW_MANUSCRIPT":
            new_manuscripts.append((journal, ms_id))

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

    if new_manuscripts:
        print(f"\n📝 {len(new_manuscripts)} new manuscript(s) detected:")
        for journal, ms_id in new_manuscripts:
            print(f"   {journal.upper()}/{ms_id}")

        try:
            from pipeline.referee_pipeline import RefereePipeline

            pipeline = RefereePipeline(use_llm=False)
            for journal, ms_id in new_manuscripts:
                print(f"\n🔍 Running referee pipeline for {journal.upper()}/{ms_id}...")
                try:
                    pipeline.run_single(journal, ms_id)
                except Exception as e:
                    print(f"   Pipeline error for {journal.upper()}/{ms_id}: {e}")
        except ImportError:
            print("   (referee pipeline not available — skipping auto-pipeline)")

        _notify(
            "New Manuscripts",
            f"{len(new_manuscripts)} new manuscript(s) processed",
        )

    mark_processed(processed)
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
