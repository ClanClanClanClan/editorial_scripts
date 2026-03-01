import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from pipeline.desk_rejection import assess_desk_rejection
from pipeline.embeddings import EmbeddingEngine
from pipeline.models.expertise_index import ExpertiseIndex, _deduplicate
from pipeline.models.outcome_predictor import ManuscriptOutcomePredictor, _classify_outcome
from pipeline.models.response_predictor import (
    RefereeResponsePredictor,
    _extract_turnaround_days,
)
from pipeline.report_quality import (
    _constructiveness,
    _recommendation_consistency,
    _thoroughness,
    _timeliness,
    assess_report_quality,
)
from pipeline.training import ModelTrainer


class TestEmbeddingEngine:
    @pytest.fixture(scope="class")
    def engine(self):
        return EmbeddingEngine()

    def test_embed_returns_vector(self, engine):
        vec = engine.embed("stochastic optimal control")
        assert isinstance(vec, np.ndarray)
        assert len(vec) > 0

    def test_embed_empty_returns_zeros(self, engine):
        vec = engine.embed("")
        assert np.allclose(vec, 0)

    def test_similarity_same_text(self, engine):
        sim = engine.similarity("optimal control theory", "optimal control theory")
        assert sim > 0.9

    def test_similarity_related_higher_than_unrelated(self, engine):
        sim_related = engine.similarity(
            "stochastic differential equations",
            "backward stochastic differential equations",
        )
        sim_unrelated = engine.similarity(
            "stochastic differential equations",
            "marine biology of tropical fish",
        )
        assert sim_related > sim_unrelated

    def test_batch_embed(self, engine):
        vecs = engine.batch_embed(["text one", "text two", "text three"])
        assert vecs.shape[0] == 3
        assert vecs.shape[1] > 0

    def test_build_and_search_index(self, engine):
        texts = [
            "stochastic control and optimization",
            "marine biology and ecology",
            "Hamilton-Jacobi-Bellman equations",
            "deep learning for image classification",
            "mean-field games and stochastic analysis",
        ]
        index = engine.build_index(texts)
        if index is None:
            pytest.skip("FAISS not installed")
        results = engine.search_index("optimal control of SDEs", index, k=3)
        assert len(results) > 0
        top_idx = results[0][0]
        assert top_idx in (0, 2, 4)

    def test_save_load_index(self, engine, tmp_path):
        texts = ["stochastic control", "optimal stopping", "variational inequality"]
        index = engine.build_index(texts)
        if index is None:
            pytest.skip("FAISS not installed")
        path = tmp_path / "test_index.faiss"
        engine.save_index(index, path)
        loaded = engine.load_index(path)
        assert loaded is not None
        results = engine.search_index("control theory", loaded, k=2)
        assert len(results) > 0


class TestExpertiseIndex:
    def test_deduplicate_by_email(self):
        refs = [
            {"name": "John Smith", "email": "john@mit.edu", "h_index": 10},
            {"name": "J. Smith", "email": "john@mit.edu", "h_index": 15},
        ]
        deduped = _deduplicate(refs)
        assert len(deduped) == 1
        assert deduped[0]["h_index"] == 15

    def test_deduplicate_by_name(self):
        refs = [
            {"name": "John Smith", "email": "", "h_index": 5},
            {"name": "john smith", "email": "", "h_index": 8},
        ]
        deduped = _deduplicate(refs)
        assert len(deduped) == 1

    def test_build_with_no_data(self):
        idx = ExpertiseIndex()
        with patch.object(Path, "iterdir", return_value=[]):
            n = idx.build(journals=[])
        assert n == 0

    def test_search_empty_index(self):
        idx = ExpertiseIndex()
        results = idx.search({"title": "test", "abstract": "test"})
        assert results == []


