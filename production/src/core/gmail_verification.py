#!/usr/bin/env python3
"""
Gmail verification code fetcher for 2FA authentication.
"""

import base64
import logging
import os
import re
import time
from datetime import datetime

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print(
        "⚠️  Gmail API not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )

logger = logging.getLogger(__name__)


def fetch_latest_verification_code(
    journal_code: str, max_wait: int = 60, poll_interval: int = 3, start_timestamp: float = None
) -> str | None:
    """
    Fetch the latest verification code from Gmail for a specific journal.

    Args:
        journal_code: Journal code (e.g., 'MF', 'MOR')
        max_wait: Maximum seconds to wait for code
        poll_interval: Seconds between checks
        start_timestamp: Unix timestamp when credentials were submitted (emails must be AFTER this)

    Returns:
        Verification code string or None
    """
    if not GMAIL_AVAILABLE:
        print("❌ Gmail API not available")
        return None

    # Initialize Gmail service
    service = _get_gmail_service()
    if not service:
        print("❌ Failed to initialize Gmail service")
        return None

    # Search for verification emails
    start_time = time.time()

    # If no start_timestamp provided, use current time minus 1 minute
    if start_timestamp is None:
        start_timestamp = time.time() - 60

    # Convert timestamp to Gmail search format (seconds since epoch)
    # Gmail wants: after:<seconds_since_epoch>
    # Look for emails 5 seconds before the timestamp to account for timing differences
    gmail_after = int(start_timestamp) - 5

    while (time.time() - start_time) < max_wait:
        try:
            # Search for verification emails from ScholarOne (MOR/MF use onbehalfof@manuscriptcentral.com)
            # Don't use after: filter initially as it may not work with very recent timestamps
            query = 'from:onbehalfof@manuscriptcentral.com (subject:"verification code" OR subject:"access code" OR subject:"login code")'
            print(
                f"   🔍 Searching for emails after timestamp {start_timestamp} ({datetime.fromtimestamp(start_timestamp).strftime('%H:%M:%S')})"
            )

            results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()

            messages = results.get("messages", [])

            for msg in messages:
                # Get full message
                message = service.users().messages().get(userId="me", id=msg["id"]).execute()

                # Get message internal date for logging
                internal_date = int(message.get("internalDate", 0)) // 1000

                # Extract code from message
                code = _extract_code_from_message(message)
                if code:
                    age_seconds = time.time() - internal_date
                    age_mins = int(age_seconds / 60)

                    # Check if email is AFTER the start_timestamp (with 5s buffer for timing)
                    if internal_date >= (start_timestamp - 5):
                        print(f"✅ Found verification code: {code} (from {age_mins} minutes ago)")
                        return code
                    else:
                        print(
                            f"⏭️  Skipping old code: {code} (from {age_mins} minutes ago, before login attempt)"
                        )

            # Wait before next check
            time.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error fetching verification code: {e}")
            time.sleep(poll_interval)

    print("❌ No verification code found within timeout")
    return None


def _get_gmail_service():
    """Get Gmail service instance with persistent credentials."""
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    # Get project root directory - FIXED PATH CALCULATION
    from pathlib import Path

    # From production/src/core/gmail_verification.py, we need to go up to project root
    current_file = Path(__file__).resolve()

    # Try multiple approaches to find project root
    possible_roots = [
        current_file.parent.parent.parent.parent,  # production/src/core -> project root
        current_file.parent.parent.parent,  # If we're in src/core
        Path.cwd(),  # Current working directory
        Path.home() / "Library/CloudStorage/Dropbox/Work/editorial_scripts",  # Explicit path
    ]

    # Find the actual project root by looking for config directory
    project_root = None
    for root in possible_roots:
        if (root / "config" / "gmail_token.json").exists():
            project_root = root
            break

    if not project_root:
        project_root = possible_roots[0]  # Fallback

    # Check for existing token - prioritize the known location
    token_paths = [
        str(project_root / "config/gmail_token.json"),
        str(project_root / "config/token.json"),
        "config/gmail_token.json",
        "config/token.json",
        "gmail_token.json",
        os.path.expanduser("~/.gmail_token.json"),
    ]

    creds = None
    for token_path in token_paths:
        if os.path.exists(token_path):
            try:
                print(f"   📁 Found token file at: {token_path}")
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info(f"Loaded credentials from {token_path}")

                # Check if token needs refresh
                if creds and creds.expired and creds.refresh_token:
                    try:
                        print("   🔄 Token expired, refreshing...")
                        creds.refresh(Request())
                        # Save refreshed token
                        with open(token_path, "w") as token:
                            token.write(creds.to_json())
                        logger.info("Refreshed expired token")
                        print("   ✅ Token refreshed successfully")
                    except Exception as e:
                        logger.error(f"Failed to refresh token: {e}")
                        print(f"   ❌ Token refresh failed: {e}")
                        creds = None

                if creds and creds.valid:
                    print("   ✅ Valid credentials loaded")
                    break
            except Exception as e:
                logger.warning(f"Failed to load credentials from {token_path}: {e}")
                print(f"   ⚠️ Failed to load from {token_path}: {e}")
                continue

    if not creds or not creds.valid:
        logger.error("No valid Gmail credentials found. Run setup_gmail_auth.py first.")
        print("   ❌ No valid Gmail credentials found")
        return None

    try:
        service = build("gmail", "v1", credentials=creds)
        # Test the service
        service.users().getProfile(userId="me").execute()
        return service
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        return None


def _extract_code_from_message(message):
    """Extract verification code from email message."""
    try:
        # Get email body
        payload = message["payload"]
        body = _get_body_from_payload(payload)

        if not body:
            return None

        # Common verification code patterns
        patterns = [
            r"verification code[:\s]*([0-9]{4,8})",
            r"access code[:\s]*([0-9]{4,8})",
            r"login code[:\s]*([0-9]{4,8})",
            r"code[:\s]*([0-9]{4,8})",
            r"([0-9]{6})\s*is your",
            r"\b([0-9]{6})\b",  # Any 6-digit number
            r"\b([0-9]{4})\b",  # Any 4-digit number
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                code = match.group(1)
                if code.isdigit() and 4 <= len(code) <= 8:
                    return code

    except Exception as e:
        logger.error(f"Error extracting code: {e}")

    return None


def _get_body_from_payload(payload):
    """Extract body text from email payload."""
    body = ""

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"]["data"]
                body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    elif payload["body"].get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")

    return body


if __name__ == "__main__":
    # Test the function
    code = fetch_latest_verification_code("MF")
    if code:
        print(f"✅ Test successful: {code}")
    else:
        print("❌ Test failed")
