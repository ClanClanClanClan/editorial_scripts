"""Tests for annual report generation."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from reporting.annual_report import (
    _compute_decision_stats,
    _filter_manuscripts_by_date,
    generate_annual_report,
    save_annual_report,
)


@pytest.fixture
def mock_journal_data():
    return {
        "extraction_timestamp": "2026-03-01T10:00:00",
        "manuscripts": [
            {
                "manuscript_id": "M100",
                "title": "Paper A",
                "status": "accepted",
                "submission_date": "2025-06-01",
                "decision_date": "2025-09-01",
                "referees": [{"name": "R1"}],
                "authors": [{"name": "Author 1"}],
                "timeline_analytics": {},
            },
            {
                "manuscript_id": "M200",
                "title": "Paper B",
                "status": "rejected",
                "submission_date": "2025-08-01",
                "decision_date": "2025-10-15",
                "referees": [{"name": "R2"}],
                "authors": [{"name": "Author 2"}],
                "timeline_analytics": {},
            },
            {
                "manuscript_id": "M300",
                "title": "Paper C",
                "status": "Under Review",
                "submission_date": "2024-01-01",
                "referees": [],
                "authors": [{"name": "Author 3"}],
                "timeline_analytics": {},
            },
        ],
    }


class TestGenerateAnnualReport:
    @patch("reporting.annual_report._compute_referee_pool_stats", return_value={})
    @patch("reporting.annual_report._compute_decision_stats", return_value={})
    @patch("reporting.annual_report.load_journal_data")
    def test_returns_correct_structure(self, mock_load, mock_dec, mock_ref, mock_journal_data):
        mock_load.return_value = mock_journal_data
        report = generate_annual_report("2025-01-01", "2025-12-31", journals=["sicon"])
        assert "period" in report
        assert "summary" in report
        assert "per_journal" in report
        assert report["period"]["start"] == "2025-01-01"
        assert report["summary"]["total_manuscripts"] == 2
        assert report["summary"]["total_accepted"] == 1

    @patch("reporting.annual_report._compute_referee_pool_stats", return_value={})
    @patch("reporting.annual_report._compute_decision_stats", return_value={})
    @patch("reporting.annual_report.load_journal_data")
    def test_empty_range_returns_zero_stats(self, mock_load, mock_dec, mock_ref, mock_journal_data):
        mock_load.return_value = mock_journal_data
        report = generate_annual_report("2020-01-01", "2020-12-31", journals=["sicon"])
        assert report["summary"]["total_manuscripts"] == 0
        assert report["summary"]["total_decided"] == 0


class TestFilterManuscriptsByDate:
    def test_filters_correctly(self):
        manuscripts = [
            {"submission_date": "2025-06-01"},
            {"submission_date": "2025-12-01"},
            {"submission_date": "2024-01-01"},
        ]
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        filtered = _filter_manuscripts_by_date(manuscripts, start, end)
        assert len(filtered) == 2


class TestSaveAnnualReport:
    def test_creates_json_and_md(self, tmp_path):
        report = {
            "period": {"start": "2025-01-01", "end": "2025-12-31"},
            "summary": {
                "total_manuscripts": 10,
                "total_decided": 8,
                "total_accepted": 5,
                "overall_acceptance_rate": 0.625,
                "avg_days_to_decision": 90.0,
                "journals_covered": 2,
            },
            "per_journal": {},
            "referee_pool": {},
            "decision_breakdown": {},
            "generated_at": "2026-03-25T10:00:00",
        }
        with patch("reporting.annual_report.REPORTS_DIR", tmp_path):
            json_path, md_path = save_annual_report(report)

        assert json_path.exists()
        assert md_path.exists()
        saved = json.loads(json_path.read_text())
        assert saved["summary"]["total_manuscripts"] == 10
        assert "Annual Editorial Report" in md_path.read_text()


class TestComputeDecisionStats:
    def test_reads_jsonl_correctly(self, tmp_path):
        outcomes_file = tmp_path / "sicon_outcomes.jsonl"
        lines = [
            json.dumps({"timestamp": "2025-06-15", "decision": "accept"}),
            json.dumps({"timestamp": "2025-07-20", "decision": "reject"}),
            json.dumps({"timestamp": "2025-08-10", "decision": "accept"}),
            json.dumps({"timestamp": "2024-01-01", "decision": "accept"}),
        ]
        outcomes_file.write_text("\n".join(lines))

        with patch("reporting.annual_report.FEEDBACK_DIR", tmp_path):
            stats = _compute_decision_stats(date(2025, 1, 1), date(2025, 12, 31))

        assert stats.get("accept", 0) == 2
        assert stats.get("reject", 0) == 1