class TestReportQuality:
    def test_constructiveness_positive(self):
        text = "I suggest the authors consider revising section 3. They could improve the clarity and expand the discussion."
        score = _constructiveness(text)
        assert score > 0.5

    def test_constructiveness_negative(self):
        text = "This paper is wrong, poor quality, and the results are flawed."
        score = _constructiveness(text)
        assert score < 0.5

    def test_recommendation_consistency(self):
        score = _recommendation_consistency(
            "This is an excellent, well-written paper with strong results.",
            "Accept",
        )
        assert score > 0.5

    def test_thoroughness_long_text(self):
        text = (
            "I suggest the authors revise section 3. The strengths of the paper include the novel approach. However, there is a weakness in the proof. Minor typos on page 5. "
            + "word " * 300
        )
        score = _thoroughness(text, len(text.split()))
        assert score > 0.5

    def test_thoroughness_empty(self):
        assert _thoroughness("", 0) == 0.0

    def test_timeliness_fast_review(self):
        ref = {"dates": {"invited": "2025-01-01", "returned": "2025-01-14"}}
        score = _timeliness(ref)
        assert score > 0.4

    def test_timeliness_slow_review(self):
        ref = {"dates": {"invited": "2025-01-01", "returned": "2025-03-01"}}
        score = _timeliness(ref)
        assert score < 0.1

    def test_timeliness_legacy_fields(self):
        ref = {"date_invited": "2025-01-01", "date_completed": "2025-01-14"}
        score = _timeliness(ref)
        assert score > 0.4

    def test_timeliness_no_dates(self):
        assert _timeliness({}) == 0.5

    def test_assess_report_quality_no_reports(self):
        ms = {"referees": []}
        result = assess_report_quality(ms)
        assert result["n_reports"] == 0
        assert result["overall_quality"] == 0.0

    def test_assess_report_quality_with_reports(self):
        ms = {
            "referees": [
                {
                    "name": "Reviewer 1",
                    "recommendation": "Accept",
                    "reports": [
                        {
                            "comments_to_author": "This is an excellent paper. I suggest minor revisions to equation (3) on page 5. The theorem in section 2 is novel and the proof is correct. Consider expanding the discussion in section 4.",
                            "recommendation": "Accept",
                        }
                    ],
                },
                {
                    "name": "Reviewer 2",
                    "recommendation": "Minor Revision",
                    "reports": [
                        {
                            "comments_to_author": "The paper addresses an interesting problem. However, the proof of Lemma 1 contains an error on page 3. Please revise Table 2 and clarify the assumptions.",
                            "recommendation": "Minor Revision",
                        }
                    ],
                },
            ],
            "abstract": "We study optimal control of stochastic systems.",
        }
        result = assess_report_quality(ms)
        assert result["n_reports"] == 2
        assert result["overall_quality"] > 0
        assert "consensus" in result
        assert result["consensus"]["n_reviewers"] == 2

    def test_assess_report_quality_recommendation_only(self):
        ms = {
            "referees": [
                {"name": "R1", "recommendation": "Accept", "reports": []},
            ]
        }
        result = assess_report_quality(ms)
        assert result["n_reports"] == 1
        assert result["reports"][0]["word_count"] == 0


