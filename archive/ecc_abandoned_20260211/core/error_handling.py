"""Centralized error handling patterns extracted from legacy code."""

import logging
import time
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationType(Enum):
    """Types of operations for error context."""

    NAVIGATION = "navigation"
    ELEMENT_INTERACTION = "element_interaction"
    DATA_EXTRACTION = "data_extraction"
    AUTHENTICATION = "authentication"
    FILE_OPERATION = "file_operation"
    NETWORK = "network"
    POPUP_HANDLING = "popup_handling"


class ExtractorError(Exception):
    """Base exception for extractor errors."""

    def __init__(
        self, message: str, operation: str = "", severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        super().__init__(message)
        self.operation = operation
        self.severity = severity


class CriticalOperationError(ExtractorError):
    """Exception for critical operation failures."""

    def __init__(self, message: str, operation: str = ""):
        super().__init__(message, operation, ErrorSeverity.CRITICAL)


class RetryableError(ExtractorError):
    """Exception that indicates operation can be retried."""

    def __init__(self, message: str, operation: str = "", max_retries: int = 3):
        super().__init__(message, operation, ErrorSeverity.MEDIUM)
        self.max_retries = max_retries


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    operation_name: str = "",
):
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch and retry
        operation_name: Name of operation for logging
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        logging.error(
                            f"❌ {operation_name or func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    else:
                        retry_delay = delay * (backoff_factor**attempt)
                        logging.warning(
                            f"⚠️ {operation_name or func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {retry_delay:.1f}s..."
                        )
                        time.sleep(retry_delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class SafeExecutor:
    """Safe execution wrapper with comprehensive error handling."""

    def __init__(self, logger: logging.Logger | None = None):
        """
        Initialize safe executor.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Exception handling mapping
        self.exception_handlers = {
            TimeoutException: self._handle_timeout_error,
            NoSuchElementException: self._handle_element_not_found,
            StaleElementReferenceException: self._handle_stale_element,
            WebDriverException: self._handle_webdriver_error,
            Exception: self._handle_generic_error,
        }

    def execute(
        self,
        operation: Callable,
        operation_name: str = "",
        operation_type: OperationType = OperationType.DATA_EXTRACTION,
        default_value: Any = None,
        critical: bool = False,
        suppress_errors: bool = False,
    ) -> Any:
        """
        Safely execute an operation with comprehensive error handling.

        Args:
            operation: Function to execute
            operation_name: Human-readable operation name
            operation_type: Type of operation being performed
            default_value: Value to return on non-critical failures
            critical: Whether failure should raise exception
            suppress_errors: Whether to suppress all errors (return default)

        Returns:
            Operation result or default_value on failure

        Raises:
            ExtractorError: On critical operation failure
        """
        if not operation_name:
            operation_name = getattr(operation, "__name__", "unknown_operation")

        try:
            result = operation()
            return result

        except Exception as e:
            # Find appropriate handler
            handler = None
            for exception_type, exception_handler in self.exception_handlers.items():
                if isinstance(e, exception_type):
                    handler = exception_handler
                    break

            # Handle the error
            if handler:
                return handler(
                    e, operation_name, operation_type, default_value, critical, suppress_errors
                )
            else:
                return self._handle_generic_error(
                    e, operation_name, operation_type, default_value, critical, suppress_errors
                )

    def _handle_timeout_error(
        self,
        error: TimeoutException,
        operation_name: str,
        operation_type: OperationType,
        default_value: Any,
        critical: bool,
        suppress_errors: bool,
    ) -> Any:
        """Handle timeout exceptions."""
        error_msg = f"Timeout during {operation_name} ({operation_type.value})"

        if suppress_errors:
            self.logger.debug(f"⏱️ {error_msg} (suppressed)")
            return default_value

        self.logger.warning(f"⏱️ {error_msg}")

        if critical:
            raise CriticalOperationError(error_msg, operation_name)

        return default_value

    def _handle_element_not_found(
        self,
        error: NoSuchElementException,
        operation_name: str,
        operation_type: OperationType,
        default_value: Any,
        critical: bool,
        suppress_errors: bool,
    ) -> Any:
        """Handle element not found exceptions."""
        error_msg = f"Element not found during {operation_name} ({operation_type.value})"

        if suppress_errors:
            self.logger.debug(f"🔍 {error_msg} (suppressed)")
            return default_value

        self.logger.warning(f"🔍 {error_msg}")

        if critical:
            raise CriticalOperationError(error_msg, operation_name)

        return default_value

    def _handle_stale_element(
        self,
        error: StaleElementReferenceException,
        operation_name: str,
        operation_type: OperationType,
        default_value: Any,
        critical: bool,
        suppress_errors: bool,
    ) -> Any:
        """Handle stale element exceptions."""
        error_msg = f"Stale element during {operation_name} ({operation_type.value})"

        if suppress_errors:
            self.logger.debug(f"🔄 {error_msg} (suppressed)")
            return default_value

        self.logger.warning(f"🔄 {error_msg}")

        # Stale elements are often retryable
        if critical:
            raise RetryableError(error_msg, operation_name, max_retries=2)

        return default_value

    def _handle_webdriver_error(
        self,
        error: WebDriverException,
        operation_name: str,
        operation_type: OperationType,
        default_value: Any,
        critical: bool,
        suppress_errors: bool,
    ) -> Any:
        """Handle WebDriver exceptions."""
        error_msg = (
            f"WebDriver error during {operation_name} ({operation_type.value}): {str(error)[:100]}"
        )

        if suppress_errors:
            self.logger.debug(f"🌐 {error_msg} (suppressed)")
            return default_value

        self.logger.warning(f"🌐 {error_msg}")

        if critical:
            raise CriticalOperationError(error_msg, operation_name)

        return default_value

    def _handle_generic_error(
        self,
        error: Exception,
        operation_name: str,
        operation_type: OperationType,
        default_value: Any,
        critical: bool,
        suppress_errors: bool,
    ) -> Any:
        """Handle generic exceptions."""
        error_msg = (
            f"Unexpected error during {operation_name} ({operation_type.value}): {str(error)[:100]}"
        )

        if suppress_errors:
            self.logger.debug(f"❌ {error_msg} (suppressed)")
            return default_value

        self.logger.error(f"❌ {error_msg}")

        if critical:
            raise CriticalOperationError(error_msg, operation_name)

        return default_value


class ErrorCollector:
    """Collects and aggregates errors during extraction operations."""

    def __init__(self):
        """Initialize error collector."""
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def add_error(
        self,
        error: Exception,
        operation: str = "",
        operation_type: OperationType = OperationType.DATA_EXTRACTION,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
    ):
        """
        Add an error to the collection.

        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            operation_type: Type of operation
            severity: Error severity level
            context: Additional context information
        """
        error_info = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "message": str(error),
            "operation": operation,
            "operation_type": operation_type.value,
            "severity": severity.value,
            "context": context or {},
        }

        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            self.errors.append(error_info)
        else:
            self.warnings.append(error_info)

    def add_warning(
        self,
        message: str,
        operation: str = "",
        operation_type: OperationType = OperationType.DATA_EXTRACTION,
        context: dict[str, Any] | None = None,
    ):
        """
        Add a warning to the collection.

        Args:
            message: Warning message
            operation: Name of the operation
            operation_type: Type of operation
            context: Additional context information
        """
        warning_info = {
            "timestamp": time.time(),
            "message": message,
            "operation": operation,
            "operation_type": operation_type.value,
            "context": context or {},
        }

        self.warnings.append(warning_info)

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if any warnings were collected."""
        return len(self.warnings) > 0

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of collected errors and warnings."""
        return {
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "operations_with_errors": list({e["operation"] for e in self.errors if e["operation"]}),
            "critical_errors": [
                e for e in self.errors if e["severity"] == ErrorSeverity.CRITICAL.value
            ],
        }

    def clear(self):
        """Clear all collected errors and warnings."""
        self.errors.clear()
        self.warnings.clear()


# Convenience functions for common patterns
def safe_selenium_operation(
    operation: Callable, operation_name: str = "", default_value: Any = None, critical: bool = False
) -> Any:
    """
    Convenience function for safe Selenium operations.

    Args:
        operation: Selenium operation to execute
        operation_name: Name of the operation
        default_value: Value to return on failure
        critical: Whether to raise on failure

    Returns:
        Operation result or default_value
    """
    executor = SafeExecutor()
    return executor.execute(
        operation=operation,
        operation_name=operation_name,
        operation_type=OperationType.ELEMENT_INTERACTION,
        default_value=default_value,
        critical=critical,
    )


def safe_navigation(operation: Callable, operation_name: str = "", critical: bool = True) -> Any:
    """
    Convenience function for safe navigation operations.

    Args:
        operation: Navigation operation to execute
        operation_name: Name of the operation
        critical: Whether navigation failure should raise

    Returns:
        Operation result
    """
    executor = SafeExecutor()
    return executor.execute(
        operation=operation,
        operation_name=operation_name,
        operation_type=OperationType.NAVIGATION,
        critical=critical,
    )


def safe_data_extraction(
    operation: Callable, operation_name: str = "", default_value: Any = None
) -> Any:
    """
    Convenience function for safe data extraction.

    Args:
        operation: Data extraction operation
        operation_name: Name of the operation
        default_value: Value to return on failure

    Returns:
        Extracted data or default_value
    """
    executor = SafeExecutor()
    return executor.execute(
        operation=operation,
        operation_name=operation_name,
        operation_type=OperationType.DATA_EXTRACTION,
        default_value=default_value,
        critical=False,
    )
