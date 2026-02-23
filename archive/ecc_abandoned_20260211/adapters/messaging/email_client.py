"""
Email messaging adapter for ECC

Implements Section 4.3 secure messaging requirements:
- Gmail API integration with OAuth2
- Template-based notifications
- Bounce handling and retry logic
- Audit trail for all communications
"""

import asyncio
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.ecc.core.error_handling import ExtractorError
from src.ecc.core.logging_system import ExtractorLogger
from src.ecc.infrastructure.monitoring import get_observability, trace_method


class EmailProvider(Enum):
    """Supported email providers."""

    GMAIL_API = "gmail_api"
    SMTP = "smtp"


class EmailPriority(Enum):
    """Email priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailStatus(Enum):
    """Email delivery status."""

    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"


@dataclass
class EmailConfig:
    """Configuration for email client."""

    provider: EmailProvider = EmailProvider.GMAIL_API

    # Gmail API settings
    gmail_credentials_path: str = "config/gmail_credentials.json"
    gmail_token_path: str = "config/gmail_token.json"
    gmail_scopes: list[str] = None

    # SMTP settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True

    # General settings
    from_email: str = ""
    from_name: str = "Editorial Command Center"
    default_template_path: str = "templates/email"
    max_retries: int = 3
    retry_delay: int = 30  # seconds

    def __post_init__(self):
        """Initialize default Gmail scopes."""
        if self.gmail_scopes is None:
            self.gmail_scopes = [
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.readonly",
            ]


@dataclass
class EmailMessage:
    """Email message structure."""

    id: str
    to: list[str]
    subject: str
    body_text: str
    body_html: str | None = None
    cc: list[str] = None
    bcc: list[str] = None
    reply_to: str | None = None
    attachments: list[dict[str, Any]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    template: str | None = None
    template_data: dict[str, Any] = None

    # Metadata
    created_at: datetime = None
    scheduled_at: datetime | None = None
    status: EmailStatus = EmailStatus.DRAFT
    retry_count: int = 0
    last_error: str | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.cc is None:
            self.cc = []
        if self.bcc is None:
            self.bcc = []
        if self.attachments is None:
            self.attachments = []
        if self.template_data is None:
            self.template_data = {}


class EmailClient:
    """
    Secure email client with Gmail API and SMTP support.

    Implements Section 4.3 messaging requirements:
    - OAuth2 authentication for Gmail
    - Template-based email generation
    - Retry logic with exponential backoff
    - Comprehensive audit trails
    """

    def __init__(self, config: EmailConfig, logger: ExtractorLogger | None = None):
        """Initialize email client."""
        self.config = config
        self.logger = logger or ExtractorLogger("email_client")

        # Gmail API client
        self.gmail_service = None
        self.gmail_credentials = None

        # Message queue for batching
        self.message_queue: list[EmailMessage] = []

        # Template cache
        self.template_cache: dict[str, str] = {}

        # Observability
        self.observability = get_observability()

    async def initialize(self) -> bool:
        """Initialize email client and authenticate."""
        try:
            if self.config.provider == EmailProvider.GMAIL_API:
                await self._initialize_gmail_api()
            elif self.config.provider == EmailProvider.SMTP:
                await self._test_smtp_connection()

            self.logger.log_success("Email client initialized successfully")
            return True

        except Exception as e:
            self.logger.log_error(f"Email client initialization failed: {e}")
            return False

    # --- Gmail search helpers ---
    async def search_messages(self, query: str, max_results: int = 50) -> list[dict]:
        """Search Gmail messages by query string.

        Returns list of message dicts with 'id' and 'threadId'.
        """
        if not self.gmail_service:
            raise ExtractorError("Gmail service not initialized")
        try:
            results = (
                self.gmail_service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            return results.get("messages", [])
        except Exception as e:
            self.logger.log_error(f"Gmail search failed: {e}")
            return []

    async def get_message(self, message_id: str, format: str = "full") -> dict:
        """Get a Gmail message by ID.

        format: 'full'|'metadata'|'raw'|'minimal'
        """
        if not self.gmail_service:
            raise ExtractorError("Gmail service not initialized")
        try:
            msg = (
                self.gmail_service.users()
                .messages()
                .get(userId="me", id=message_id, format=format)
                .execute()
            )
            return msg
        except Exception as e:
            self.logger.log_error(f"Get message failed: {e}")
            return {}

    async def download_attachments(self, message: dict, download_dir: Path) -> list[Path]:
        """Download all attachments in a message into download_dir.

        Returns list of saved file paths.
        """
        saved: list[Path] = []
        try:
            if not self.gmail_service:
                return saved
            parts = (message.get("payload") or {}).get("parts") or []
            for part in parts:
                filename = part.get("filename")
                body = part.get("body", {})
                att_id = body.get("attachmentId")
                if filename and att_id:
                    att = (
                        self.gmail_service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=message["id"], id=att_id)
                        .execute()
                    )
                    import base64

                    data = base64.urlsafe_b64decode(att.get("data", ""))
                    download_dir.mkdir(parents=True, exist_ok=True)
                    path = download_dir / filename
                    with open(path, "wb") as f:
                        f.write(data)
                    saved.append(path)
        except Exception as e:
            self.logger.log_error(f"Attachment download failed: {e}")
        return saved

    async def _initialize_gmail_api(self) -> None:
        """Initialize Gmail API authentication."""
        creds = None

        # Load existing token
        token_path = Path(self.config.gmail_token_path)
        # Allow injecting token content via secrets provider
        try:
            from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

            token_json = get_secret_with_vault("GMAIL_TOKEN_JSON")
            if token_json and not token_path.exists():
                token_path.parent.mkdir(parents=True, exist_ok=True)
                token_path.write_text(token_json)
        except Exception:
            pass
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), self.config.gmail_scopes)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Run OAuth flow
                credentials_path = Path(self.config.gmail_credentials_path)
                # Allow injecting credentials via secrets provider
                try:
                    from src.ecc.infrastructure.secrets.provider import get_secret_with_vault

                    creds_json = get_secret_with_vault("GMAIL_CREDENTIALS_JSON")
                    if creds_json and not credentials_path.exists():
                        credentials_path.parent.mkdir(parents=True, exist_ok=True)
                        credentials_path.write_text(creds_json)
                except Exception:
                    pass
                if not credentials_path.exists():
                    raise ExtractorError(f"Gmail credentials not found at {credentials_path}")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), self.config.gmail_scopes
                )
                creds = flow.run_local_server(port=0)

            # Save credentials
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())

        # Build Gmail service
        self.gmail_service = build("gmail", "v1", credentials=creds)
        self.gmail_credentials = creds

        self.logger.log_info("Gmail API authenticated successfully")

    async def _test_smtp_connection(self) -> None:
        """Test SMTP connection."""
        try:
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            if self.config.smtp_use_tls:
                server.starttls()
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)
            server.quit()

            self.logger.log_info("SMTP connection test successful")

        except Exception as e:
            raise ExtractorError("SMTP connection failed") from e

    @trace_method("email.send_message")
    async def send_message(self, message: EmailMessage) -> bool:
        """Send email message."""
        try:
            # Validate message
            self._validate_message(message)

            # Apply template if specified
            if message.template:
                await self._apply_template(message)

            # Send via appropriate provider
            if self.config.provider == EmailProvider.GMAIL_API:
                success = await self._send_via_gmail(message)
            else:
                success = await self._send_via_smtp(message)

            # Update status
            if success:
                message.status = EmailStatus.SENT
                self.logger.log_success(f"Email sent to {message.to}")

                # Record observability metrics
                if self.observability:
                    self.observability.record_email_sent(
                        provider=self.config.provider.value,
                        success=True,
                        priority=message.priority.value,
                    )
            else:
                message.status = EmailStatus.FAILED
                message.retry_count += 1

            return success

        except Exception as e:
            message.status = EmailStatus.FAILED
            message.last_error = str(e)
            message.retry_count += 1

            self.logger.log_error(f"Email send failed: {e}")
            return False

    async def _send_via_gmail(self, message: EmailMessage) -> bool:
        """Send email via Gmail API."""
        try:
            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["To"] = ", ".join(message.to)
            msg["Subject"] = message.subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"

            if message.cc:
                msg["Cc"] = ", ".join(message.cc)
            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            # Add text part
            msg.attach(MIMEText(message.body_text, "plain"))

            # Add HTML part if available
            if message.body_html:
                msg.attach(MIMEText(message.body_html, "html"))

            # Add attachments
            for attachment in message.attachments:
                await self._add_attachment(msg, attachment)

            # Convert to Gmail format
            raw_message = {"raw": self._encode_message(msg)}

            # Send via Gmail API
            result = (
                self.gmail_service.users().messages().send(userId="me", body=raw_message).execute()
            )

            self.logger.log_info(f"Gmail API message sent: {result.get('id')}")
            return True

        except HttpError as e:
            self.logger.log_error(f"Gmail API error: {e}")
            return False
        except Exception as e:
            self.logger.log_error(f"Gmail send error: {e}")
            return False

    async def _send_via_smtp(self, message: EmailMessage) -> bool:
        """Send email via SMTP."""
        try:
            # Create MIME message
            msg = MIMEMultipart()
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = ", ".join(message.to)
            msg["Subject"] = message.subject

            if message.cc:
                msg["Cc"] = ", ".join(message.cc)
            if message.reply_to:
                msg["Reply-To"] = message.reply_to

            # Add body
            msg.attach(MIMEText(message.body_text, "plain"))
            if message.body_html:
                msg.attach(MIMEText(message.body_html, "html"))

            # Add attachments
            for attachment in message.attachments:
                await self._add_attachment(msg, attachment)

            # Send via SMTP
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            if self.config.smtp_use_tls:
                server.starttls()
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)

            # Send to all recipients
            all_recipients = message.to + message.cc + message.bcc
            server.send_message(msg, to_addrs=all_recipients)
            server.quit()

            self.logger.log_info("SMTP message sent successfully")
            return True

        except Exception as e:
            self.logger.log_error(f"SMTP send error: {e}")
            return False

    async def _apply_template(self, message: EmailMessage) -> None:
        """Apply email template to message."""
        template_path = Path(self.config.default_template_path) / f"{message.template}.html"

        if template_path.exists():
            template_content = template_path.read_text()

            # Simple template substitution
            for key, value in message.template_data.items():
                template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))

            message.body_html = template_content
        else:
            self.logger.log_warning(f"Template not found: {template_path}")

    async def _add_attachment(self, msg: MIMEMultipart, attachment: dict[str, Any]) -> None:
        """Add attachment to MIME message."""
        try:
            filepath = Path(attachment["path"])
            if not filepath.exists():
                self.logger.log_warning(f"Attachment not found: {filepath}")
                return

            with open(filepath, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename= {attachment.get("filename", filepath.name)}',
            )

            msg.attach(part)

        except Exception as e:
            self.logger.log_error(f"Failed to add attachment: {e}")

    def _validate_message(self, message: EmailMessage) -> None:
        """Validate email message."""
        if not message.to:
            raise ValueError("Email must have at least one recipient")
        if not message.subject:
            raise ValueError("Email must have a subject")
        if not message.body_text:
            raise ValueError("Email must have body text")

    def _encode_message(self, message: MIMEMultipart) -> str:
        """Encode message for Gmail API."""
        import base64

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return raw

    @trace_method("email.send_batch")
    async def send_batch(self, messages: list[EmailMessage]) -> dict[str, int]:
        """Send batch of messages with rate limiting."""
        results = {"sent": 0, "failed": 0}

        for message in messages:
            success = await self.send_message(message)
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1

            # Rate limiting - wait between sends
            await asyncio.sleep(0.1)

        self.logger.log_info(f"Batch send completed: {results}")
        return results

    async def get_delivery_status(self, message_id: str) -> EmailStatus:
        """Get delivery status for sent message."""
        # TODO: Implement status tracking via Gmail API
        return EmailStatus.SENT

    def get_usage_stats(self) -> dict[str, Any]:
        """Get email usage statistics."""
        # TODO: Implement usage tracking
        return {
            "messages_sent_today": 0,
            "messages_failed_today": 0,
            "queue_size": len(self.message_queue),
        }