class TestOutcomePredictor:
    def test_classify_outcome_accept(self):
        assert _classify_outcome({"status": "Completed Accept"}) == 1
        assert _classify_outcome({"status": "accepted"}) == 1

    def test_classify_outcome_reject(self):
        assert _classify_outcome({"status": "Completed Reject"}) == 0
        assert _classify_outcome({"status": "Desk Reject"}) == 0

    def test_classify_outcome_unknown(self):
        assert _classify_outcome({"status": "Under Review"}) is None
        assert _classify_outcome({"status": ""}) is None

    def test_predict_without_model(self):
        predictor = ManuscriptOutcomePredictor()
        result = predictor.predict({"abstract": "test"})
        assert result == 0.5

    def test_train_insufficient_data(self):
        predictor = ManuscriptOutcomePredictor()
        with patch.object(
            predictor,
            "_build_training_data",
            return_value=(np.array([]).reshape(0, 10), np.array([])),
        ):
            result = predictor.train()
        assert result["status"] == "insufficient_data"

    def test_quality_gate_rejects_weak_model(self):
        predictor = ManuscriptOutcomePredictor()
        n = 20
        rng = np.random.RandomState(99)
        X = rng.rand(n, 10)
        y = rng.randint(0, 2, n)
        with patch.object(predictor, "_build_training_data", return_value=(X, y)):
            result = predictor.train()
        assert result["status"] == "model_not_useful"
        assert predictor.model is None

    def test_train_and_predict(self):
        predictor = ManuscriptOutcomePredictor()
        n = 20
        rng = np.random.RandomState(42)
        X = rng.rand(n, 10)
        y = (X[:, 0] > 0.5).astype(int)
        with patch.object(predictor, "_build_training_data", return_value=(X, y)):
            result = predictor.train()
        assert result["status"] == "trained"
        assert result["n_samples"] == n
        assert 0.0 <= result["cv_accuracy"] <= 1.0

        ms = {"abstract": "test " * 50, "keywords": ["control"], "authors": []}
        prob = predictor.predict(ms)
        assert 0.0 <= prob <= 1.0

    def test_save_load(self, tmp_path):
        predictor = ManuscriptOutcomePredictor()
        n = 10
        rng = np.random.RandomState(42)
        X = rng.rand(n, 10)
        y = (X[:, 0] > 0.5).astype(int)
        with patch.object(predictor, "_build_training_data", return_value=(X, y)):
            predictor.train()

        predictor.save(tmp_path)
        assert (tmp_path / "outcome_predictor.joblib").exists()

        loaded = ManuscriptOutcomePredictor()
        assert loaded.load(tmp_path) is True
        assert loaded.model is not None


