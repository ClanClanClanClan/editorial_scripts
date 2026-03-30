"""Tests for decision letter drafting."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pipeline.decision_letters import (
    VALID_DECISIONS,
    _build_author_prompt,
    _build_eic_prompt,
    _save_decision,
    draft_letters,
)


@pytest.fixture
def assembled_data():
    return {
        "journal": "SICON",
        "manuscript_id": "M181987",
        "title": "Optimal Control Under Uncertainty",
        "revision_round": 1,
        "reports": [
            {
                "name": "Referee 1",
                "recommendation": "Minor Revision",
                "quality_score": 4.5,
                "text": "The paper addresses an important problem in stochastic control.",
                "scores": {"originality": 8, "rigor": 7},
            },
            {
                "name": "Referee 2",
                "recommendation": "Accept",
                "quality_score": 3.8,
                "text": "Well-written paper with solid theoretical foundations.",
                "scores": {"originality": 7, "rigor": 8},
            },
        ],
        "consensus": {"label": "Favorable"},
    }


class TestDraftLetters:
    @patch("pipeline.decision_letters._call_claude")
    @patch("pipeline.decision_letters.assemble")
    @patch("pipeline.decision_letters._save_decision")
    def test_returns_both_letters_on_success(
        self, mock_save, mock_assemble, mock_claude, assembled_data
    ):
        mock_assemble.return_value = assembled_data
        mock_claude.return_value = "Dear Editor, I recommend..."
        mock_save.return_value = "/tmp/fake.json"

        result = draft_letters("sicon", "M181987", "Minor Revision")
        assert "eic_letter" in result
        assert "author_letter" in result
        assert result["eic_letter"] == "Dear Editor, I recommend..."
        assert result["metadata"]["decision"] == "Minor Revision"
        assert mock_claude.call_count == 2

    @patch("pipeline.decision_letters._call_claude")
    @patch("pipeline.decision_letters.assemble")
    @patch("pipeline.decision_letters._save_decision")
    def test_reject_decision_has_different_content(
        self, mock_save, mock_assemble, mock_claude, assembled_data
    ):
        mock_assemble.return_value = assembled_data
        mock_claude.return_value = "Dear Editor, the paper should be rejected..."
        mock_save.return_value = "/tmp/fake.json"

        result = draft_letters("sicon", "M181987", "Reject")
        assert result["metadata"]["decision"] == "Reject"
        assert mock_claude.call_count == 2

    @patch("pipeline.decision_letters.assemble")
    def test_invalid_decision_raises(self, mock_assemble, assembled_data):
        mock_assemble.return_value = assembled_data
        with pytest.raises(ValueError, match="Invalid decision"):
            draft_letters("sicon", "M181987", "Pending")

    @patch("pipeline.decision_letters._clipboard_fallback", return_value="[Prompt copied]")
    @patch("pipeline.decision_letters.assemble")
    @patch("pipeline.decision_letters._save_decision")
    def test_clipboard_fallback(self, mock_save, mock_assemble, mock_clip, assembled_data):
        mock_assemble.return_value = assembled_data
        mock_save.return_value = "/tmp/fake.json"

        result = draft_letters("sicon", "M181987", "Accept", provider="clipboard")
        assert "[Prompt copied]" in result["eic_letter"]
        assert mock_clip.call_count == 2


class TestSaveDecision:
    def test_creates_json_and_md_files(self, tmp_path):
        letters = {
            "eic_letter": "Dear EIC, ...",
            "author_letter": "Dear Authors, ...",
            "metadata": {
                "journal": "SICON",
                "manuscript_id": "M181987",
                "title": "Test Paper",
                "decision": "Accept",
                "notes": "",
                "provider": "claude",
                "referee_count": 2,
                "revision_round": 0,
                "generated_at": "2026-03-25T10:00:00",
            },
        }
        with patch("pipeline.decision_letters.OUTPUTS_DIR", tmp_path):
            path = _save_decision("sicon", "M181987", "Accept", letters)

        assert path.exists()
        saved = json.loads(path.read_text())
        assert saved["metadata"]["decision"] == "Accept"

        md_files = list((tmp_path / "sicon" / "decisions").glob("*.md"))
        assert len(md_files) == 1


class TestBuildPrompts:
    def test_eic_prompt_includes_manuscript_data(self, assembled_data):
        system, user = _build_eic_prompt(assembled_data, "Minor Revision", "")
        assert "SICON" in system
        assert "M181987" in user
        assert "Minor Revision" in user
        assert "Referee 1" in user

    def test_author_prompt_includes_revision_points(self, assembled_data):
        system, user = _build_author_prompt(
            assembled_data, "Major Revision", "Please address all comments"
        )
        assert "Major Revision" in user
        assert "major revision is required" in system.lower() or "major revision" in user.lower()
        assert "Please address all comments" in user
