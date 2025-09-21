"""
Enhanced Gmail Verification with Timestamp Filtering
===================================================

Fetches verification codes with proper timestamp filtering to ensure
we only get codes sent AFTER a specific action (like clicking login).
"""

import base64
import logging
import os
import re
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

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
    journal_code: str,
    max_wait: int = 60,
    poll_interval: int = 3,
    start_timestamp: datetime | None = None,
) -> str | None:
    """
    Fetch the latest verification code from Gmail for a specific journal.

    Args:
        journal_code: Journal code (e.g., 'MF', 'MOR')
        max_wait: Maximum seconds to wait for code
        poll_interval: Seconds between checks
        start_timestamp: Only accept emails received after this time

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

    # If no start timestamp provided, use current time minus 5 minutes
    if not start_timestamp:
        start_timestamp = datetime.now(UTC) - timedelta(minutes=5)

    # Ensure start_timestamp is timezone-aware
    if start_timestamp.tzinfo is None:
        # If naive, assume it's UTC
        start_timestamp = start_timestamp.replace(tzinfo=UTC)

    logger.info(f"Looking for verification codes after {start_timestamp}")

    # Search for verification emails
    start_time = time.time()
    while (time.time() - start_time) < max_wait:
        try:
            # Search for recent verification emails
            query = '(subject:"verification code" OR subject:"access code" OR subject:"login code") newer_than:5m'

            results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()

            messages = results.get("messages", [])

            for msg in messages:
                # Get full message
                message = service.users().messages().get(userId="me", id=msg["id"]).execute()

                # Check message timestamp
                msg_time = _get_message_timestamp(message)
                if not msg_time:
                    print("⚠️  Could not get message timestamp, skipping")
                    continue

                # Debug: Show timestamp comparison
                print(f"📧 Message time: {msg_time}")
                print(f"🕐 Start time:   {start_timestamp}")
                print(f"   Difference:   {(msg_time - start_timestamp).total_seconds()} seconds")

                # ONLY accept messages sent AFTER the login click
                if msg_time <= start_timestamp:
                    print("⏭️  Skipping (too old)")
                    continue

                print("✅ Message is new enough!")

                # Extract code from message
                code = _extract_code_from_message(message)
                if code:
                    print(f"✅ Found verification code: {code} (sent at {msg_time})")
                    return code

            # Wait before next check
            time.sleep(poll_interval)

        except Exception as e:
            logger.error(f"Error fetching verification code: {e}")
            time.sleep(poll_interval)

    print("❌ No verification code found within timeout")
    return None


def _get_message_timestamp(message) -> datetime | None:
    """Extract timestamp from email message."""
    try:
        # Get headers
        headers = message["payload"].get("headers", [])

        # Find Date header
        for header in headers:
            if header["name"] == "Date":
                date_str = header["value"]
                # Parse email date format (this returns timezone-aware datetime)
                return parsedate_to_datetime(date_str)

        # Fallback to internalDate
        internal_date = message.get("internalDate")
        if internal_date:
            # Convert milliseconds to datetime (UTC)
            timestamp = int(internal_date) / 1000
            return datetime.fromtimestamp(timestamp, tz=UTC)

    except Exception as e:
        logger.error(f"Error parsing message timestamp: {e}")

    return None


def _get_gmail_service():
    """Get Gmail service instance with persistent credentials."""
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    # Get project root directory
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    # Check for existing token
    token_paths = [
        str(project_root / "config/gmail_token.json"),
        str(project_root / "config/token.json"),
        os.path.expanduser("~/.editorial_scripts/gmail_token.json"),
    ]

    creds = None
    for token_path in token_paths:
        if os.path.exists(token_path):
            logger.info(f"Loading Gmail token from: {token_path}")
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            break

    # If credentials are invalid or missing, refresh/create them
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Look for credentials file
            cred_paths = [
                str(project_root / "config/gmail_credentials.json"),
                str(project_root / "config/credentials.json"),
                os.path.expanduser("~/.editorial_scripts/gmail_credentials.json"),
            ]

            flow = None
            for cred_path in cred_paths:
                if os.path.exists(cred_path):
                    logger.info(f"Using Gmail credentials from: {cred_path}")
                    flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
                    break

            if not flow:
                logger.error("No Gmail credentials file found")
                return None

            creds = flow.run_local_server(port=0)

        # Save the credentials for next run
        save_path = token_paths[0]
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w") as token:
            token.write(creds.to_json())
        logger.info(f"Saved Gmail token to: {save_path}")

    try:
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to build Gmail service: {e}")
        return None


def _extract_code_from_message(message) -> str | None:
    """Extract verification code from email message."""
    try:
        # Get email body
        parts = message["payload"].get("parts", [])
        body = ""

        if parts:
            for part in parts:
                if part["mimeType"] == "text/plain":
                    data = part["body"]["data"]
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
        else:
            # Single part message
            data = message["payload"]["body"].get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")

        # Look for 6-digit codes
        codes = re.findall(r"\b(\d{6})\b", body)
        if codes:
            # Return the first code found
            return codes[0]

        # Look for codes with spaces or dashes
        codes = re.findall(r"(\d{3}[\s-]?\d{3})", body)
        if codes:
            # Remove spaces/dashes and return
            return re.sub(r"[\s-]", "", codes[0])

    except Exception as e:
        logger.error(f"Error extracting code from message: {e}")

    return None