class TestResponsePredictor:
    def test_predict_without_model(self):
        predictor = RefereeResponsePredictor()
        result = predictor.predict({"h_index": 0.5})
        assert result == 0.5

    def test_train_insufficient_data(self):
        predictor = RefereeResponsePredictor()
        with patch.object(
            predictor,
            "_build_training_data",
            return_value=(
                np.array([]).reshape(0, 8),
                np.array([]),
                np.array([]),
            ),
        ):
            result = predictor.train()
        assert result["status"] == "insufficient_data"

    def test_quality_gate_rejects_weak_model(self):
        predictor = RefereeResponsePredictor()
        n = 30
        rng = np.random.RandomState(99)
        X = rng.rand(n, 8)
        y_agree = rng.randint(0, 2, n)
        y_complete = rng.randint(0, 2, n)
        with patch.object(predictor, "_build_training_data", return_value=(X, y_agree, y_complete)):
            result = predictor.train()
        assert result["status"] == "model_not_useful"
        assert predictor.model is None

    def test_train_and_predict(self):
        predictor = RefereeResponsePredictor()
        n = 60
        rng = np.random.RandomState(42)
        X = np.vstack([rng.rand(30, 8) * 0.3, rng.rand(30, 8) * 0.3 + 0.7])
        y_agree = np.array([0] * 30 + [1] * 30)
        y_complete = (X[:, 1] > 0.5).astype(int)
        with patch.object(predictor, "_build_training_data", return_value=(X, y_agree, y_complete)):
            result = predictor.train()
        assert result["status"] == "trained"
        assert result["n_samples"] == n

        features = {
            "h_index": 0.5,
            "acceptance_rate": 0.8,
            "n_past_reviews": 0.3,
            "journal_match": 1.0,
            "expertise_similarity": 0.7,
            "avg_turnaround": 0.4,
            "active_load": 0.2,
            "institution_distance": 1.0,
        }
        prob = predictor.predict(features)
        assert 0.0 <= prob <= 1.0

    def test_predict_completion(self):
        predictor = RefereeResponsePredictor()
        n = 30
        rng = np.random.RandomState(42)
        X = rng.rand(n, 8)
        y_agree = (X[:, 0] > 0.2).astype(int)
        y_complete = (X[:, 1] > 0.3).astype(int)
        with patch.object(predictor, "_build_training_data", return_value=(X, y_agree, y_complete)):
            predictor.train()
        prob = predictor.predict_completion({"h_index": 0.5})
        assert 0.0 <= prob <= 1.0

    def test_predict_for_candidate(self):
        predictor = RefereeResponsePredictor()
        n = 20
        rng = np.random.RandomState(42)
        X = rng.rand(n, 8)
        y_agree = (X[:, 0] > 0.4).astype(int)
        y_complete = (X[:, 1] > 0.3).astype(int)
        with patch.object(predictor, "_build_training_data", return_value=(X, y_agree, y_complete)):
            predictor.train()

        candidate = {
            "web_profile": {"h_index": 15},
            "_referee_stats": {
                "acceptance_rate": 0.7,
                "n_reviews": 5,
                "journals": {"sicon": 2},
                "avg_turnaround_days": 20,
                "active_reviews": 1,
            },
        }
        ms = {
            "title": "test",
            "abstract": "test",
            "keywords": ["control"],
            "authors": [{"institution": "MIT"}],
        }
        prob = predictor.predict_for_candidate(candidate, ms, "sicon")
        assert 0.0 <= prob <= 1.0

    def test_save_load(self, tmp_path):
        predictor = RefereeResponsePredictor()
        rng = np.random.RandomState(42)
        X = np.vstack([rng.rand(30, 8) * 0.3, rng.rand(30, 8) * 0.3 + 0.7])
        y_agree = np.array([0] * 30 + [1] * 30)
        y_complete = (X[:, 1] > 0.5).astype(int)
        with patch.object(predictor, "_build_training_data", return_value=(X, y_agree, y_complete)):
            predictor.train()

        predictor.save(tmp_path)
        assert (tmp_path / "response_predictor.joblib").exists()

        loaded = RefereeResponsePredictor()
        assert loaded.load(tmp_path) is True
        assert loaded.model is not None


class TestModelTrainer:
    def test_record_outcome(self, tmp_path):
        trainer = ModelTrainer()
        with patch("pipeline.training.FEEDBACK_DIR", tmp_path):
            trainer.record_outcome("sicon", "M12345", "accept")
            feedback_file = tmp_path / "sicon_outcomes.jsonl"
            assert feedback_file.exists()
            line = feedback_file.read_text().strip()
            record = json.loads(line)
            assert record["journal"] == "sicon"
            assert record["manuscript_id"] == "M12345"
            assert record["decision"] == "accept"

    def test_get_feedback_stats(self, tmp_path):
        trainer = ModelTrainer()
        feedback_file = tmp_path / "sicon_outcomes.jsonl"
        feedback_file.write_text(
            '{"journal":"sicon","manuscript_id":"M1","decision":"accept"}\n'
            '{"journal":"sicon","manuscript_id":"M2","decision":"reject"}\n'
            '{"journal":"sicon","manuscript_id":"M3","decision":"accept"}\n'
        )
        with patch("pipeline.training.FEEDBACK_DIR", tmp_path):
            stats = trainer.get_feedback_stats()
        assert "sicon" in stats
        assert stats["sicon"]["total"] == 3
        assert stats["sicon"]["decisions"]["accept"] == 2
        assert stats["sicon"]["decisions"]["reject"] == 1


