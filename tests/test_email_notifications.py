"""Tests for email notification system."""

import json
from unittest.mock import MagicMock, patch

import pytest
from core.email_notifications import (
    EVENT_EMAIL_DEFAULTS,
    _load_config,
    format_event_email,
    send_event_notification,
    send_notification,
    verify_send_scope,
)


class TestSendNotification:
    @patch("core.email_notifications._get_gmail_service")
    def test_success_with_mocked_service(self, mock_get_service):
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "123"
        }
        mock_get_service.return_value = mock_service

        result = send_notification("Test Subject", "<p>Hello</p>")
        assert result is True
        mock_service.users.return_value.messages.return_value.send.assert_called_once()

    @patch("core.email_notifications._get_gmail_service", return_value=None)
    def test_returns_false_when_no_credentials(self, mock_get_service):
        result = send_notification("Test Subject", "<p>Hello</p>")
        assert result is False


class TestFormatEventEmail:
    def test_all_reports_in_subject(self):
        event = {"type": "ALL_REPORTS_IN", "journal": "sicon", "manuscript_id": "M181987"}
        subject, body = format_event_email(event)
        # Subject now uses human-readable journal name (or falls back to code)
        assert "SICON" in subject or "SIAM" in subject
        assert "M181987" in subject
        assert "All reports in" in subject

    def test_new_manuscript_subject(self):
        event = {"type": "NEW_MANUSCRIPT", "journal": "mf", "manuscript_id": "MF-2026-001"}
        subject, body = format_event_email(event)
        # Either the raw code or the resolved "Mathematical Finance" name
        assert "MF" in subject or "Mathematical Finance" in subject
        assert "New manuscript" in subject
        assert "MF-2026-001" in subject

    def test_mf_wiley_uses_human_name(self):
        event = {"type": "NEW_MANUSCRIPT", "journal": "mf_wiley", "manuscript_id": "1384665"}
        subject, _ = format_event_email(event)
        # MF_WILEY should resolve to "Mathematical Finance", not raw code
        assert "Mathematical Finance" in subject
        assert "MF_WILEY" not in subject


class TestSendEventNotification:
    @patch("core.email_notifications.send_notification", return_value=True)
    @patch("core.email_notifications._load_config")
    def test_respects_config_disabled(self, mock_config, mock_send):
        mock_config.return_value = {"STATUS_CHANGED": False}
        event = {"type": "STATUS_CHANGED", "journal": "sicon", "manuscript_id": "M1"}
        result = send_event_notification(event)
        assert result is False
        mock_send.assert_not_called()


class TestLoadConfig:
    def test_returns_defaults_when_file_missing(self, tmp_path):
        with patch("core.email_notifications.CONFIG_PATH", tmp_path / "nonexistent.json"):
            config = _load_config()
        assert config == EVENT_EMAIL_DEFAULTS
        assert config["ALL_REPORTS_IN"] is True
        assert config["STATUS_CHANGED"] is False


class TestVerifySendScope:
    @patch("core.email_notifications._get_gmail_service", return_value=None)
    def test_no_service(self, mock_svc):
        result = verify_send_scope()
        assert result["ok"] is False
        assert "unavailable" in result["error"]

    @patch("core.email_notifications._get_gmail_service")
    def test_read_fails(self, mock_svc):
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.list.return_value.execute.side_effect = Exception(
            "read error"
        )
        mock_svc.return_value = mock_service
        result = verify_send_scope()
        assert result["ok"] is False
        assert "read failed" in result["error"]

    @patch("core.email_notifications._get_gmail_service")
    def test_send_scope_missing(self, mock_svc):
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = (
            {}
        )
        mock_service.users.return_value.drafts.return_value.create.return_value.execute.side_effect = Exception(
            "403 insufficient permissions"
        )
        mock_svc.return_value = mock_service
        result = verify_send_scope()
        assert result["ok"] is False
        assert "gmail.send" in result["error"]

    @patch("core.email_notifications._get_gmail_service")
    def test_success(self, mock_svc):
        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.list.return_value.execute.return_value = (
            {}
        )
        mock_service.users.return_value.drafts.return_value.create.return_value.execute.return_value = {
            "id": "draft1"
        }
        mock_svc.return_value = mock_service
        result = verify_send_scope()
        assert result["ok"] is True
        assert "gmail.send" in result["scopes"]
