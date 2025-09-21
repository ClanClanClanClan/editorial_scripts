"""
CLI Configuration Management

Handles CLI-specific configuration loading and validation.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class CLIConfig:
    """CLI configuration settings."""

    # Output settings
    default_output_format: str = "table"
    color_output: bool = True

    # Progress settings
    show_progress: bool = True
    progress_update_interval: float = 1.0

    # Extraction settings
    default_output_dir: str = "outputs"
    default_batch_size: int = 10

    # Logging settings
    log_level: str = "INFO"
    log_file: str | None = None

    # System settings
    config_file: str | None = None

    def __post_init__(self):
        """Initialize configuration from environment and files."""
        self._load_from_environment()
        if self.config_file:
            self._load_from_file(self.config_file)

    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Output settings
        if os.getenv("ECC_OUTPUT_FORMAT"):
            self.default_output_format = os.getenv("ECC_OUTPUT_FORMAT")

        if os.getenv("ECC_NO_COLOR"):
            self.color_output = False

        # Directory settings
        if os.getenv("ECC_OUTPUT_DIR"):
            self.default_output_dir = os.getenv("ECC_OUTPUT_DIR")

        # Logging settings
        if os.getenv("ECC_LOG_LEVEL"):
            self.log_level = os.getenv("ECC_LOG_LEVEL")

        if os.getenv("ECC_LOG_FILE"):
            self.log_file = os.getenv("ECC_LOG_FILE")

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from YAML file."""
        config_path = Path(config_file)

        if not config_path.exists():
            return

        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)

            # Load CLI-specific settings
            cli_config = config_data.get("cli", {})

            for key, value in cli_config.items():
                if hasattr(self, key):
                    setattr(self, key, value)

        except Exception as e:
            # Don't fail on config loading errors, just log
            logging.getLogger(__name__).warning("Could not load config file %s: %s", config_file, e)

    def get_output_directory(self, custom_dir: str | None = None) -> Path:
        """Get output directory, creating if needed."""
        output_dir = Path(custom_dir or self.default_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
