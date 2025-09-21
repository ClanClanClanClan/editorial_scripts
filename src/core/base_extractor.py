"""Base extractor class for all journal extractors."""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .browser_manager import BrowserManager
from .credential_manager import CredentialManager
from .data_models import ExtractionResult, Manuscript


class BaseExtractor(ABC):
    """Abstract base class for all journal extractors."""

    def __init__(self, journal_code: str, headless: bool = False):
        self.journal_code = journal_code.upper()
        self.headless = headless
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{journal_code}]")

        # Setup paths
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.download_dir = self.data_dir / "downloads" / self.journal_code.lower()

        # Initialize components
        self.browser_manager = BrowserManager(self.download_dir, headless)
        self.credential_manager = CredentialManager()

        # Get credentials
        self.credentials = self.credential_manager.get_credentials(self.journal_code)

        # Browser shortcuts
        self.driver = None
        self.wait = None

        # Results
        self.manuscripts: list[Manuscript] = []
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @abstractmethod
    def login(self) -> bool:
        """Authenticate with the journal platform."""
        pass

    @abstractmethod
    def extract_manuscripts(self) -> list[Manuscript]:
        """Extract all available manuscripts."""
        pass

    def run(self) -> ExtractionResult:
        """Run the complete extraction process."""
        start_time = datetime.now()

        try:
            # Create browser
            self.driver = self.browser_manager.create_driver()
            self.wait = self.browser_manager.wait

            # Login
            self.logger.info("Starting extraction...")
            if not self.login():
                raise Exception("Login failed")

            # Extract manuscripts
            self.manuscripts = self.extract_manuscripts()

            # Create result
            result = ExtractionResult(
                success=True,
                manuscripts=self.manuscripts,
                errors=self.errors,
                warnings=self.warnings,
                extraction_time=start_time,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

            self.logger.info(f"Extraction complete: {len(self.manuscripts)} manuscripts")
            return result

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self.errors.append(str(e))

            return ExtractionResult(
                success=False,
                manuscripts=self.manuscripts,
                errors=self.errors,
                warnings=self.warnings,
                extraction_time=start_time,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        if self.browser_manager:
            self.browser_manager.quit()

    def save_results(self, result: ExtractionResult):
        """Save extraction results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = self.data_dir / "extractions" / self.journal_code.lower()
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{self.journal_code.lower()}_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

        self.logger.info(f"Results saved to: {output_file}")
        return output_file

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.logger.error(error)

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
        self.logger.warning(warning)

    def take_debug_screenshot(self, name: str):
        """Take a screenshot for debugging."""
        if self.browser_manager:
            self.browser_manager.take_screenshot(f"{self.journal_code}_{name}.png")
