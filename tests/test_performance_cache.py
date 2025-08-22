"""Test the performance caching system."""

import tempfile
import time
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ecc.core.performance_cache import (
    MemoryCache,
    FileCache,
    PerformanceCache,
    ExtractionCache,
    CacheStrategy,
    CacheEntry,
    create_cache,
    create_extraction_cache
)


def test_cache_entry():
    """Test CacheEntry functionality."""
    entry = CacheEntry(
        key="test",
        value="data",
        created_at=time.time(),
        accessed_at=time.time(),
        ttl_seconds=60
    )
    
    assert not entry.is_expired()
    assert entry.access_count == 0
    
    entry.touch()
    assert entry.access_count == 1
    
    # Test expired entry
    old_entry = CacheEntry(
        key="old",
        value="data",
        created_at=time.time() - 120,  # 2 minutes ago
        accessed_at=time.time() - 120,
        ttl_seconds=60  # 1 minute TTL
    )
    assert old_entry.is_expired()
    
    print("✅ CacheEntry test passed")


def test_memory_cache():
    """Test MemoryCache functionality."""
    cache = MemoryCache(max_size=3, default_ttl=60)
    
    # Test basic operations
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"
    assert cache.get("key3") == "value3"
    assert cache.get("nonexistent") is None
    
    # Test LRU eviction
    cache.set("key4", "value4")  # Should evict key1 (LRU)
    assert cache.get("key1") is None
    assert cache.get("key4") == "value4"
    
    # Test deletion
    assert cache.delete("key2") is True
    assert cache.get("key2") is None
    assert cache.delete("nonexistent") is False
    
    # Test TTL expiration
    cache.set("ttl_key", "ttl_value", ttl=1)
    assert cache.get("ttl_key") == "ttl_value"
    time.sleep(1.1)
    assert cache.get("ttl_key") is None  # Should be expired
    
    # Test clear
    cache.clear()
    assert cache.get("key3") is None
    assert cache.get("key4") is None
    
    # Test stats
    cache.set("stats_key", "stats_value")
    stats = cache.stats()
    assert stats['total_entries'] == 1
    assert stats['max_size'] == 3
    
    print("✅ MemoryCache test passed")


def test_file_cache():
    """Test FileCache functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = FileCache(Path(temp_dir), default_ttl=60)
        
        # Test basic operations
        cache.set("file_key1", "file_value1")
        cache.set("file_key2", {"nested": "data"})
        
        assert cache.get("file_key1") == "file_value1"
        assert cache.get("file_key2") == {"nested": "data"}
        assert cache.get("nonexistent") is None
        
        # Test TTL
        cache.set("ttl_key", "ttl_value", ttl=1)
        assert cache.get("ttl_key") == "ttl_value"
        time.sleep(1.1)
        assert cache.get("ttl_key") is None
        
        # Test deletion
        assert cache.delete("file_key1") is True
        assert cache.get("file_key1") is None
        assert cache.delete("nonexistent") is False
        
        # Test clear
        cache.clear()
        assert cache.get("file_key2") is None
        
        # Test cleanup expired
        cache.set("exp1", "value1", ttl=1)
        cache.set("exp2", "value2", ttl=60)
        time.sleep(1.1)
        cache.cleanup_expired()
        assert cache.get("exp1") is None
        assert cache.get("exp2") == "value2"
    
    print("✅ FileCache test passed")


def test_performance_cache_memory():
    """Test PerformanceCache with memory strategy."""
    cache = PerformanceCache(
        strategy=CacheStrategy.MEMORY,
        max_memory_size=100,
        default_ttl=60
    )
    
    # Test basic operations
    cache.set("perf_key", "perf_value")
    assert cache.get("perf_key") == "perf_value"
    
    assert cache.delete("perf_key") is True
    assert cache.get("perf_key") is None
    
    # Test caching decorator
    call_count = 0
    
    @cache.cached(ttl=60)
    def expensive_function(x, y):
        nonlocal call_count
        call_count += 1
        return x + y
    
    # First call should execute function
    result1 = expensive_function(1, 2)
    assert result1 == 3
    assert call_count == 1
    
    # Second call should use cache
    result2 = expensive_function(1, 2)
    assert result2 == 3
    assert call_count == 1  # Should not increment
    
    # Different arguments should execute function
    result3 = expensive_function(2, 3)
    assert result3 == 5
    assert call_count == 2
    
    cache.clear()
    print("✅ PerformanceCache memory test passed")


def test_performance_cache_file():
    """Test PerformanceCache with file strategy."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = PerformanceCache(
            strategy=CacheStrategy.FILE,
            cache_dir=Path(temp_dir),
            default_ttl=60
        )
        
        # Test basic operations
        cache.set("file_perf_key", {"complex": "data"})
        assert cache.get("file_perf_key") == {"complex": "data"}
        
        # Test memoization
        @cache.memoize(ttl=60)
        def compute_value(n):
            return n * n
        
        assert compute_value(5) == 25
        assert compute_value(5) == 25  # Should use cache
        
        cache.clear()
    
    print("✅ PerformanceCache file test passed")


