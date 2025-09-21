#!/usr/bin/env python3
"""
Editorial Scripts Ultimate - Production Entry Point
The definitive, optimized system that actually works
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add paths for imports
sys.path.append(str(Path(__file__).parent))

from core.models.optimized_models import OptimizedExtractionResult
from extractors.siam.optimized_sicon_extractor import OptimizedSICONExtractor


class UltimateSystemManager:
    """Manager for the ultimate editorial scripts system"""

    JULY_11_BASELINE = {
        "total_manuscripts": 4,
        "total_referees": 13,
        "referees_with_emails": 13,
        "pdfs_downloaded": 4,
    }

    def __init__(self):
        self.setup_logging()
        self.results_dir = Path("ultimate_results")
        self.results_dir.mkdir(exist_ok=True)

    def setup_logging(self, log_level: str = "INFO"):
        """Setup comprehensive logging"""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        # Configure logging
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # File handler
        log_file = logs_dir / f"ultimate_system_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))

        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Silence noisy libraries
        logging.getLogger("playwright").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    async def extract_sicon(
        self, test_mode: bool = False, headless: bool = True
    ) -> OptimizedExtractionResult:
        """Extract SICON with optimized system"""
        logger = logging.getLogger(__name__)

        logger.info("🚀 Starting ULTIMATE SICON extraction")

        # Verify credentials
        if not self._verify_credentials():
            raise Exception(
                "Missing required credentials. Set ORCID_EMAIL and ORCID_PASSWORD environment variables."
            )

        # Create extractor
        output_dir = self.results_dir / "sicon"
        extractor = OptimizedSICONExtractor(output_dir=output_dir)

        try:
            # Perform extraction
            result = await extractor.extract(headless=headless, use_cache=True)

            # Save result
            self._save_result(result, "sicon")

            # Test against baseline if requested
            if test_mode:
                self._test_against_baseline(result)

            # Log final summary
            self._log_final_summary(result)

            return result

        except Exception as e:
            logger.error(f"❌ SICON extraction failed: {e}")
            raise

    def _verify_credentials(self) -> bool:
        """Verify required credentials are available"""
        required_vars = ["ORCID_EMAIL", "ORCID_PASSWORD"]
        missing = [var for var in required_vars if not os.getenv(var)]

        if missing:
            print(f"❌ Missing required environment variables: {missing}")
            print("\nPlease set:")
            for var in missing:
                print(f'  export {var}="your_value"')
            return False

        return True

    def _save_result(self, result: OptimizedExtractionResult, journal: str):
        """Save extraction result with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save main result
        result_file = self.results_dir / f"{journal}_ultimate_{timestamp}.json"
        result.save_to_file(result_file)

        # Save summary
        summary_file = self.results_dir / f"{journal}_summary_{timestamp}.txt"
        self._save_summary(result, summary_file)

        print(f"✅ Results saved to {result_file}")

    def _save_summary(self, result: OptimizedExtractionResult, summary_file: Path):
        """Save human-readable summary"""
        with open(summary_file, "w") as f:
            f.write(f"ULTIMATE EDITORIAL SCRIPTS - {result.journal.upper()} EXTRACTION SUMMARY\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Extraction Time: {result.extraction_time}\n")
            f.write(f"Session ID: {result.session_id}\n\n")

            f.write("RESULTS:\n")
            f.write(f"  📄 Manuscripts: {result.total_manuscripts}\n")
            f.write(
                f"  👥 Referees: {result.total_referees} ({result.referees_with_emails} with emails)\n"
            )
            f.write(f"  📁 PDFs: {result.pdfs_downloaded}\n")
            f.write(f"  🎯 Quality Score: {result.overall_quality_score:.2f}\n\n")

            f.write("PERFORMANCE:\n")
            f.write(f"  ⏱️  Duration: {result.extraction_duration_seconds:.1f}s\n")
            f.write(f"  📈 Success Rate: {result._calculate_success_rate():.1%}\n\n")

            f.write("REFEREE STATUS BREAKDOWN:\n")
            for status, count in result.referee_status_breakdown.items():
                f.write(f"  {status}: {count}\n")

            f.write("\nMANUSCRIPTS:\n")
            for i, manuscript in enumerate(result.manuscripts, 1):
                f.write(f"  {i}. {manuscript.id}: {manuscript.title[:60]}...\n")
                f.write(
                    f"     Authors: {len(manuscript.authors)}, Referees: {len(manuscript.referees)}, PDFs: {len(manuscript.pdf_paths)}\n"
                )

    def _test_against_baseline(self, result: OptimizedExtractionResult):
        """Test extraction result against July 11 baseline"""
        logger = logging.getLogger(__name__)

        logger.info("🧪 Testing against July 11 baseline")

        baseline_test = result.meets_baseline_criteria(self.JULY_11_BASELINE)

        if baseline_test["meets_criteria"]:
            logger.info("✅ ALL BASELINE CRITERIA MET!")
        else:
            logger.warning("⚠️  Some baseline criteria not met:")
            for issue in baseline_test["issues"]:
                logger.warning(f"   {issue}")

        # Detailed analysis
        print("\n" + "=" * 60)
        print("📊 BASELINE COMPARISON")
        print("=" * 60)

        for criterion, analysis in baseline_test["criteria_analysis"].items():
            status = "✅" if analysis["meets"] else "❌"
            print(
                f"{status} {criterion.replace('_', ' ').title()}: {analysis['actual']}/{analysis['expected']} ({analysis['percentage']:.0f}%)"
            )

        print("=" * 60)

        if baseline_test["meets_criteria"]:
            print("🎉 SYSTEM RESTORED TO JULY 11 BASELINE PERFORMANCE!")
        else:
            print("🔧 System needs additional tuning to meet baseline")

    def _log_final_summary(self, result: OptimizedExtractionResult):
        """Log final extraction summary"""
        logger = logging.getLogger(__name__)

        logger.info(
            f"""
🎯 ULTIMATE EXTRACTION COMPLETE - {result.journal}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 FINAL RESULTS:
   Manuscripts: {result.total_manuscripts}
   Referees: {result.total_referees} ({result.referees_with_emails} with emails)
   PDFs: {result.pdfs_downloaded}
   Quality Score: {result.overall_quality_score:.2f}

⏱️  PERFORMANCE:
   Duration: {result.extraction_duration_seconds:.1f}s
   Success Rate: {result._calculate_success_rate():.1%}
   Manuscripts/min: {result.performance_metrics.get('manuscripts_per_minute', 0):.1f}

🏆 STATUS: {'✅ SUCCESS' if result._calculate_success_rate() > 0.8 else '⚠️  PARTIAL SUCCESS'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """
        )


