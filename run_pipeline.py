#!/usr/bin/env python3
"""
Referee recommendation pipeline CLI.

Usage:
    python3 run_pipeline.py --journal sicon --manuscript M178221
    python3 run_pipeline.py --journal sicon --pending
    python3 run_pipeline.py --journal sicon --manuscript M178221 --llm
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "production" / "src"))

from pipeline.referee_pipeline import RefereePipeline


def main():
    parser = argparse.ArgumentParser(
        description="Referee Recommendation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 run_pipeline.py -j sicon -m M178221       Single manuscript
  python3 run_pipeline.py -j sicon --pending         All pending manuscripts
  python3 run_pipeline.py -j sicon -m M178221 --llm  With LLM desk-rejection""",
    )
    parser.add_argument(
        "--journal",
        "-j",
        required=True,
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
    args = parser.parse_args()

    if not args.manuscript and not args.pending:
        parser.error("Specify --manuscript ID or --pending")

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