def test_multi_tier_cache():
    """Test multi-tier caching strategy."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = PerformanceCache(
            strategy=CacheStrategy.MULTI_TIER,
            cache_dir=Path(temp_dir),
            max_memory_size=50,
            default_ttl=60
        )
        
        # Set value (should be in all tiers)
        cache.set("multi_key", "multi_value")
        
        # Get value (should come from memory first)
        assert cache.get("multi_key") == "multi_value"
        
        # Clear memory and get again (should promote from file)
        cache.cache.memory_cache.clear()
        assert cache.get("multi_key") == "multi_value"
        
        # Should now be back in memory
        assert cache.cache.memory_cache.get("multi_key") == "multi_value"
        
        cache.clear()
    
    print("✅ Multi-tier cache test passed")


def test_extraction_cache():
    """Test ExtractionCache specialized operations."""
    cache = create_extraction_cache(CacheStrategy.MEMORY)
    
    # Test popup content caching
    test_url = "javascript:popWindow('test')"
    test_content = "<html>Email: test@example.com</html>"
    
    cache.cache_popup_content(test_url, test_content)
    assert cache.get_popup_content(test_url) == test_content
    
    # Test email lookup caching
    test_email = "test@example.com"
    cache.cache_email_lookup(test_url, test_email)
    assert cache.get_cached_email(test_url) == test_email
    
    # Test referee data caching
    referee_name = "John Smith"
    referee_data = {
        "name": referee_name,
        "affiliation": "Test University",
        "email": "john@test.edu"
    }
    
    cache.cache_referee_data(referee_name, referee_data)
    cached_referee = cache.get_cached_referee(referee_name)
    assert cached_referee == referee_data
    
    # Test manuscript status caching
    manuscript_id = "MS-2025-001"
    status = "Under Review"
    
    cache.cache_manuscript_status(manuscript_id, status)
    assert cache.get_cached_status(manuscript_id) == status
    
    print("✅ ExtractionCache test passed")


def test_cache_integration_example():
    """Test cache integration in a realistic scenario."""
    cache = create_extraction_cache(CacheStrategy.MEMORY)
    
    # Simulate extraction workflow
    class MockExtractor:
        def __init__(self, cache: ExtractionCache):
            self.cache = cache
            self.api_calls = 0
        
        def get_referee_info(self, name: str) -> dict:
            # Check cache first
            cached = self.cache.get_cached_referee(name)
            if cached:
                return cached
            
            # Simulate expensive API call
            self.api_calls += 1
            data = {
                "name": name,
                "affiliation": f"University of {name}",
                "email": f"{name.lower().replace(' ', '.')}@university.edu"
            }
            
            # Cache the result
            self.cache.cache_referee_data(name, data)
            return data
        
        def extract_email_from_popup(self, popup_url: str) -> str:
            # Check cache first
            cached = self.cache.get_cached_email(popup_url)
            if cached:
                return cached
            
            # Simulate popup extraction
            self.api_calls += 1
            email = "extracted@example.com"
            
            # Cache the result
            self.cache.cache_email_lookup(popup_url, email)
            return email
    
    extractor = MockExtractor(cache)
    
    # First calls should hit the "API"
    referee1 = extractor.get_referee_info("John Smith")
    email1 = extractor.extract_email_from_popup("javascript:test1")
    assert extractor.api_calls == 2
    
    # Second calls should use cache
    referee2 = extractor.get_referee_info("John Smith")
    email2 = extractor.extract_email_from_popup("javascript:test1")
    assert extractor.api_calls == 2  # No increase
    
    # Verify data integrity
    assert referee1 == referee2
    assert email1 == email2
    
    print("✅ Cache integration test passed")


def test_cache_performance():
    """Test cache performance characteristics."""
    memory_cache = PerformanceCache(CacheStrategy.MEMORY, max_memory_size=1000)
    
    # Test performance with many operations
    start_time = time.time()
    
    # Set 1000 items
    for i in range(1000):
        memory_cache.set(f"key_{i}", f"value_{i}")
    
    set_time = time.time() - start_time
    
    # Get 1000 items
    start_time = time.time()
    for i in range(1000):
        value = memory_cache.get(f"key_{i}")
        assert value == f"value_{i}"
    
    get_time = time.time() - start_time
    
    print(f"✅ Performance test passed:")
    print(f"   Set 1000 items: {set_time:.3f}s")
    print(f"   Get 1000 items: {get_time:.3f}s")
    
    # Performance should be reasonable
    assert set_time < 1.0  # Less than 1 second
    assert get_time < 0.5  # Less than 0.5 seconds


def test_cache_create_functions():
    """Test cache creation convenience functions."""
    # Test create_cache function
    cache1 = create_cache(CacheStrategy.MEMORY, max_memory_size=100)
    assert isinstance(cache1, PerformanceCache)
    
    # Test create_extraction_cache function
    cache2 = create_extraction_cache(CacheStrategy.MEMORY)
    assert isinstance(cache2, ExtractionCache)
    
    print("✅ Cache creation functions test passed")


if __name__ == "__main__":
    print("Testing performance caching system...")
    print("=" * 60)
    
    # Run all tests
    test_cache_entry()
    test_memory_cache()
    test_file_cache()
    test_performance_cache_memory()
    test_performance_cache_file()
    test_multi_tier_cache()
    test_extraction_cache()
    test_cache_integration_example()
    test_cache_performance()
    test_cache_create_functions()
    
    print("\n✅ All performance cache tests passed!")