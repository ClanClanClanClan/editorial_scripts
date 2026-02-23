"""Example usage of the centralized logging system."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ecc.core.logging_system import (
    LogCategory,
    LoggingContext,
    log_operation,
    setup_extraction_logging,
)


class ExampleExtractor:
    """Example extractor showing logging integration."""

    def __init__(self):
        # Setup logging for this extractor
        self.logger = setup_extraction_logging(
            name="example_extractor", log_file="example_extraction.log"
        )

    def extract_all(self):
        """Main extraction workflow with logging."""
        self.logger.progress("Starting manuscript extraction")

        try:
            # Login phase
            with LoggingContext(self.logger, "authentication", LogCategory.AUTHENTICATION):
                self._authenticate()

            # Navigation phase
            with LoggingContext(self.logger, "navigation", LogCategory.NAVIGATION):
                self._navigate_to_manuscripts()

            # Extraction phase
            with LoggingContext(self.logger, "data_extraction", LogCategory.EXTRACTION):
                manuscripts = self._extract_manuscripts()

            # Save results
            with LoggingContext(self.logger, "save_results", LogCategory.FILE):
                self._save_results(manuscripts)

            self.logger.success(f"Extraction completed: {len(manuscripts)} manuscripts")

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            raise
        finally:
            self.logger.print_summary()

    @log_operation("user_authentication", LogCategory.AUTHENTICATION)
    def _authenticate(self):
        """Simulate authentication with logging."""
        self.logger.info("Loading credentials from secure storage")
        time.sleep(0.1)  # Simulate work

        self.logger.auth_success("Credentials loaded from secure storage")

        self.logger.info("Attempting login to journal platform")
        time.sleep(0.2)  # Simulate work

        self.logger.auth_success("Login successful")

        # Simulate 2FA
        self.logger.info("Checking for 2FA requirement")
        self.logger.warning("2FA code required", LogCategory.AUTHENTICATION)
        self.logger.info("Retrieving 2FA code from Gmail")
        time.sleep(0.1)

        self.logger.auth_success("2FA verification successful")

    @log_operation("manuscript_navigation", LogCategory.NAVIGATION)
    def _navigate_to_manuscripts(self):
        """Simulate navigation with logging."""
        self.logger.info("Navigating to Associate Editor Center")
        time.sleep(0.1)

        self.logger.success("Reached AE dashboard", LogCategory.NAVIGATION)

        self.logger.info("Finding manuscript categories")
        self.logger.data_info("Found 5 manuscript categories")

    @log_operation("manuscript_extraction", LogCategory.EXTRACTION)
    def _extract_manuscripts(self):
        """Simulate manuscript extraction with logging."""
        manuscripts = []

        categories = ["Under Review", "Awaiting AE Decision", "Revision Required"]

        for i, category in enumerate(categories, 1):
            self.logger.enter_context(f"category_{i}")
            try:
                self.logger.progress(f"Processing category: {category}")

                # Simulate finding manuscripts
                manuscript_count = 3 if i == 1 else 2
                self.logger.data_info(f"Found {manuscript_count} manuscripts in {category}")

                for j in range(manuscript_count):
                    self.logger.enter_context(f"manuscript_{j+1}")
                    try:
                        manuscript = self._extract_single_manuscript(f"MS-{i}-{j+1}")
                        manuscripts.append(manuscript)

                        self.logger.extraction_success(f"Extracted manuscript: {manuscript['id']}")
                    finally:
                        self.logger.exit_context(success=True)

            except Exception as e:
                self.logger.extraction_error(f"Failed to process category {category}: {e}")
            finally:
                self.logger.exit_context(success=True)

        return manuscripts

    def _extract_single_manuscript(self, manuscript_id: str):
        """Simulate single manuscript extraction with detailed logging."""
        manuscript = {"id": manuscript_id}

        # Simulate extracting basic info
        self.logger.info("Extracting basic manuscript information")
        manuscript["title"] = f"Sample Title for {manuscript_id}"
        manuscript["status"] = "Under Review"

        # Simulate extracting authors
        self.logger.info("Extracting author information")
        time.sleep(0.05)
        manuscript["authors"] = [
            {"name": "John Smith", "email": "john@university.edu"},
            {"name": "Jane Doe", "email": "jane@institute.org"},
        ]
        self.logger.extraction_success(f"Found {len(manuscript['authors'])} authors")

        # Simulate extracting referees with popup handling
        self.logger.info("Extracting referee information")
        self.logger.enter_context("referee_extraction")
        try:
            referees = []
            for ref_num in range(3):
                self.logger.info(f"Processing referee {ref_num + 1}")

                # Simulate popup email extraction
                self.logger.frame_info("Detected popup window for referee email")
                time.sleep(0.02)

                # Simulate successful email extraction
                email = f"referee{ref_num+1}@university.edu"
                self.logger.success(f"Found email in popup: {email}", LogCategory.POPUP)

                referees.append(
                    {"name": f"Referee {ref_num + 1}", "email": email, "status": "Agreed"}
                )

            manuscript["referees"] = referees
            self.logger.extraction_success(f"Extracted {len(referees)} referees")

        except Exception as e:
            self.logger.popup_error(f"Referee extraction failed: {e}")
            manuscript["referees"] = []
        finally:
            self.logger.exit_context(success=len(manuscript.get("referees", [])) > 0)

        return manuscript

    @log_operation("save_extraction_results", LogCategory.FILE)
    def _save_results(self, manuscripts):
        """Simulate saving results with logging."""
        filename = f"extraction_results_{int(time.time())}.json"

        self.logger.info(f"Saving {len(manuscripts)} manuscripts to {filename}")
        time.sleep(0.1)  # Simulate file I/O

        self.logger.file_success(f"Results saved to: {filename}")
        self.logger.data_info(f"File size: ~{len(manuscripts) * 2}KB")


def demonstrate_logging_patterns():
    """Demonstrate various logging patterns from legacy code."""
    logger = setup_extraction_logging("demo")

    print("\n" + "=" * 50)
    print("DEMONSTRATING LEGACY LOGGING PATTERNS")
    print("=" * 50)

    # Authentication patterns
    logger.auth_success("Credentials loaded from secure storage")
    logger.warning("Falling back to environment variables...", LogCategory.AUTHENTICATION)

    # Popup patterns
    logger.frame_info("Found 3 frames in popup")
    logger.popup_warning("Popup window timeout for javascript:test...")
    logger.success("Found email in frame 1: test@university.edu", LogCategory.POPUP)
    logger.popup_error("No email found in popup")

    # Data extraction patterns
    logger.data_info("MANUSCRIPTS FOUND: 15")
    logger.progress("Processing manuscript 3/15")
    logger.extraction_success("Found manuscript ID: MF-2025-001")
    logger.extraction_error("Failed to extract title")

    # File operations
    logger.file_success("Full data saved to: extraction_20250822.json")
    logger.info("File size: 2.5MB", LogCategory.FILE)

    # Summary patterns (like legacy code)
    logger.data_info("SUCCESS/FAILURE ANALYSIS:")
    logger.data_info("Manuscripts processed: 15")
    logger.data_info("Successful extractions: 13")
    logger.data_info("Failed extractions: 2")

    # Final summary
    logger.print_summary()


if __name__ == "__main__":
    demo_logger = setup_extraction_logging("demo_main")
    demo_logger.info("🚀 CENTRALIZED LOGGING SYSTEM DEMO")
    demo_logger.info("=" * 60)

    # Run full extraction example
    extractor = ExampleExtractor()
    extractor.extract_all()

    # Demonstrate logging patterns
    demonstrate_logging_patterns()

    demo_logger.success("Logging system demonstration complete!")
    demo_logger.info("Check 'example_extraction.log' for file output")
