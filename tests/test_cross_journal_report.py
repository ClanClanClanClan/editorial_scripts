#!/usr/bin/env python3
"""Tests for cross-journal reporting."""

import json
from unittest.mock import patch

import pytest
from reporting.cross_journal_report import (
    compute_journal_stats,
    find_latest_output,
    generate_json_report,
)


class TestComputeJournalStats:
    def test_basic_stats(self):
        data = {
            "extraction_timestamp": "2026-03-01T10:00:00",
            "manuscripts": [
                {
                    "referees": [{"name": "R1"}, {"name": "R2"}],
                    "authors": [{"name": "A1", "web_profile": {"h_index": 10}}],
                    "timeline_analytics": {
                        "communication_span_days": 30,
                        "response_time_analysis": {"average_response_days": 14},
                    },
                }
            ],
        }
        stats = compute_journal_stats("sicon", data)
        assert stats["manuscripts"] == 1
        assert stats["referees"] == 2
        assert stats["authors"] == 1
        assert stats["enriched"] == 1
        assert stats["avg_span_days"] == 30.0
        assert stats["avg_response_days"] == 14.0

    def test_empty_manuscripts(self):
        stats = compute_journal_stats("sicon", {"manuscripts": []})
        assert stats["manuscripts"] == 0
        assert stats["referees"] == 0
        assert stats["enrichment_pct"] == 0

    def test_missing_timestamp(self):
        stats = compute_journal_stats("sicon", {"manuscripts": [], "extraction_timestamp": ""})
        assert stats["age_days"] is None
        assert stats["extraction_date"] == ""

    def test_multiple_manuscripts(self):
        data = {
            "extraction_timestamp": "2026-03-01T10:00:00",
            "manuscripts": [
                {
                    "referees": [{"name": "R1"}],
                    "authors": [{"name": "A1"}],
                    "timeline_analytics": {},
                },
                {
                    "referees": [{"name": "R2"}, {"name": "R3"}],
                    "authors": [{"name": "A2", "web_profile": {"h_index": 5}}],
                    "timeline_analytics": {},
                },
            ],
        }
        stats = compute_journal_stats("mf", data)
        assert stats["manuscripts"] == 2
        assert stats["referees"] == 3
        assert stats["authors"] == 2
        assert stats["enriched"] == 1
        assert stats["total_people"] == 5

    def test_journal_name_lookup(self):
        stats = compute_journal_stats("mf", {"manuscripts": [], "extraction_timestamp": ""})
        assert stats["journal_name"] == "Mathematical Finance"
        assert stats["platform"] == "ScholarOne"


class TestFindLatestOutput:
    def test_no_directory(self, tmp_path):
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            assert find_latest_output("sicon") is None

    def test_skips_baseline(self, tmp_path):
        d = tmp_path / "sicon"
        d.mkdir()
        (d / "BASELINE_sicon.json").write_text("{}")
        (d / "sicon_extraction_20260301.json").write_text("{}")
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            result = find_latest_output("sicon")
            assert result is not None
            assert "BASELINE" not in result.name

    def test_returns_latest_by_mtime(self, tmp_path):
        import time

        d = tmp_path / "mf"
        d.mkdir()
        old = d / "mf_extraction_20260201.json"
        old.write_text("{}")
        time.sleep(0.05)
        new = d / "mf_extraction_20260301.json"
        new.write_text("{}")
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            result = find_latest_output("mf")
            assert result is not None
            assert result.name == "mf_extraction_20260301.json"

    def test_empty_directory(self, tmp_path):
        d = tmp_path / "sicon"
        d.mkdir()
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            assert find_latest_output("sicon") is None


class TestGenerateJsonReport:
    def test_report_structure(self):
        stats = [
            {
                "manuscripts": 5,
                "referees": 10,
                "authors": 8,
                "enriched": 6,
                "journal": "SICON",
            },
        ]
        report = generate_json_report(stats)
        assert report["report_type"] == "cross_journal"
        assert "totals" in report
        assert report["totals"]["manuscripts"] == 5
        assert report["totals"]["referees"] == 10
        assert report["totals"]["journals_total"] == 1

    def test_empty_stats(self):
        report = generate_json_report([])
        assert report["totals"]["manuscripts"] == 0
        assert report["totals"]["journals_active"] == 0