async def main():
    """Main entry point for ultimate system"""
    parser = argparse.ArgumentParser(description="Editorial Scripts Ultimate - Production System")
    parser.add_argument(
        "journal", choices=["sicon", "sifin", "mf", "mor", "fs", "jota"], help="Journal to extract"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode (compare against baseline)"
    )
    parser.add_argument(
        "--headed", action="store_true", help="Run with visible browser (for debugging)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--check-credentials", action="store_true", help="Check credentials and exit"
    )

    args = parser.parse_args()

    # Initialize system
    system = UltimateSystemManager()
    system.setup_logging(args.log_level)

    logger = logging.getLogger(__name__)

    # Check credentials if requested
    if args.check_credentials:
        if system._verify_credentials():
            print("✅ All required credentials are set")
            return 0
        else:
            return 1

    try:
        if args.journal == "sicon":
            result = await system.extract_sicon(test_mode=args.test, headless=not args.headed)

            # Exit with appropriate code
            success_rate = result._calculate_success_rate()
            return 0 if success_rate > 0.8 else 1

        else:
            logger.error(f"Journal {args.journal} not yet implemented in ultimate system")
            print(f"❌ {args.journal.upper()} extractor not yet available")
            print("Available: SICON")
            print("Coming soon: SIFIN, MF, MOR, FS, JOTA")
            return 1

    except KeyboardInterrupt:
        logger.info("Extraction interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return 1


if __name__ == "__main__":
    # Install required packages if missing
    try:
        import bs4
        import email_validator
        import playwright
        import tenacity
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install with: pip install -r requirements.txt")
        sys.exit(1)

    # Run the system
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
