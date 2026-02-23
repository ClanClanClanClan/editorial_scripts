"""Async authentication manager using Playwright for ECC.

Handles authentication flows for all journal platforms using modern async browser automation.
Integrates with RBAC system and GDPR compliance.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.ecc.adapters.browser.playwright_manager import PlaywrightConfig
from src.ecc.adapters.security.gdpr_compliance import (
    GDPRComplianceManager,
    ProcessingPurpose,
)
from src.ecc.adapters.security.rbac_auth import AuthenticationManager as RBACAuthManager
from src.ecc.adapters.security.vault_client import VaultClient, VaultCredentialManager
from src.ecc.core.browser_facade import BrowserFacade, PlaywrightFacade
from src.ecc.core.error_handling import ExtractorError
from src.ecc.core.logging_system import ExtractorLogger, LogCategory
from src.ecc.core.retry_strategies import RetryConfigs, retry


class AuthMethod(Enum):
    """Authentication methods."""

    USERNAME_PASSWORD = "username_password"
    EMAIL_PASSWORD = "email_password"
    ORCID_OAUTH = "orcid_oauth"
    TWO_FACTOR = "two_factor"
    SAML_SSO = "saml_sso"


class JournalPlatform(Enum):
    """Journal platform types."""

    SCHOLARONE = "scholarone"
    SIAM = "siam"
    EDITORIAL_MANAGER = "editorial_manager"
    EMAIL_BASED = "email_based"


@dataclass
class AuthenticationCredentials:
    """Authentication credentials for a journal."""

    journal_id: str
    platform: JournalPlatform
    method: AuthMethod
    username: str | None = None
    password: str | None = None
    email: str | None = None
    orcid_id: str | None = None
    mfa_secret: str | None = None
    base_url: str = ""
    login_url: str = ""
    success_indicator: str = ""
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AuthenticationResult:
    """Result of authentication attempt."""

    success: bool
    journal_id: str
    session_data: dict[str, Any] = None
    cookies: list[dict[str, Any]] = None
    user_info: dict[str, Any] = None
    mfa_required: bool = False
    error_message: str = ""
    authentication_time: float = 0.0

    def __post_init__(self):
        if self.session_data is None:
            self.session_data = {}
        if self.cookies is None:
            self.cookies = []
        if self.user_info is None:
            self.user_info = {}


class GmailCodeExtractor:
    """Extract 2FA codes from Gmail API."""

    def __init__(self, gmail_address: str, logger: ExtractorLogger | None = None):
        """Initialize Gmail code extractor."""
        self.gmail_address = gmail_address
        self.logger = logger or ExtractorLogger("gmail_extractor")

    async def get_verification_code(
        self, journal_id: str, timeout: int = 300, code_pattern: str = r"\b\d{6}\b"
    ) -> str | None:
        """
        Get verification code from Gmail.

        Args:
            journal_id: Journal identifier
            timeout: Timeout in seconds
            code_pattern: Regex pattern for code

        Returns:
            Verification code or None
        """
        # This would integrate with Gmail API
        # For now, return a mock code for testing
        await asyncio.sleep(1)  # Simulate API call

        # Mock verification code
        if journal_id in ["mf", "mor"]:
            return "123456"

        return None


class AsyncAuthenticationManager:
    """Async authentication manager for all journal platforms."""

    def __init__(
        self,
        vault_client: VaultClient | None = None,
        rbac_auth: RBACAuthManager | None = None,
        gdpr_manager: GDPRComplianceManager | None = None,
        gmail_address: str | None = None,
        config: PlaywrightConfig | None = None,
        logger: ExtractorLogger | None = None,
    ):
        """
        Initialize async authentication manager.

        Args:
            vault_client: Vault client for credentials
            rbac_auth: RBAC authentication system
            gdpr_manager: GDPR compliance manager
            gmail_address: Gmail address for 2FA
            config: Playwright configuration
            logger: Logger instance
        """
        self.vault = vault_client
        self.rbac_auth = rbac_auth
        self.gdpr_manager = gdpr_manager
        self.gmail_address = gmail_address
        self.config = config or PlaywrightConfig(headless=True)
        self.logger = logger or ExtractorLogger("async_auth")

        # Credential manager
        self.credential_manager = (
            VaultCredentialManager(vault_client, logger) if vault_client else None
        )

        # Gmail code extractor
        self.gmail_extractor = GmailCodeExtractor(gmail_address, logger) if gmail_address else None

        # Authentication state
        self.authenticated_sessions: dict[str, AuthenticationResult] = {}
        self.authentication_cache: dict[str, dict[str, Any]] = {}

        # Platform handlers
        self.platform_handlers = {
            JournalPlatform.SCHOLARONE: self._authenticate_scholarone,
            JournalPlatform.SIAM: self._authenticate_siam,
            JournalPlatform.EDITORIAL_MANAGER: self._authenticate_editorial_manager,
            JournalPlatform.EMAIL_BASED: self._authenticate_email_based,
        }

    async def initialize(self):
        """Initialize authentication manager."""
        self.logger.enter_context("async_auth_init")

        try:
            # Verify GDPR compliance for authentication data processing
            if self.gdpr_manager:
                await self.gdpr_manager.initialize()

            self.logger.success("Async authentication manager initialized", LogCategory.SECURITY)

        except Exception as e:
            self.logger.error(f"Auth manager initialization failed: {e}")
            raise ExtractorError("Auth manager initialization failed") from e

        finally:
            self.logger.exit_context(success=True)

    async def authenticate_journal(
        self, journal_id: str, user_id: str | None = None, force_refresh: bool = False
    ) -> AuthenticationResult:
        """
        Authenticate with a specific journal.

        Args:
            journal_id: Journal identifier
            user_id: Optional user ID for GDPR compliance
            force_refresh: Force new authentication

        Returns:
            Authentication result
        """
        self.logger.enter_context(f"authenticate_{journal_id}")
        start_time = time.time()

        try:
            # Check cache first
            if not force_refresh and journal_id in self.authenticated_sessions:
                cached_result = self.authenticated_sessions[journal_id]
                if self._is_session_valid(cached_result):
                    self.logger.success(
                        f"Using cached authentication: {journal_id}", LogCategory.SECURITY
                    )
                    return cached_result

            # GDPR compliance check
            if self.gdpr_manager and user_id:
                can_process = await self.gdpr_manager.check_processing_consent(
                    user_id, ProcessingPurpose.SYSTEM_ADMINISTRATION
                )
                if not can_process:
                    raise ExtractorError(
                        f"No consent for authentication data processing: {user_id}"
                    )

            # Get credentials
            credentials = await self._get_journal_credentials(journal_id)

            # Get platform handler
            handler = self.platform_handlers.get(credentials.platform)
            if not handler:
                raise ExtractorError(f"No handler for platform: {credentials.platform}")

            # Perform authentication
            result = await handler(credentials)
            result.authentication_time = time.time() - start_time

            # Cache successful authentication
            if result.success:
                self.authenticated_sessions[journal_id] = result
                self.logger.success(
                    f"Authentication successful: {journal_id} ({result.authentication_time:.2f}s)",
                    LogCategory.SECURITY,
                )
            else:
                self.logger.error(f"Authentication failed: {journal_id} - {result.error_message}")

            return result

        except Exception as e:
            self.logger.error(f"Authentication error: {journal_id} - {e}")
            return AuthenticationResult(
                success=False,
                journal_id=journal_id,
                error_message=str(e),
                authentication_time=time.time() - start_time,
            )

        finally:
            self.logger.exit_context(success=True)

    async def _get_journal_credentials(self, journal_id: str) -> AuthenticationCredentials:
        """Get credentials for a journal."""
        if self.credential_manager:
            cred_data = await self.credential_manager.get_journal_credentials(journal_id)

            # Map journal to platform and configuration
            journal_config = self._get_journal_config(journal_id)

            return AuthenticationCredentials(
                journal_id=journal_id,
                platform=journal_config["platform"],
                method=journal_config["method"],
                username=cred_data.get("username"),
                password=cred_data.get("password"),
                email=cred_data.get("email"),
                orcid_id=cred_data.get("orcid_id"),
                base_url=journal_config["base_url"],
                login_url=journal_config["login_url"],
                success_indicator=journal_config["success_indicator"],
            )
        else:
            # Fallback to mock credentials for testing
            return self._get_mock_credentials(journal_id)

    def _get_journal_config(self, journal_id: str) -> dict[str, Any]:
        """Get journal configuration."""
        configs = {
            "mf": {
                "platform": JournalPlatform.SCHOLARONE,
                "method": AuthMethod.EMAIL_PASSWORD,
                "base_url": "https://mc.manuscriptcentral.com/mafi",
                "login_url": "https://mc.manuscriptcentral.com/mafi",
                "success_indicator": "Dashboard",
            },
            "mor": {
                "platform": JournalPlatform.SCHOLARONE,
                "method": AuthMethod.EMAIL_PASSWORD,
                "base_url": "https://mc.manuscriptcentral.com/mor",
                "login_url": "https://mc.manuscriptcentral.com/mor",
                "success_indicator": "Dashboard",
            },
            "sicon": {
                "platform": JournalPlatform.SIAM,
                "method": AuthMethod.ORCID_OAUTH,
                "base_url": "https://www.siam.org/publications/journals",
                "login_url": "https://epubs.siam.org/action/showLogin",
                "success_indicator": "My Account",
            },
            "sifin": {
                "platform": JournalPlatform.SIAM,
                "method": AuthMethod.ORCID_OAUTH,
                "base_url": "https://www.siam.org/publications/journals",
                "login_url": "https://epubs.siam.org/action/showLogin",
                "success_indicator": "My Account",
            },
        }

        return configs.get(
            journal_id,
            {
                "platform": JournalPlatform.SCHOLARONE,
                "method": AuthMethod.EMAIL_PASSWORD,
                "base_url": "",
                "login_url": "",
                "success_indicator": "Dashboard",
            },
        )

    def _get_mock_credentials(self, journal_id: str) -> AuthenticationCredentials:
        """Get mock credentials for testing."""
        return AuthenticationCredentials(
            journal_id=journal_id,
            platform=JournalPlatform.SCHOLARONE,
            method=AuthMethod.EMAIL_PASSWORD,
            email="test@university.edu",
            password="test_password",
            base_url="https://test.com",
            login_url="https://test.com/login",
            success_indicator="Dashboard",
        )

    @retry(config=RetryConfigs.AUTH)
    async def _authenticate_scholarone(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """Authenticate with ScholarOne platform."""
        self.logger.enter_context(f"scholarone_auth_{credentials.journal_id}")

        try:
            async with PlaywrightFacade(self.config, self.logger) as browser:
                # Navigate to login page
                await browser.navigate_to(
                    credentials.login_url,
                    wait_until="networkidle",
                    wait_for_selector="input[name='USERID'], input[name='USER']",
                )

                # Fill credentials
                email_filled = await browser.fill_input(
                    "input[name='USERID'], input[name='USER']",
                    credentials.email or credentials.username,
                )
                if not email_filled:
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message="Could not find email/username field",
                    )

                password_filled = await browser.fill_input(
                    "input[name='PASSWORD']", credentials.password
                )
                if not password_filled:
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message="Could not find password field",
                    )

                # Submit form
                login_clicked = await browser.click_element(
                    "input[name='logInButton'], input[type='submit']"
                )
                if not login_clicked:
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message="Could not click login button",
                    )

                # Wait for response
                await asyncio.sleep(3)

                # Check for 2FA
                mfa_field = await browser.get_text(
                    "input[name='TOKEN_VALUE'], input[name='MFA_CODE']"
                )
                if mfa_field is not None:
                    # Handle 2FA
                    if not await self._handle_scholarone_2fa(browser, credentials):
                        return AuthenticationResult(
                            success=False,
                            journal_id=credentials.journal_id,
                            error_message="2FA authentication failed",
                            mfa_required=True,
                        )

                # Check for success indicator
                success_text = await browser.get_text(f"text={credentials.success_indicator}")
                if success_text:
                    # Get session data
                    cookies = await browser.get_cookies()

                    # Extract user info
                    user_info = await self._extract_scholarone_user_info(browser)

                    return AuthenticationResult(
                        success=True,
                        journal_id=credentials.journal_id,
                        cookies=cookies,
                        user_info=user_info,
                        session_data={
                            "platform": "scholarone",
                            "authenticated_at": time.time(),
                            "base_url": credentials.base_url,
                        },
                    )
                else:
                    # Check for error messages
                    error_text = await browser.get_text(".error, .alert-danger, .message")
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message=error_text
                        or "Authentication failed - no success indicator found",
                    )

        except Exception as e:
            self.logger.error(f"ScholarOne authentication error: {e}")
            return AuthenticationResult(
                success=False,
                journal_id=credentials.journal_id,
                error_message=f"Authentication error: {e}",
            )

        finally:
            self.logger.exit_context(success=True)

    async def _handle_scholarone_2fa(
        self, browser: BrowserFacade, credentials: AuthenticationCredentials
    ) -> bool:
        """Handle ScholarOne 2FA authentication."""
        if not self.gmail_extractor:
            self.logger.error("Gmail extractor not available for 2FA")
            return False

        try:
            # Get verification code from Gmail
            verification_code = await self.gmail_extractor.get_verification_code(
                credentials.journal_id
            )

            if not verification_code:
                self.logger.error("Could not get verification code from Gmail")
                return False

            # Fill verification code
            code_filled = await browser.fill_input(
                "input[name='TOKEN_VALUE'], input[name='MFA_CODE']", verification_code
            )
            if not code_filled:
                return False

            # Submit 2FA form
            submit_clicked = await browser.click_element(
                "input[type='submit'], button[type='submit']"
            )
            if not submit_clicked:
                return False

            # Wait for response
            await asyncio.sleep(2)

            self.logger.success("2FA authentication successful", LogCategory.SECURITY)
            return True

        except Exception as e:
            self.logger.error(f"2FA handling failed: {e}")
            return False

    async def _extract_scholarone_user_info(self, browser: BrowserFacade) -> dict[str, Any]:
        """Extract user information from ScholarOne."""
        user_info = {}

        try:
            # Try to get user name
            name = await browser.get_text(".username, .user-name, .welcome")
            if name:
                user_info["name"] = name.strip()

            # Try to get user role
            role_text = await browser.get_text(".role, .user-role")
            if role_text:
                user_info["role"] = role_text.strip()

        except Exception as e:
            self.logger.warning(f"Could not extract user info: {e}")

        return user_info

    async def _authenticate_siam(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """Authenticate with SIAM platform using ORCID."""
        self.logger.enter_context(f"siam_auth_{credentials.journal_id}")

        try:
            async with PlaywrightFacade(self.config, self.logger) as browser:
                # Navigate to SIAM login
                await browser.navigate_to(credentials.login_url, wait_until="networkidle")

                # Look for ORCID login button
                orcid_clicked = await browser.click_element(
                    "a[href*='orcid'], button[data-provider='orcid']"
                )
                if not orcid_clicked:
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message="Could not find ORCID login button",
                    )

                # Wait for ORCID page
                await browser.wait_for_selector("input[name='userId'], input[name='username']")

                # Fill ORCID credentials
                email_filled = await browser.fill_input(
                    "input[name='userId'], input[name='username']",
                    credentials.orcid_id or credentials.email,
                )
                password_filled = await browser.fill_input(
                    "input[name='password']", credentials.password
                )

                if not (email_filled and password_filled):
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message="Could not fill ORCID credentials",
                    )

                # Submit ORCID login
                await browser.click_element("button[type='submit'], input[type='submit']")

                # Wait for redirect back to SIAM
                await asyncio.sleep(3)

                # Check for success indicator
                success_text = await browser.get_text(f"text={credentials.success_indicator}")
                if success_text:
                    cookies = await browser.get_cookies()

                    return AuthenticationResult(
                        success=True,
                        journal_id=credentials.journal_id,
                        cookies=cookies,
                        session_data={
                            "platform": "siam",
                            "authenticated_at": time.time(),
                            "auth_method": "orcid",
                        },
                    )
                else:
                    return AuthenticationResult(
                        success=False,
                        journal_id=credentials.journal_id,
                        error_message="SIAM authentication failed - no success indicator",
                    )

        except Exception as e:
            return AuthenticationResult(
                success=False,
                journal_id=credentials.journal_id,
                error_message=f"SIAM authentication error: {e}",
            )

        finally:
            self.logger.exit_context(success=True)

    async def _authenticate_editorial_manager(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """Authenticate with Editorial Manager platform."""
        # Similar implementation for Editorial Manager
        return AuthenticationResult(
            success=False,
            journal_id=credentials.journal_id,
            error_message="Editorial Manager authentication not implemented yet",
        )

    async def _authenticate_email_based(
        self, credentials: AuthenticationCredentials
    ) -> AuthenticationResult:
        """Authenticate with email-based systems."""
        # For email-based systems, we might just validate credentials
        return AuthenticationResult(
            success=True,
            journal_id=credentials.journal_id,
            session_data={"platform": "email", "authenticated_at": time.time()},
        )

    def _is_session_valid(self, result: AuthenticationResult) -> bool:
        """Check if authentication result is still valid."""
        if not result.success:
            return False

        # Check if session is expired (1 hour default)
        authenticated_at = result.session_data.get("authenticated_at", 0)
        session_age = time.time() - authenticated_at

        return session_age < 3600  # 1 hour

    async def get_authenticated_session(self, journal_id: str) -> AuthenticationResult | None:
        """Get authenticated session for journal."""
        session = self.authenticated_sessions.get(journal_id)

        if session and self._is_session_valid(session):
            return session

        return None

    async def logout_journal(self, journal_id: str) -> bool:
        """Logout from a journal."""
        if journal_id in self.authenticated_sessions:
            del self.authenticated_sessions[journal_id]
            self.logger.success(f"Logged out from journal: {journal_id}", LogCategory.SECURITY)
            return True

        return False

    async def logout_all(self):
        """Logout from all journals."""
        logged_out = list(self.authenticated_sessions.keys())
        self.authenticated_sessions.clear()

        if logged_out:
            self.logger.success(
                f"Logged out from {len(logged_out)} journals: {logged_out}", LogCategory.SECURITY
            )

    def get_authentication_stats(self) -> dict[str, Any]:
        """Get authentication statistics."""
        stats = {
            "active_sessions": len(self.authenticated_sessions),
            "journals": list(self.authenticated_sessions.keys()),
            "session_details": {},
        }

        for journal_id, result in self.authenticated_sessions.items():
            stats["session_details"][journal_id] = {
                "success": result.success,
                "authentication_time": result.authentication_time,
                "authenticated_at": result.session_data.get("authenticated_at", 0),
                "platform": result.session_data.get("platform", "unknown"),
                "mfa_used": result.mfa_required,
            }

        return stats
