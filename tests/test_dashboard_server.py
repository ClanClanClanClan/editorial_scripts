"""Tests for the Flask dashboard API server."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR / "production" / "src"))

from scripts.dashboard_server import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestServeDashboard:
    def test_serves_html_when_exists(self, client, tmp_path):
        html = tmp_path / "dashboard.html"
        html.write_text("<html>dashboard</html>")
        with patch("scripts.dashboard_server.DASHBOARD_PATH", html):
            resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_404_when_missing(self, client, tmp_path):
        missing = tmp_path / "no_such.html"
        with patch("scripts.dashboard_server.DASHBOARD_PATH", missing):
            resp = client.get("/")
        assert resp.status_code == 404


class TestAEReport:
    def test_missing_params_returns_400(self, client):
        resp = client.post("/api/ae-report", json={})
        assert resp.status_code == 400
        assert "required" in resp.get_json()["error"]

    def test_missing_manuscript_id_returns_400(self, client):
        resp = client.post("/api/ae-report", json={"journal": "sicon"})
        assert resp.status_code == 400

    def test_missing_journal_returns_400(self, client):
        resp = client.post("/api/ae-report", json={"manuscript_id": "M123"})
        assert resp.status_code == 400

    @patch("pipeline.ae_report.generate", return_value={"recommendation": "accept"})
    def test_successful_generation(self, mock_gen, client):
        resp = client.post(
            "/api/ae-report",
            json={"journal": "sicon", "manuscript_id": "M123"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["recommendation"] == "accept"
        call_args = mock_gen.call_args
        assert call_args[0] == ("sicon", "M123")
        assert call_args[1]["provider"] in ("claude", "prompt")

    @patch("pipeline.ae_report.generate", return_value=None)
    def test_generation_failure_returns_500(self, mock_gen, client):
        resp = client.post(
            "/api/ae-report",
            json={"journal": "sicon", "manuscript_id": "M123"},
        )
        assert resp.status_code == 500


class TestGetAEReport:
    def test_found(self, client, tmp_path):
        ae_dir = tmp_path / "sicon" / "ae_reports"
        ae_dir.mkdir(parents=True)
        report = {"recommendation": "revise"}
        (ae_dir / "ae_M123_20260101.json").write_text(json.dumps(report))
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path / "fake"):
            with patch(
                "scripts.dashboard_server.PROJECT_DIR",
                new=tmp_path,
            ):
                patched_dir = tmp_path / "production" / "outputs" / "sicon" / "ae_reports"
                patched_dir.mkdir(parents=True)
                (patched_dir / "ae_M123_20260101.json").write_text(json.dumps(report))
                resp = client.get("/api/ae-reports/sicon/M123")
        assert resp.status_code == 200
        assert resp.get_json()["recommendation"] == "revise"

    def test_not_found(self, client, tmp_path):
        patched_dir = tmp_path / "production" / "outputs" / "sicon" / "ae_reports"
        patched_dir.mkdir(parents=True)
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path):
            resp = client.get("/api/ae-reports/sicon/MISSING")
        assert resp.status_code == 404


class TestAEList:
    @patch(
        "pipeline.ae_report.find_manuscripts_needing_ae_report",
        return_value=[{"journal": "sicon", "manuscript_id": "M1"}],
    )
    def test_returns_list(self, mock_find, client):
        resp = client.get("/api/ae-list")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1


class TestRefreshDashboard:
    @patch("scripts.dashboard_server.subprocess.run")
    def test_success(self, mock_run, client):
        mock_run.return_value = MagicMock(returncode=0)
        resp = client.post("/api/refresh-dashboard")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    @patch("scripts.dashboard_server.subprocess.run")
    def test_failure(self, mock_run, client):
        from subprocess import CalledProcessError

        err = CalledProcessError(1, "cmd")
        err.stderr = b"something went wrong"
        mock_run.side_effect = err
        resp = client.post("/api/refresh-dashboard")
        assert resp.status_code == 500


class TestRunExtraction:
    def test_missing_journal_returns_400(self, client):
        resp = client.post("/api/run-extraction", json={})
        assert resp.status_code == 400

    @patch("scripts.dashboard_server.threading.Thread")
    def test_starts_thread(self, mock_thread, client):
        mock_thread.return_value = MagicMock()
        resp = client.post("/api/run-extraction", json={"journal": "mf"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "started"
        assert data["journal"] == "mf"
        mock_thread.return_value.start.assert_called_once()


class TestRefereeEndpoints:
    def _mock_db(self):
        db = MagicMock()
        return db

    @patch("pipeline.referee_db.RefereeDB")
    def test_profile_found(self, MockDB, client):
        db = self._mock_db()
        db.get_profile.return_value = {"name": "Smith, J.", "acceptance_rate": 0.8}
        db.get_referee_assignments.return_value = [{"ms": "M1"}]
        MockDB.return_value = db
        resp = client.get("/api/referee/Smith%2C%20J.")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Smith, J."
        assert "assignments" in data

    @patch("pipeline.referee_db.RefereeDB")
    def test_profile_not_found(self, MockDB, client):
        db = self._mock_db()
        db.get_profile.return_value = None
        MockDB.return_value = db
        resp = client.get("/api/referee/Nobody")
        assert resp.status_code == 404

    @patch("pipeline.referee_db.RefereeDB")
    def test_search_too_short(self, MockDB, client):
        resp = client.get("/api/referee/search?q=A")
        assert resp.status_code == 400

    @patch("pipeline.referee_db.RefereeDB")
    def test_search_success(self, MockDB, client):
        db = self._mock_db()
        db.search_referees.return_value = [{"name": "Smith"}]
        MockDB.return_value = db
        resp = client.get("/api/referee/search?q=Smith")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1

    @patch("pipeline.referee_db.RefereeDB")
    def test_assignments(self, MockDB, client):
        db = self._mock_db()
        db.get_referee_assignments.return_value = [{"ms": "M1"}, {"ms": "M2"}]
        MockDB.return_value = db
        resp = client.get("/api/referee/Smith/assignments")
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

    @patch("pipeline.referee_db.RefereeDB")
    def test_top_referees(self, MockDB, client):
        db = self._mock_db()
        db.get_top_referees.return_value = [{"name": "A"}, {"name": "B"}]
        MockDB.return_value = db
        resp = client.get("/api/referee/top")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    @patch("pipeline.referee_db.RefereeDB")
    def test_decliners(self, MockDB, client):
        db = self._mock_db()
        db.get_chronic_decliners.return_value = []
        MockDB.return_value = db
        resp = client.get("/api/referee/decliners")
        assert resp.status_code == 200

    @patch("pipeline.referee_db.RefereeDB")
    def test_overdue(self, MockDB, client):
        db = self._mock_db()
        db.get_overdue_repeat_offenders.return_value = [{"name": "Late Larry"}]
        MockDB.return_value = db
        resp = client.get("/api/referee/overdue")
        assert resp.status_code == 200


class TestPipeline:
    def test_run_missing_params(self, client):
        resp = client.post("/api/pipeline/run", json={"journal": "sicon"})
        assert resp.status_code == 400

    @patch("scripts.dashboard_server.threading.Thread")
    def test_run_starts_thread(self, mock_thread, client):
        mock_thread.return_value = MagicMock()
        resp = client.post(
            "/api/pipeline/run",
            json={"journal": "sicon", "manuscript_id": "M123"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "started"

    def test_recommendation_not_found(self, client, tmp_path):
        rec_dir = tmp_path / "production" / "outputs" / "sicon" / "recommendations"
        rec_dir.mkdir(parents=True)
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path):
            resp = client.get("/api/pipeline/recommendations/sicon/M999")
        assert resp.status_code == 404

    def test_recommendation_found(self, client, tmp_path):
        rec_dir = tmp_path / "production" / "outputs" / "sicon" / "recommendations"
        rec_dir.mkdir(parents=True)
        rec = {"candidates": [{"name": "A"}]}
        (rec_dir / "rec_M123_20260101.json").write_text(json.dumps(rec))
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path):
            resp = client.get("/api/pipeline/recommendations/sicon/M123")
        assert resp.status_code == 200
        assert resp.get_json()["candidates"][0]["name"] == "A"


class TestManuscriptSearch:
    def test_query_too_short(self, client):
        resp = client.get("/api/manuscripts/search?q=M")
        assert resp.status_code == 400

    def test_search_finds_match(self, client, tmp_path):
        outputs = tmp_path / "production" / "outputs"
        sicon_dir = outputs / "sicon"
        sicon_dir.mkdir(parents=True)
        extraction = {
            "manuscripts": [
                {"manuscript_id": "M123", "title": "Test Paper", "status": "Under Review"}
            ]
        }
        (sicon_dir / "sicon_extraction_20260101.json").write_text(json.dumps(extraction))
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path):
            resp = client.get("/api/manuscripts/search?q=m123")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["manuscript_id"] == "M123"

    def test_search_no_match(self, client, tmp_path):
        outputs = tmp_path / "production" / "outputs"
        sicon_dir = outputs / "sicon"
        sicon_dir.mkdir(parents=True)
        extraction = {
            "manuscripts": [{"manuscript_id": "M123", "title": "Test", "status": "Under Review"}]
        }
        (sicon_dir / "sicon_extraction_20260101.json").write_text(json.dumps(extraction))
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path):
            resp = client.get("/api/manuscripts/search?q=zzz")
        assert resp.status_code == 200
        assert resp.get_json() == []


class TestEvents:
    @patch(
        "core.event_dispatcher.get_pending_events",
        return_value=[{"type": "NEW_MANUSCRIPT", "journal": "sicon"}],
    )
    def test_returns_events(self, mock_events, client):
        resp = client.get("/api/events")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["type"] == "NEW_MANUSCRIPT"


class TestRecordDecision:
    def test_missing_params(self, client):
        resp = client.post("/api/record-decision", json={})
        assert resp.status_code == 400

    def test_invalid_decision(self, client):
        resp = client.post(
            "/api/record-decision",
            json={"journal": "sicon", "manuscript_id": "M1", "decision": "maybe"},
        )
        assert resp.status_code == 400


class TestAuthorHistory:
    def test_short_name(self, client):
        resp = client.get("/api/author-history/X")
        assert resp.status_code == 400


class TestNotificationConfig:
    def test_get_default(self, client):
        with patch(
            "core.email_notifications._load_config",
            return_value={"ALL_REPORTS_IN": True, "NEW_MANUSCRIPT": True},
        ):
            resp = client.get("/api/notification-config")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)


class TestSendReminders:
    @patch("reporting.action_items.compute_action_items", return_value=[])
    def test_no_overdue(self, mock_items, client):
        resp = client.post("/api/send-reminders")
        assert resp.status_code == 200
        assert resp.get_json()["reminders_sent"] == 0


class TestRefereeNote:
    def test_get_empty(self, client):
        with patch("pipeline.referee_db.RefereeDB") as MockDB:
            MockDB.return_value.get_referee_note.return_value = None
            resp = client.get("/api/referee/nobody/note")
        assert resp.status_code == 200
        assert resp.get_json()["note"] == ""


class TestAnnualReport:
    def test_missing_dates(self, client):
        resp = client.post("/api/annual-report", json={})
        assert resp.status_code == 400


class TestSimilarity:
    def test_invalid_params(self, client):
        resp = client.get("/api/similarity/../../etc/passwd")
        assert resp.status_code in (400, 404)


class TestGetSimilarity:
    def test_no_extraction(self, client, tmp_path):
        outputs = tmp_path / "production" / "outputs" / "sicon"
        outputs.mkdir(parents=True)
        with patch("scripts.dashboard_server.PROJECT_DIR", tmp_path):
            resp = client.get("/api/similarity/sicon/M123")
        assert resp.status_code == 404
