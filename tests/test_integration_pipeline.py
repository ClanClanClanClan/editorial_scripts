#!/usr/bin/env python3
"""Integration tests: end-to-end pipeline flows with synthetic data."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.integration
class TestPipelineIntegration:
    def test_full_pipeline_produces_report(self, tmp_path):
        extraction = {
            "schema_version": "1.0.0",
            "extraction_timestamp": "2026-03-01T10:00:00",
            "journal": "sicon",
            "manuscripts": [
                {
                    "manuscript_id": "TEST-001",
                    "title": "Optimal Control of Stochastic Differential Equations",
                    "abstract": "We study optimal stochastic control problems with mean-field interaction under partial observation. Using the stochastic maximum principle we derive necessary and sufficient conditions.",
                    "keywords": [
                        "optimal control",
                        "stochastic differential equation",
                        "mean-field",
                    ],
                    "status": "Waiting for Potential Referee Assignment",
                    "category": "",
                    "authors": [
                        {
                            "name": "Test Author",
                            "institution": "ETH Zurich",
                            "email": "test@ethz.ch",
                            "web_profile": {"h_index": 15},
                        }
                    ],
                    "referees": [],
                    "editors": [{"name": "Dylan Possamai"}],
                    "documents": [],
                    "audit_trail": [],
                    "platform_specific": {
                        "metadata": {"current_stage": "Waiting for Potential Referee Assignment"}
                    },
                }
            ],
        }

        sicon_dir = tmp_path / "sicon"
        sicon_dir.mkdir()
        (sicon_dir / "sicon_extraction_20260301_100000.json").write_text(json.dumps(extraction))

        mock_enricher = MagicMock()
        mock_enricher.name_match = MagicMock(return_value=False)
        mock_enricher.institution_match = MagicMock(return_value=False)
        mock_enricher.enrich = MagicMock(return_value={})

        with (
            patch("pipeline.referee_pipeline.OUTPUTS_DIR", tmp_path),
            patch("core.file_utils.OUTPUTS_DIR", tmp_path),
        ):
            from pipeline.referee_pipeline import RefereePipeline

            pipe = RefereePipeline.__new__(RefereePipeline)
            pipe.use_llm = False
            pipe.max_candidates = 5
            pipe.session = MagicMock()
            pipe.enricher = mock_enricher
            pipe.expertise_index = None
            pipe.response_predictor = None
            pipe.outcome_predictor = None

            report = pipe.run_single("sicon", "TEST-001")

        assert report is not None
        assert report["manuscript_id"] == "TEST-001"
        assert "desk_rejection" in report
        assert report["desk_rejection"]["should_desk_reject"] is False
        assert "referee_candidates" in report
        assert isinstance(report["referee_candidates"], list)


@pytest.mark.integration
class TestCrossJournalIntegration:
    def test_report_with_real_output_structure(self, tmp_path):
        for journal in ["mf", "sicon"]:
            d = tmp_path / journal
            d.mkdir()
            data = {
                "extraction_timestamp": "2026-03-01T10:00:00",
                "schema_version": "1.0.0",
                "manuscripts": [
                    {
                        "referees": [{"name": f"Ref-{journal}"}],
                        "authors": [{"name": f"Auth-{journal}"}],
                        "timeline_analytics": {},
                    }
                ],
            }
            (d / f"{journal}_extraction_20260301_100000.json").write_text(json.dumps(data))

        with patch("reporting.cross_journal_report.OUTPUTS_DIR", tmp_path):
            from reporting.cross_journal_report import compute_journal_stats, load_journal_data

            for journal in ["mf", "sicon"]:
                data = load_journal_data(journal)
                assert data is not None
                stats = compute_journal_stats(journal, data)
                assert stats["manuscripts"] == 1
                assert stats["referees"] == 1
