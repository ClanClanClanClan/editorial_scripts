"""Example showing cache integration with extraction pipeline."""

import time
from pathlib import Path
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ecc.core.performance_cache import (
    create_extraction_cache,
    PerformanceCache,
    CacheStrategy
)
from src.ecc.core.logging_system import setup_extraction_logging, LogCategory


class CachedExtractionExample:
    """Example showing how to integrate caching with extraction operations."""
    
    def __init__(self):
        # Setup logging and caching
        self.logger = setup_extraction_logging("cached_extractor")
        self.cache = create_extraction_cache(CacheStrategy.MULTI_TIER)
        
        # Simulation counters
        self.expensive_operations = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def simulate_popup_extraction(self, popup_url: str) -> str:
        """Simulate extracting email from popup with caching."""
        self.logger.info(f"Extracting email from popup: {popup_url[:50]}...", 
                        category=LogCategory.POPUP)
        
        # Check cache first
        cached_email = self.cache.get_cached_email(popup_url)
        if cached_email:
            self.cache_hits += 1
            self.logger.success(f"Cache hit - Found email: {cached_email}", 
                              category=LogCategory.POPUP)
            return cached_email
        
        # Cache miss - perform expensive operation
        self.cache_misses += 1
        self.expensive_operations += 1
        
        self.logger.warning("Cache miss - extracting from popup", 
                          category=LogCategory.POPUP)
        
        # Simulate network delay
        time.sleep(0.1)
        
        # Simulate email extraction
        extracted_email = f"referee{self.expensive_operations}@university.edu"
        
        # Cache the result
        self.cache.cache_email_lookup(popup_url, extracted_email, ttl=300)
        
        self.logger.success(f"Extracted and cached email: {extracted_email}", 
                          category=LogCategory.POPUP)
        
        return extracted_email
    
    def simulate_referee_lookup(self, referee_name: str) -> dict:
        """Simulate referee database lookup with caching."""
        self.logger.info(f"Looking up referee: {referee_name}", 
                        category=LogCategory.EXTRACTION)
        
        # Check cache first
        cached_data = self.cache.get_cached_referee(referee_name)
        if cached_data:
            self.cache_hits += 1
            self.logger.success(f"Cache hit - Found referee data", 
                              category=LogCategory.EXTRACTION)
            return cached_data
        
        # Cache miss - perform lookup
        self.cache_misses += 1
        self.expensive_operations += 1
        
        self.logger.warning("Cache miss - performing database lookup", 
                          category=LogCategory.EXTRACTION)
        
        # Simulate database delay
        time.sleep(0.2)
        
        # Simulate referee data
        referee_data = {
            "name": referee_name,
            "affiliation": f"University of {referee_name.split()[-1]}",
            "department": "Mathematics Department",
            "email": f"{referee_name.lower().replace(' ', '.')}@university.edu",
            "orcid": f"0000-0000-0000-{self.expensive_operations:04d}",
            "country": "United States"
        }
        
        # Cache the result for 24 hours
        self.cache.cache_referee_data(referee_name, referee_data, ttl=86400)
        
        self.logger.success("Referee data looked up and cached", 
                          category=LogCategory.EXTRACTION)
        
        return referee_data
    
    def simulate_manuscript_processing(self, manuscript_id: str) -> dict:
        """Simulate processing a manuscript with caching."""
        self.logger.enter_context(f"manuscript_{manuscript_id}")
        
        try:
            self.logger.progress(f"Processing manuscript: {manuscript_id}")
            
            # Check manuscript status cache
            cached_status = self.cache.get_cached_status(manuscript_id)
            if cached_status:
                self.logger.success(f"Using cached status: {cached_status}", 
                                  category=LogCategory.DATA)
            else:
                # Simulate status lookup
                time.sleep(0.05)
                cached_status = "Under Review"
                self.cache.cache_manuscript_status(manuscript_id, cached_status)
                self.logger.info(f"Status looked up and cached: {cached_status}", 
                               category=LogCategory.DATA)
            
            # Simulate extracting referees
            referees = []
            referee_names = ["John Smith", "Jane Doe", "Bob Wilson"]
            popup_urls = [
                f"javascript:popWindow('{name.replace(' ', '')}')"
                for name in referee_names
            ]
            
            for name, popup_url in zip(referee_names, popup_urls):
                self.logger.enter_context(f"referee_{name.replace(' ', '_')}")
                
                try:
                    # Get referee data (potentially cached)
                    referee_data = self.simulate_referee_lookup(name)
                    
                    # Extract email from popup (potentially cached)
                    popup_email = self.simulate_popup_extraction(popup_url)
                    
                    # Use popup email if different from database
                    if popup_email != referee_data["email"]:
                        referee_data["email"] = popup_email
                        self.logger.info("Updated email from popup extraction")
                    
                    referees.append(referee_data)
                    
                finally:
                    self.logger.exit_context(success=True)
            
            manuscript = {
                "id": manuscript_id,
                "status": cached_status,
                "title": f"Sample Paper {manuscript_id}",
                "referees": referees,
                "processing_time": time.time()
            }
            
            self.logger.success(f"Manuscript processing complete: {len(referees)} referees")
            
            return manuscript
            
        finally:
            self.logger.exit_context(success=True)
    
    def demonstrate_cache_performance(self):
        """Demonstrate cache performance benefits."""
        self.logger.progress("Starting cache performance demonstration")
        
        manuscripts = ["MS-2025-001", "MS-2025-002", "MS-2025-003"]
        
        # First pass - populate caches
        self.logger.data_info("=== FIRST PASS (Cache Population) ===")
        start_time = time.time()
        
        for manuscript_id in manuscripts:
            self.simulate_manuscript_processing(manuscript_id)
        
        first_pass_time = time.time() - start_time
        first_pass_ops = self.expensive_operations
        
        # Reset counters for second pass
        self.expensive_operations = 0
        
        # Second pass - use cached data
        self.logger.data_info("=== SECOND PASS (Cache Utilization) ===")
        start_time = time.time()
        
        for manuscript_id in manuscripts:
            self.simulate_manuscript_processing(manuscript_id)
        
        second_pass_time = time.time() - start_time
        second_pass_ops = self.expensive_operations
        
        # Report performance
        self.logger.data_info("=== PERFORMANCE RESULTS ===")
        self.logger.data_info(f"First pass: {first_pass_time:.2f}s ({first_pass_ops} expensive ops)")
        self.logger.data_info(f"Second pass: {second_pass_time:.2f}s ({second_pass_ops} expensive ops)")
        self.logger.data_info(f"Speedup: {first_pass_time/second_pass_time:.1f}x faster")
        self.logger.data_info(f"Cache hits: {self.cache_hits}")
        self.logger.data_info(f"Cache misses: {self.cache_misses}")
        self.logger.data_info(f"Cache hit rate: {100*self.cache_hits/(self.cache_hits+self.cache_misses):.1f}%")
        
        if second_pass_time < first_pass_time * 0.5:
            self.logger.success("🎯 Cache performance target achieved! (>50% speedup)")
        else:
            self.logger.warning("⚠️ Cache performance below target")


