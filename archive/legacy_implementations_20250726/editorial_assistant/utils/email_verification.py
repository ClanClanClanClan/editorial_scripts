"""
Email Verification Manager

Handles 2FA email verification for journal logins.
Ports proven functionality from core/email_utils.py.
"""

import logging
import os
import re
from pathlib import Path

from .session_manager import session_manager


class EmailVerificationManager:
    """
    Handles 2FA email verification for journal logins.

    This class ports the proven email verification functionality
    from the legacy core/email_utils.py file.
    """

    def __init__(self):
        """Initialize email verification manager."""
        self.logger = logging.getLogger(__name__)

        # Try to import legacy email utilities
        self._legacy_available = self._check_legacy_availability()

    def _check_legacy_availability(self) -> bool:
        """Check if legacy email utilities are available."""
        try:
            # Check if legacy email_utils exists
            project_root = Path(__file__).parent.parent.parent
            legacy_email_utils = project_root / "core" / "email_utils.py"

            if legacy_email_utils.exists():
                session_manager.add_learning(
                    "Legacy email utilities available for 2FA verification"
                )
                return True
            else:
                session_manager.add_learning(
                    "Legacy email utilities not found - 2FA verification may be limited"
                )
                return False

        except Exception as e:
            self.logger.warning(f"Error checking legacy email utilities: {e}")
            return False

    def fetch_verification_code(
        self, journal: str, max_wait: int = 120, poll_interval: int = 5
    ) -> str | None:
        """
        Fetch verification code for journal login.

        This method uses the exact same approach as the legacy system
        for maximum compatibility and reliability.

        Args:
            journal: Journal code (e.g., 'MF', 'MOR')
            max_wait: Maximum time to wait for email in seconds
            poll_interval: Time between checks in seconds

        Returns:
            Verification code if found, None otherwise
        """
        session_manager.add_learning(f"Attempting to fetch verification code for {journal}")

        if self._legacy_available:
            return self._fetch_using_legacy(journal, max_wait, poll_interval)
        else:
            self.logger.warning(
                "Legacy email utilities not available - cannot fetch verification code"
            )
            return None

    def _fetch_using_legacy(self, journal: str, max_wait: int, poll_interval: int) -> str | None:
        """
        Fetch verification code using legacy email utilities.

        This method imports and uses the exact same function that works
        in the legacy extractors for maximum compatibility.
        """
        try:
            # Import legacy function
            import sys

            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))

            from core.email_utils import fetch_latest_verification_code

            self.logger.info(f"Fetching verification code for {journal} using legacy method...")

            # Use exact same function call as legacy extractors
            verification_code = fetch_latest_verification_code(
                journal=journal, max_wait=max_wait, poll_interval=poll_interval
            )

            # Clean up path
            if str(project_root) in sys.path:
                sys.path.remove(str(project_root))

            if verification_code:
                session_manager.add_learning(
                    f"Successfully fetched verification code for {journal}: {verification_code}"
                )
                return verification_code
            else:
                session_manager.add_learning(
                    f"No verification code found for {journal} within {max_wait} seconds"
                )
                return None

        except ImportError as e:
            self.logger.error(f"Could not import legacy email utilities: {e}")
            session_manager.add_learning(f"Legacy email import failed for {journal}: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching verification code for {journal}: {e}")
            session_manager.add_learning(f"Verification code fetch failed for {journal}: {str(e)}")
            return None

    def extract_code_from_text(self, text: str) -> str | None:
        """
        Extract verification code from email text.

        Uses the exact same patterns as legacy system for compatibility.
        """
        if not text:
            return None

        # Exact same patterns as legacy extract_verification_code_from_text
        patterns = [
            r"verification code[:\s]*([0-9]{4,8})",  # "verification code: 123456"
            r"verification token[:\s]*([0-9]{4,8})",  # "verification token: 123456"
            r"access code[:\s]*([0-9]{4,8})",  # "access code: 123456"
            r"authentication code[:\s]*([0-9]{4,8})",  # "authentication code: 123456"
            r"security code[:\s]*([0-9]{4,8})",  # "security code: 123456"
            r"login code[:\s]*([0-9]{4,8})",  # "login code: 123456"
            r"code[:\s]*([0-9]{4,8})",  # "code: 123456"
            r"token[:\s]*([0-9]{4,8})",  # "token: 123456"
            r"your code is[:\s]*([0-9]{4,8})",  # "your code is: 123456"
            r"enter the code[:\s]*([0-9]{4,8})",  # "enter the code: 123456"
            r"use this code[:\s]*([0-9]{4,8})",  # "use this code: 123456"
            r"([0-9]{4,8})\s*is your verification",  # "123456 is your verification"
            r"([0-9]{4,8})\s*is your access",  # "123456 is your access"
            r"\b([0-9]{4,8})\b(?=\s*(?:verification|access|authentication|security|login|code|token))",  # standalone numbers before keywords
            r"(?:verification|access|authentication|security|login|code|token)\s*[:\-]*\s*([0-9]{4,8})",  # keywords followed by numbers
            r"\b([0-9]{6})\b",  # any 6-digit number (common for verification codes)
            r"\b([0-9]{4})\b",  # any 4-digit number
            r"\b([0-9]{8})\b",  # any 8-digit number
        ]

        text_lower = text.lower()

        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Return the first match, ensuring it's a reasonable length
                code = matches[0]
                if 4 <= len(code) <= 8 and code.isdigit():
                    self.logger.debug(f"Extracted verification code: {code}")
                    return code

        return None

    def validate_email_setup(self) -> bool:
        """
        Validate that email verification is properly set up.

        Returns:
            True if email verification can be used, False otherwise
        """
        try:
            # Check for required environment variables
            required_vars = ["GMAIL_USER"]
            missing_vars = []

            for var in required_vars:
                if not os.environ.get(var):
                    missing_vars.append(var)

            if missing_vars:
                self.logger.warning(
                    f"Missing environment variables for email verification: {missing_vars}"
                )
                session_manager.add_learning(
                    f"Email verification setup incomplete: missing {missing_vars}"
                )
                return False

            # Check if we can access Gmail API
            if self._legacy_available:
                try:
                    import sys

                    project_root = Path(__file__).parent.parent.parent
                    sys.path.insert(0, str(project_root))

                    from core.email_utils import get_gmail_service

                    service = get_gmail_service()
                    if service:
                        session_manager.add_learning(
                            "Email verification setup validated successfully"
                        )
                        return True
                    else:
                        session_manager.add_learning("Gmail service could not be initialized")
                        return False

                except Exception as e:
                    self.logger.error(f"Error validating Gmail setup: {e}")
                    session_manager.add_learning(f"Gmail setup validation failed: {str(e)}")
                    return False
                finally:
                    if str(project_root) in sys.path:
                        sys.path.remove(str(project_root))
            else:
                session_manager.add_learning("Legacy email utilities not available for validation")
                return False

        except Exception as e:
            self.logger.error(f"Error validating email setup: {e}")
            return False


# Global email verification manager instance
_email_manager = None


def get_email_verification_manager() -> EmailVerificationManager:
    """Get or create global email verification manager."""
    global _email_manager

    if _email_manager is None:
        _email_manager = EmailVerificationManager()

    return _email_manager
