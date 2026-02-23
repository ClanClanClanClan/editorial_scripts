"""Configuration management for manuscript extractors."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BrowserConfig:
    """Browser configuration settings."""

    headless: bool = False
    window_size: tuple = (1200, 800)
    timeout: int = 30
    implicit_wait: int = 5
    page_load_timeout: int = 30
    download_dir: str = "./downloads"
    screenshot_dir: str = "./screenshots"

    # Chrome options
    disable_gpu: bool = True
    no_sandbox: bool = True
    disable_dev_shm: bool = True
    disable_automation: bool = True

    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """Create config from environment variables."""
        return cls(
            headless=os.getenv("EXTRACTOR_HEADLESS", "false").lower() == "true",
            window_size=tuple(map(int, os.getenv("EXTRACTOR_WINDOW_SIZE", "1200,800").split(","))),
            timeout=int(os.getenv("EXTRACTOR_TIMEOUT", "30")),
            download_dir=os.getenv("EXTRACTOR_DOWNLOAD_DIR", "./downloads"),
            screenshot_dir=os.getenv("EXTRACTOR_SCREENSHOT_DIR", "./screenshots"),
        )


@dataclass
class RetryConfig:
    """Retry configuration for operations."""

    max_attempts: int = 3
    delay: float = 1.0
    backoff_factor: float = 2.0

    # Specific retry settings
    login_attempts: int = 3
    navigation_attempts: int = 3
    element_wait_attempts: int = 5
    popup_wait_timeout: int = 10


@dataclass
class Selectors:
    """CSS/XPath selectors for page elements."""

    # Login page
    userid_field: str = "USERID"
    password_field: str = "PASSWORD"
    login_button: str = "logInButton"
    token_field: str = "TOKEN_VALUE"
    verify_button: str = "VERIFY_BTN"

    # Cookie banner
    cookie_reject: str = "onetrust-reject-all-handler"
    cookie_accept: str = "onetrust-accept-btn-handler"

    # Navigation
    ae_center_link: str = "Associate Editor Center"
    logout_link: str = "Log Out"

    # Manuscript details
    manuscript_table: str = "//table[@class='manuscriptTable']"
    manuscript_link: str = "//a[contains(@href, 'REVIEWER_MANUSCRIPTMANAGEMENTDETAILS')]"

    # Referee table
    referee_table: str = "//table[contains(@class, 'refereeTable')]"
    referee_row: str = "//tr[contains(@class, 'tablerows')]"
    referee_name_cell: str = "td[1]"
    referee_status_cell: str = "td[2]"
    referee_dates_cell: str = "td[3]"

    # Author table
    author_table: str = "//table[contains(@class, 'authorTable')]"
    author_row: str = "//tr[contains(@class, 'tablerows')]"

    # Document links
    pdf_link: str = "//a[contains(@href, '.pdf')]"
    cover_letter_link: str = "//a[contains(text(), 'Cover Letter')]"

    # Audit trail
    audit_trail_link: str = "//a[contains(text(), 'Audit Trail')]"
    event_table: str = "//table[@class='eventTable']"

    @classmethod
    def for_journal(cls, journal: str) -> "Selectors":
        """Get journal-specific selectors."""
        # Could load from JSON file for different journals
        return cls()


@dataclass
class URLConfig:
    """URL configuration for different journals."""

    base_url: str = ""
    login_url: str = ""
    ae_center_url: str = ""
    manuscript_details_url: str = ""

    @classmethod
    def for_journal(cls, journal: str) -> "URLConfig":
        """Get journal-specific URLs."""
        configs = {
            "mf": cls(
                base_url="https://mc.manuscriptcentral.com/mafi",
                login_url="https://mc.manuscriptcentral.com/mafi",
                ae_center_url="https://mc.manuscriptcentral.com/mafi?NEXT_PAGE=ASSOCIATE_EDITOR_CENTER",
                manuscript_details_url="https://mc.manuscriptcentral.com/mafi?NEXT_PAGE=REVIEWER_MANUSCRIPTMANAGEMENTDETAILS&id=",
            ),
            "mor": cls(
                base_url="https://mc.manuscriptcentral.com/mor",
                login_url="https://mc.manuscriptcentral.com/mor",
                ae_center_url="https://mc.manuscriptcentral.com/mor?NEXT_PAGE=ASSOCIATE_EDITOR_CENTER",
                manuscript_details_url="https://mc.manuscriptcentral.com/mor?NEXT_PAGE=REVIEWER_MANUSCRIPTMANAGEMENTDETAILS&id=",
            ),
        }
        return configs.get(journal, cls())


@dataclass
class ExtractionConfig:
    """Configuration for data extraction."""

    # What to extract
    extract_abstracts: bool = True
    extract_keywords: bool = True
    extract_audit_trail: bool = True
    extract_cover_letters: bool = True
    extract_referee_reports: bool = True
    extract_mor_parity_fields: bool = True

    # Extraction settings
    max_manuscripts_per_category: int | None = None
    skip_completed_manuscripts: bool = False
    save_intermediate_results: bool = True

    # Timeouts
    popup_wait_timeout: int = 10
    page_load_wait: int = 5
    element_wait_timeout: int = 10

    # Output settings
    output_format: str = "json"  # json, csv, excel
    output_dir: str = "./outputs"
    timestamp_format: str = "%Y%m%d_%H%M%S"


@dataclass
class JournalConfig:
    """Complete configuration for a journal."""

    journal_code: str
    journal_name: str
    platform: str  # scholarone, siam, editorial_manager

    urls: URLConfig = field(default_factory=URLConfig)
    selectors: Selectors = field(default_factory=Selectors)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)

    # Credentials
    email_env: str = ""
    password_env: str = ""

    @classmethod
    def load_for_journal(cls, journal: str) -> "JournalConfig":
        """Load configuration for a specific journal."""
        if journal == "mf":
            return cls(
                journal_code="mf",
                journal_name="Mathematical Finance",
                platform="scholarone",
                urls=URLConfig.for_journal("mf"),
                selectors=Selectors.for_journal("mf"),
                browser=BrowserConfig.from_env(),
                email_env="MF_EMAIL",  # pragma: allowlist secret - env var name only
                password_env="MF_PASSWORD",  # pragma: allowlist secret - env var name only
            )
        elif journal == "mor":
            return cls(
                journal_code="mor",
                journal_name="Mathematics of Operations Research",
                platform="scholarone",
                urls=URLConfig.for_journal("mor"),
                selectors=Selectors.for_journal("mor"),
                browser=BrowserConfig.from_env(),
                email_env="MOR_EMAIL",  # pragma: allowlist secret - env var name only
                password_env="MOR_PASSWORD",  # pragma: allowlist secret - env var name only
            )
        else:
            raise ValueError(f"Unknown journal: {journal}")

    def get_credentials(self) -> tuple[str, str]:
        """Get credentials from environment."""
        email = os.getenv(self.email_env)
        password = os.getenv(self.password_env)

        if not email or not password:
            raise ValueError(f"Missing credentials: {self.email_env} or {self.password_env}")

        return email, password

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "journal_code": self.journal_code,
            "journal_name": self.journal_name,
            "platform": self.platform,
            "urls": vars(self.urls),
            "selectors": vars(self.selectors),
            "browser": vars(self.browser),
            "retry": vars(self.retry),
            "extraction": vars(self.extraction),
        }

    def save_to_file(self, filepath: str):
        """Save configuration to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "JournalConfig":
        """Load configuration from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        config = cls(
            journal_code=data["journal_code"],
            journal_name=data["journal_name"],
            platform=data["platform"],
        )

        # Load nested configs
        for key in ["urls", "selectors", "browser", "retry", "extraction"]:
            if key in data:
                setattr(config, key, type(getattr(config, key))(**data[key]))

        return config


class ConfigManager:
    """Manages configurations for all journals."""

    def __init__(self, config_dir: str = "./config"):
        """
        Initialize config manager.

        Args:
            config_dir: Directory containing config files
        """
        self.config_dir = Path(config_dir)
        self.configs: dict[str, JournalConfig] = {}

    def load_configs(self):
        """Load all journal configurations."""
        if not self.config_dir.exists():
            return

        for config_file in self.config_dir.glob("*_config.json"):
            journal_code = config_file.stem.replace("_config", "")
            try:
                config = JournalConfig.load_from_file(str(config_file))
                self.configs[journal_code] = config
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    "Failed to load config for %s: %s", journal_code, e
                )

    def get_config(self, journal: str) -> JournalConfig:
        """
        Get configuration for a journal.

        Args:
            journal: Journal code

        Returns:
            Journal configuration
        """
        if journal not in self.configs:
            # Try to load from file
            config_file = self.config_dir / f"{journal}_config.json"
            if config_file.exists():
                self.configs[journal] = JournalConfig.load_from_file(str(config_file))
            else:
                # Load default config
                self.configs[journal] = JournalConfig.load_for_journal(journal)

        return self.configs[journal]

    def save_config(self, journal: str, config: JournalConfig):
        """
        Save configuration for a journal.

        Args:
            journal: Journal code
            config: Configuration to save
        """
        self.config_dir.mkdir(exist_ok=True)
        config_file = self.config_dir / f"{journal}_config.json"
        config.save_to_file(str(config_file))
        self.configs[journal] = config

    def list_journals(self) -> list[str]:
        """List all configured journals."""
        return list(self.configs.keys())