def demonstrate_advanced_caching():
    """Demonstrate advanced caching features."""
    logger = setup_extraction_logging("advanced_cache")
    
    # Create cache with custom settings
    cache = PerformanceCache(
        strategy=CacheStrategy.MULTI_TIER,
        max_memory_size=100,
        default_ttl=60
    )
    
    logger.progress("Demonstrating advanced caching features")
    
    # Function caching decorator
    @cache.cached(ttl=30)
    def expensive_computation(n):
        logger.info(f"Computing factorial of {n}")
        time.sleep(0.1)  # Simulate expensive operation
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result
    
    logger.data_info("=== Function Caching Demo ===")
    
    # First call - will compute
    start = time.time()
    result1 = expensive_computation(10)
    time1 = time.time() - start
    logger.success(f"First call: {result1} (took {time1:.3f}s)")
    
    # Second call - will use cache
    start = time.time()
    result2 = expensive_computation(10)
    time2 = time.time() - start
    logger.success(f"Second call: {result2} (took {time2:.3f}s)")
    
    # Verify results and performance
    assert result1 == result2
    assert time2 < time1 * 0.1  # Should be much faster
    
    logger.success(f"Function caching speedup: {time1/time2:.1f}x")
    
    # Memoization example
    @cache.memoize(ttl=60)
    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    
    logger.data_info("=== Memoization Demo ===")
    
    start = time.time()
    fib_result = fibonacci(20)
    fib_time = time.time() - start
    
    logger.success(f"Fibonacci(20) = {fib_result} (computed in {fib_time:.3f}s)")
    
    # Second call should be instant
    start = time.time()
    fib_result2 = fibonacci(20)
    fib_time2 = time.time() - start
    
    logger.success(f"Fibonacci(20) = {fib_result2} (cached in {fib_time2:.6f}s)")


if __name__ == "__main__":
    print("🚀 CACHE INTEGRATION DEMONSTRATION")
    print("=" * 60)
    
    # Basic extraction caching
    example = CachedExtractionExample()
    example.demonstrate_cache_performance()
    
    print("\n" + "=" * 60)
    
    # Advanced caching features
    demonstrate_advanced_caching()
    
    print("\n✅ Cache integration demonstration complete!")
    print("💡 Key benefits demonstrated:")
    print("   - Multi-tier caching (memory + file)")
    print("   - Extraction-specific cache helpers")
    print("   - Function result caching")
    print("   - Significant performance improvements")
    print("   - Integrated logging and monitoring")