#!/usr/bin/env python3
"""Tests for cross-journal reporting."""

import json
from unittest.mock import patch

import pytest
from reporting.cross_journal_report import (
    _is_active_referee,
    compute_journal_stats,
    find_author_across_journals,
    find_latest_output,
    generate_json_report,
    load_journal_data,
    print_terminal_report,
    run_report,
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


class TestLoadJournalDataManifest:
    def _write_json(self, path, data):
        path.write_text(json.dumps(data))

    def test_no_manifest_returns_latest(self, tmp_path):
        d = tmp_path / "mor"
        d.mkdir()
        self._write_json(
            d / "mor_extraction_20260308.json",
            {"manuscripts": [{"manuscript_id": "A"}, {"manuscript_id": "B"}]},
        )
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            data = load_journal_data("mor")
            assert len(data["manuscripts"]) == 2

    def test_manifest_filters_removed_manuscripts(self, tmp_path):
        d = tmp_path / "mor"
        d.mkdir()
        self._write_json(
            d / "mor_extraction_20260308.json",
            {
                "manuscripts": [
                    {"manuscript_id": "A", "category": "Awaiting Reviewer Reports"},
                    {"manuscript_id": "B", "category": "Awaiting Reviewer Reports"},
                    {"manuscript_id": "C", "category": "Overdue Reviewer Response"},
                ],
            },
        )
        self._write_json(
            d / "mor_extraction_20260310.json",
            {
                "manuscripts": [{"manuscript_id": "A"}],
                "dashboard_manifest": {
                    "scanned": {
                        "Overdue Reviewer Response": [],
                        "Awaiting Reviewer Reports": ["A", "B"],
                    },
                    "failed": [],
                },
            },
        )
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            data = load_journal_data("mor")
            ids = {m["manuscript_id"] for m in data["manuscripts"]}
            assert ids == {"A", "B"}
            assert "C" not in ids

    def test_manifest_pulls_data_from_older_file(self, tmp_path):
        d = tmp_path / "mor"
        d.mkdir()
        self._write_json(
            d / "mor_extraction_20260308.json",
            {
                "manuscripts": [
                    {"manuscript_id": "A", "title": "Full A"},
                    {"manuscript_id": "B", "title": "Full B"},
                ],
            },
        )
        self._write_json(
            d / "mor_extraction_20260310.json",
            {
                "manuscripts": [{"manuscript_id": "A", "title": "Partial A"}],
                "dashboard_manifest": {
                    "scanned": {"Cat1": ["A", "B"]},
                    "failed": [],
                },
            },
        )
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            data = load_journal_data("mor")
            ms_map = {m["manuscript_id"]: m for m in data["manuscripts"]}
            assert ms_map["A"]["title"] == "Partial A"
            assert ms_map["B"]["title"] == "Full B"

    def test_manifest_keeps_manuscripts_from_failed_categories(self, tmp_path):
        d = tmp_path / "mor"
        d.mkdir()
        self._write_json(
            d / "mor_extraction_20260308.json",
            {
                "manuscripts": [
                    {"manuscript_id": "A", "category": "Awaiting Reviewer Reports"},
                    {"manuscript_id": "D", "category": "Overdue Reviewer Reports"},
                ],
            },
        )
        self._write_json(
            d / "mor_extraction_20260310.json",
            {
                "manuscripts": [{"manuscript_id": "A"}],
                "dashboard_manifest": {
                    "scanned": {"Awaiting Reviewer Reports": ["A"]},
                    "failed": ["Overdue Reviewer Reports"],
                },
            },
        )
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            data = load_journal_data("mor")
            ids = {m["manuscript_id"] for m in data["manuscripts"]}
            assert "A" in ids
            assert "D" in ids

    def test_no_files_returns_none(self, tmp_path):
        d = tmp_path / "mor"
        d.mkdir()
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            assert load_journal_data("mor") is None


class TestRunReport:
    @patch("reporting.cross_journal_report.load_journal_data")
    @patch("reporting.cross_journal_report._get_feedback_summary", return_value=None)
    def test_returns_dict_with_expected_keys(self, _fb, mock_load):
        mock_load.return_value = None
        report = run_report()
        assert "report_type" in report
        assert report["report_type"] == "cross_journal"
        assert "totals" in report
        assert "journals" in report
        assert report["totals"]["manuscripts"] == 0

    @patch("reporting.cross_journal_report.load_journal_data")
    @patch("reporting.cross_journal_report._get_feedback_summary", return_value=None)
    def test_save_json_writes_file(self, _fb, mock_load, tmp_path):
        mock_load.return_value = None
        run_report(save_json=True, output_dir=tmp_path)
        files = list(tmp_path.glob("cross_journal_report_*.json"))
        assert len(files) == 1
        saved = json.loads(files[0].read_text())
        assert saved["report_type"] == "cross_journal"

    @patch("reporting.cross_journal_report.load_journal_data")
    @patch("reporting.cross_journal_report._get_feedback_summary", return_value=None)
    def test_with_real_data(self, _fb, mock_load):
        def side_effect(journal):
            if journal == "mf":
                return {
                    "extraction_timestamp": "2026-03-01T10:00:00",
                    "manuscripts": [
                        {
                            "referees": [{"name": "R1"}],
                            "authors": [{"name": "A1", "web_profile": {"h_index": 5}}],
                            "timeline_analytics": {},
                        }
                    ],
                }
            return None

        mock_load.side_effect = side_effect
        report = run_report()
        assert report["totals"]["manuscripts"] == 1
        assert report["totals"]["referees"] == 1


class TestPrintTerminalReport:
    def test_zero_manuscript_journals(self, capsys):
        stats = [
            {
                "journal": "NACO",
                "platform": "EditFlow",
                "manuscripts": 0,
                "referees": 0,
                "authors": 0,
                "enriched": 0,
                "total_people": 0,
                "enrichment_pct": 0,
                "avg_span_days": None,
                "avg_response_days": None,
                "extraction_date": "",
                "age_days": None,
            }
        ]
        print_terminal_report(stats)
        out = capsys.readouterr().out
        assert "NACO" in out
        assert "0/1 journals active" in out

    def test_stale_data_flagged(self, capsys):
        stats = [
            {
                "journal": "MF",
                "platform": "ScholarOne",
                "manuscripts": 2,
                "referees": 3,
                "authors": 5,
                "enriched": 4,
                "total_people": 8,
                "enrichment_pct": 50.0,
                "avg_span_days": 30.0,
                "avg_response_days": 14.0,
                "extraction_date": "2025-01-01",
                "age_days": 30,
            }
        ]
        print_terminal_report(stats)
        out = capsys.readouterr().out
        assert "Stale data" in out
        assert "MF" in out


class TestLoadJournalDataErrors:
    def test_corrupt_json_returns_none(self, tmp_path):
        d = tmp_path / "mf"
        d.mkdir()
        (d / "mf_extraction_20260301.json").write_text("{{not json}}")
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            assert load_journal_data("mf") is None

    def test_empty_file_returns_none(self, tmp_path):
        d = tmp_path / "mf"
        d.mkdir()
        (d / "mf_extraction_20260301.json").write_text("")
        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            assert load_journal_data("mf") is None


class TestIsActiveReferee:
    def test_no_response_is_inactive(self):
        ref = {"platform_specific": {"status": "No Response"}}
        assert not _is_active_referee(ref)

    def test_no_response_lowercase_is_inactive(self):
        ref = {"platform_specific": {"status": "no response"}}
        assert not _is_active_referee(ref)

    def test_declined_is_inactive(self):
        ref = {"platform_specific": {"status": "Declined"}}
        assert not _is_active_referee(ref)

    def test_terminated_is_inactive(self):
        ref = {"status": "Terminated"}
        assert not _is_active_referee(ref)

    def test_agreed_is_active(self):
        ref = {"platform_specific": {"status": "Agreed"}}
        assert _is_active_referee(ref)


class TestFindAuthorAcrossJournals:
    @patch("reporting.cross_journal_report.load_journal_data")
    def test_finds_author(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "M1",
                    "title": "Test",
                    "status": "Under Review",
                    "authors": [{"name": "John Smith"}],
                }
            ]
        }
        results = find_author_across_journals("John Smith")
        assert len(results) >= 1

    @patch("reporting.cross_journal_report.load_journal_data")
    def test_excludes_journal(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "M1",
                    "title": "Test",
                    "status": "OK",
                    "authors": [{"name": "Smith"}],
                }
            ]
        }
        results = find_author_across_journals("Smith", exclude_journal="mf")
        assert isinstance(results, list)

    @patch("reporting.cross_journal_report.load_journal_data")
    def test_not_found(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [{"manuscript_id": "M1", "authors": [{"name": "Alice"}]}]
        }
        results = find_author_across_journals("Bob")
        assert len(results) == 0

    def test_empty_name(self):
        assert find_author_across_journals("") == []

    @patch("reporting.cross_journal_report.load_journal_data")
    def test_normalized_matching(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "M1",
                    "title": "T",
                    "status": "OK",
                    "authors": [{"name": "Muller, Hans"}],
                }
            ]
        }
        results = find_author_across_journals("muller, hans")
        assert len(results) >= 1

    @patch("reporting.cross_journal_report.load_journal_data")
    def test_surname_only_search(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "M1",
                    "title": "T",
                    "status": "OK",
                    "authors": [{"name": "Alice Wonderland"}],
                }
            ]
        }
        results = find_author_across_journals("Wonderland")
        assert len(results) >= 1

    @patch("reporting.cross_journal_report.load_journal_data")
    def test_surname_only_no_partial_word_match(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "M1",
                    "title": "T",
                    "status": "OK",
                    "authors": [{"name": "Alice Wonderland"}],
                }
            ]
        }
        results = find_author_across_journals("Wonder")
        assert len(results) == 0

    @patch("reporting.cross_journal_report.load_journal_data")
    def test_full_name_requires_exact_match(self, mock_load):
        mock_load.return_value = {
            "manuscripts": [
                {
                    "manuscript_id": "M1",
                    "title": "T",
                    "status": "OK",
                    "authors": [{"name": "Alice Smith"}],
                }
            ]
        }
        results = find_author_across_journals("Alice Smith")
        assert len(results) >= 1
        results2 = find_author_across_journals("Alice Jones")
        assert len(results2) == 0
