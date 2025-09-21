#!/usr/bin/env python3
"""
Gmail search functionality for cross-checking manuscript communications.
"""

import base64
import logging
import os
import re
from datetime import UTC, datetime, timedelta

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


class GmailSearchManager:
    """Manages Gmail searches for manuscript-related communications."""

    def __init__(self):
        """Initialize Gmail search manager."""
        self.service = None
        self._cache = {}  # Cache search results

    def initialize(self):
        """Initialize Gmail service."""
        if not GMAIL_AVAILABLE:
            logger.error("Gmail API not available")
            return False

        SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

        # Use same token loading logic as gmail_verification.py
        from pathlib import Path

        token_paths = [
            "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json",
            Path.home()
            / "Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json",
            "config/gmail_token.json",
        ]

        creds = None
        for token_path in token_paths:
            if os.path.exists(token_path):
                try:
                    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        # Save refreshed token
                        with open(token_path, "w") as token:
                            token.write(creds.to_json())
                    if creds and creds.valid:
                        break
                except Exception as e:
                    logger.warning(f"Failed to load credentials from {token_path}: {e}")
                    continue

        if not creds or not creds.valid:
            logger.error("No valid Gmail credentials found")
            return False

        try:
            self.service = build("gmail", "v1", credentials=creds)
            # Test the service
            self.service.users().getProfile(userId="me").execute()
            logger.info("Gmail service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False

    def search_manuscript_emails(
        self, manuscript_id: str, referee_emails: list[str], date_range: tuple | None = None
    ) -> list[dict]:
        """
        Search for emails related to a manuscript.

        Args:
            manuscript_id: Manuscript ID (e.g., 'MAFI-2025-0166')
            referee_emails: List of referee email addresses
            date_range: Optional tuple of (start_date, end_date) as datetime objects

        Returns:
            List of email communications with metadata
        """
        if not self.service:
            if not self.initialize():
                return []

        # Build search query
        query_parts = []

        # Search for manuscript ID
        if manuscript_id:
            # Remove any journal prefix for broader search
            clean_id = re.sub(r"^[A-Z]+-", "", manuscript_id)
            query_parts.append(f'("{manuscript_id}" OR "{clean_id}")')

        # Search for referee emails
        if referee_emails:
            email_queries = []
            for email in referee_emails:
                if email and "@" in email:
                    email_queries.append(f"(from:{email} OR to:{email})")
            if email_queries:
                query_parts.append(f'({" OR ".join(email_queries)})')

        # Add date range if provided
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            if start_date:
                query_parts.append(f'after:{start_date.strftime("%Y/%m/%d")}')
            if end_date:
                query_parts.append(f'before:{end_date.strftime("%Y/%m/%d")}')

        # Add keywords to narrow down results
        keyword_query = (
            '(referee OR review OR manuscript OR "peer review" OR revision OR decision OR editor)'
        )
        query_parts.append(keyword_query)

        # Combine query parts
        query = " ".join(query_parts)

        # Check cache
        cache_key = f"{manuscript_id}_{hash(frozenset(referee_emails or []))}"
        if cache_key in self._cache:
            logger.info(f"Using cached results for {manuscript_id}")
            return self._cache[cache_key]

        try:
            logger.info(f"Searching Gmail with query: {query[:100]}...")

            messages = []
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=100)  # Limit to prevent too many results
                .execute()
            )

            message_list = results.get("messages", [])

            # Get detailed information for each message
            for msg in message_list:
                try:
                    message = (
                        self.service.users().messages().get(userId="me", id=msg["id"]).execute()
                    )

                    # Extract email metadata
                    email_data = self._extract_email_data(message)
                    if email_data:
                        messages.append(email_data)

                except Exception as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
                    continue

            # Sort by date
            messages.sort(key=lambda x: x.get("date", ""), reverse=True)

            # Cache results
            self._cache[cache_key] = messages

            logger.info(f"Found {len(messages)} emails for manuscript {manuscript_id}")
            return messages

        except Exception as e:
            logger.error(f"Error searching Gmail: {e}")
            return []

    def _extract_email_data(self, message) -> dict | None:
        """Extract relevant data from Gmail message."""
        try:
            headers = message["payload"].get("headers", [])

            # Extract headers
            email_data = {"id": message["id"], "thread_id": message["threadId"]}

            for header in headers:
                name = header["name"].lower()
                value = header["value"]

                if name == "from":
                    email_data["from"] = value
                    # Extract just email address
                    match = re.search(r"<(.+?)>", value)
                    email_data["from_email"] = match.group(1) if match else value
                elif name == "to":
                    email_data["to"] = value
                elif name == "subject":
                    email_data["subject"] = value
                elif name == "date":
                    email_data["date"] = value
                    # Parse date
                    try:
                        from email.utils import parsedate_to_datetime

                        email_data["datetime"] = parsedate_to_datetime(value)
                    except:
                        pass

            # Extract body snippet
            email_data["snippet"] = message.get("snippet", "")

            # Extract full body
            body = self._get_body_from_payload(message["payload"])
            email_data["body"] = body

            # Determine communication type
            email_data["type"] = self._determine_email_type(email_data)

            # Mark as external (not from MF platform)
            email_data["source"] = "gmail"
            email_data["external"] = True

            return email_data

        except Exception as e:
            logger.error(f"Error extracting email data: {e}")
            return None

    def _get_body_from_payload(self, payload) -> str:
        """Extract body text from email payload."""
        body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"]["data"]
                    body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif "parts" in part:
                    # Recursive for nested parts
                    body += self._get_body_from_payload(part)
        elif payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                "utf-8", errors="ignore"
            )

        return body

    def _determine_email_type(self, email_data: dict) -> str:
        """Determine the type of communication from email content."""
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "").lower()
        snippet = email_data.get("snippet", "").lower()

        combined_text = f"{subject} {snippet} {body[:500]}"  # Check first 500 chars of body

        # Patterns for different email types
        if any(
            term in combined_text for term in ["referee report", "review report", "reviewer report"]
        ):
            return "referee_report_submitted"
        elif any(term in combined_text for term in ["invitation to review", "referee invitation"]):
            return "referee_invited"
        elif any(term in combined_text for term in ["accepted to review", "agreed to review"]):
            return "referee_accepted"
        elif any(
            term in combined_text for term in ["decline", "unable to review", "cannot review"]
        ):
            return "referee_declined"
        elif any(
            term in combined_text for term in ["revision", "revised manuscript", "resubmission"]
        ):
            return "revision_submitted"
        elif any(term in combined_text for term in ["decision", "accept", "reject"]):
            return "editorial_decision"
        elif any(term in combined_text for term in ["reminder", "overdue", "deadline"]):
            return "reminder"
        else:
            return "general_correspondence"

    def merge_with_audit_trail(
        self, audit_trail: list[dict], external_emails: list[dict], manuscript_id: str
    ) -> list[dict]:
        """
        Merge external emails with audit trail to create complete timeline.

        Args:
            audit_trail: Communication events from MF platform
            external_emails: Emails found via Gmail search
            manuscript_id: Manuscript ID for deduplication

        Returns:
            Merged and sorted timeline of all communications
        """
        # Create a set to track what we've already seen (to avoid duplicates)
        seen_events = set()
        merged_timeline = []

        # First, add all audit trail events
        for event in audit_trail:
            # Create a unique key for the event
            event_key = self._create_event_key(event)
            if event_key:
                seen_events.add(event_key)
                event["source"] = "mf_platform"
                event["external"] = False
                merged_timeline.append(event)

        # Then add external emails that don't duplicate audit trail
        for email in external_emails:
            # Check if this email might already be in audit trail
            email_key = self._create_event_key(email)

            # Also check for close time matches (within 5 minutes)
            is_duplicate = False
            if email_key in seen_events:
                is_duplicate = True
            else:
                # Check for time-based duplicates
                email_time = email.get("datetime")
                if email_time:
                    for event in audit_trail:
                        event_time = event.get("datetime") or event.get("date")
                        # Convert string timestamps if needed
                        if not isinstance(event_time, datetime) and event.get("timestamp_gmt"):
                            try:
                                clean_date = event["timestamp_gmt"].replace(" GMT", "")
                                # Parse without timezone first
                                event_time = datetime.strptime(clean_date, "%d-%b-%Y %I:%M %p")
                                # Make it timezone-aware if email_time is timezone-aware
                                if email_time.tzinfo is not None:
                                    event_time = event_time.replace(tzinfo=UTC)
                            except:
                                event_time = None

                        if event_time and isinstance(event_time, datetime):
                            # Ensure both datetimes have same timezone awareness
                            if email_time.tzinfo is not None and event_time.tzinfo is None:
                                event_time = event_time.replace(tzinfo=UTC)
                            elif email_time.tzinfo is None and event_time.tzinfo is not None:
                                event_time = event_time.replace(tzinfo=None)

                            time_diff = abs((email_time - event_time).total_seconds())
                            if time_diff < 300:  # 5 minutes
                                # Check if same type or similar content
                                if email.get("type") == event.get("type") or self._similar_content(
                                    email, event
                                ):
                                    is_duplicate = True
                                    break

            if not is_duplicate:
                # This is a unique external communication
                email["external"] = True
                email["note"] = "External communication (not in MF audit trail)"
                merged_timeline.append(email)
                logger.info(f"Added external email: {email.get('subject', 'No subject')}")

        # Sort by date with proper date parsing
        def get_sort_date(event):
            """Get a sortable date from various formats."""
            # Try datetime first
            if event.get("datetime"):
                if isinstance(event["datetime"], datetime):
                    return event["datetime"]
                try:
                    return datetime.fromisoformat(event["datetime"].replace("Z", "+00:00"))
                except:
                    pass

            # Try date field
            if event.get("date"):
                if isinstance(event["date"], datetime):
                    return event["date"]

            # Try GMT timestamp from platform events
            if event.get("timestamp_gmt"):
                try:
                    clean_date = event["timestamp_gmt"].replace(" GMT", "")
                    parsed = datetime.strptime(clean_date, "%d-%b-%Y %I:%M %p")
                    # Make it timezone-aware UTC to match Gmail dates

                    return parsed.replace(tzinfo=UTC)
                except:
                    pass

            # Default to epoch (timezone-aware)

            return datetime(1970, 1, 1, tzinfo=UTC)

        merged_timeline.sort(key=get_sort_date, reverse=True)

        # Add sequence numbers
        for i, event in enumerate(merged_timeline):
            event["sequence"] = i + 1
            event["manuscript_id"] = manuscript_id

        logger.info(
            f"Merged timeline: {len(audit_trail)} platform events + "
            f"{len([e for e in merged_timeline if e.get('external')])} external emails = "
            f"{len(merged_timeline)} total events"
        )

        return merged_timeline

    def _create_event_key(self, event: dict) -> str | None:
        """Create a unique key for deduplication."""
        # Use combination of date, type, and participants
        date = event.get("date") or event.get("datetime") or event.get("timestamp_gmt")
        event_type = event.get("type", "") or event.get("event_type", "")
        from_email = event.get("from_email", "") or event.get("from", "")
        to_email = event.get("to", "")

        if date:
            # Handle various date formats
            if isinstance(date, datetime):
                date_str = date.strftime("%Y-%m-%d %H:%M")
            elif isinstance(date, str) and "GMT" in date:
                # Handle GMT timestamp format from platform events
                try:
                    clean_date = date.replace(" GMT", "").replace(" EDT", "")
                    parsed = datetime.strptime(clean_date, "%d-%b-%Y %I:%M %p")
                    date_str = parsed.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = date[:20]  # First 20 chars as fallback
            else:
                date_str = str(date)

            if from_email or to_email:
                return f"{date_str}_{event_type}_{from_email}_{to_email}"

        return None

    def _similar_content(self, email: dict, event: dict) -> bool:
        """Check if email and event have similar content."""
        # Compare subjects/descriptions
        email_subject = email.get("subject", "").lower()
        event_desc = event.get("description", "").lower()

        if email_subject and event_desc:
            # Check for common keywords
            common_keywords = ["review", "report", "decision", "invitation", "reminder"]
            for keyword in common_keywords:
                if keyword in email_subject and keyword in event_desc:
                    return True

        # Compare participants
        email_from = email.get("from_email", "").lower()
        event_from = event.get("from", "").lower()

        if email_from and event_from and email_from == event_from:
            return True

        return False


