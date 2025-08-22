#!/usr/bin/env python3
"""
TEST CACHE ISOLATION HELPER
============================

Utilities to ensure tests don't pollute production cache.
"""

import os
import tempfile
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# Import only when needed to avoid circular imports


class TestCacheContext:
    """Context manager for isolated test caching."""
    
    def __init__(self, cleanup_on_exit: bool = True):
        self.cleanup_on_exit = cleanup_on_exit
        self.temp_dir: Optional[Path] = None
        self.cache_manager = None
        self.multi_cache = None
    
    def __enter__(self):
        """Enter test context with isolated cache."""
        # Force test mode
        os.environ['TESTING'] = '1'
        
        # Create temporary directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix="editorial_test_"))
        
        # Initialize isolated caches (import here to avoid circular imports)
        from .cache_manager import CacheManager
        from .multi_layer_cache import MultiLayerCache
        
        # Create cache manager first, then pass its directory to multi-layer cache
        self.cache_manager = CacheManager(cache_dir=self.temp_dir, test_mode=True)
        # Use the same directory to avoid creating multiple temp dirs
        self.multi_cache = MultiLayerCache(cache_dir=self.cache_manager.cache_dir, test_mode=True)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit test context and cleanup if requested."""
        if self.cleanup_on_exit:
            self.cleanup()
        
        # Remove test environment variable
        if 'TESTING' in os.environ:
            del os.environ['TESTING']
    
    def cleanup(self):
        """Clean up all test cache data."""
        if self.cache_manager:
            self.cache_manager.cleanup_test_cache()
        if self.multi_cache:
            self.multi_cache.cleanup_test_cache()


@contextmanager
def isolated_cache(cleanup=True):
    """
    Context manager for isolated cache testing.
    
    Usage:
        with isolated_cache() as test_ctx:
            cache = test_ctx.cache_manager
            # ... run tests ...
            # Cache automatically cleaned up on exit
    """
    with TestCacheContext(cleanup_on_exit=cleanup) as ctx:
        yield ctx


class TestExtractorMixin:
    """Test-safe extractor mixin that auto-enables test mode."""
    
    def init_enhanced_cache(self, journal_name: str, test_mode: bool = True):
        """Initialize cache in test mode by default."""
        from .multi_layer_cache import EnhancedExtractorCacheMixin
        
        # Dynamically inherit behavior to avoid circular imports
        if not hasattr(self, '_cache_mixin'):
            self._cache_mixin = EnhancedExtractorCacheMixin()
        
        self._cache_mixin.init_enhanced_cache(journal_name, test_mode=test_mode)
        
        # Copy attributes to self
        for attr in ['multi_cache', 'journal_name', 'run_id', 'extraction_stats']:
            if hasattr(self._cache_mixin, attr):
                setattr(self, attr, getattr(self._cache_mixin, attr))
    
    def cleanup_after_test(self):
        """Clean up test cache after test completes."""
        if hasattr(self, 'multi_cache'):
            self.multi_cache.cleanup_test_cache()


def force_test_mode():
    """Force all caches to use test mode (for pytest fixtures)."""
    os.environ['TESTING'] = '1'


def clear_test_mode():
    """Clear test mode flag."""
    if 'TESTING' in os.environ:
        del os.environ['TESTING']


# Usage Examples:

"""
# Example 1: Context manager approach
def test_manuscript_caching():
    with isolated_cache() as test_ctx:
        cache = test_ctx.cache_manager
        
        # Test manuscript operations
        manuscript_data = {...}
        cache.update_manuscript(manuscript_data, 'MOR')
        
        # Check cache works
        cached = cache.get_manuscript('MOR-123', 'MOR')
        assert cached is not None
        
        # Cache automatically cleaned up when exiting context

# Example 2: Test class approach
class TestMORExtractor(TestExtractorMixin):
    def setUp(self):
        self.init_enhanced_cache('MOR', test_mode=True)
    
    def tearDown(self):
        self.cleanup_after_test()
    
    def test_extraction(self):
        # Run extraction tests
        # All cache operations use temporary isolated cache
        pass

# Example 3: Pytest fixture approach
@pytest.fixture(autouse=True)
def setup_test_cache():
    force_test_mode()
    yield
    clear_test_mode()

def test_something():
    # All cache operations automatically use test mode
    cache = CacheManager()  # Will auto-detect test mode
    # ... test code ...

# Example 4: Development isolation (automatic)
# When running from dev/ directory, test mode auto-enabled:
cd dev/mf
python3 run_mf_dev.py  # Automatically uses test mode
"""