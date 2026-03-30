"""Tests for reporting.action_items module."""

import datetime
from unittest.mock import patch

import pytest
from reporting.action_items import (
    DEFAULT_REVIEW_DEADLINE_DAYS,
    STALE_INVITATION_DAYS,
    ManuscriptSummary,
    RefereeAction,
    _apply_revision_awareness,
    _clean_raw_status,
    _display_name,
    _effective_dates,
    _get_due_date,
    _get_manuscript_status,
    _get_reminders,
    _get_revision_date,
    _has_current_round_report,
    _is_terminal,
    _normalize_referee_status,
    _parse_date,
    compute_action_items,
    compute_manuscript_summaries,
    harmonize_status,
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
        assert _normalize_referee_status(ref, "fs") == "declined"

    def test_no_response_raw_status(self):
        ref = {"platform_specific": {"status": "No Response"}, "dates": {}}
        assert _normalize_referee_status(ref, "mor") == "declined"

    def test_no_response_in_status_field(self):
        ref = {"status": "No Response", "dates": {}, "platform_specific": {}}
        assert _normalize_referee_status(ref, "mf") == "declined"

    def test_no_response_case_insensitive(self):
        ref = {"status": "no response", "dates": {}, "platform_specific": {}}
        assert _normalize_referee_status(ref, "mor") == "declined"


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

    def test_synthetic_due_from_agreed(self):
        ref = {"dates": {"agreed": "2025-11-18"}, "platform_specific": {}}
        expected = datetime.date(2025, 11, 18) + datetime.timedelta(
            days=DEFAULT_REVIEW_DEADLINE_DAYS
        )
        assert _get_due_date(ref, "mor") == expected

    def test_mafe_due_from_platform_specific(self):
        ref = {
            "dates": {},
            "platform_specific": {"due_date": "27 Jun 2023"},
        }
        assert _get_due_date(ref, "mafe") == datetime.date(2023, 6, 27)

    def test_real_due_date_preferred_over_synthetic(self):
        ref = {
            "dates": {"agreed": "2025-11-18", "due": "2025-12-30"},
            "platform_specific": {},
        }
        assert _get_due_date(ref, "mor") == datetime.date(2025, 12, 30)

    def test_sicon_due_from_dates_dict(self):
        ref = {
            "dates": {"invited": "2026-01-15", "agreed": "2026-01-30", "due": "2026-03-01"},
            "platform_specific": {},
        }
        assert _get_due_date(ref, "sicon") == datetime.date(2026, 3, 1)


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

    def test_is_current_false_is_terminal(self):
        ms = {
            "status": "Under Review",
            "platform_specific": {"is_current": False},
        }
        assert _is_terminal(ms)

    def test_is_current_true_not_terminal(self):
        ms = {
            "status": "Under Review",
            "platform_specific": {"is_current": True},
        }
        assert not _is_terminal(ms)

    def test_is_current_missing_not_terminal(self):
        ms = {"status": "Under Review", "platform_specific": {}}
        assert not _is_terminal(ms)

    def test_is_current_zero_is_terminal(self):
        ms = {
            "status": "Under Review",
            "platform_specific": {"is_current": 0},
        }
        assert _is_terminal(ms)

    def test_category_final_disposition_is_terminal(self):
        ms = {
            "status": "Some Status",
            "category": "My Assignments with Final Disposition",
        }
        assert _is_terminal(ms)

    @patch("reporting.action_items.load_journal_data")
    def test_is_current_false_excluded_from_action_items(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "FS-25-4725",
                    "title": "Closed Paper",
                    "status": "Under Review",
                    "platform_specific": {"is_current": False},
                    "referees": [
                        {
                            "name": "Zhou Zhou",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2025-01-01", "due": "2025-04-01"},
                            "statistics": {},
                        }
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["fs"])
        assert len(items) == 0

    @patch("reporting.action_items.load_journal_data")
    def test_is_current_false_excluded_from_summaries(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "FS-25-4725",
                    "title": "Closed Paper",
                    "status": "Under Review",
                    "platform_specific": {"is_current": False},
                    "referees": [],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["fs"])
        assert len(summaries) == 0


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

    @patch("reporting.action_items.load_journal_data")
    def test_needs_more_referees(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-005",
                    "title": "Lonely Referee Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Solo Ref",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2026-06-01"},
                            "statistics": {},
                        }
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        more = [i for i in items if i.action_type == "needs_more_referees"]
        assert len(more) == 1
        assert more[0].priority == "high"

    @patch("reporting.action_items.load_journal_data")
    def test_multi_action_per_manuscript(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-006",
                    "title": "Multi Action",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Overdue Ref",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2025-01-01", "due": "2025-06-01"},
                            "statistics": {},
                        }
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        types = {i.action_type for i in items}
        assert "overdue_report" in types
        assert "needs_more_referees" in types

    @patch("reporting.action_items.load_journal_data")
    def test_priority_ordering(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-007",
                    "title": "Priority Test",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Overdue 30d",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {
                                "agreed": "2025-01-01",
                                "due": (
                                    datetime.date.today() - datetime.timedelta(days=30)
                                ).isoformat(),
                            },
                            "statistics": {},
                        },
                        {
                            "name": "Overdue 60d",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {
                                "agreed": "2025-01-01",
                                "due": (
                                    datetime.date.today() - datetime.timedelta(days=60)
                                ).isoformat(),
                            },
                            "statistics": {},
                        },
                    ],
                },
                {
                    "manuscript_id": "TEST-008",
                    "title": "Assignment Test",
                    "status": "New Submission",
                    "referees": [],
                    "platform_specific": {"metadata": {"current_stage": "Waiting"}},
                },
            ]
        }
        items = compute_action_items(journals=["test"])
        assert items[0].action_type == "overdue_report"
        assert items[0].days_overdue >= 60
        assert items[1].action_type == "overdue_report"
        assert items[1].days_overdue >= 30
        low = [i for i in items if i.priority == "low"]
        assert low[-1].action_type == "needs_assignment"

    @patch("reporting.action_items.load_journal_data")
    def test_pending_invitation_boundary(self, mock_load):
        day7 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        day8 = (datetime.date.today() - datetime.timedelta(days=8)).isoformat()
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-009",
                    "title": "Boundary Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Exactly 7",
                            "platform_specific": {"status": "Invited"},
                            "dates": {"invited": day7},
                            "statistics": {},
                        },
                        {
                            "name": "Day 8",
                            "platform_specific": {"status": "Invited"},
                            "dates": {"invited": day8},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        pending = [i for i in items if i.action_type == "pending_invitation"]
        names = [i.referee_name for i in pending]
        assert "Exactly 7" not in names
        assert "Day 8" in names

    @patch("reporting.action_items.load_journal_data")
    def test_journal_filtering(self, mock_load):
        mock_load.return_value = None
        items = compute_action_items(journals=["nonexistent"])
        assert items == []

    @patch("reporting.action_items.load_journal_data")
    def test_needs_assignment_new_submission(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-010",
                    "title": "New Paper",
                    "status": "New Submission",
                    "referees": [],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        assign = [i for i in items if i.action_type == "needs_assignment"]
        assert len(assign) == 1

    @patch("reporting.action_items.load_journal_data")
    def test_needs_ae_decision_not_triggered_with_agreed(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-011",
                    "title": "Partial Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Done A",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-01-15"},
                            "statistics": {},
                        },
                        {
                            "name": "Done B",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-02-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Still Working",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-10", "due": "2026-06-01"},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        decisions = [i for i in items if i.action_type == "needs_ae_decision"]
        assert len(decisions) == 0

    @patch("reporting.action_items.load_journal_data")
    def test_due_soon(self, mock_load):
        due_date = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-012",
                    "title": "Due Soon Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Almost Due",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": due_date},
                            "statistics": {},
                        },
                        {
                            "name": "Far Off",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2027-01-01"},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        due_soon = [i for i in items if i.action_type == "due_soon"]
        assert len(due_soon) == 1
        assert due_soon[0].referee_name == "Almost Due"
        assert due_soon[0].priority == "medium"


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

    @patch("reporting.action_items.load_journal_data")
    def test_needs_ae_decision_flag(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "AE-001",
                    "title": "Decide Me",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "A",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-01-15"},
                            "statistics": {},
                        },
                        {
                            "name": "B",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-02-01"},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].needs_ae_decision is True

    @patch("reporting.action_items.load_journal_data")
    def test_needs_ae_decision_false_with_agreed(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "AE-002",
                    "title": "Still Pending",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "A",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-01-15"},
                            "statistics": {},
                        },
                        {
                            "name": "B",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-02-01"},
                            "statistics": {},
                        },
                        {
                            "name": "C",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-10", "due": "2026-06-01"},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].needs_ae_decision is False

    @patch("reporting.action_items.load_journal_data")
    def test_needs_referee_assignment_flag(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "ASSIGN-001",
                    "title": "New Paper",
                    "status": "New Submission",
                    "referees": [],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].needs_referee_assignment is True

    @patch("reporting.action_items.load_journal_data")
    def test_needs_referee_assignment_false(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "ASSIGN-002",
                    "title": "Active Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Ref",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2026-06-01"},
                            "statistics": {},
                        }
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].needs_referee_assignment is False

    @patch("reporting.action_items.load_journal_data")
    def test_days_in_system(self, mock_load):
        sub_date = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "DIS-001",
                    "title": "Old Paper",
                    "status": "Under Review",
                    "submission_date": sub_date,
                    "referees": [],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].days_in_system == 45

    @patch("reporting.action_items.load_journal_data")
    def test_days_in_system_none(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "DIS-002",
                    "title": "No Date Paper",
                    "status": "Under Review",
                    "referees": [],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].days_in_system is None

    @patch("reporting.action_items.load_journal_data")
    def test_referee_counters_accurate(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "CNT-001",
                    "title": "Counter Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Agreed",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2026-06-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Complete",
                            "platform_specific": {"status": "Complete"},
                            "dates": {"returned": "2026-02-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Pending",
                            "platform_specific": {"status": "Invited"},
                            "dates": {"invited": "2026-01-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Declined",
                            "platform_specific": {"status": "Declined"},
                            "dates": {},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        s = summaries[0]
        assert s.referees_agreed == 1
        assert s.referees_completed == 1
        assert s.referees_pending_response == 1
        assert s.referees_declined == 1

    @patch("reporting.action_items.load_journal_data")
    def test_next_due_date_picks_earliest(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "DUE-001",
                    "title": "Multi Due Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Late",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2026-06-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Early",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2026-04-01"},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["test"])
        assert summaries[0].next_due_date == "2026-04-01"

    @patch("reporting.action_items.load_journal_data")
    def test_sorting_ae_decision_first(self, mock_load):
        def side_effect(journal):
            if journal == "test1":
                return {
                    "manuscripts": [
                        {
                            "manuscript_id": "SORT-A",
                            "title": "Regular",
                            "status": "Under Review",
                            "referees": [
                                {
                                    "name": "Ref",
                                    "platform_specific": {"status": "Agreed"},
                                    "dates": {"agreed": "2026-01-01", "due": "2026-06-01"},
                                    "statistics": {},
                                }
                            ],
                        }
                    ]
                }
            if journal == "test2":
                return {
                    "manuscripts": [
                        {
                            "manuscript_id": "SORT-B",
                            "title": "AE Needed",
                            "status": "Under Review",
                            "referees": [
                                {
                                    "name": "A",
                                    "platform_specific": {"status": "Complete"},
                                    "dates": {"returned": "2026-01-15"},
                                    "statistics": {},
                                },
                                {
                                    "name": "B",
                                    "platform_specific": {"status": "Complete"},
                                    "dates": {"returned": "2026-02-01"},
                                    "statistics": {},
                                },
                            ],
                        }
                    ]
                }
            return None

        mock_load.side_effect = side_effect
        summaries = compute_manuscript_summaries(journals=["test1", "test2"])
        assert len(summaries) == 2
        assert summaries[0].manuscript_id == "SORT-B"
        assert summaries[0].needs_ae_decision is True


class TestCleanRawStatus:
    def test_multiline_declined(self):
        assert _clean_raw_status("Declined\ninvite again") == "Declined"

    def test_multiline_invited(self):
        assert _clean_raw_status("Invited\nResponse\nSelect...") == "Invited"

    def test_clean_string(self):
        assert _clean_raw_status("Agreed") == "Agreed"

    def test_empty(self):
        assert _clean_raw_status("") == ""

    def test_none_like(self):
        assert _clean_raw_status(None) == ""

    def test_extra_whitespace(self):
        assert _clean_raw_status("Major  Revision\n\nrescind") == "Major Revision"


class TestDirtyStatusNormalization:
    def test_declined_with_invite_again(self):
        ref = {"status": "Declined\ninvite again", "dates": {}}
        assert _normalize_referee_status(ref, "mor") == "declined"

    def test_invited_multiline(self):
        ref = {"status": "Invited\nResponse\nSelect...", "dates": {"invited": "2025-01-01"}}
        assert _normalize_referee_status(ref, "mor") == "pending"

    def test_overdue_maps_to_agreed(self):
        ref = {"status": "Overdue", "dates": {}, "platform_specific": {}}
        assert _normalize_referee_status(ref, "mor") == "agreed"

    def test_accepted_maps_to_agreed(self):
        ref = {"status": "Accepted", "dates": {}, "platform_specific": {}}
        assert _normalize_referee_status(ref, "fs") == "agreed"

    def test_contacted_maps_to_pending(self):
        ref = {"status": "Contacted", "dates": {"invited": "2025-01-01"}, "platform_specific": {}}
        assert _normalize_referee_status(ref, "naco") == "pending"

    def test_un_invited_maps_to_declined(self):
        ref = {
            "status": "Un-invited Before Agreeing to Review",
            "dates": {},
            "platform_specific": {},
        }
        assert _normalize_referee_status(ref, "jota") == "declined"


class TestRevisionAwareness:
    def _make_ms_with_revision(self, revision_date, reports=None):
        return {
            "platform_specific": {
                "revision_round": 1,
                "revision_history": [{"round": 1, "submitted_date": revision_date}],
                "referee_reports": reports or [],
            }
        }

    def test_r0_report_not_current_round(self):
        ref = {"name": "Talbi", "dates": {"returned": "2025-03-18"}}
        ms = self._make_ms_with_revision("2025-10-29")
        result = _apply_revision_awareness("completed", ref, ms, "fs")
        assert result == "agreed"

    def test_r1_report_is_current_round(self):
        ref = {"name": "Hubert", "dates": {"returned": "2026-03-04"}}
        ms = self._make_ms_with_revision(
            "2025-10-29",
            reports=[{"referee": "Hubert Emma", "date": "Wed, 4 Mar 2026 16:19:03 +0000"}],
        )
        result = _apply_revision_awareness("completed", ref, ms, "fs")
        assert result == "completed"

    def test_non_fs_journal_unchanged(self):
        ref = {"name": "Smith", "dates": {"returned": "2025-03-18"}}
        ms = self._make_ms_with_revision("2025-10-29")
        result = _apply_revision_awareness("completed", ref, ms, "sicon")
        assert result == "completed"

    def test_no_revision_unchanged(self):
        ref = {"name": "Smith", "dates": {"returned": "2025-03-18"}}
        ms = {"platform_specific": {}}
        result = _apply_revision_awareness("completed", ref, ms, "fs")
        assert result == "completed"

    def test_agreed_status_unchanged(self):
        ref = {"name": "Smith", "dates": {}}
        ms = self._make_ms_with_revision("2025-10-29")
        result = _apply_revision_awareness("agreed", ref, ms, "fs")
        assert result == "agreed"


class TestGetRevisionDate:
    def test_rfc_date(self):
        ms = {
            "platform_specific": {
                "revision_history": [
                    {"round": 1, "submitted_date": "Wed, 29 Oct 2025 13:13:12 +0000"}
                ]
            }
        }
        assert _get_revision_date(ms) == datetime.date(2025, 10, 29)

    def test_no_revision(self):
        ms = {"platform_specific": {}}
        assert _get_revision_date(ms) is None


class TestHasCurrentRoundReport:
    def test_found(self):
        ref = {"name": "Emma Hubert"}
        ms = {
            "platform_specific": {
                "referee_reports": [
                    {"referee": "Hubert Emma", "date": "Wed, 4 Mar 2026 16:19:03 +0000"}
                ]
            }
        }
        assert _has_current_round_report(ref, ms, datetime.date(2025, 10, 29)) is True

    def test_old_report_not_current(self):
        ref = {"name": "Mehdi Talbi"}
        ms = {
            "platform_specific": {
                "referee_reports": [
                    {"referee": "Mehdi Talbi", "date": "Tue, 18 Mar 2025 11:23:52 +0100"}
                ]
            }
        }
        assert _has_current_round_report(ref, ms, datetime.date(2025, 10, 29)) is False

    def test_no_reports(self):
        ref = {"name": "Smith"}
        ms = {"platform_specific": {"referee_reports": []}}
        assert _has_current_round_report(ref, ms, datetime.date(2025, 10, 29)) is False


class TestGetReminders:
    def test_from_statistics(self):
        ref = {"statistics": {"reminders_received": 3}}
        assert _get_reminders(ref) == 3

    def test_no_statistics_returns_zero(self):
        ref = {}
        assert _get_reminders(ref) == 0

    def test_fs_fallback_to_timeline_metrics(self):
        ref = {"name": "Mehdi Talbi"}
        ms = {
            "platform_specific": {
                "timeline_metrics": {"reminders_received": {"Mehdi Talbi": 2, "Emma Hubert": 0}}
            }
        }
        assert _get_reminders(ref, ms, "fs") == 2

    def test_fs_no_match_returns_zero(self):
        ref = {"name": "Unknown"}
        ms = {"platform_specific": {"timeline_metrics": {"reminders_received": {"Mehdi Talbi": 2}}}}
        assert _get_reminders(ref, ms, "fs") == 0

    def test_timeline_analytics_by_email(self):
        ref = {
            "name": "Anthropelos",
            "email": "anthropel@unipi.gr",
            "statistics": {"reminders_received": 0},
        }
        ms = {
            "timeline_analytics": {
                "referee_metrics": {"anthropel@unipi.gr": {"reminders_received": 1}}
            }
        }
        assert _get_reminders(ref, ms, "mf") == 1

    def test_timeline_analytics_by_name(self):
        ref = {"name": "Cetin, Umut", "statistics": {"reminders_received": 0}}
        ms = {"timeline_analytics": {"referee_metrics": {"cetin, umut": {"reminders_received": 3}}}}
        assert _get_reminders(ref, ms, "mor") == 3

    def test_max_of_statistics_and_timeline(self):
        ref = {"name": "Song Yao", "email": "yao@test.edu", "statistics": {"reminders_received": 4}}
        ms = {
            "timeline_analytics": {"referee_metrics": {"yao@test.edu": {"reminders_received": 2}}}
        }
        assert _get_reminders(ref, ms, "sicon") == 4

    def test_timeline_higher_than_statistics(self):
        ref = {
            "name": "Yang Shen",
            "email": "y.shen@test.edu",
            "statistics": {"reminders_received": 2},
        }
        ms = {
            "timeline_analytics": {
                "referee_metrics": {"y.shen@test.edu": {"reminders_received": 3}}
            }
        }
        assert _get_reminders(ref, ms, "sicon") == 3


class TestHarmonizeStatus:
    def test_overdue_reviewer_reports(self):
        assert harmonize_status("Overdue Reviewer Reports") == "Under Review (Overdue)"

    def test_all_referees_assigned(self):
        assert harmonize_status("All Referees Assigned") == "Under Review"

    def test_awaiting_reviewer_scores(self):
        assert harmonize_status("Awaiting Reviewer Scores") == "Under Review"

    def test_waiting_for_assignment(self):
        assert harmonize_status("Waiting for Potential Referee Assignment") == "Awaiting Assignment"

    def test_r1_under_review(self):
        assert harmonize_status("Revision R1 Under Review") == "R1 Under Review"

    def test_unknown_passes_through(self):
        assert harmonize_status("Some New Status") == "Some New Status"

    def test_case_insensitive(self):
        assert harmonize_status("under review") == "Under Review"

    def test_submissions_under_review(self):
        assert harmonize_status("Submissions Under Review") == "Under Review"


class TestParseDateRFC:
    def test_rfc2822_format(self):
        assert _parse_date("Wed, 29 Oct 2025 13:13:12 +0000") == datetime.date(2025, 10, 29)

    def test_rfc2822_with_timezone(self):
        assert _parse_date("Tue, 18 Mar 2025 11:23:52 +0100") == datetime.date(2025, 3, 18)


class TestFSRevisionDueDate:
    def test_fs_due_date_uses_revision_response_date(self):
        ref = {
            "dates": {"agreed": "2024-11-07"},
            "platform_specific": {"response_date": "Fri, 7 Nov 2025 18:23:49 +0100"},
        }
        ms = {
            "platform_specific": {
                "revision_round": 1,
                "revision_history": [
                    {"round": 1, "submitted_date": "Wed, 29 Oct 2025 13:13:12 +0000"}
                ],
            }
        }
        due = _get_due_date(ref, "fs", ms)
        assert due == datetime.date(2025, 11, 7) + datetime.timedelta(days=90)

    def test_fs_due_date_no_revision(self):
        ref = {"dates": {"agreed": "2025-01-01"}, "platform_specific": {}}
        due = _get_due_date(ref, "fs", None)
        assert due == datetime.date(2025, 1, 1) + datetime.timedelta(days=90)


class TestComputeActionItemsRevision:
    @patch("reporting.action_items.load_journal_data")
    def test_fs_r1_no_false_decision(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "FS-24-4618",
                    "title": "Test R1",
                    "status": "Revision R1 Under Review",
                    "referees": [
                        {
                            "name": "Talbi",
                            "dates": {
                                "invited": "2024-11-01",
                                "agreed": "2025-11-07",
                                "returned": "2025-03-18",
                            },
                            "status_details": {"review_received": True},
                            "platform_specific": {
                                "report_date": "Tue, 18 Mar 2025 11:23:52 +0100",
                                "response_date": "Fri, 7 Nov 2025 18:23:49 +0100",
                            },
                        },
                        {
                            "name": "Hubert",
                            "dates": {
                                "invited": "2024-11-01",
                                "agreed": "2025-02-15",
                                "returned": "2026-03-04",
                            },
                            "status_details": {"review_received": True},
                            "platform_specific": {},
                        },
                    ],
                    "platform_specific": {
                        "revision_round": 1,
                        "revision_history": [
                            {"round": 1, "submitted_date": "Wed, 29 Oct 2025 13:13:12 +0000"}
                        ],
                        "referee_reports": [
                            {
                                "referee": "Emma Hubert",
                                "date": "Sat, 15 Feb 2025 00:29:34 +0000",
                            },
                            {
                                "referee": "Mehdi Talbi",
                                "date": "Tue, 18 Mar 2025 11:23:52 +0100",
                            },
                            {
                                "referee": "Hubert Emma",
                                "date": "Wed, 4 Mar 2026 16:19:03 +0000",
                            },
                        ],
                    },
                }
            ]
        }
        items = compute_action_items(journals=["fs"])
        decisions = [i for i in items if i.action_type == "needs_ae_decision"]
        assert len(decisions) == 0
        overdue = [i for i in items if i.action_type == "overdue_report"]
        assert len(overdue) == 1
        assert overdue[0].referee_name == "Talbi"


class TestEffectiveDates:
    def test_standard_dates(self):
        ref = {"dates": {"invited": "2025-01-01", "agreed": "2025-01-05"}, "platform_specific": {}}
        d = _effective_dates(ref)
        assert d["invited"] == "2025-01-01"
        assert d["agreed"] == "2025-01-05"

    def test_fallback_to_platform_specific(self):
        ref = {
            "dates": {"invited": None, "agreed": None, "due": None, "returned": None},
            "platform_specific": {
                "contact_date": "29 Mar 2023",
                "acceptance_date": "29 Mar 2023",
                "due_date": "27 Jun 2023",
                "received_date": "27 Jun 2023",
            },
        }
        d = _effective_dates(ref)
        assert d["invited"] == "29 Mar 2023"
        assert d["agreed"] == "29 Mar 2023"
        assert d["due"] == "27 Jun 2023"
        assert d["returned"] == "27 Jun 2023"

    def test_standard_takes_precedence(self):
        ref = {
            "dates": {"invited": "2025-01-01"},
            "platform_specific": {"contact_date": "2024-12-01"},
        }
        d = _effective_dates(ref)
        assert d["invited"] == "2025-01-01"

    def test_mafe_completed_via_platform_specific(self):
        ref = {
            "status": "Review Complete",
            "dates": {"invited": None, "agreed": None, "due": None, "returned": None},
            "platform_specific": {"received_date": "2024-09-13"},
        }
        assert _normalize_referee_status(ref, "mafe") == "completed"


class TestNoResponseExclusion:
    @patch("reporting.action_items.load_journal_data")
    def test_no_response_excluded_from_action_items(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "MOR-2025-1255",
                    "title": "Test",
                    "status": "Overdue Reviewer Reports",
                    "referees": [
                        {
                            "name": "Szpruch",
                            "platform_specific": {"status": "No Response"},
                            "dates": {"invited": "2025-11-09"},
                            "status_details": {"no_response": True},
                            "statistics": {},
                        },
                        {
                            "name": "Lauriere",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"invited": "2025-11-09", "agreed": "2025-11-18"},
                            "statistics": {"reminders_received": 4},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["mor"])
        names = [i.referee_name for i in items]
        assert "Szpruch" not in names
        assert "Lauriere" in names

    @patch("reporting.action_items.load_journal_data")
    def test_no_response_counted_as_declined_in_summary(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "MOR-2025-1255",
                    "title": "Test",
                    "status": "Overdue Reviewer Reports",
                    "referees": [
                        {
                            "name": "Szpruch",
                            "platform_specific": {"status": "No Response"},
                            "dates": {"invited": "2025-11-09"},
                            "status_details": {"no_response": True},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        summaries = compute_manuscript_summaries(journals=["mor"])
        assert summaries[0].referees_declined == 1
        assert summaries[0].referees_pending_response == 0


class TestStaleInvitationExclusion:
    @patch("reporting.action_items.load_journal_data")
    def test_stale_pending_excluded(self, mock_load):
        old_date = (
            datetime.date.today() - datetime.timedelta(days=STALE_INVITATION_DAYS + 10)
        ).isoformat()
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-003",
                    "title": "Stale Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Ghost Referee",
                            "platform_specific": {"status": "Invited"},
                            "dates": {"invited": old_date},
                            "statistics": {},
                        }
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        pending = [i for i in items if i.action_type == "pending_invitation"]
        assert len(pending) == 0

    @patch("reporting.action_items.load_journal_data")
    def test_fresh_pending_included(self, mock_load):
        recent_date = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-004",
                    "title": "Fresh Paper",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "New Referee",
                            "platform_specific": {"status": "Invited"},
                            "dates": {"invited": recent_date},
                            "statistics": {},
                        }
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        pending = [i for i in items if i.action_type == "pending_invitation"]
        assert len(pending) == 1
        assert pending[0].referee_name == "New Referee"

    @patch("reporting.action_items.load_journal_data")
    def test_stale_pending_plus_accepted_no_needs_more(self, mock_load):
        old_date = (
            datetime.date.today() - datetime.timedelta(days=STALE_INVITATION_DAYS + 10)
        ).isoformat()
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "TEST-STALE",
                    "title": "Two Refs One Stale",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Active Ref",
                            "platform_specific": {"status": "Agreed"},
                            "dates": {"agreed": "2026-01-01", "due": "2026-06-01"},
                            "statistics": {},
                        },
                        {
                            "name": "Stale Ref",
                            "platform_specific": {"status": "Invited"},
                            "dates": {"invited": old_date},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["test"])
        more = [i for i in items if i.action_type == "needs_more_referees"]
        assert len(more) == 0


class TestDisplayName:
    def test_openalex_preferred(self):
        ref = {
            "name": "Lauriere, Mathieu",
            "web_profile": {"openalex": {"display_name": "Mathieu Laurière"}},
        }
        assert _display_name(ref) == "Mathieu Laurière"

    def test_comma_flip_fallback(self):
        ref = {"name": "Lauriere, Mathieu"}
        assert _display_name(ref) == "Mathieu Lauriere"

    def test_no_comma_passthrough(self):
        ref = {"name": "Yang Shen"}
        assert _display_name(ref) == "Yang Shen"

    def test_missing_name(self):
        assert _display_name({}) == "Unknown"

    def test_multi_part_name(self):
        ref = {"name": "Tam, Jonathan Yick Yeung"}
        assert _display_name(ref) == "Jonathan Yick Yeung Tam"

    def test_openalex_overrides_uppercase(self):
        ref = {
            "name": "HUBERT, Emma",
            "web_profile": {"openalex": {"display_name": "Emma Hubert"}},
        }
        assert _display_name(ref) == "Emma Hubert"


class TestEdgeCasesFromRealData:
    """Edge cases discovered during audit of real extraction outputs."""

    def test_display_name_web_profile_none(self):
        ref = {"name": "Lindensjo, Kristoffer", "web_profile": None}
        assert _display_name(ref) == "Kristoffer Lindensjo"

    def test_display_name_web_profile_missing_key(self):
        ref = {"name": "Zhou Zhou"}
        assert _display_name(ref) == "Zhou Zhou"

    def test_display_name_empty_web_profile(self):
        ref = {"name": "Smith, John", "web_profile": {}}
        assert _display_name(ref) == "John Smith"

    def test_display_name_openalex_no_display_name(self):
        ref = {
            "name": "Zhang, Wei",
            "web_profile": {"openalex": {"author_id": "A123"}},
        }
        assert _display_name(ref) == "Wei Zhang"

    def test_normalize_status_mafe_terminated_null_dates(self):
        ref = {
            "status": "Terminated After Agreeing to Review",
            "dates": {"invited": None, "agreed": None, "due": None, "returned": None},
            "platform_specific": {"due_date": "19 Feb 2026"},
        }
        assert _normalize_referee_status(ref, "mafe") == "terminated"

    def test_effective_dates_null_dates_with_ps_due(self):
        ref = {
            "dates": {"invited": None, "agreed": None, "due": None, "returned": None},
            "platform_specific": {"due_date": "27 Jun 2023"},
        }
        eff = _effective_dates(ref)
        assert eff["invited"] is None
        assert eff["agreed"] is None
        assert eff["due"] == "27 Jun 2023"
        assert eff["returned"] is None

    def test_manuscript_status_none_with_category(self):
        ms = {"status": None, "category": "Awaiting Reviewer Reports"}
        assert _get_manuscript_status(ms) == "Awaiting Reviewer Reports"

    def test_manuscript_status_both_none(self):
        ms = {"status": None, "category": None, "platform_specific": {}}
        assert _get_manuscript_status(ms) == "Unknown"

    def test_effective_dates_no_dates_key(self):
        ref = {"name": "Test", "platform_specific": {"contact_date": "15 Jan 2025"}}
        eff = _effective_dates(ref)
        assert eff["invited"] == "15 Jan 2025"

    def test_effective_dates_no_platform_specific(self):
        ref = {"name": "Test", "dates": {"invited": "2025-01-15"}}
        eff = _effective_dates(ref)
        assert eff["invited"] == "2025-01-15"
        assert eff["agreed"] is None

    def test_get_due_date_mafe_from_ps(self):
        ref = {
            "dates": {"due": None},
            "platform_specific": {"due_date": "27 Jun 2023"},
        }
        assert _get_due_date(ref, "mafe") == datetime.date(2023, 6, 27)

    def test_normalize_status_recommendation_implies_completed(self):
        ref = {
            "name": "Emma Hubert",
            "recommendation": "Major Revision",
            "dates": {"invited": None, "agreed": None, "due": None, "returned": None},
            "platform_specific": {
                "reports": [{"revision": 0, "recommendation": "Major Revision"}],
            },
        }
        assert _normalize_referee_status(ref, "mafe") == "completed"

    def test_normalize_status_reports_only_implies_completed(self):
        ref = {
            "name": "Test Ref",
            "dates": {},
            "platform_specific": {
                "reports": [{"revision": 0, "recommendation": "Accept"}],
            },
        }
        assert _normalize_referee_status(ref, "mafe") == "completed"

    def test_normalize_status_ps_status_none_falls_to_ref_status(self):
        ref = {
            "status": "Awaiting Report",
            "platform_specific": {"status": None},
            "dates": {},
        }
        assert _normalize_referee_status(ref, "sicon") == "agreed"

    @patch("reporting.action_items.load_journal_data")
    def test_fs_revision_structure_no_crash(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "FS-99-0001",
                    "title": "Test Revision Paper",
                    "status": "Revision R1 Under Review",
                    "referees": [
                        {
                            "name": "Talbi",
                            "dates": {
                                "invited": "2024-11-01",
                                "agreed": "2024-11-07",
                                "returned": "2025-03-18",
                            },
                            "status_details": {"review_received": True},
                            "platform_specific": {},
                        },
                    ],
                    "platform_specific": {
                        "revision_round": 1,
                        "revision_history": [
                            {
                                "round": 1,
                                "submitted_date": "Wed, 29 Oct 2025 13:13:12 +0000",
                            }
                        ],
                        "referee_reports": [
                            {
                                "referee": "Mehdi Talbi",
                                "date": "Tue, 18 Mar 2025 11:23:52 +0100",
                            }
                        ],
                        "timeline_metrics": {"reminders_received": {"Talbi": 0}},
                    },
                }
            ]
        }
        items = compute_action_items(journals=["fs"])
        overdue = [i for i in items if i.action_type == "overdue_report"]
        assert len(overdue) == 1
        assert overdue[0].referee_name == "Talbi"

    @patch("reporting.action_items.load_journal_data")
    def test_empty_referees_needs_assignment(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "SICON-M999",
                    "title": "New Paper",
                    "status": "Waiting for Potential Referee Assignment",
                    "referees": [],
                    "platform_specific": {
                        "metadata": {"current_stage": "Waiting for Potential Referee Assignment"}
                    },
                }
            ]
        }
        items = compute_action_items(journals=["sicon"])
        assignments = [i for i in items if i.action_type == "needs_assignment"]
        assert len(assignments) == 1

    @patch("reporting.action_items.load_journal_data")
    def test_no_response_via_status_details(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "FS-25-9999",
                    "title": "Test",
                    "status": "Under Review",
                    "referees": [
                        {
                            "name": "Ghost",
                            "dates": {"invited": "2025-01-01"},
                            "status_details": {"no_response": True},
                            "platform_specific": {},
                        },
                        {
                            "name": "Active",
                            "dates": {
                                "invited": "2025-01-01",
                                "agreed": "2025-01-05",
                                "due": "2025-06-01",
                            },
                            "status_details": {"agreed_to_review": True},
                            "platform_specific": {},
                            "statistics": {},
                        },
                    ],
                }
            ]
        }
        items = compute_action_items(journals=["fs"])
        names = [i.referee_name for i in items]
        assert "Ghost" not in names


class TestSeasonalMode:
    def test_summer_mode(self):
        from reporting.action_items import get_seasonal_mode

        result = get_seasonal_mode(datetime.date(2026, 7, 15))
        assert result is not None
        assert result["label"] == "Summer Mode"

    def test_holiday_mode(self):
        from reporting.action_items import get_seasonal_mode

        result = get_seasonal_mode(datetime.date(2026, 12, 25))
        assert result is not None
        assert result["label"] == "Holiday Mode"

    def test_holiday_wraps_year(self):
        from reporting.action_items import get_seasonal_mode

        result = get_seasonal_mode(datetime.date(2027, 1, 3))
        assert result is not None

    def test_no_seasonal_march(self):
        from reporting.action_items import get_seasonal_mode

        assert get_seasonal_mode(datetime.date(2026, 3, 15)) is None

    def test_seasonal_extra_days_constant(self):
        from reporting.action_items import SEASONAL_EXTRA_DAYS

        assert SEASONAL_EXTRA_DAYS == 14
