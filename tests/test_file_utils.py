import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def outputs_dir(tmp_path):
    with patch("core.file_utils.OUTPUTS_DIR", tmp_path):
        yield tmp_path


@pytest.fixture
def journal_dir(outputs_dir):
    d = outputs_dir / "mf"
    d.mkdir()
    return d


class TestListExtractionFiles:
    def test_returns_sorted_reverse(self, journal_dir, outputs_dir):
        (journal_dir / "mf_20260101_100000.json").write_text("{}")
        (journal_dir / "mf_20260102_100000.json").write_text("{}")
        (journal_dir / "mf_20260103_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        files = list_extraction_files("mf")
        names = [f.name for f in files]
        assert names == [
            "mf_20260103_100000.json",
            "mf_20260102_100000.json",
            "mf_20260101_100000.json",
        ]

    def test_skips_baseline(self, journal_dir, outputs_dir):
        (journal_dir / "mf_BASELINE.json").write_text("{}")
        (journal_dir / "mf_20260101_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        files = list_extraction_files("mf")
        assert len(files) == 1
        assert "BASELINE" not in files[0].name

    def test_skips_debug(self, journal_dir, outputs_dir):
        (journal_dir / "debug_mf.json").write_text("{}")
        (journal_dir / "mf_20260101_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        files = list_extraction_files("mf")
        assert len(files) == 1

    def test_skips_rec_prefix(self, journal_dir, outputs_dir):
        (journal_dir / "rec_mf_candidates.json").write_text("{}")
        (journal_dir / "mf_20260101_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        files = list_extraction_files("mf")
        assert len(files) == 1

    def test_skips_ae_prefix(self, journal_dir, outputs_dir):
        (journal_dir / "ae_MS001_20260101.json").write_text("{}")
        (journal_dir / "mf_20260101_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        files = list_extraction_files("mf")
        assert len(files) == 1

    def test_skips_partial_and_recommendation(self, journal_dir, outputs_dir):
        (journal_dir / "partial_run.json").write_text("{}")
        (journal_dir / "recommendation_MS001.json").write_text("{}")
        (journal_dir / "mf_20260101_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        files = list_extraction_files("mf")
        assert len(files) == 1

    def test_missing_directory(self, outputs_dir):
        from core.file_utils import list_extraction_files

        assert list_extraction_files("nonexistent") == []

    def test_case_insensitive_journal(self, outputs_dir):
        d = outputs_dir / "mf"
        d.mkdir(exist_ok=True)
        (d / "mf_20260101_100000.json").write_text("{}")

        from core.file_utils import list_extraction_files

        assert len(list_extraction_files("MF")) == 1


class TestFindLatestOutput:
    def test_returns_latest(self, journal_dir, outputs_dir):
        (journal_dir / "mf_20260101_100000.json").write_text("{}")
        (journal_dir / "mf_20260102_100000.json").write_text("{}")

        from core.file_utils import find_latest_output

        result = find_latest_output("mf")
        assert result is not None
        assert result.name == "mf_20260102_100000.json"

    def test_returns_none_empty(self, outputs_dir):
        from core.file_utils import find_latest_output

        assert find_latest_output("mf") is None


class TestLoadLatestExtraction:
    def test_loads_json(self, journal_dir, outputs_dir):
        data = {"manuscripts": [{"manuscript_id": "MS-001"}]}
        (journal_dir / "mf_20260101_100000.json").write_text(json.dumps(data))

        from core.file_utils import load_latest_extraction

        result = load_latest_extraction("mf")
        assert result == data

    def test_returns_none_missing(self, outputs_dir):
        from core.file_utils import load_latest_extraction

        assert load_latest_extraction("mf") is None

    def test_returns_none_corrupt_json(self, journal_dir, outputs_dir):
        (journal_dir / "mf_20260101_100000.json").write_text("NOT VALID JSON {{{")

        from core.file_utils import load_latest_extraction

        assert load_latest_extraction("mf") is None
