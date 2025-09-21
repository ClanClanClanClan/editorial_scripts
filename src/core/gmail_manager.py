"""Gmail integration for verification codes and email-based extraction."""

import logging
import re
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import pickle

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False


class GmailManager:
    """Manages Gmail API access for verification codes and email extraction."""

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.service = None

        if not GMAIL_AVAILABLE:
            self.logger.warning("Gmail API libraries not installed")
            return

        self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        token_path = Path("config/gmail_token.json")

        # Load existing token
        if token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)
            except Exception as e:
                self.logger.error(f"Failed to load token: {e}")
                # Try pickle format as fallback
                token_pickle = Path("config/gmail_token.pickle")
                if token_pickle.exists():
                    with open(token_pickle, "rb") as token:
                        creds = pickle.load(token)

        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Need credentials.json from Google Cloud Console
                creds_path = Path("config/credentials.json")
                if not creds_path.exists():
                    # Try gmail_credentials.json as fallback
                    creds_path = Path("config/gmail_credentials.json")
                    if not creds_path.exists():
                        self.logger.error("Gmail credentials.json not found")
                        return

                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token as JSON
            token_path.parent.mkdir(exist_ok=True)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)
        self.logger.info("Gmail API authenticated")

    def get_verification_code(
        self, journal: str, start_time: datetime, wait_time: int = 60, poll_interval: int = 3
    ) -> str | None:
        """Get verification code from Gmail."""
        if not self.service:
            # Fallback to wrapper if available
            try:
                # Use local Gmail verification helper when API client not initialized
                from src.core.gmail_verification import fetch_latest_verification_code

                return fetch_latest_verification_code(
                    journal,
                    max_wait=wait_time,
                    poll_interval=poll_interval,
                    start_timestamp=start_time,
                )
            except Exception:
                self.logger.error("Gmail service not available")
                return None

        # Give the email system time to send the verification email
        self.logger.info("Waiting 5 seconds for email system to send verification email...")
        time.sleep(5)

        end_time = datetime.now() + timedelta(seconds=wait_time)
        attempt = 0

        while datetime.now() < end_time:
            attempt += 1
            remaining_time = int((end_time - datetime.now()).total_seconds())
            self.logger.debug(
                f"Attempt {attempt}: Checking for verification emails ({remaining_time}s remaining)"
            )
            try:
                # Search for verification emails
                query = self._build_verification_query(journal, start_time)
                results = (
                    self.service.users()
                    .messages()
                    .list(userId="me", q=query, maxResults=10)
                    .execute()
                )

                messages = results.get("messages", [])

                for message in messages:
                    msg = (
                        self.service.users().messages().get(userId="me", id=message["id"]).execute()
                    )

                    # Check timestamp - only accept emails after login
                    headers = msg["payload"].get("headers", [])
                    date_str = next((h["value"] for h in headers if h["name"] == "Date"), None)

                    if date_str:
                        from email.utils import parsedate_to_datetime

                        email_time = parsedate_to_datetime(date_str)

                        # Only process emails sent after login click
                        # Make both datetime objects timezone-aware for comparison
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=UTC)
                        if email_time.tzinfo is None:
                            email_time = email_time.replace(tzinfo=UTC)

                        if email_time > start_time:
                            code = self._extract_code_from_message(msg)
                            if code:
                                self.logger.info(
                                    f"Found verification code: {code[:3]}*** (sent at {email_time})"
                                )
                                return code
                        else:
                            self.logger.debug(f"Skipping old email from {email_time}")

            except Exception as e:
                self.logger.error(f"Error fetching emails: {e}")

            time.sleep(poll_interval)

        self.logger.warning(f"No verification code found after {wait_time}s")
        return None

    def _build_verification_query(self, journal: str, start_time: datetime) -> str:
        """Build Gmail search query for verification emails."""
        # Format time for Gmail query
        time_str = start_time.strftime("%Y/%m/%d")

        journal_queries = {
            "MF": 'from:onbehalfof@manuscriptcentral.com subject:"Mathematical Finance Verification Code"',
            "MOR": 'from:onbehalfof@manuscriptcentral.com subject:"Mathematics of Operations Research Verification Code"',
            "SICON": 'from:siam.org subject:"verification"',
            "SIFIN": 'from:siam.org subject:"verification"',
        }

        base_query = journal_queries.get(journal.upper(), 'subject:"verification code"')
        return f"{base_query} after:{time_str}"

    def _extract_code_from_message(self, message: dict[str, Any]) -> str | None:
        """Extract verification code from email message."""
        try:
            # Get email body
            body = self._get_body_from_message(message)
            if not body:
                return None

            # Common verification code patterns
            patterns = [
                r"Verification Code[:\s]+(\d{6})",  # Exact pattern from MF emails
                r"verification code[:\s]+(\d{6})",
                r"code[:\s]+(\d{6})",
                r"(\d{6})\s*is your",
                r"enter[:\s]+(\d{6})",
                r"\b(\d{6})\b",  # Any 6-digit number
            ]

            for pattern in patterns:
                match = re.search(pattern, body, re.IGNORECASE)
                if match:
                    return match.group(1)

        except Exception as e:
            self.logger.error(f"Error extracting code: {e}")

        return None

    def _get_body_from_message(self, message: dict[str, Any]) -> str | None:
        """Extract body text from Gmail message."""
        try:
            payload = message["payload"]

            # Check for plain text
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part["body"]["data"]
                        return self._decode_base64(data)
            elif payload["body"].get("data"):
                return self._decode_base64(payload["body"]["data"])

        except Exception as e:
            self.logger.error(f"Error getting message body: {e}")

        return None

    def _decode_base64(self, data: str) -> str:
        """Decode base64 email data."""
        import base64

        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    def search_emails(self, query: str, max_results: int = 50) -> list[dict[str, Any]]:
        """Search emails with a query."""
        if not self.service:
            return []

        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])

            # Get full message details
            full_messages = []
            for message in messages:
                msg = self.service.users().messages().get(userId="me", id=message["id"]).execute()
                full_messages.append(msg)

            return full_messages

        except Exception as e:
            self.logger.error(f"Email search failed: {e}")
            return []
