"""Extraction pipeline abstraction for manuscript extractors."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from selenium.webdriver.common.by import By

from src.ecc.auth.scholarone_auth import ScholarOneAuthenticator
from src.ecc.browser.popup_handler import PopupHandler
from src.ecc.browser.selenium_manager import SeleniumBrowserManager
from src.ecc.config.extractor_config import JournalConfig
from src.ecc.core.extraction_models import ExtractedManuscript


class ExtractionStep(ABC):
    """Abstract base class for extraction steps."""

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the extraction step.

        Args:
            context: Extraction context with shared data

        Returns:
            Updated context
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Step name for logging."""
        pass


@dataclass
class ExtractionContext:
    """Context shared across extraction steps."""

    manuscript_id: str
    browser: SeleniumBrowserManager
    popup_handler: PopupHandler
    config: JournalConfig
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def add_data(self, key: str, value: Any):
        """Add data to context."""
        self.data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get data from context."""
        return self.data.get(key, default)

    def add_error(self, error: str):
        """Add error to context."""
        self.errors.append(error)

    def to_manuscript(self) -> ExtractedManuscript:
        """Convert context to manuscript object."""
        return ExtractedManuscript(id=self.manuscript_id, **self.data)


class NavigationStep(ExtractionStep):
    """Navigate to manuscript details page."""

    def __init__(self, url_template: str):
        self.url_template = url_template

    @property
    def name(self) -> str:
        return "Navigation"

    def execute(self, context: ExtractionContext) -> ExtractionContext:
        """Navigate to manuscript page."""
        url = self.url_template.format(manuscript_id=context.manuscript_id)

        if context.browser.navigate_with_retry(url):
            logging.info(f"Navigated to {context.manuscript_id}")
        else:
            context.add_error(f"Failed to navigate to {context.manuscript_id}")

        return context


class BasicInfoStep(ExtractionStep):
    """Extract basic manuscript information."""

    @property
    def name(self) -> str:
        return "BasicInfo"

    def execute(self, context: ExtractionContext) -> ExtractionContext:
        """Extract basic info."""
        try:
            # Extract title
            title_element = context.browser.wait_for_element(
                By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td"
            )
            if title_element:
                context.add_data("title", title_element.text.strip())

            # Extract status
            status_element = context.browser.wait_for_element(
                By.XPATH, "//td[contains(text(), 'Status:')]/following-sibling::td"
            )
            if status_element:
                context.add_data("status", status_element.text.strip())

            logging.info(f"Extracted basic info for {context.manuscript_id}")

        except Exception as e:
            context.add_error(f"Basic info extraction failed: {e}")

        return context


class AuthorExtractionStep(ExtractionStep):
    """Extract author information."""

    @property
    def name(self) -> str:
        return "Authors"

    def execute(self, context: ExtractionContext) -> ExtractionContext:
        """Extract authors."""
        authors = []

        try:
            # Find author table
            author_rows = context.browser.driver.find_elements(
                By.XPATH, context.config.selectors.author_row
            )

            for row in author_rows:
                author = self._extract_author_from_row(row, context)
                if author:
                    authors.append(author)

            context.add_data("authors", authors)
            logging.info(f"Extracted {len(authors)} authors for {context.manuscript_id}")

        except Exception as e:
            context.add_error(f"Author extraction failed: {e}")

        return context

    def _extract_author_from_row(self, row, context: ExtractionContext) -> dict[str, Any] | None:
        """Extract author from table row."""
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 2:
                return None

            # Extract name
            name_cell = cells[0]
            name = name_cell.text.strip()

            # Extract email from popup
            email = ""
            email_links = name_cell.find_elements(By.TAG_NAME, "a")
            if email_links:
                popup_url = email_links[0].get_attribute("href")
                if popup_url:
                    email = context.popup_handler.extract_from_javascript_popup(popup_url)

            # Extract affiliation
            affiliation = cells[1].text.strip() if len(cells) > 1 else ""

            return {"name": name, "email": email, "affiliation": affiliation}

        except Exception as e:
            logging.warning(f"Failed to extract author from row: {e}")
            return None


class RefereeExtractionStep(ExtractionStep):
    """Extract referee information."""

    @property
    def name(self) -> str:
        return "Referees"

    def execute(self, context: ExtractionContext) -> ExtractionContext:
        """Extract referees."""
        referees = []

        try:
            # Find referee table
            referee_rows = context.browser.driver.find_elements(
                By.XPATH, context.config.selectors.referee_row
            )

            for row in referee_rows:
                referee = self._extract_referee_from_row(row, context)
                if referee:
                    referees.append(referee)

            context.add_data("referees", referees)
            logging.info(f"Extracted {len(referees)} referees for {context.manuscript_id}")

        except Exception as e:
            context.add_error(f"Referee extraction failed: {e}")

        return context

    def _extract_referee_from_row(self, row, context: ExtractionContext) -> dict[str, Any] | None:
        """Extract referee from table row."""
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:
                return None

            # Extract name and email
            name_cell = cells[0]
            name = name_cell.text.strip()

            email = ""
            email_links = name_cell.find_elements(By.TAG_NAME, "a")
            if email_links:
                popup_url = email_links[0].get_attribute("href")
                if popup_url:
                    email = context.popup_handler.extract_from_javascript_popup(popup_url)

            # Extract status
            status = cells[1].text.strip() if len(cells) > 1 else ""

            # Extract dates
            dates = cells[2].text.strip() if len(cells) > 2 else ""

            return {"name": name, "email": email, "status": status, "dates": dates}

        except Exception as e:
            logging.warning(f"Failed to extract referee from row: {e}")
            return None


class ExtractionPipeline:
    """Main extraction pipeline orchestrator."""

    def __init__(self, config: JournalConfig):
        """
        Initialize extraction pipeline.

        Args:
            config: Journal configuration
        """
        self.config = config
        self.steps: list[ExtractionStep] = []
        self.browser: SeleniumBrowserManager | None = None
        self.popup_handler: PopupHandler | None = None
        self.authenticator: ScholarOneAuthenticator | None = None

        # Setup logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_step(self, step: ExtractionStep):
        """Add extraction step to pipeline."""
        self.steps.append(step)
        return self

    def setup(self):
        """Setup browser and handlers."""
        self.browser = SeleniumBrowserManager(
            headless=self.config.browser.headless, window_size=self.config.browser.window_size
        )
        self.browser.setup_driver()

        self.popup_handler = PopupHandler(self.browser)

        if self.config.platform == "scholarone":
            self.authenticator = ScholarOneAuthenticator(self.browser)

    def login(self) -> bool:
        """Login to the platform."""
        if not self.authenticator:
            self.logger.error("No authenticator configured")
            return False

        return self.authenticator.login(self.config.journal_code)

    def extract_manuscript(self, manuscript_id: str) -> ExtractedManuscript:
        """
        Extract single manuscript.

        Args:
            manuscript_id: Manuscript ID to extract

        Returns:
            Extracted manuscript data
        """
        # Create context
        context = ExtractionContext(
            manuscript_id=manuscript_id,
            browser=self.browser,
            popup_handler=self.popup_handler,
            config=self.config,
        )

        # Execute steps
        for step in self.steps:
            try:
                self.logger.info(f"Executing {step.name} for {manuscript_id}")
                context = step.execute(context)
            except Exception as e:
                self.logger.error(f"Step {step.name} failed: {e}")
                context.add_error(f"Step {step.name} failed: {e}")

        # Log any errors
        if context.errors:
            self.logger.warning(
                f"Extraction completed with errors for {manuscript_id}: {context.errors}"
            )

        return context.to_manuscript()

    def extract_all(self, manuscript_ids: list[str]) -> list[ExtractedManuscript]:
        """
        Extract multiple manuscripts.

        Args:
            manuscript_ids: List of manuscript IDs

        Returns:
            List of extracted manuscripts
        """
        results = []

        # Setup browser
        self.setup()

        # Login
        if not self.login():
            self.logger.error("Login failed")
            return results

        # Extract each manuscript
        for manuscript_id in manuscript_ids:
            try:
                manuscript = self.extract_manuscript(manuscript_id)
                results.append(manuscript)

                # Save intermediate results if configured
                if self.config.extraction.save_intermediate_results:
                    self._save_intermediate_results(results)

            except Exception as e:
                self.logger.error(f"Failed to extract {manuscript_id}: {e}")

        # Cleanup
        self.cleanup()

        return results

    def _save_intermediate_results(self, results: list[ExtractedManuscript]):
        """Save intermediate extraction results."""
        try:
            timestamp = datetime.now().strftime(self.config.extraction.timestamp_format)
            output_dir = Path(self.config.extraction.output_dir)
            output_dir.mkdir(exist_ok=True)

            output_file = output_dir / f"intermediate_{timestamp}.json"

            with open(output_file, "w") as f:
                json.dump([m.to_dict() for m in results], f, indent=2)

            self.logger.info(f"Saved intermediate results to {output_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save intermediate results: {e}")

    def cleanup(self):
        """Cleanup resources."""
        if self.browser:
            self.browser.cleanup()


class PipelineBuilder:
    """Builder for creating extraction pipelines."""

    def __init__(self, config: JournalConfig):
        """
        Initialize pipeline builder.

        Args:
            config: Journal configuration
        """
        self.config = config
        self.pipeline = ExtractionPipeline(config)

    def add_navigation(self) -> "PipelineBuilder":
        """Add navigation step."""
        self.pipeline.add_step(NavigationStep(self.config.urls.manuscript_details_url))
        return self

    def add_basic_info(self) -> "PipelineBuilder":
        """Add basic info extraction."""
        self.pipeline.add_step(BasicInfoStep())
        return self

    def add_authors(self) -> "PipelineBuilder":
        """Add author extraction."""
        self.pipeline.add_step(AuthorExtractionStep())
        return self

    def add_referees(self) -> "PipelineBuilder":
        """Add referee extraction."""
        self.pipeline.add_step(RefereeExtractionStep())
        return self

    def add_custom_step(self, step: ExtractionStep) -> "PipelineBuilder":
        """Add custom extraction step."""
        self.pipeline.add_step(step)
        return self

    def build(self) -> ExtractionPipeline:
        """Build the pipeline."""
        return self.pipeline

    @classmethod
    def create_default_pipeline(cls, journal: str) -> ExtractionPipeline:
        """
        Create default pipeline for a journal.

        Args:
            journal: Journal code

        Returns:
            Configured extraction pipeline
        """
        config = JournalConfig.load_for_journal(journal)

        return cls(config).add_navigation().add_basic_info().add_authors().add_referees().build()
