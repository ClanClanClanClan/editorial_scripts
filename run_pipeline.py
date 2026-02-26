#!/usr/bin/env python3
"""
Referee recommendation pipeline CLI.

Usage:
    python3 run_pipeline.py --journal sicon --manuscript M178221
    python3 run_pipeline.py --journal sicon --pending
    python3 run_pipeline.py --journal sicon --manuscript M178221 --llm
    python3 run_pipeline.py --train
    python3 run_pipeline.py --rebuild-index
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "production" / "src"))

from pipeline.referee_pipeline import RefereePipeline


def main():
    parser = argparse.ArgumentParser(
        description="Referee Recommendation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 run_pipeline.py -j sicon -m M178221       Single manuscript
  python3 run_pipeline.py -j sicon --pending         All pending manuscripts
  python3 run_pipeline.py -j sicon -m M178221 --llm  With LLM desk-rejection
  python3 run_pipeline.py --train                     Train all ML models
  python3 run_pipeline.py --rebuild-index             Rebuild FAISS referee index""",
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
    args = parser.parse_args()

    if args.train:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        results = trainer.train_all()
        print("\nTraining complete.")
        return

    if args.validate:
        from pipeline.training import ModelTrainer

        trainer = ModelTrainer()
        results = trainer.train_all()
        stats = trainer.get_feedback_stats()
        if stats:
            print("\nFeedback stats:")
            for journal, s in stats.items():
                print(f"  {journal}: {s['total']} outcomes — {s['decisions']}")
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
