import pytest
from core.cache_manager import CacheManager


@pytest.fixture
def cache():
    cm = CacheManager(test_mode=True)
    yield cm
    cm.cleanup_test_cache()
