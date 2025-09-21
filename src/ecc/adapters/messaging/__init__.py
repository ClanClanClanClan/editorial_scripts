"""Messaging adapters for ECC."""

from .email_client import EmailClient, EmailConfig, EmailMessage, EmailPriority, EmailStatus
from .notification_service import NotificationConfig, NotificationMessage, NotificationService

__all__ = [
    "EmailClient",
    "EmailConfig",
    "EmailMessage",
    "EmailStatus",
    "EmailPriority",
    "NotificationService",
    "NotificationConfig",
    "NotificationMessage",
]
