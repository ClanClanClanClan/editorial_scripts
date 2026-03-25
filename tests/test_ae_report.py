import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def _make_extraction(tmp_path):
    def _factory(journal, manuscripts):
        journal_dir = tmp_path / journal
        journal_dir.mkdir(parents=True, exist_ok=True)
        data = {"manuscripts": manuscripts}
        out = journal_dir / f"{journal}_20260325_120000.json"
        out.write_text(json.dumps(data))
        return data

    return _factory


def _ref(
    name,
    status="report submitted",
    recommendation="",
    reports=None,
    report=None,
    status_details=None,
):
    r = {"name": name, "status": status}
    if recommendation:
        r["recommendation"] = recommendation
    if reports is not None:
        r["reports"] = reports
    if report is not None:
        r["report"] = report
    if status_details is not None:
        r["status_details"] = status_details
    return r


class TestIsReportComplete:
    @pytest.fixture(autouse=True)
    def _import(self):
        from pipeline.ae_report import _is_report_complete

        self.fn = _is_report_complete

    def test_status_report_submitted(self):
        assert self.fn({"status": "Report Submitted"}, "mf") is True

    def test_status_review_complete(self):
        assert self.fn({"status": "Review Complete"}, "mf") is True

    def test_status_completed(self):
        assert self.fn({"status": "Completed"}, "mf") is True

    def test_status_details_review_received(self):
        ref = {"status": "in progress", "status_details": {"review_received": True}}
        assert self.fn(ref, "mf") is True

    def test_status_details_review_complete(self):
        ref = {"status": "in progress", "status_details": {"review_complete": True}}
        assert self.fn(ref, "mf") is True

    def test_report_with_comments(self):
        ref = {"status": "invited", "report": {"comments_to_author": "Good paper."}}
        assert self.fn(ref, "mf") is True

    def test_report_with_recommendation_only(self):
        ref = {"status": "invited", "report": {"recommendation": "Accept"}}
        assert self.fn(ref, "mf") is True

    def test_recommendation_plus_reports(self):
        ref = {
            "status": "invited",
            "recommendation": "Major Revision",
            "reports": [{"path": "dummy.pdf"}],
        }
        assert self.fn(ref, "mf") is True

    def test_recommendation_unknown_not_complete(self):
        ref = {"status": "invited", "recommendation": "unknown", "reports": [{"path": "dummy.pdf"}]}
        assert self.fn(ref, "mf") is False

    def test_recommendation_na_not_complete(self):
        ref = {"status": "invited", "recommendation": "N/A", "reports": [{"path": "dummy.pdf"}]}
        assert self.fn(ref, "mf") is False

    def test_recommendation_without_reports_not_complete(self):
        ref = {"status": "invited", "recommendation": "Accept"}
        assert self.fn(ref, "mf") is False

    def test_empty_referee_not_complete(self):
        assert self.fn({"status": "invited"}, "mf") is False

    def test_no_status_not_complete(self):
        assert self.fn({}, "mf") is False


class TestDetectRevisionRound:
    @pytest.fixture(autouse=True)
    def _import(self):
        from pipeline.ae_report import _detect_revision_round

        self.fn = _detect_revision_round

    def test_r1_in_id(self):
        assert self.fn({"manuscript_id": "MS-2024-001-R1", "status": ""}) == 1

    def test_r2_in_id(self):
        assert self.fn({"manuscript_id": "MS-2024-001-R2", "status": ""}) == 2

    def test_r1_in_status(self):
        assert self.fn({"manuscript_id": "MS-2024-001", "status": "Under Review R1"}) == 1

    def test_r2_in_status(self):
        assert self.fn({"manuscript_id": "MS-2024-001", "status": "Under Review R2"}) == 2

    def test_revision_in_status(self):
        assert self.fn({"manuscript_id": "MS-2024-001", "status": "Revision Submitted"}) == 1

    def test_original_manuscript(self):
        assert self.fn({"manuscript_id": "MS-2024-001", "status": "Under Review"}) == 0

    def test_id_takes_precedence_over_status(self):
        assert self.fn({"manuscript_id": "MS-001-R2", "status": "revision r1"}) == 2