class TestDeskRejectionWithModel:
    def test_with_outcome_predictor(self):
        from unittest.mock import MagicMock

        predictor = MagicMock()
        predictor.predict.return_value = 0.8

        ms = {
            "abstract": "We study optimal control of stochastic systems with applications.",
            "keywords": ["optimal control", "stochastic"],
            "authors": [{"name": "Smith", "web_profile": {"h_index": 10}}],
            "title": "Optimal Control of SDEs",
        }
        result = assess_desk_rejection(ms, "SICON", outcome_predictor=predictor)
        signals = [s["signal_name"] for s in result["signals"]]
        assert "model_prediction" in signals
        assert "model" in result["method"]

    def test_without_outcome_predictor(self):
        ms = {
            "abstract": "We study optimal control of stochastic systems with applications.",
            "keywords": ["optimal control", "stochastic"],
            "authors": [],
            "title": "Optimal Control of SDEs",
        }
        result = assess_desk_rejection(ms, "SICON")
        assert result["method"] == "heuristic"


class TestRefereeFinderWithModels:
    def test_relevance_with_semantic_similarity(self):
        from pipeline.referee_finder import _compute_relevance

        c_semantic = {
            "research_topics": [],
            "source": "expertise_index",
            "relevant_papers": [],
            "semantic_similarity": 0.8,
        }
        c_no_semantic = {
            "research_topics": ["stochastic control"],
            "source": "openalex_search",
            "relevant_papers": [],
        }
        s1 = _compute_relevance(c_semantic, ["stochastic control"], "Test", "")
        s2 = _compute_relevance(c_no_semantic, ["stochastic control"], "Test", "")
        assert s1 > 0
        assert s2 > 0

    def test_relevance_with_response_predictor(self):
        from unittest.mock import MagicMock

        from pipeline.referee_finder import _compute_relevance

        predictor = MagicMock()
        predictor.predict_for_candidate.return_value = 0.9

        c = {
            "research_topics": ["control"],
            "source": "openalex_search",
            "relevant_papers": [],
            "h_index": 10,
        }
        ms = {"title": "test", "abstract": "test", "keywords": ["control"]}
        s_with = _compute_relevance(c, ["control"], "Test", "", predictor, "sicon", ms)
        s_without = _compute_relevance(c, ["control"], "Test", "")
        assert s_with > s_without


class TestTurnaroundDays:
    def test_nested_dates(self):
        ref = {"dates": {"invited": "2025-01-01", "returned": "2025-01-21"}}
        assert _extract_turnaround_days(ref) == 20

    def test_legacy_fields(self):
        ref = {"date_invited": "2025-01-01", "date_completed": "2025-01-15"}
        assert _extract_turnaround_days(ref) == 14

    def test_no_dates(self):
        assert _extract_turnaround_days({}) is None

    def test_null_returned(self):
        ref = {"dates": {"invited": "2025-01-01", "returned": None}}
        assert _extract_turnaround_days(ref) is None

    def test_various_formats(self):
        ref = {"dates": {"invited": "01 Jan 2025", "returned": "15 Jan 2025"}}
        assert _extract_turnaround_days(ref) == 14


class TestResponsePredictorDedup:
    def test_dedup_across_files(self, tmp_path):
        journal_dir = tmp_path / "testj"
        journal_dir.mkdir()
        ms = {
            "manuscript_id": "M1",
            "keywords": ["control"],
            "referees": [
                {
                    "name": "Smith",
                    "email": "smith@mit.edu",
                    "status": "Agreed",
                    "web_profile": {"h_index": 10, "research_topics": ["control"]},
                }
            ],
        }
        file1 = journal_dir / "testj_extraction_20250101.json"
        file1.write_text(json.dumps({"manuscripts": [ms]}))
        import time

        time.sleep(0.05)
        file2 = journal_dir / "testj_extraction_20250201.json"
        file2.write_text(json.dumps({"manuscripts": [ms]}))

        predictor = RefereeResponsePredictor()
        with patch("pipeline.models.response_predictor.OUTPUTS_DIR", tmp_path):
            X, y_agree, y_complete = predictor._build_training_data(["testj"])

        assert len(X) == 1
