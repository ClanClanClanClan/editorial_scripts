"""Tests for manuscript similarity detection."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pipeline.manuscript_similarity import ManuscriptIndex, find_similar_manuscripts


class FakeEngine:
    def __init__(self):
        self._texts = []

    def build_index(self, texts):
        self._texts = list(texts)
        return {"texts": self._texts}

    def search_index(self, query, index, k=5):
        results = []
        for i, text in enumerate(index["texts"]):
            overlap = len(set(query.lower().split()) & set(text.lower().split()))
            results.append((i, overlap / max(len(query.split()), 1)))
        results.sort(key=lambda x: -x[1])
        return results[:k]

    def save_index(self, index, path):
        pass

    def load_index(self, path):
        return None


@pytest.fixture
def fake_engine():
    return FakeEngine()


@pytest.fixture
def extraction_dir(tmp_path):
    sicon_dir = tmp_path / "sicon"
    sicon_dir.mkdir()
    data = {
        "manuscripts": [
            {
                "manuscript_id": "M100",
                "title": "Stochastic Control of Diffusion Processes",
                "abstract": "We study optimal stochastic control problems.",
                "status": "Under Review",
                "keywords": ["stochastic control"],
            },
            {
                "manuscript_id": "M200",
                "title": "Mean Field Games and Applications",
                "abstract": "Mean field game theory for large populations.",
                "status": "Under Review",
                "keywords": ["mean field games"],
            },
        ]
    }
    (sicon_dir / "sicon_extraction_20260301.json").write_text(json.dumps(data))
    return tmp_path


class TestManuscriptIndexBuild:
    @patch(
        "pipeline.manuscript_similarity.get_engine" if False else "pipeline.embeddings.get_engine"
    )
    def test_indexes_manuscripts(self, mock_get_engine, fake_engine, extraction_dir):
        mock_get_engine.return_value = fake_engine
        with patch("pipeline.manuscript_similarity.OUTPUTS_DIR", extraction_dir):
            idx = ManuscriptIndex()
            count = idx.build(journals=["sicon"])
        assert count == 2
        assert len(idx.manuscripts) == 2


class TestManuscriptIndexSearch:
    @patch("pipeline.embeddings.get_engine")
    def test_finds_similar_title(self, mock_get_engine, fake_engine, extraction_dir):
        mock_get_engine.return_value = fake_engine
        with patch("pipeline.manuscript_similarity.OUTPUTS_DIR", extraction_dir):
            idx = ManuscriptIndex()
            idx.build(journals=["sicon"])
            results = idx.search(
                "Stochastic Optimal Control", "We study control problems.", top_k=5
            )
        assert len(results) >= 1
        ms_ids = [r["manuscript_id"] for r in results]
        if "M100" in ms_ids and "M200" in ms_ids:
            assert ms_ids.index("M100") < ms_ids.index("M200")

    @patch("pipeline.embeddings.get_engine")
    def test_excludes_exact_match(self, mock_get_engine, fake_engine, extraction_dir):
        mock_get_engine.return_value = fake_engine
        with patch("pipeline.manuscript_similarity.OUTPUTS_DIR", extraction_dir):
            idx = ManuscriptIndex()
            idx.build(journals=["sicon"])
            results = idx.search(
                "Stochastic Control of Diffusion Processes",
                "We study optimal stochastic control problems.",
                top_k=5,
            )
        titles = [r["title"] for r in results]
        assert "Stochastic Control of Diffusion Processes" not in titles


class TestManuscriptIndexEmpty:
    @patch("pipeline.embeddings.get_engine")
    def test_handles_empty_journal_data(self, mock_get_engine, fake_engine, tmp_path):
        mock_get_engine.return_value = fake_engine
        empty_dir = tmp_path / "sicon"
        empty_dir.mkdir()
        (empty_dir / "sicon_extraction_20260301.json").write_text(json.dumps({"manuscripts": []}))
        with patch("pipeline.manuscript_similarity.OUTPUTS_DIR", tmp_path):
            idx = ManuscriptIndex()
            count = idx.build(journals=["sicon"])
        assert count == 0
        assert idx.search("anything", "anything") == []


class TestFindSimilarManuscripts:
    @patch("pipeline.embeddings.get_engine")
    def test_convenience_function(self, mock_get_engine, fake_engine, extraction_dir):
        mock_get_engine.return_value = fake_engine
        with (
            patch("pipeline.manuscript_similarity.OUTPUTS_DIR", extraction_dir),
            patch("pipeline.manuscript_similarity.MODELS_DIR", extraction_dir / "models"),
        ):
            results = find_similar_manuscripts("Stochastic Control", "We study control.")
        assert isinstance(results, list)