# Convenience function for integration with MF extractor
def enhance_audit_trail_with_gmail(manuscript_data: dict) -> dict:
    """
    Enhance manuscript audit trail with Gmail communications.

    Args:
        manuscript_data: Manuscript data dictionary with audit_trail

    Returns:
        Enhanced manuscript data with complete timeline
    """
    try:
        # Initialize Gmail search
        gmail_manager = GmailSearchManager()

        # Get manuscript info
        manuscript_id = manuscript_data.get("id", "")
        referees = manuscript_data.get("referees", [])
        referee_emails = [r.get("email") for r in referees if r.get("email")]

        # Get date range from manuscript
        submission_date = manuscript_data.get("submission_date")
        date_range = None
        if submission_date:
            try:
                # Search from 30 days before submission to now
                if isinstance(submission_date, str):
                    submission_date = datetime.strptime(submission_date, "%Y-%m-%d")
                start_date = submission_date - timedelta(days=30)
                end_date = datetime.now()
                date_range = (start_date, end_date)
            except:
                pass

        # Search for external emails
        external_emails = gmail_manager.search_manuscript_emails(
            manuscript_id=manuscript_id, referee_emails=referee_emails, date_range=date_range
        )

        # Get current audit trail from the correct field
        # The extractor stores platform events in both 'audit_trail' and 'communication_timeline'
        audit_trail = manuscript_data.get("audit_trail", [])
        if not audit_trail:
            # Fallback to communication_timeline if audit_trail is empty
            audit_trail = manuscript_data.get("communication_timeline", [])
        logger.info(f"Found {len(audit_trail)} existing platform events")

        # Merge with external emails
        complete_timeline = gmail_manager.merge_with_audit_trail(
            audit_trail=audit_trail, external_emails=external_emails, manuscript_id=manuscript_id
        )

        # Update manuscript data
        manuscript_data["communication_timeline"] = complete_timeline
        manuscript_data["timeline_enhanced"] = True
        manuscript_data["external_communications_count"] = len(
            [e for e in complete_timeline if e.get("external")]
        )

        logger.info(
            f"Enhanced timeline for {manuscript_id}: "
            f"{len(complete_timeline)} total events "
            f"({manuscript_data['external_communications_count']} external)"
        )

        return manuscript_data

    except Exception as e:
        logger.error(f"Error enhancing audit trail: {e}")
        return manuscript_data
