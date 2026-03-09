"""Tests for reporting.action_items module."""

import datetime
from unittest.mock import patch

import pytest
from reporting.action_items import (
    ManuscriptSummary,
    RefereeAction,
    _get_due_date,
    _get_manuscript_status,
    _is_terminal,
    _normalize_referee_status,
    _parse_date,
    compute_action_items,
    compute_manuscript_summaries,
)


class TestParseDate:
    def test_iso_format(self):
        assert _parse_date("2026-03-07") == datetime.date(2026, 3, 7)

    def test_day_month_year(self):
        assert _parse_date("19 Apr 2026") == datetime.date(2026, 4, 19)

    def test_slash_format(self):
        assert _parse_date("04/21/2026") == datetime.date(2026, 4, 21)

    def test_none(self):
        assert _parse_date(None) is None

    def test_empty(self):
        assert _parse_date("") is None

    def test_garbage(self):
        assert _parse_date("not a date") is None


class TestNormalizeStatus:
    def test_agreed(self):
        ref = {"platform_specific": {"status": "Agreed"}, "dates": {}}
        assert _normalize_referee_status(ref, "jota") == "agreed"

    def test_complete(self):
        ref = {"platform_specific": {"status": "Complete"}, "dates": {}}
        assert _normalize_referee_status(ref, "jota") == "completed"

    def test_review_complete(self):
        ref = {"platform_specific": {"status": "Review Complete"}, "dates": {}}
        assert _normalize_referee_status(ref, "jota") == "completed"

    def test_report_submitted(self):
        ref = {"platform_specific": {"status": "Report Submitted"}, "dates": {}}
        assert _normalize_referee_status(ref, "sicon") == "completed"

    def test_awaiting_report(self):
        ref = {"platform_specific": {"status": "Awaiting Report"}, "dates": {}}
        assert _normalize_referee_status(ref, "sicon") == "agreed"

    def test_declined(self):
        ref = {"platform_specific": {"status": "Declined"}, "dates": {}}
        assert _normalize_referee_status(ref, "sicon") == "declined"

    def test_terminated(self):
        ref = {"platform_specific": {"status": "Terminated After Agreeing to Review"}, "dates": {}}
        assert _normalize_referee_status(ref, "mafe") == "terminated"

    def test_returned_date_means_completed(self):
        ref = {"platform_specific": {}, "dates": {"returned": "2026-01-15"}}
        assert _normalize_referee_status(ref, "mf") == "completed"

    def test_invited_no_response_means_pending(self):
        ref = {"platform_specific": {}, "dates": {"invited": "2026-01-01"}}
        assert _normalize_referee_status(ref, "mf") == "pending"

    def test_fs_agreed_via_status_details(self):
        ref = {
            "platform_specific": {},
            "dates": {},
            "status_details": {"agreed_to_review": True},
        }
        assert _normalize_referee_status(ref, "fs") == "agreed"

    def test_fs_no_response(self):
        ref = {
            "platform_specific": {},
            "dates": {},
            "status_details": {"no_response": True},
        }
        assert _normalize_referee_status(ref, "fs") == "pending"


class TestGetDueDate:
    def test_from_dates_field(self):
        ref = {"dates": {"due": "2026-04-13"}, "platform_specific": {}}
        assert _get_due_date(ref, "mf") == datetime.date(2026, 4, 13)

    def test_from_platform_specific(self):
        ref = {"dates": {}, "platform_specific": {"due_date": "19 Apr 2026"}}
        assert _get_due_date(ref, "jota") == datetime.date(2026, 4, 19)

    def test_fs_synthetic_from_agreed(self):
        ref = {"dates": {"agreed": "2026-01-01"}, "platform_specific": {}}
        expected = datetime.date(2026, 1, 1) + datetime.timedelta(days=90)
        assert _get_due_date(ref, "fs") == expected

    def test_fs_synthetic_from_invited(self):
        ref = {"dates": {"invited": "2026-01-01"}, "platform_specific": {}}
        expected = datetime.date(2026, 1, 1) + datetime.timedelta(days=90)
        assert _get_due_date(ref, "fs") == expected

    def test_no_due_date(self):
        ref = {"dates": {}, "platform_specific": {}}
        assert _get_due_date(ref, "mor") is None


class TestManuscriptStatus:
    def test_direct_status(self):
        ms = {"status": "Under Review"}
        assert _get_manuscript_status(ms) == "Under Review"

    def test_from_category(self):
        ms = {
            "status": None,
            "category": "Awaiting Reviewer Reports",
        }
        assert _get_manuscript_status(ms) == "Awaiting Reviewer Reports"

    def test_from_metadata(self):
        ms = {
            "status": None,
            "platform_specific": {"metadata": {"current_stage": "All Referees Assigned"}},
        }
        assert _get_manuscript_status(ms) == "All Referees Assigned"


class TestIsTerminal:
    @pytest.mark.parametrize(
        "status",
        [
            "Completed Reject",
            "Completed Accept",
            "Completed",
            "Submission Transferred",
            "Withdrawn",
        ],
    )
    def test_terminal_statuses(self, status):
        ms = {"status": status}
        assert _is_terminal(ms)

    def test_under_review_not_terminal(self):
        ms = {"status": "Under Review"}
        assert not _is_terminal(ms)

    def test_awaiting_not_terminal(self):
        ms = {"status": "Awaiting Reviewer Scores"}
        assert not _is_terminal(ms)


class TestComputeActionItems:
    @patch("reporting.action_items.load_journal_data")
    def test_overdue_referee(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-001",
                    "title": "Test Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "John Smith",
                            "email": "john@test.edu",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {
                                "invited": "2025-01-01",
                                "agreed": "2025-01-02",
                                "due": "2025-06-01",
                            },
                            "statistics": {"reminders_received": 3},
                        }
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        overdue = [i for i in items if i.action_type == "overdue_report"]
        assert len(overdue) == 1
        assert overdue[0].priority == "critical"
        assert overdue[0].referee_name == "John Smith"
        assert overdue[0].reminders_sent == 3

    @patch("reporting.action_items.load_journal_data")
    def test_needs_ae_decision(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-002",
                    "title": "Decision Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Ref A",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-01-15"},
                            "statistics": {},
                        },
                        {
                            "name": "Ref B",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-02-01"},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        decisions = [i for i in items if i.action_type == "needs_ae_decision"]
        assert len(decisions) == 1
        assert decisions[0].priority == "critical"

    @patch("reporting.action_items.load_journal_data")
    def test_terminal_manuscripts_excluded(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "OLD-001",
                    "title": "Old Paper",
                    "status": "Completed Accept",
                    "referees": [],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        assert len(items) == 0


class TestComputeManuscriptSummaries:
    @patch("reporting.action_items.load_journal_data")
    def test_basic_summary(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-001",
                    "title": "A Paper",
                    "status": "Under Review",
                    "submission_date": "2026-01-01",
                    "referees": [
                        {
                            "name": "Ref A",
                            "email": "a@test.edu",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-02-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Ref B",
                            "email": "b@test.edu",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-10", "due": "2026-04-10"},
                            "statistics": {"reminders_received": 1},
                        },
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert len(summaries) == 1
        s = summaries[0]
        assert s.referees_completed == 1
        assert s.referees_agreed == 1
        assert s.reports_received == 1
        assert s.reports_pending == 1
        assert len(s.referee_details) == 2

    @patch("reporting.action_items.load_journal_data")
    def test_terminal_excluded(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {"manuscript_id": "OLD", "title": "Done", "status": "Rejected", "referees": []}
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert len(summaries) == 0
