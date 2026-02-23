import os
import tempfile

from core.cache_manager import CacheManager


class TestCacheManagerTestMode:
    def test_creates_temp_dir(self):
        cm = CacheManager(test_mode=True)
        assert cm.test_mode is True
        assert cm.cache_dir is not None
        assert "test_cache" in str(cm.cache_dir) or tempfile.gettempdir() in str(cm.cache_dir)
        cm.cleanup_test_cache()

    def test_isolation(self):
        cm1 = CacheManager(test_mode=True)
        cm2 = CacheManager(test_mode=True)
        assert str(cm1.cache_dir) != str(cm2.cache_dir)
        cm1.cleanup_test_cache()
        cm2.cleanup_test_cache()


class TestManuscriptRoundtrip:
    def test_update_then_get(self, cache):
        ms_data = {
            "id": "TEST-2025-001",
            "title": "Test Paper",
            "status": "Under Review",
            "authors": ["Smith, J."],
            "submission_date": "2025-01-15",
            "referees": [],
        }
        cache.update_manuscript(ms_data, "MOR")
        result = cache.get_manuscript("TEST-2025-001", "MOR")
        assert result is not None
        assert result.manuscript_id == "TEST-2025-001"
        assert result.title == "Test Paper"

    def test_missing_manuscript_returns_none(self, cache):
        result = cache.get_manuscript("NONEXISTENT-001", "MOR")
        assert result is None


class TestRefereeRoundtrip:
    def test_update_then_get(self, cache):
        ref_data = {
            "email": "referee@example.com",
            "name": "Jane Doe",
            "institution": "MIT",
        }
        cache.update_referee(ref_data, "MOR")
        result = cache.get_referee("referee@example.com")
        assert result is not None
        assert result.name == "Jane Doe"
        assert result.institution == "MIT"

    def test_missing_referee_returns_none(self, cache):
        result = cache.get_referee("nonexistent@example.com")
        assert result is None
