#!/usr/bin/env python3
"""
Email-Audit Trail Crosscheck System

Crosschecks MF system audit trail with direct email communications
to create comprehensive referee interaction timelines.
"""

import base64
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

# Gmail API imports (require: pip install google-api-python-client google-auth)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("⚠️ Gmail API not available. Install: pip install google-api-python-client google-auth")

logger = logging.getLogger(__name__)


class EmailAuditCrosschecker:
    """Crosscheck email communications with MF audit trail."""

    # Gmail API scopes
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, credentials_path: str = "config/gmail_credentials.json"):
        """Initialize the email crosschecker."""
        self.credentials_path = credentials_path
        self.service = None
        self.user_email = None

        # Communication event types
        self.event_types = {
            "invitation": {
                "keywords": ["review", "referee", "invitation", "manuscript", "invite"],
                "patterns": [r"would you.*review", r"invitation.*review", r"referee.*manuscript"],
            },
            "follow_up": {
                "keywords": ["follow up", "reminder", "status", "checking", "wondered"],
                "patterns": [r"follow.?up", r"just.*wondering", r"checking.*status"],
            },
            "response": {
                "keywords": ["accept", "decline", "agree", "unable", "happy to", "sorry"],
                "patterns": [r"happy to.*review", r"unable to.*review", r"accept.*invitation"],
            },
            "submission": {
                "keywords": ["review", "report", "completed", "attached", "comments"],
                "patterns": [r"review.*attached", r"completed.*review", r"my.*comments"],
            },
        }

    def authenticate_gmail(self) -> bool:
        """Authenticate with Gmail API."""
        if not GMAIL_AVAILABLE:
            print("❌ Gmail API not available")
            return False

        try:
            creds = None
            token_path = Path(self.credentials_path).parent / "gmail_token.json"

            # Load existing token
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), self.SCOPES)

            # If no valid credentials, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not Path(self.credentials_path).exists():
                        print(f"❌ Gmail credentials not found at {self.credentials_path}")
                        print("   Please download from Google Cloud Console")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save the credentials
                with open(token_path, "w") as token:
                    token.write(creds.to_json())

            self.service = build("gmail", "v1", credentials=creds)

            # Get user email
            profile = self.service.users().getProfile(userId="me").execute()
            self.user_email = profile["emailAddress"]

            print(f"✅ Gmail authenticated for: {self.user_email}")
            return True

        except Exception as e:
            print(f"❌ Gmail authentication failed: {e}")
            return False

    def search_manuscript_emails(
        self, manuscript_id: str, referee_emails: list[str], date_range_days: int = 365
    ) -> list[dict]:
        """Search Gmail for manuscript-related emails."""
        if not self.service:
            print("❌ Gmail not authenticated")
            return []

        try:
            print(f"🔍 Searching emails for manuscript: {manuscript_id}")

            # Build search queries
            queries = []

            # 1. Manuscript ID in subject or body
            queries.append(f"subject:{manuscript_id}")
            queries.append(f"{manuscript_id}")

            # 2. Communications with referee emails
            for email in referee_emails:
                if email and "@" in email:
                    # Handle multiple emails (comma-separated)
                    for single_email in email.split(","):
                        single_email = single_email.strip()
                        if single_email:
                            queries.append(f"to:{single_email}")
                            queries.append(f"from:{single_email}")

            # 3. Date range
            date_from = (datetime.now() - timedelta(days=date_range_days)).strftime("%Y/%m/%d")
            queries = [f"{q} after:{date_from}" for q in queries]

            all_emails = []
            processed_message_ids = set()

            print(f"   📧 Running {len(queries)} search queries...")

            for query in queries[:10]:  # Limit to prevent API quota issues
                try:
                    results = (
                        self.service.users()
                        .messages()
                        .list(userId="me", q=query, maxResults=50)
                        .execute()
                    )

                    messages = results.get("messages", [])
                    print(f"   🔍 Query '{query[:50]}...' found {len(messages)} messages")

                    for msg in messages:
                        if msg["id"] not in processed_message_ids:
                            email_data = self.parse_email(msg["id"], manuscript_id, referee_emails)
                            if email_data:
                                all_emails.append(email_data)
                                processed_message_ids.add(msg["id"])

                except Exception as e:
                    print(f"   ⚠️ Query failed: {e}")
                    continue

            print(f"✅ Found {len(all_emails)} relevant emails for {manuscript_id}")
            return all_emails

        except Exception as e:
            print(f"❌ Email search failed: {e}")
            return []

    def parse_email(
        self, message_id: str, manuscript_id: str, referee_emails: list[str]
    ) -> dict | None:
        """Parse individual email message."""
        try:
            msg = self.service.users().messages().get(userId="me", id=message_id).execute()

            headers = msg["payload"].get("headers", [])
            header_dict = {h["name"].lower(): h["value"] for h in headers}

            # Extract email metadata
            email_data = {
                "message_id": message_id,
                "date": self.parse_email_date(header_dict.get("date", "")),
                "from": header_dict.get("from", ""),
                "to": header_dict.get("to", ""),
                "cc": header_dict.get("cc", ""),
                "subject": header_dict.get("subject", ""),
                "manuscript_id": manuscript_id,
                "body_snippet": msg.get("snippet", ""),
                "source": "direct_email",
            }

            # Extract email body for analysis
            body_text = self.extract_email_body(msg)
            email_data["body_preview"] = (
                body_text[:500] if body_text else email_data["body_snippet"]
            )

            # Classify communication type
            email_data["communication_type"] = self.classify_email_type(
                email_data["subject"], email_data["body_preview"]
            )

            # Match referee
            email_data["referee_matched"] = self.match_referee(
                email_data["from"], email_data["to"], referee_emails
            )

            # Determine direction
            email_data["direction"] = self.determine_email_direction(
                email_data["from"], referee_emails
            )

            return email_data

        except Exception as e:
            print(f"   ⚠️ Failed to parse email {message_id}: {e}")
            return None

    def extract_email_body(self, msg: dict) -> str:
        """Extract text content from email body."""
        try:
            payload = msg["payload"]

            # Handle different email structures
            if "parts" in payload:
                # Multipart email
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part["body"]:
                            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            else:
                # Single part email
                if payload["mimeType"] == "text/plain" and "data" in payload["body"]:
                    return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

            return ""

        except Exception:
            return ""

    def parse_email_date(self, date_str: str) -> str:
        """Parse email date to ISO format."""
        try:
            # Gmail date format example: "Thu, 22 Jun 2025 10:30:45 +0000"
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except:
            return date_str

    def classify_email_type(self, subject: str, body: str) -> str:
        """Classify the type of communication."""
        text = f"{subject} {body}".lower()

        for event_type, rules in self.event_types.items():
            # Check keywords
            if any(keyword in text for keyword in rules["keywords"]):
                return event_type

            # Check patterns
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in rules["patterns"]):
                return event_type

        return "other"

    def match_referee(
        self, from_email: str, to_email: str, referee_emails: list[str]
    ) -> str | None:
        """Match email to a referee."""
        all_emails = f"{from_email} {to_email}".lower()

        for ref_email in referee_emails:
            if ref_email and "@" in ref_email:
                # Handle multiple emails
                for single_email in ref_email.split(","):
                    single_email = single_email.strip().lower()
                    if single_email in all_emails:
                        return single_email

        return None

    def determine_email_direction(self, from_email: str, referee_emails: list[str]) -> str:
        """Determine if email is outgoing (to referee) or incoming (from referee)."""
        if self.user_email and self.user_email.lower() in from_email.lower():
            return "outgoing"

        for ref_email in referee_emails:
            if ref_email and ref_email.lower() in from_email.lower():
                return "incoming"

        return "unknown"

    def crosscheck_manuscript(self, manuscript_data: dict) -> dict:
        """Crosscheck a single manuscript with email communications."""
        manuscript_id = manuscript_data.get("id", "")

        # Extract referee emails
        referee_emails = []
        referees = manuscript_data.get("referees", [])

        for referee in referees:
            email = referee.get("email", "")
            if email:
                referee_emails.append(email)

        print(f"📋 Crosschecking manuscript: {manuscript_id}")
        print(f"   👥 Referee emails: {len(referee_emails)}")

        # Search for emails
        email_communications = self.search_manuscript_emails(
            manuscript_id, referee_emails, date_range_days=365
        )

        # Create enhanced timeline
        enhanced_timeline = self.create_enhanced_timeline(manuscript_data, email_communications)

        # Add email data to manuscript
        enhanced_manuscript = manuscript_data.copy()
        enhanced_manuscript["email_communications"] = email_communications
        enhanced_manuscript["enhanced_communication_timeline"] = enhanced_timeline

        return enhanced_manuscript

    def create_enhanced_timeline(
        self, manuscript_data: dict, email_communications: list[dict]
    ) -> list[dict]:
        """Create combined timeline of MF system events and email communications."""
        timeline = []

        # Add MF system events (if any)
        mf_timeline = manuscript_data.get("communication_timeline", [])
        for event in mf_timeline:
            timeline.append({**event, "source": "mf_system"})

        # Add email events
        for email in email_communications:
            timeline.append(
                {
                    "date": email["date"],
                    "event": f"{email['communication_type']} email ({email['direction']})",
                    "referee": email.get("referee_matched", "Unknown"),
                    "details": email["subject"],
                    "source": "direct_email",
                    "email_id": email["message_id"],
                    "direction": email["direction"],
                }
            )

        # Sort by date
        timeline.sort(key=lambda x: x.get("date", ""))

        return timeline

    def crosscheck_all_manuscripts(self, manuscripts_file: str, output_file: str = None) -> str:
        """Crosscheck all manuscripts with email communications."""
        try:
            # Load manuscripts
            with open(manuscripts_file) as f:
                manuscripts = json.load(f)

            if not isinstance(manuscripts, list):
                manuscripts = [manuscripts]

            print(f"🔄 Crosschecking {len(manuscripts)} manuscripts with email data...")

            enhanced_manuscripts = []
            for i, manuscript in enumerate(manuscripts):
                print(f"\n📧 Processing manuscript {i+1}/{len(manuscripts)}")
                try:
                    enhanced = self.crosscheck_manuscript(manuscript)
                    enhanced_manuscripts.append(enhanced)
                except Exception as e:
                    print(
                        f"⚠️ Failed to crosscheck manuscript {manuscript.get('id', 'Unknown')}: {e}"
                    )
                    enhanced_manuscripts.append(manuscript)  # Keep original

            # Save enhanced data
            if not output_file:
                input_path = Path(manuscripts_file)
                output_file = str(input_path.parent / f"{input_path.stem}_email_enhanced.json")

            with open(output_file, "w") as f:
                json.dump(enhanced_manuscripts, f, indent=2, ensure_ascii=False)

            print(f"\n✅ Email-enhanced manuscripts saved to: {output_file}")

            # Generate summary
            self.generate_crosscheck_summary(enhanced_manuscripts)

            return output_file

        except Exception as e:
            print(f"❌ Crosscheck failed: {e}")
            return ""

    def generate_crosscheck_summary(self, enhanced_manuscripts: list[dict]):
        """Generate summary of email crosscheck results."""
        print("\n📊 EMAIL CROSSCHECK SUMMARY")
        print("=" * 40)

        total_manuscripts = len(enhanced_manuscripts)
        manuscripts_with_emails = 0
        total_emails = 0
        communication_types = {}

        for manuscript in enhanced_manuscripts:
            emails = manuscript.get("email_communications", [])
            if emails:
                manuscripts_with_emails += 1
                total_emails += len(emails)

                for email in emails:
                    comm_type = email.get("communication_type", "unknown")
                    communication_types[comm_type] = communication_types.get(comm_type, 0) + 1

        print(f"📋 Total manuscripts: {total_manuscripts}")
        print(f"📧 Manuscripts with email data: {manuscripts_with_emails}")
        print(f"📩 Total email communications found: {total_emails}")
        print(f"📈 Average emails per manuscript: {total_emails/total_manuscripts:.1f}")

        print("\n🏷️ Communication Types:")
        for comm_type, count in sorted(communication_types.items()):
            print(f"   {comm_type}: {count} emails")


def main():
    """Example usage of email crosscheck system."""
    crosschecker = EmailAuditCrosschecker()

    # Authenticate with Gmail
    if not crosschecker.authenticate_gmail():
        print("❌ Gmail authentication required for email crosscheck")
        return

    # Example: crosscheck existing extraction data
    manuscripts_file = "mf_details_page_extraction_20250723_234323.json"

    if Path(manuscripts_file).exists():
        output_file = crosschecker.crosscheck_all_manuscripts(manuscripts_file)
        print(f"\n🎉 Email crosscheck complete! Enhanced data: {output_file}")
    else:
        print(f"❌ Manuscripts file not found: {manuscripts_file}")


if __name__ == "__main__":
    main()
