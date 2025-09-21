"""Retry strategies and decorators extracted from legacy code."""

import logging
import random
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


class RetryStrategy(Enum):
    """Retry strategy types."""

    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    RANDOM_JITTER = "random_jitter"


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor: float = 2.0,
        jitter: bool = False,
        jitter_factor: float = 0.1,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries
            strategy: Retry strategy to use
            backoff_factor: Multiplier for exponential/linear backoff
            jitter: Whether to add random jitter to delays
            jitter_factor: Maximum jitter as factor of delay (0.1 = 10%)
            exceptions: Tuple of exceptions to catch and retry
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.exceptions = exceptions

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (self.backoff_factor**attempt)
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay + (self.backoff_factor * attempt)
        elif self.strategy == RetryStrategy.RANDOM_JITTER:
            delay = self.base_delay + random.uniform(0, self.base_delay * self.jitter_factor)
        else:
            delay = self.base_delay

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter and self.strategy != RetryStrategy.RANDOM_JITTER:
            jitter_amount = delay * self.jitter_factor * random.uniform(-1, 1)
            delay = max(0, delay + jitter_amount)

        return delay


# Predefined retry configurations for common scenarios
class RetryConfigs:
    """Common retry configurations."""

    # Quick operations (UI interactions)
    QUICK = RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor=1.5,
        exceptions=(TimeoutException, StaleElementReferenceException),
    )

    # Standard operations
    STANDARD = RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor=2.0,
        jitter=True,
        exceptions=(TimeoutException, NoSuchElementException, WebDriverException),
    )

    # Network operations
    NETWORK = RetryConfig(
        max_attempts=5,
        base_delay=2.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor=2.0,
        jitter=True,
        exceptions=(TimeoutException, WebDriverException, ConnectionError),
    )

    # File operations
    FILE_OPS = RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
        strategy=RetryStrategy.FIXED_DELAY,
        exceptions=(FileNotFoundError, PermissionError, OSError),
    )

    # Authentication operations
    AUTH = RetryConfig(
        max_attempts=2,
        base_delay=5.0,
        max_delay=15.0,
        strategy=RetryStrategy.FIXED_DELAY,
        exceptions=(TimeoutException, NoSuchElementException),
    )

    # Navigation operations
    NAVIGATION = RetryConfig(
        max_attempts=4,
        base_delay=3.0,
        max_delay=20.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor=1.8,
        jitter=True,
        exceptions=(TimeoutException, WebDriverException),
    )


