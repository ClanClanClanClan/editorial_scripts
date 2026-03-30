import json

import pytest
from core.cache_manager import CacheManager


@pytest.fixture
def cache():
    cm = CacheManager(test_mode=True)
    yield cm
    cm.cleanup_test_cache()


@pytest.fixture
def sample_manuscript():
    return {
        "manuscript_id": "TEST-001",
        "title": "A Test Paper on Stochastic Control",
        "abstract": "We study optimal control under uncertainty.",
        "status": "Under Review",
        "keywords": ["stochastic control", "optimization"],
        "authors": [{"name": "Jane Doe", "email": "jane@example.com", "institution": "MIT"}],
        "referees": [
            {
                "name": "Alice Smith",
                "email": "alice@test.com",
                "status": "Report Submitted",
                "recommendation": "Accept",
                "dates": {
                    "invited": "2025-01-01",
                    "agreed": "2025-01-05",
                    "due": "2025-03-01",
                    "returned": "2025-02-20",
                },
            },
            {
                "name": "Bob Jones",
                "email": "bob@test.com",
                "status": "Report Submitted",
                "recommendation": "Minor Revision",
                "dates": {
                    "invited": "2025-01-01",
                    "agreed": "2025-01-03",
                    "due": "2025-03-01",
                    "returned": "2025-02-25",
                },
            },
        ],
    }


@pytest.fixture
def sample_extraction(sample_manuscript):
    return {
        "extraction_timestamp": "2026-03-25T10:00:00",
        "journal": "sicon",
        "journal_name": "SICON",
        "extractor_version": "1.0",
        "platform": "SIAM",
        "manuscripts": [sample_manuscript],
        "schema_version": "1.0",
        "summary": {"total_manuscripts": 1},
        "errors": [],
    }


@pytest.fixture
def temp_outputs(tmp_path, sample_extraction):
    sicon_dir = tmp_path / "sicon"
    sicon_dir.mkdir()
    extraction_file = sicon_dir / "sicon_extraction_20260325_100000.json"
    extraction_file.write_text(json.dumps(sample_extraction))
    return tmp_path