class TestFindManuscriptsNeedingAeReport:
    def test_finds_manuscript_all_complete(self, tmp_path, _make_extraction):
        ms = {
            "manuscript_id": "MS-001",
            "title": "Test Paper",
            "referees": [
                _ref("Alice", status="report submitted"),
                _ref("Bob", status="review complete"),
            ],
        }
        _make_extraction("sicon", [ms])
        ae_dir = tmp_path / "sicon" / "ae_reports"
        ae_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("pipeline.ae_report.OUTPUTS_DIR", tmp_path),
            patch("pipeline.ae_report._latest_extraction") as mock_le,
            patch("pipeline.ae_report.JOURNALS", ["sicon"]),
        ):
            mock_le.return_value = {"manuscripts": [ms]}
            results = self._call(journal="sicon")
            assert len(results) == 1
            assert results[0]["manuscript_id"] == "MS-001"
            assert results[0]["completed_reports"] == 2
            assert results[0]["has_ae_report"] is False

    def test_skips_if_active_referee_pending(self, tmp_path, _make_extraction):
        ms = {
            "manuscript_id": "MS-002",
            "title": "Test",
            "referees": [
                _ref("Alice", status="report submitted"),
                _ref("Bob", status="report submitted"),
                _ref("Carol", status="review in progress"),
            ],
        }
        with (
            patch("pipeline.ae_report.OUTPUTS_DIR", tmp_path),
            patch("pipeline.ae_report._latest_extraction") as mock_le,
            patch("pipeline.ae_report.JOURNALS", ["mf"]),
        ):
            mock_le.return_value = {"manuscripts": [ms]}
            results = self._call(journal="mf")
            assert len(results) == 0

    def test_declined_referee_not_counted_as_active(self, tmp_path, _make_extraction):
        ms = {
            "manuscript_id": "MS-003",
            "title": "Test",
            "referees": [
                _ref("Alice", status="report submitted"),
                _ref("Bob", status="review complete"),
                _ref("Carol", status="declined"),
            ],
        }
        ae_dir = tmp_path / "mf" / "ae_reports"
        ae_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("pipeline.ae_report.OUTPUTS_DIR", tmp_path),
            patch("pipeline.ae_report._latest_extraction") as mock_le,
            patch("pipeline.ae_report.JOURNALS", ["mf"]),
        ):
            mock_le.return_value = {"manuscripts": [ms]}
            results = self._call(journal="mf")
            assert len(results) == 1

    def test_fewer_than_2_complete_excluded(self, tmp_path):
        ms = {
            "manuscript_id": "MS-004",
            "title": "Test",
            "referees": [
                _ref("Alice", status="report submitted"),
                _ref("Bob", status="invited"),
            ],
        }
        with (
            patch("pipeline.ae_report.OUTPUTS_DIR", tmp_path),
            patch("pipeline.ae_report._latest_extraction") as mock_le,
            patch("pipeline.ae_report.JOURNALS", ["mf"]),
        ):
            mock_le.return_value = {"manuscripts": [ms]}
            results = self._call(journal="mf")
            assert len(results) == 0

    def test_no_extraction_data(self, tmp_path):
        with (
            patch("pipeline.ae_report.OUTPUTS_DIR", tmp_path),
            patch("pipeline.ae_report._latest_extraction") as mock_le,
            patch("pipeline.ae_report.JOURNALS", ["mf"]),
        ):
            mock_le.return_value = None
            results = self._call(journal="mf")
            assert results == []

    @staticmethod
    def _call(**kwargs):
        from pipeline.ae_report import find_manuscripts_needing_ae_report

        return find_manuscripts_needing_ae_report(**kwargs)


class TestAssemble:
    def test_returns_none_if_no_extraction(self):
        with patch("pipeline.ae_report._latest_extraction", return_value=None):
            from pipeline.ae_report import assemble

            assert assemble("mf", "MS-001") is None

    def test_returns_none_if_manuscript_not_found(self):
        data = {"manuscripts": [{"manuscript_id": "MS-OTHER"}]}
        with patch("pipeline.ae_report._latest_extraction", return_value=data):
            from pipeline.ae_report import assemble

            assert assemble("mf", "MS-001") is None

    def test_returns_none_if_fewer_than_2_complete(self):
        ms = {
            "manuscript_id": "MS-001",
            "title": "T",
            "referees": [_ref("Alice", status="report submitted")],
        }
        data = {"manuscripts": [ms]}
        with patch("pipeline.ae_report._latest_extraction", return_value=data):
            from pipeline.ae_report import assemble

            assert assemble("mf", "MS-001") is None

    def test_returns_assembled_dict(self):
        ms = {
            "manuscript_id": "MS-001-R1",
            "title": "Great Paper",
            "abstract": "Abstract text",
            "keywords": ["finance"],
            "authors": [{"name": "Author One"}],
            "status": "Under Review",
            "referees": [
                _ref(
                    "Alice",
                    status="report submitted",
                    report={"comments_to_author": "Looks good", "recommendation": "Accept"},
                ),
                _ref(
                    "Bob",
                    status="review complete",
                    report={"comments_to_author": "Needs work", "recommendation": "Revise"},
                ),
            ],
        }
        data = {"manuscripts": [ms]}
        with (
            patch("pipeline.ae_report._latest_extraction", return_value=data),
            patch(
                "pipeline.ae_report.assess_report_quality",
                return_value={"consensus": {"agreement": "high"}, "reports": []},
            ),
        ):
            from pipeline.ae_report import assemble

            result = assemble("mf", "MS-001-R1")
            assert result is not None
            assert result["manuscript_id"] == "MS-001-R1"
            assert result["revision_round"] == 1
            assert len(result["reports"]) == 2
            assert result["consensus"] == {"agreement": "high"}