def retry(
    config: RetryConfig | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    strategy: RetryStrategy | None = None,
    exceptions: tuple[type[Exception], ...] | None = None,
    operation_name: str = "",
):
    """
    Retry decorator with configurable strategy.

    Args:
        config: RetryConfig instance (overrides individual parameters)
        max_attempts: Maximum number of attempts
        base_delay: Base delay between retries
        strategy: Retry strategy to use
        exceptions: Exceptions to catch and retry
        operation_name: Name for logging purposes
    """
    # Use provided config or create from parameters
    if config is None:
        config = RetryConfig(
            max_attempts=max_attempts or 3,
            base_delay=base_delay or 1.0,
            strategy=strategy or RetryStrategy.EXPONENTIAL_BACKOFF,
            exceptions=exceptions or (Exception,),
        )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            func_name = operation_name or func.__name__

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        # Final attempt failed
                        logging.error(
                            f"❌ {func_name} failed after {config.max_attempts} attempts: {e}"
                        )
                        raise
                    else:
                        # Calculate delay and retry
                        delay = config.calculate_delay(attempt)
                        logging.warning(
                            f"⚠️ {func_name} attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)

            # Should never reach here
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# Convenience decorators for common scenarios
def retry_quick(func: Callable = None, *, operation_name: str = ""):
    """Quick retry for UI interactions."""

    def decorator(f):
        return retry(config=RetryConfigs.QUICK, operation_name=operation_name)(f)

    if func is None:
        return decorator
    return decorator(func)


def retry_standard(func: Callable = None, *, operation_name: str = ""):
    """Standard retry for most operations."""

    def decorator(f):
        return retry(config=RetryConfigs.STANDARD, operation_name=operation_name)(f)

    if func is None:
        return decorator
    return decorator(func)


def retry_network(func: Callable = None, *, operation_name: str = ""):
    """Network-specific retry with longer delays."""

    def decorator(f):
        return retry(config=RetryConfigs.NETWORK, operation_name=operation_name)(f)

    if func is None:
        return decorator
    return decorator(func)


def retry_navigation(func: Callable = None, *, operation_name: str = ""):
    """Navigation-specific retry."""

    def decorator(f):
        return retry(config=RetryConfigs.NAVIGATION, operation_name=operation_name)(f)

    if func is None:
        return decorator
    return decorator(func)


def retry_auth(func: Callable = None, *, operation_name: str = ""):
    """Authentication-specific retry."""

    def decorator(f):
        return retry(config=RetryConfigs.AUTH, operation_name=operation_name)(f)

    if func is None:
        return decorator
    return decorator(func)


class RetryableOperation:
    """Context manager for retryable operations."""

    def __init__(self, config: RetryConfig, operation_name: str = ""):
        """
        Initialize retryable operation context.

        Args:
            config: Retry configuration
            operation_name: Name for logging
        """
        self.config = config
        self.operation_name = operation_name
        self.attempt = 0
        self.last_exception = None

    def __enter__(self):
        """Enter retry context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit retry context and handle exceptions."""
        if exc_type is None:
            return False  # No exception occurred

        if not issubclass(exc_type, self.config.exceptions):
            return False  # Not a retryable exception

        self.last_exception = exc_val
        self.attempt += 1

        if self.attempt >= self.config.max_attempts:
            logging.error(
                f"❌ {self.operation_name} failed after {self.config.max_attempts} attempts: {exc_val}"
            )
            return False  # Don't suppress - let exception propagate

        # Calculate delay and wait
        delay = self.config.calculate_delay(self.attempt - 1)
        logging.warning(
            f"⚠️ {self.operation_name} attempt {self.attempt} failed: {exc_val}. Retrying in {delay:.1f}s..."
        )
        time.sleep(delay)

        return True  # Suppress exception - will retry

    def should_retry(self) -> bool:
        """Check if should continue retrying."""
        return self.attempt < self.config.max_attempts


class AdaptiveRetry:
    """Adaptive retry that adjusts based on success/failure patterns."""

    def __init__(self, initial_config: RetryConfig):
        """
        Initialize adaptive retry.

        Args:
            initial_config: Initial retry configuration
        """
        self.config = initial_config
        self.success_count = 0
        self.failure_count = 0
        self.consecutive_failures = 0

    def record_success(self):
        """Record a successful operation."""
        self.success_count += 1
        self.consecutive_failures = 0

        # Adapt: reduce delays if consistently successful
        if self.success_count > 10 and self.success_count % 5 == 0:
            self.config.base_delay = max(0.1, self.config.base_delay * 0.9)

    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.consecutive_failures += 1

        # Adapt: increase delays if consistently failing
        if self.consecutive_failures >= 3:
            self.config.base_delay = min(10.0, self.config.base_delay * 1.2)
            self.config.max_attempts = min(5, self.config.max_attempts + 1)

    def get_current_config(self) -> RetryConfig:
        """Get current adapted configuration."""
        return self.config

    def reset(self):
        """Reset adaptation statistics."""
        self.success_count = 0
        self.failure_count = 0
        self.consecutive_failures = 0


# Utility functions
def with_retry_context(operation: Callable, config: RetryConfig, operation_name: str = "") -> Any:
    """
    Execute operation with retry context manager.

    Args:
        operation: Function to execute
        config: Retry configuration
        operation_name: Operation name for logging

    Returns:
        Operation result
    """
    while True:
        with RetryableOperation(config, operation_name) as retry_ctx:
            try:
                return operation()
            except config.exceptions:
                if not retry_ctx.should_retry():
                    raise


def create_selenium_retry_config() -> RetryConfig:
    """Create retry config optimized for Selenium operations."""
    return RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_factor=2.0,
        jitter=True,
        jitter_factor=0.2,
        exceptions=(
            TimeoutException,
            NoSuchElementException,
            StaleElementReferenceException,
            WebDriverException,
        ),
    )
