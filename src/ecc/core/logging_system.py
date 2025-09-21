"""Centralized logging system extracted from legacy extractor patterns."""

import logging
import sys
import time
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any


class LogLevel(Enum):
    """Log levels with emoji indicators."""

    DEBUG = ("DEBUG", "🔧", logging.DEBUG)
    INFO = ("INFO", "ℹ️", logging.INFO)
    SUCCESS = ("SUCCESS", "✅", logging.INFO)
    WARNING = ("WARNING", "⚠️", logging.WARNING)
    ERROR = ("ERROR", "❌", logging.ERROR)
    CRITICAL = ("CRITICAL", "🚨", logging.CRITICAL)


class LogCategory(Enum):
    """Log categories with specific emoji indicators from legacy code."""

    AUTHENTICATION = ("AUTH", "🔐")
    BROWSER = ("BROWSER", "🌐")
    EXTRACTION = ("EXTRACT", "🔍")
    NAVIGATION = ("NAV", "🧭")
    POPUP = ("POPUP", "🖼️")
    DATA = ("DATA", "📊")
    FILE = ("FILE", "💾")
    NETWORK = ("NETWORK", "🌐")
    RETRY = ("RETRY", "🔄")
    CLEANUP = ("CLEANUP", "🧹")
    PROGRESS = ("PROGRESS", "🎯")
    TIMING = ("TIMING", "⏱️")
    FRAME = ("FRAME", "📋")
    CONFIG = ("CONFIG", "⚙️")


