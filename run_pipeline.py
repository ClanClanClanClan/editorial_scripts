#!/usr/bin/env python3
"""
Referee recommendation pipeline CLI.

Usage:
    python3 run_pipeline.py --journal sicon --manuscript M178221
    python3 run_pipeline.py --journal sicon --pending
    python3 run_pipeline.py --journal sicon --manuscript M178221 --llm
    python3 run_pipeline.py --train
    python3 run_pipeline.py --rebuild-index
    python3 run_pipeline.py --record-outcome -j sicon -m M178221 --decision accept
    python3 run_pipeline.py --interactive -j sicon
    python3 run_pipeline.py --feedback-stats
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "production" / "src"))

from pipeline.referee_pipeline import RefereePipeline  # noqa: E402

RETRAIN_THRESHOLD = 5


def _print_feedback_stats():
    from pipeline.training import ModelTrainer

    trainer = ModelTrainer()
    stats = trainer.get_feedback_stats()
    if not stats:
        print("No feedback recorded yet.")
        return
    total = sum(s["total"] for s in stats.values())
    print(f"\nFeedback: {total} outcomes recorded")
    for journal, s in sorted(stats.items()):
        decisions = ", ".join(f"{k}: {v}" for k, v in s["decisions"].items())
        print(f"  {journal.upper()}: {s['total']} — {decisions}")


def _maybe_retrain_after_feedback():
    from pipeline import MODELS_DIR
    from pipeline.training import ModelTrainer

    trainer = ModelTrainer()
    stats = trainer.get_feedback_stats()
    total = sum(s["total"] for s in stats.values())
    count_file = MODELS_DIR / ".last_feedback_count"
    last_count = 0
    if count_file.exists():
        try:
            last_count = int(count_file.read_text().strip())
        except ValueError:
            pass
    new_outcomes = total - last_count
    if new_outcomes >= RETRAIN_THRESHOLD:
        print(f"\n{new_outcomes} new outcomes since last training — retraining models...")
        trainer.train_all()
        count_file.write_text(str(total))
    else:
        remaining = RETRAIN_THRESHOLD - new_outcomes
        print(f"\n{new_outcomes} new outcomes ({remaining} more until auto-retrain)")


def _run_interactive(journal):
    from pipeline import OUTPUTS_DIR
    from pipeline.training import ModelTrainer

    journal_dir = OUTPUTS_DIR / journal
    if not journal_dir.exists():
        print(f"No extraction data for {journal}")
        return

    files = sorted(journal_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    data_file = None
    for f in files:
        if "BASELINE" not in f.name and "debug" not in str(f):
            data_file = f
            break
    if not data_file:
        print(f"No extraction file found for {journal}")
        return

    import json

    with open(data_file) as fh:
        data = json.load(fh)

    manuscripts = data.get("manuscripts", [])
    if not manuscripts:
        print(f"No manuscripts in {data_file.name}")
        return

    trainer = ModelTrainer()
    recorded = 0
    print(f"\n{'='*60}")
    print(f"  Interactive feedback: {journal.upper()} ({len(manuscripts)} manuscripts)")
    print(f"  Source: {data_file.name}")
    print(f"{'='*60}")

    for ms in manuscripts:
        ms_id = ms.get("manuscript_id", "?")
        title = ms.get("title", "?")
        status = ms.get("status", "?")
        n_refs = len(ms.get("referees", []))

        print(f"\n  {ms_id}: {title[:70]}")
        print(f"  Status: {status} | Referees: {n_refs}")
        try:
            decision = (
                input("  Decision [accept/reject/revise/desk_reject/skip/quit]: ").strip().lower()
            )
        except (EOFError, KeyboardInterrupt):
            print("\n  Quitting.")
            break
        if decision == "quit" or decision == "q":
            break
        if decision in ("accept", "reject", "revise", "desk_reject"):
            trainer.record_outcome(journal, ms_id, decision)
            recorded += 1
        elif decision in ("skip", "s", ""):
            continue
        else:
            print(f"  Unknown '{decision}', skipping")

    print(f"\n  Recorded {recorded} outcomes.")
    if recorded > 0:
        _maybe_retrain_after_feedback()


def main():
    parser = argparse.ArgumentParser(
        description="Referee Recommendation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 run_pipeline.py -j sicon -m M178221       Single manuscript
  python3 run_pipeline.py -j sicon --pending         All pending manuscripts
  python3 run_pipeline.py -j sicon -m M178221 --llm  With LLM desk-rejection
  python3 run_pipeline.py --train                     Train all ML models
  python3 run_pipeline.py --rebuild-index             Rebuild FAISS referee index
  python3 run_pipeline.py --record-outcome -j sicon -m M178221 --decision accept
  python3 run_pipeline.py --interactive -j sicon      Record decisions interactively
  python3 run_pipeline.py --feedback-stats            Show recorded feedback""",
    )
    parser.add_argument(
        "--journal",
        "-j",
        choices=["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"],
        help="Journal code",
    )
    parser.add_argument("--manuscript", "-m", help="Specific manuscript ID")
    parser.add_argument("--pending", action="store_true", help="Process all pending manuscripts")
    parser.add_argument(
        "--llm", action="store_true", help="Enable LLM desk-rejection (needs ANTHROPIC_API_KEY)"
    )
    parser.add_argument(
        "--max-candidates", type=int, default=15, help="Max referee candidates (default: 15)"
    )
    parser.add_argument("--train", action="store_true", help="Train/retrain all ML models")
    parser.add_argument(
        "--validate", action="store_true", help="Run model validation and print metrics"
    )
    parser.add_argument(
        "--rebuild-index", action="store_true", help="Rebuild FAISS expertise index"
    )
    parser.add_argument(
        "--record-outcome", action="store_true", help="Record an editorial decision"
    )
    parser.add_argument(
        "--decision",
        choices=["accept", "reject", "revise", "desk_reject"],
        help="Decision (use with --record-outcome)",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Interactive mode: review and record decisions"
    )
    parser.add_argument(
        "--feedback-stats", action="store_true", help="Show recorded feedback statistics"
    )
    args = parser.parse_args()

    if args.feedback_stats:
        _print_feedback_stats()
        return

    if args.record_outcome:
        if not args.journal or not args.manuscript or not args.decision:
            parser.error("--record-outcome requires --journal, --manuscript, and --decision")
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        trainer.record_outcome(args.journal, args.manuscript, args.decision)
        _print_feedback_stats()
        _maybe_retrain_after_feedback()
        return

    if args.interactive:
        if not args.journal:
            parser.error("--interactive requires --journal")
        _run_interactive(args.journal)
        return

    if args.train:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        trainer.train_all()
        print("\nTraining complete.")
        return

    if args.validate:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        trainer.train_all()
        _print_feedback_stats()
        return

    if args.rebuild_index:
        from pipeline.models.expertise_index import ExpertiseIndex

        idx = ExpertiseIndex()
        n = idx.build()
        if n > 0:
            idx.save()
            print(f"Index rebuilt: {n} referees")
        else:
            print("No referee data found to index")
        return

    if not args.journal:
        parser.error("--journal is required with --manuscript or --pending")
    if not args.manuscript and not args.pending:
        parser.error("Specify --manuscript ID, --pending, --train, --validate, or --rebuild-index")

    pipeline = RefereePipeline(use_llm=args.llm, max_candidates=args.max_candidates)

    if args.manuscript:
        report = pipeline.run_single(args.journal, args.manuscript)
        if not report:
            sys.exit(1)
    elif args.pending:
        reports = pipeline.run_pending(args.journal)
        if not reports:
            print("No manuscripts processed.")


if __name__ == "__main__":
    main()
