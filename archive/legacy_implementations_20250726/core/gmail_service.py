#!/usr/bin/env python3
"""
Persistent Gmail Service Manager
================================

Singleton pattern for maintaining a persistent Gmail API connection
across all scripts in the project.
"""

import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class GmailServiceManager:
    """
    Singleton Gmail service manager.

    Maintains a persistent connection to Gmail API with automatic
    token refresh and connection pooling.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the service manager (only runs once)."""
        if self._initialized:
            return

        self.service = None
        self.credentials = None
        self.last_refresh = None
        self.token_path = None
        self.email_address = None

        self.SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
        self._initialized = True

        # Auto-initialize on creation
        self._initialize_service()

    def _initialize_service(self):
        """Initialize Gmail service with saved credentials."""
        if not GMAIL_AVAILABLE:
            logger.error("Gmail API packages not installed")
            return False

        # Find token file
        token_paths = [
            "config/gmail_token.json",
            "config/token.json",
            "gmail_token.json",
            ".gmail_token.json",
            os.path.expanduser("~/.config/editorial_scripts/gmail_token.json"),
        ]

        for path in token_paths:
            if os.path.exists(path):
                self.token_path = path
                break

        if not self.token_path:
            logger.error("No Gmail token found. Run setup_gmail_auth.py first.")
            return False

        try:
            # Load credentials
            self.credentials = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

            # Refresh if needed
            if self.credentials.expired and self.credentials.refresh_token:
                self.refresh_credentials()

            # Build service
            self.service = build("gmail", "v1", credentials=self.credentials)

            # Get user email
            profile = self.service.users().getProfile(userId="me").execute()
            self.email_address = profile.get("emailAddress")

            logger.info(f"Gmail service initialized for {self.email_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return False

    def refresh_credentials(self):
        """Refresh expired credentials."""
        try:
            self.credentials.refresh(Request())

            # Save refreshed token
            with open(self.token_path, "w") as token:
                token.write(self.credentials.to_json())

            self.last_refresh = datetime.now()
            logger.info("Refreshed Gmail credentials")

        except Exception as e:
            logger.error(f"Failed to refresh credentials: {e}")
            raise

    def get_service(self):
        """
        Get Gmail service instance.

        Automatically handles credential refresh and connection issues.
        """
        if not self.service:
            if not self._initialize_service():
                return None

        # Check if we need to refresh (every 45 minutes to be safe)
        if self.last_refresh:
            if datetime.now() - self.last_refresh > timedelta(minutes=45):
                try:
                    self.refresh_credentials()
                    self.service = build("gmail", "v1", credentials=self.credentials)
                except:
                    pass

        return self.service

    def search_messages(self, query: str, max_results: int = 10) -> list:
        """
        Search Gmail messages.

        Args:
            query: Gmail search query
            max_results: Maximum number of results

        Returns:
            List of message IDs
        """
        service = self.get_service()
        if not service:
            return []

        try:
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            return results.get("messages", [])

        except HttpError as e:
            if e.resp.status == 401:
                # Try to refresh and retry
                self.refresh_credentials()
                service = self.get_service()
                if service:
                    results = (
                        service.users()
                        .messages()
                        .list(userId="me", q=query, maxResults=max_results)
                        .execute()
                    )
                    return results.get("messages", [])

            logger.error(f"Search failed: {e}")
            return []

    def get_message(self, message_id: str) -> dict[str, Any] | None:
        """Get full message by ID."""
        service = self.get_service()
        if not service:
            return None

        try:
            return service.users().messages().get(userId="me", id=message_id).execute()
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None

    def get_latest_verification_code(self, timeout_seconds: int = 60) -> str | None:
        """
        Get the latest verification code from Gmail.

        Searches for recent verification emails and extracts codes.
        """
        import base64
        import re
        import time

        start_time = time.time()

        while (time.time() - start_time) < timeout_seconds:
            # Search for recent verification emails
            messages = self.search_messages(
                query='(subject:"verification code" OR subject:"access code" OR subject:"login code") newer_than:5m',
                max_results=5,
            )

            for msg in messages:
                full_msg = self.get_message(msg["id"])
                if not full_msg:
                    continue

                # Extract body
                body = ""
                payload = full_msg.get("payload", {})

                if "parts" in payload:
                    for part in payload["parts"]:
                        if part["mimeType"] == "text/plain":
                            data = part["body"]["data"]
                            body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif payload.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                        "utf-8", errors="ignore"
                    )

                # Look for verification code
                patterns = [
                    r"verification code[:\s]*([0-9]{4,8})",
                    r"access code[:\s]*([0-9]{4,8})",
                    r"login code[:\s]*([0-9]{4,8})",
                    r"code[:\s]*([0-9]{4,8})",
                    r"([0-9]{6})\s*is your",
                    r"\b([0-9]{6})\b",
                ]

                for pattern in patterns:
                    match = re.search(pattern, body, re.IGNORECASE)
                    if match:
                        code = match.group(1)
                        if code.isdigit() and 4 <= len(code) <= 8:
                            logger.info(f"Found verification code: {code}")
                            return code

            # Wait before next check
            time.sleep(3)

        return None


# Global instance
_gmail_service = None


def get_gmail_service():
    """Get the global Gmail service instance."""
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailServiceManager()
    return _gmail_service


# Convenience functions
def fetch_latest_verification_code(
    journal_code: str = None, max_wait: int = 60, poll_interval: int = 3
) -> str | None:
    """
    Fetch latest verification code using persistent Gmail connection.

    Args:
        journal_code: Journal code (for logging)
        max_wait: Maximum seconds to wait
        poll_interval: Seconds between checks (not used with new implementation)

    Returns:
        Verification code or None
    """
    service = get_gmail_service()
    return service.get_latest_verification_code(max_wait)


def search_emails(query: str, max_results: int = 10) -> list:
    """Search emails using persistent connection."""
    service = get_gmail_service()
    return service.search_messages(query, max_results)


def get_email(message_id: str) -> dict[str, Any] | None:
    """Get email by ID using persistent connection."""
    service = get_gmail_service()
    return service.get_message(message_id)