class ExtractorLogger:
    """Enhanced logger for extraction operations based on legacy patterns."""

    def __init__(self, name: str = "extractor", log_file: str | None = None):
        """
        Initialize extractor logger.

        Args:
            name: Logger name
            log_file: Optional file path for logging
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.start_time = time.time()
        self.operation_stack: list[str] = []
        self.context_depth = 0

        # Configure logger
        self._setup_logger(log_file)

        # Statistics tracking
        self.stats = {
            "operations_started": 0,
            "operations_completed": 0,
            "operations_failed": 0,
            "warnings_count": 0,
            "errors_count": 0,
        }

    def _setup_logger(self, log_file: str | None):
        """Setup logger with console and optional file output."""
        # Clear existing handlers
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)

        # Console handler with emoji formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = ExtractorFormatter(use_colors=True)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_formatter = ExtractorFormatter(use_colors=False)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def _get_indent(self) -> str:
        """Get current indentation based on context depth."""
        if self.context_depth == 0:
            return ""
        elif self.context_depth == 1:
            return "   "  # 3 spaces like legacy
        else:
            return "         "  # 9 spaces for deep nesting like legacy

    def _log_with_category(
        self, level: LogLevel, category: LogCategory, message: str, *args, **kwargs
    ):
        """Internal logging with category and level."""
        indent = self._get_indent()
        emoji = level.value[1]
        cat_emoji = category.value[1]

        # Format message
        if args:
            message = message % args

        formatted_msg = f"{indent}{emoji} [{cat_emoji} {category.value[0]}] {message}"

        # Update statistics
        if level == LogLevel.WARNING:
            self.stats["warnings_count"] += 1
        elif level in (LogLevel.ERROR, LogLevel.CRITICAL):
            self.stats["errors_count"] += 1

        # Log with appropriate level
        log_level = level.value[2]
        self.logger.log(log_level, formatted_msg, **kwargs)

    # Success operations
    def success(self, message: str, category: LogCategory = LogCategory.EXTRACTION, *args):
        """Log successful operation."""
        self._log_with_category(LogLevel.SUCCESS, category, message, *args)

    def auth_success(self, message: str, *args):
        """Log authentication success."""
        self.success(message, LogCategory.AUTHENTICATION, *args)

    def extraction_success(self, message: str, *args):
        """Log extraction success."""
        self.success(message, LogCategory.EXTRACTION, *args)

    def file_success(self, message: str, *args):
        """Log file operation success."""
        self.success(message, LogCategory.FILE, *args)

    # Warning operations
    def warning(self, message: str, category: LogCategory = LogCategory.EXTRACTION, *args):
        """Log warning."""
        self._log_with_category(LogLevel.WARNING, category, message, *args)

    def popup_warning(self, message: str, *args):
        """Log popup-related warning."""
        self.warning(message, LogCategory.POPUP, *args)

    def retry_warning(self, message: str, *args):
        """Log retry warning."""
        self.warning(message, LogCategory.RETRY, *args)

    # Error operations
    def error(self, message: str, category: LogCategory = LogCategory.EXTRACTION, *args):
        """Log error."""
        self._log_with_category(LogLevel.ERROR, category, message, *args)

    def extraction_error(self, message: str, *args):
        """Log extraction error."""
        self.error(message, LogCategory.EXTRACTION, *args)

    def browser_error(self, message: str, *args):
        """Log browser error."""
        self.error(message, LogCategory.BROWSER, *args)

    def popup_error(self, message: str, *args):
        """Log popup error."""
        self.error(message, LogCategory.POPUP, *args)

    # Info operations
    def info(self, message: str, category: LogCategory = LogCategory.EXTRACTION, *args):
        """Log info."""
        self._log_with_category(LogLevel.INFO, category, message, *args)

    def progress(self, message: str, *args):
        """Log progress information."""
        self.info(message, LogCategory.PROGRESS, *args)

    def data_info(self, message: str, *args):
        """Log data information."""
        self.info(message, LogCategory.DATA, *args)

    def timing_info(self, message: str, *args):
        """Log timing information."""
        self.info(message, LogCategory.TIMING, *args)

    def frame_info(self, message: str, *args):
        """Log frame information."""
        self.info(message, LogCategory.FRAME, *args)

    # Debug operations
    def debug(self, message: str, category: LogCategory = LogCategory.EXTRACTION, *args):
        """Log debug information."""
        self._log_with_category(LogLevel.DEBUG, category, message, *args)

    def config_debug(self, message: str, *args):
        """Log configuration debug."""
        self.debug(message, LogCategory.CONFIG, *args)

    def cleanup_debug(self, message: str, *args):
        """Log cleanup debug."""
        self.debug(message, LogCategory.CLEANUP, *args)

    # Context management
    def enter_context(self, operation_name: str = ""):
        """Enter a logging context (increases indentation)."""
        if operation_name:
            self.operation_stack.append(operation_name)
            self.stats["operations_started"] += 1
        self.context_depth += 1

    def exit_context(self, success: bool = True):
        """Exit a logging context (decreases indentation)."""
        self.context_depth = max(0, self.context_depth - 1)
        if self.operation_stack:
            self.operation_stack.pop()
            if success:
                self.stats["operations_completed"] += 1
            else:
                self.stats["operations_failed"] += 1

    # Statistics and summary
    def get_stats(self) -> dict[str, Any]:
        """Get logging statistics."""
        runtime = time.time() - self.start_time
        return {**self.stats, "runtime_seconds": runtime, "runtime_formatted": f"{runtime:.1f}s"}

    def print_summary(self):
        """Print execution summary like legacy code."""
        stats = self.get_stats()

        self.data_info("EXECUTION SUMMARY")
        self.data_info(f"Operations started: {stats['operations_started']}")
        self.data_info(f"Operations completed: {stats['operations_completed']}")
        self.data_info(f"Operations failed: {stats['operations_failed']}")
        self.data_info(f"Warnings: {stats['warnings_count']}")
        self.data_info(f"Errors: {stats['errors_count']}")
        self.data_info(f"Runtime: {stats['runtime_formatted']}")

        if stats["errors_count"] == 0:
            self.success("No errors detected!")
        else:
            self.warning(f"EXTRACTION ERROR SUMMARY: {stats['errors_count']} errors")


class ExtractorFormatter(logging.Formatter):
    """Custom formatter for extractor logs."""

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors

        # Color codes for terminal output
        self.colors = {
            "RESET": "\033[0m",
            "BOLD": "\033[1m",
            "RED": "\033[31m",
            "GREEN": "\033[32m",
            "YELLOW": "\033[33m",
            "BLUE": "\033[34m",
            "MAGENTA": "\033[35m",
            "CYAN": "\033[36m",
            "WHITE": "\033[37m",
        }

    def format(self, record):
        """Format log record."""
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")

        if self.use_colors:
            # Add colors based on level
            if record.levelno >= logging.ERROR:
                color = self.colors["RED"]
            elif record.levelno >= logging.WARNING:
                color = self.colors["YELLOW"]
            elif "✅" in record.getMessage():
                color = self.colors["GREEN"]
            else:
                color = self.colors["RESET"]

            formatted = f"{color}{record.getMessage()}{self.colors['RESET']}"
        else:
            formatted = f"[{timestamp}] {record.getMessage()}"

        return formatted


class LoggingContext:
    """Context manager for logging operations."""

    def __init__(
        self,
        logger: ExtractorLogger,
        operation_name: str,
        category: LogCategory = LogCategory.EXTRACTION,
    ):
        self.logger = logger
        self.operation_name = operation_name
        self.category = category
        self.start_time = time.time()

    def __enter__(self):
        self.logger.enter_context(self.operation_name)
        self.logger.info(f"Starting {self.operation_name}", self.category)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        runtime = time.time() - self.start_time

        if exc_type is None:
            self.logger.success(f"Completed {self.operation_name} ({runtime:.1f}s)", self.category)
            self.logger.exit_context(success=True)
        else:
            self.logger.error(
                f"Failed {self.operation_name} ({runtime:.1f}s): {exc_val}", self.category
            )
            self.logger.exit_context(success=False)

        return False  # Don't suppress exceptions


def log_operation(operation_name: str = "", category: LogCategory = LogCategory.EXTRACTION):
    """Decorator for logging operations."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get logger from self if available
            logger = None
            if args and hasattr(args[0], "logger") and isinstance(args[0].logger, ExtractorLogger):
                logger = args[0].logger
            else:
                logger = get_default_logger()

            op_name = operation_name or func.__name__

            with LoggingContext(logger, op_name, category):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# Global logger instance
_default_logger: ExtractorLogger | None = None


def get_default_logger() -> ExtractorLogger:
    """Get or create default logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = ExtractorLogger("default")
    return _default_logger


def setup_extraction_logging(
    name: str = "extractor", log_file: str | None = None, console_level: int = logging.INFO
) -> ExtractorLogger:
    """Setup extraction logging system."""
    logger = ExtractorLogger(name, log_file)
    logger.logger.setLevel(console_level)

    global _default_logger
    _default_logger = logger

    return logger


# Convenience functions matching legacy patterns
def print_success(message: str, category: LogCategory = LogCategory.EXTRACTION):
    """Convenience function for success logging."""
    get_default_logger().success(message, category)


def print_warning(message: str, category: LogCategory = LogCategory.EXTRACTION):
    """Convenience function for warning logging."""
    get_default_logger().warning(message, category)


def print_error(message: str, category: LogCategory = LogCategory.EXTRACTION):
    """Convenience function for error logging."""
    get_default_logger().error(message, category)


def print_info(message: str, category: LogCategory = LogCategory.EXTRACTION):
    """Convenience function for info logging."""
    get_default_logger().info(message, category)


def print_progress(message: str):
    """Convenience function for progress logging."""
    get_default_logger().progress(message)


def print_data(message: str):
    """Convenience function for data logging."""
    get_default_logger().data_info(message)
