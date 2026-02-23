"""
Notification Service for ECC

Implements unified notification system with multiple channels:
- Email notifications
- Slack integration
- Webhook delivery
- In-app notifications
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import aiohttp

from src.ecc.core.logging_system import ExtractorLogger
from src.ecc.infrastructure.monitoring import get_observability, trace_method

from .email_client import EmailClient, EmailConfig, EmailMessage, EmailPriority


class NotificationChannel(Enum):
    """Supported notification channels."""

    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SMS = "sms"  # Future implementation


class NotificationTemplate(Enum):
    """Predefined notification templates."""

    MANUSCRIPT_SUBMITTED = "manuscript_submitted"
    REFEREE_ASSIGNED = "referee_assigned"
    REPORT_RECEIVED = "report_received"
    DECISION_MADE = "decision_made"
    DEADLINE_REMINDER = "deadline_reminder"
    SYSTEM_ALERT = "system_alert"


@dataclass
class NotificationConfig:
    """Configuration for notification service."""

    # Channel configurations
    email_config: EmailConfig | None = None
    slack_webhook_url: str | None = None
    default_webhook_url: str | None = None

    # Default settings
    default_channels: list[NotificationChannel] = None
    template_path: str = "templates/notifications"
    retry_attempts: int = 3
    retry_delay: int = 30  # seconds

    # Rate limiting
    max_notifications_per_minute: int = 60
    max_notifications_per_hour: int = 1000

    def __post_init__(self):
        """Initialize default channels."""
        if self.default_channels is None:
            self.default_channels = [NotificationChannel.EMAIL]


@dataclass
class NotificationMessage:
    """Unified notification message."""

    id: str
    template: NotificationTemplate
    channels: list[NotificationChannel]
    recipients: list[str]
    data: dict[str, Any]

    # Optional overrides
    subject: str | None = None
    body: str | None = None
    priority: EmailPriority = EmailPriority.NORMAL

    # Scheduling
    send_at: datetime | None = None
    expires_at: datetime | None = None

    # Metadata
    created_at: datetime = None
    sent_at: datetime | None = None
    delivery_status: dict[str, str] = None
    retry_count: int = 0
    last_error: str | None = None

    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.delivery_status is None:
            self.delivery_status = {}


class NotificationService:
    """
    Unified notification service supporting multiple channels.

    Provides a single interface for sending notifications via:
    - Email (via EmailClient)
    - Slack webhooks
    - Custom webhooks
    - In-app notifications
    """

    def __init__(self, config: NotificationConfig, logger: ExtractorLogger | None = None):
        """Initialize notification service."""
        self.config = config
        self.logger = logger or ExtractorLogger("notification_service")

        # Initialize email client if configured
        self.email_client = None
        if config.email_config:
            self.email_client = EmailClient(config.email_config, logger)

        # HTTP client for webhooks
        self.http_session: aiohttp.ClientSession | None = None

        # Template cache
        self.template_cache: dict[str, dict[str, str]] = {}

        # Rate limiting tracking
        self.minute_count = 0
        self.hour_count = 0
        self.last_minute_reset = datetime.utcnow()
        self.last_hour_reset = datetime.utcnow()

        # In-app notifications storage (in production would use Redis)
        self.in_app_notifications: dict[str, list[dict[str, Any]]] = {}

        # Observability
        self.observability = get_observability()

    async def initialize(self) -> bool:
        """Initialize notification service and all clients."""
        try:
            # Initialize email client
            if self.email_client:
                await self.email_client.initialize()
                self.logger.log_info("Email client initialized")

            # Initialize HTTP session for webhooks
            self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

            # Load notification templates
            await self._load_templates()

            self.logger.log_success("Notification service initialized")
            return True

        except Exception as e:
            self.logger.log_error(f"Notification service initialization failed: {e}")
            return False

    async def close(self) -> None:
        """Clean up notification service resources."""
        if self.http_session:
            await self.http_session.close()

    @trace_method("notification.send")
    async def send_notification(self, notification: NotificationMessage) -> bool:
        """Send notification through all specified channels."""
        try:
            # Check rate limits
            if not self._check_rate_limits():
                self.logger.log_warning("Rate limit exceeded for notifications")
                return False

            # Check if scheduled for later
            if notification.send_at and notification.send_at > datetime.now(UTC):
                self.logger.log_info(
                    f"Notification {notification.id} scheduled for {notification.send_at}"
                )
                return True

            # Send through each channel
            success_count = 0

            for channel in notification.channels:
                try:
                    if channel == NotificationChannel.EMAIL:
                        success = await self._send_email(notification)
                    elif channel == NotificationChannel.SLACK:
                        success = await self._send_slack(notification)
                    elif channel == NotificationChannel.WEBHOOK:
                        success = await self._send_webhook(notification)
                    elif channel == NotificationChannel.IN_APP:
                        success = await self._send_in_app(notification)
                    else:
                        self.logger.log_warning(f"Unsupported channel: {channel}")
                        success = False

                    if success:
                        success_count += 1
                        notification.delivery_status[channel.value] = "sent"
                    else:
                        notification.delivery_status[channel.value] = "failed"

                except Exception as e:
                    self.logger.log_error(f"Failed to send via {channel.value}: {e}")
                    notification.delivery_status[channel.value] = f"error: {e}"

            # Update notification status
            overall_success = success_count > 0
            if overall_success:
                notification.sent_at = datetime.now(UTC)
                self._update_rate_limits()

            # Record observability metrics
            if self.observability:
                self.observability.record_notification_sent(
                    template=notification.template.value,
                    channels=len(notification.channels),
                    success=overall_success,
                )

            self.logger.log_info(
                f"Notification sent via {success_count}/{len(notification.channels)} channels"
            )
            return overall_success

        except Exception as e:
            notification.last_error = str(e)
            notification.retry_count += 1
            self.logger.log_error(f"Notification send failed: {e}")
            return False

    async def _send_email(self, notification: NotificationMessage) -> bool:
        """Send notification via email."""
        if not self.email_client:
            self.logger.log_warning("Email client not configured")
            return False

        try:
            # Get template content
            template_content = await self._get_template_content(
                notification.template, NotificationChannel.EMAIL
            )

            # Create email message
            email_message = EmailMessage(
                id=f"notif_{notification.id}",
                to=notification.recipients,
                subject=notification.subject or template_content.get("subject", "Notification"),
                body_text=notification.body or template_content.get("body_text", ""),
                body_html=template_content.get("body_html"),
                priority=notification.priority,
                template_data=notification.data,
            )

            return await self.email_client.send_message(email_message)

        except Exception as e:
            self.logger.log_error(f"Email notification failed: {e}")
            return False

    async def _send_slack(self, notification: NotificationMessage) -> bool:
        """Send notification via Slack webhook."""
        if not self.config.slack_webhook_url:
            self.logger.log_warning("Slack webhook URL not configured")
            return False

        try:
            # Get template content
            template_content = await self._get_template_content(
                notification.template, NotificationChannel.SLACK
            )

            # Format Slack message
            slack_message = {
                "text": notification.subject or template_content.get("text", "Notification"),
                "attachments": [
                    {
                        "color": self._get_priority_color(notification.priority),
                        "fields": [
                            {"title": key, "value": str(value), "short": True}
                            for key, value in notification.data.items()
                        ],
                    }
                ],
            }

            # Send via webhook
            async with self.http_session.post(
                self.config.slack_webhook_url, json=slack_message
            ) as response:
                success = response.status == 200
                if not success:
                    self.logger.log_error(f"Slack webhook failed: {response.status}")
                return success

        except Exception as e:
            self.logger.log_error(f"Slack notification failed: {e}")
            return False

    async def _send_webhook(self, notification: NotificationMessage) -> bool:
        """Send notification via custom webhook."""
        webhook_url = notification.data.get("webhook_url", self.config.default_webhook_url)

        if not webhook_url:
            self.logger.log_warning("No webhook URL configured")
            return False

        try:
            # Create webhook payload
            payload = {
                "id": notification.id,
                "template": notification.template.value,
                "timestamp": notification.created_at.isoformat(),
                "data": notification.data,
                "recipients": notification.recipients,
            }

            # Send webhook
            async with self.http_session.post(
                webhook_url, json=payload, headers={"Content-Type": "application/json"}
            ) as response:
                success = response.status in [200, 201, 202]
                if not success:
                    self.logger.log_error(f"Webhook failed: {response.status}")
                return success

        except Exception as e:
            self.logger.log_error(f"Webhook notification failed: {e}")
            return False

    async def _send_in_app(self, notification: NotificationMessage) -> bool:
        """Send in-app notification."""
        try:
            # Get template content
            template_content = await self._get_template_content(
                notification.template, NotificationChannel.IN_APP
            )

            # Create in-app notification
            in_app_notification = {
                "id": notification.id,
                "title": notification.subject or template_content.get("title", "Notification"),
                "message": notification.body or template_content.get("message", ""),
                "priority": notification.priority.value,
                "timestamp": notification.created_at.isoformat(),
                "data": notification.data,
                "read": False,
            }

            # Store for each recipient
            for recipient in notification.recipients:
                if recipient not in self.in_app_notifications:
                    self.in_app_notifications[recipient] = []

                self.in_app_notifications[recipient].append(in_app_notification)

                # Keep only last 100 notifications per user
                if len(self.in_app_notifications[recipient]) > 100:
                    self.in_app_notifications[recipient] = self.in_app_notifications[recipient][
                        -100:
                    ]

            return True

        except Exception as e:
            self.logger.log_error(f"In-app notification failed: {e}")
            return False

    async def _get_template_content(
        self, template: NotificationTemplate, channel: NotificationChannel
    ) -> dict[str, str]:
        """Get template content for specific channel."""
        cache_key = f"{template.value}_{channel.value}"

        if cache_key in self.template_cache:
            return self.template_cache[cache_key]

        # Load template from file (simplified implementation)
        template_content = {
            "subject": f"ECC Notification: {template.value}",
            "body_text": f"This is a notification about {template.value}",
            "title": f"ECC: {template.value}",
            "message": f"Notification about {template.value}",
        }

        self.template_cache[cache_key] = template_content
        return template_content

    async def _load_templates(self) -> None:
        """Load notification templates from files."""
        # TODO: Implement template loading from files
        self.logger.log_info("Using default templates")

    def _check_rate_limits(self) -> bool:
        """Check if notification is within rate limits."""
        now = datetime.utcnow()

        # Reset counters if needed
        if (now - self.last_minute_reset).total_seconds() >= 60:
            self.minute_count = 0
            self.last_minute_reset = now

        if (now - self.last_hour_reset).total_seconds() >= 3600:
            self.hour_count = 0
            self.last_hour_reset = now

        # Check limits
        return (
            self.minute_count < self.config.max_notifications_per_minute
            and self.hour_count < self.config.max_notifications_per_hour
        )

    def _update_rate_limits(self) -> None:
        """Update rate limiting counters."""
        self.minute_count += 1
        self.hour_count += 1

    def _get_priority_color(self, priority: EmailPriority) -> str:
        """Get color code for priority."""
        colors = {
            EmailPriority.LOW: "#36a64f",  # Green
            EmailPriority.NORMAL: "#2196F3",  # Blue
            EmailPriority.HIGH: "#ff9800",  # Orange
            EmailPriority.URGENT: "#f44336",  # Red
        }
        return colors.get(priority, "#2196F3")

    @trace_method("notification.get_in_app")
    async def get_in_app_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get in-app notifications for user."""
        notifications = self.in_app_notifications.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n.get("read", False)]

        # Sort by timestamp (newest first) and limit
        notifications.sort(key=lambda x: x["timestamp"], reverse=True)
        return notifications[:limit]

    @trace_method("notification.mark_read")
    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        """Mark in-app notification as read."""
        if user_id not in self.in_app_notifications:
            return False

        for notification in self.in_app_notifications[user_id]:
            if notification["id"] == notification_id:
                notification["read"] = True
                return True

        return False

    async def send_system_alert(
        self, message: str, severity: str = "warning", recipients: list[str] | None = None
    ) -> bool:
        """Send system alert notification."""
        if recipients is None:
            recipients = ["admin@example.com"]  # TODO: Load from config

        priority = EmailPriority.HIGH if severity == "error" else EmailPriority.NORMAL

        notification = NotificationMessage(
            id=str(uuid4()),
            template=NotificationTemplate.SYSTEM_ALERT,
            channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
            recipients=recipients,
            data={"message": message, "severity": severity},
            subject=f"ECC System Alert: {severity}",
            body=message,
            priority=priority,
        )

        return await self.send_notification(notification)

    def get_usage_stats(self) -> dict[str, Any]:
        """Get notification usage statistics."""
        return {
            "minute_count": self.minute_count,
            "hour_count": self.hour_count,
            "minute_limit": self.config.max_notifications_per_minute,
            "hour_limit": self.config.max_notifications_per_hour,
            "in_app_users": len(self.in_app_notifications),
            "total_in_app": sum(
                len(notifications) for notifications in self.in_app_notifications.values()
            ),
        }
