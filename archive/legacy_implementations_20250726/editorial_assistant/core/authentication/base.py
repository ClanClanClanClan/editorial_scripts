"""
Base Authentication Provider Interface

Defines the contract that all authentication providers must implement.
This eliminates inconsistent authentication patterns across the codebase.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver


class AuthStatus(Enum):
    """Authentication status enumeration."""

    SUCCESS = "success"
    FAILED = "failed"
    REQUIRES_2FA = "requires_2fa"
    BLOCKED = "blocked"
    INVALID_CREDENTIALS = "invalid_credentials"


@dataclass
class AuthenticationResult:
    """Result of authentication attempt."""

    status: AuthStatus
    message: str
    requires_2fa: bool = False
    session_data: dict[str, Any] | None = None
    error_details: str | None = None


class AuthenticationProvider(ABC):
    """
    Abstract base class for all authentication providers.

    This interface ensures consistent authentication behavior across
    all journal platforms while allowing platform-specific implementations.
    """

    def __init__(self, credentials: dict[str, str], logger=None):
        """
        Initialize authentication provider.

        Args:
            credentials: Dictionary containing authentication credentials
            logger: Logger instance for debug/error reporting
        """
        self.credentials = credentials
        self.logger = logger
        self._session_data: dict[str, Any] = {}

    @abstractmethod
    async def authenticate(self, driver: WebDriver) -> AuthenticationResult:
        """
        Perform authentication for the platform.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            AuthenticationResult with status and details
        """
        pass

    @abstractmethod
    def get_login_url(self) -> str:
        """
        Get the login URL for the platform.

        Returns:
            Login URL string
        """
        pass

    @abstractmethod
    def verify_authentication(self, driver: WebDriver) -> bool:
        """
        Verify that authentication was successful.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            True if authenticated, False otherwise
        """
        pass

    def handle_2fa(self, driver: WebDriver) -> bool:
        """
        Handle two-factor authentication if required.

        Default implementation returns False (no 2FA support).
        Override in subclasses that support 2FA.

        Args:
            driver: Selenium WebDriver instance

        Returns:
            True if 2FA handled successfully, False otherwise
        """
        return False

    def cleanup_session(self, driver: WebDriver) -> None:
        """
        Clean up authentication session.

        Default implementation does nothing.
        Override in subclasses if cleanup is needed.

        Args:
            driver: Selenium WebDriver instance
        """
        pass

    def get_session_data(self) -> dict[str, Any]:
        """
        Get session data collected during authentication.

        Returns:
            Dictionary containing session data
        """
        return self._session_data.copy()

    def validate_credentials(self) -> bool:
        """
        Validate that required credentials are present.

        Returns:
            True if credentials are valid, False otherwise
        """
        required_fields = self.get_required_credentials()
        return all(
            field in self.credentials and self.credentials[field] for field in required_fields
        )

    @abstractmethod
    def get_required_credentials(self) -> list:
        """
        Get list of required credential field names.

        Returns:
            List of required credential field names
        """
        pass

    def _log_info(self, message: str) -> None:
        """Log info message if logger available."""
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str) -> None:
        """Log error message if logger available."""
        if self.logger:
            self.logger.error(message)

    def _log_debug(self, message: str) -> None:
        """Log debug message if logger available."""
        if self.logger:
            self.logger.debug(message)
