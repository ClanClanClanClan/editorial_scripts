"""
Smart Cache Manager for Manuscript Data
Implements intelligent caching strategy from COMPREHENSIVE_DATA_EXTRACTION_REQUIREMENTS.md

Provides multi-level caching with change detection and smart invalidation
"""

import asyncio
import logging
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pickle

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Individual cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    checksum: str
    ttl_seconds: Optional[int] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl_seconds is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl_seconds
    
    @property
    def age_hours(self) -> float:
        """Get age of cache entry in hours"""
        return (datetime.now() - self.created_at).total_seconds() / 3600


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_entries: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_size_mb: float = 0.0
    expired_entries: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_requests = self.total_hits + self.total_misses
        return self.total_hits / total_requests if total_requests > 0 else 0.0


class SmartCacheManager:
    """
    Smart cache manager with multi-level caching and change detection
    Implements intelligent caching strategy for manuscript data
    """
    
    def __init__(
        self,
        cache_dir: Path,
        default_ttl_hours: int = 24,
        max_cache_size_mb: int = 1000,
        cleanup_interval_hours: int = 6
    ):
        self.cache_dir = Path(cache_dir)
        self.default_ttl_hours = default_ttl_hours
        self.max_cache_size_mb = max_cache_size_mb
        self.cleanup_interval_hours = cleanup_interval_hours
        
        # Create cache directories
        self._setup_cache_directories()
        
        # In-memory cache (Level 1)
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        # Cache statistics
        self.stats = CacheStats()
        
        # Background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _setup_cache_directories(self):
        """Setup cache directory structure"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            subdirs = [
                'manuscripts',     # Manuscript data cache
                'referees',        # Referee data cache
                'emails',          # Email timeline cache
                'documents',       # Document metadata cache
                'sessions',        # Session state cache
                'metadata',        # Cache metadata
                'temp'            # Temporary cache
            ]
            
            for subdir in subdirs:
                (self.cache_dir / subdir).mkdir(exist_ok=True)
            
            logger.info(f"✅ Cache directories created: {self.cache_dir}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create cache directories: {e}")
            raise
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        try:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        except Exception as e:
            logger.warning(f"Failed to start cleanup task: {e}")
    
    async def _periodic_cleanup(self):
        """Periodic cache cleanup"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
                await self.cleanup_expired_entries()
                await self._enforce_size_limit()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    async def get(self, key: str, category: str = "general") -> Optional[Any]:
        """
        Get data from cache with intelligent lookup
        
        Args:
            key: Cache key
            category: Cache category (manuscripts, referees, etc.)
            
        Returns:
            Cached data if found and valid, None otherwise
        """
        try:
            # Level 1: Memory cache
            memory_entry = self.memory_cache.get(key)
            if memory_entry and not memory_entry.is_expired:
                memory_entry.last_accessed = datetime.now()
                memory_entry.access_count += 1
                self.stats.total_hits += 1
                logger.debug(f"📄 Memory cache hit: {key}")
                return memory_entry.data
            
            # Level 2: Disk cache
            disk_entry = await self._load_from_disk(key, category)
            if disk_entry and not disk_entry.is_expired:
                # Promote to memory cache
                self.memory_cache[key] = disk_entry
                disk_entry.last_accessed = datetime.now()
                disk_entry.access_count += 1
                self.stats.total_hits += 1
                logger.debug(f"💾 Disk cache hit: {key}")
                return disk_entry.data
            
            # Cache miss
            self.stats.total_misses += 1
            logger.debug(f"❌ Cache miss: {key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Cache get failed for {key}: {e}")
            self.stats.total_misses += 1
            return None
    
    async def set(
        self,
        key: str,
        data: Any,
        category: str = "general",
        ttl_hours: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Store data in cache with intelligent placement
        
        Args:
            key: Cache key
            data: Data to cache
            category: Cache category
            ttl_hours: Time to live in hours
            tags: Tags for cache entry
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate TTL
            ttl_seconds = None
            if ttl_hours is not None:
                ttl_seconds = ttl_hours * 3600
            elif self.default_ttl_hours:
                ttl_seconds = self.default_ttl_hours * 3600
            
            # Calculate checksum
            checksum = self._calculate_checksum(data)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=1,
                checksum=checksum,
                ttl_seconds=ttl_seconds,
                tags=tags or []
            )
            
            # Store in memory cache
            self.memory_cache[key] = entry
            
            # Store on disk for persistence
            await self._save_to_disk(entry, category)
            
            self.stats.total_entries += 1
            logger.debug(f"💾 Cached: {key} in {category}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache set failed for {key}: {e}")
            return False
    
    async def invalidate(self, key: str, category: str = "general") -> bool:
        """Invalidate specific cache entry"""
        try:
            # Remove from memory cache
            if key in self.memory_cache:
                del self.memory_cache[key]
            
            # Remove from disk cache
            await self._remove_from_disk(key, category)
            
            logger.debug(f"🗑️ Invalidated cache: {key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache invalidation failed for {key}: {e}")
            return False
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate all cache entries with specified tags"""
        try:
            invalidated_count = 0
            
            # Find entries with matching tags
            keys_to_invalidate = []
            for key, entry in self.memory_cache.items():
                if any(tag in entry.tags for tag in tags):
                    keys_to_invalidate.append(key)
            
            # Invalidate found entries
            for key in keys_to_invalidate:
                await self.invalidate(key)
                invalidated_count += 1
            
            logger.info(f"🗑️ Invalidated {invalidated_count} entries by tags: {tags}")
            return invalidated_count
            
        except Exception as e:
            logger.error(f"❌ Tag-based invalidation failed: {e}")
            return 0
    
    async def has_changed(self, key: str, current_data: Any, category: str = "general") -> bool:
        """
        Check if data has changed since last cache
        
        Args:
            key: Cache key
            current_data: Current data to compare
            category: Cache category
            
        Returns:
            True if data has changed, False otherwise
        """
        try:
            cached_entry = await self._load_from_disk(key, category)
            if not cached_entry:
                return True  # No cache entry means it's "changed"
            
            current_checksum = self._calculate_checksum(current_data)
            return current_checksum != cached_entry.checksum
            
        except Exception as e:
            logger.error(f"❌ Change detection failed for {key}: {e}")
            return True  # Assume changed on error
    
    async def cache_manuscript_data(
        self,
        manuscript_id: str,
        manuscript_data: Dict[str, Any],
        force_update: bool = False
    ) -> bool:
        """
        Cache manuscript data with intelligent update detection
        
        Args:
            manuscript_id: Manuscript identifier
            manuscript_data: Complete manuscript data
            force_update: Force cache update even if unchanged
            
        Returns:
            True if cached (new or updated), False if unchanged
        """
        try:
            cache_key = f"manuscript_{manuscript_id}"
            
            # Check if data has changed
            if not force_update:
                if not await self.has_changed(cache_key, manuscript_data, "manuscripts"):
                    logger.debug(f"📋 Manuscript {manuscript_id} unchanged, skipping cache update")
                    return False
            
            # Cache with manuscript-specific TTL and tags
            tags = [
                "manuscript",
                f"journal_{manuscript_data.get('journal', 'unknown')}",
                f"status_{manuscript_data.get('status', 'unknown')}"
            ]
            
            # Longer TTL for stable manuscripts
            ttl_hours = self._calculate_manuscript_ttl(manuscript_data)
            
            success = await self.set(
                key=cache_key,
                data=manuscript_data,
                category="manuscripts",
                ttl_hours=ttl_hours,
                tags=tags
            )
            
            if success:
                logger.info(f"💾 Cached manuscript {manuscript_id} (TTL: {ttl_hours}h)")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Manuscript caching failed for {manuscript_id}: {e}")
            return False
    
    def _calculate_manuscript_ttl(self, manuscript_data: Dict[str, Any]) -> int:
        """Calculate appropriate TTL for manuscript based on status"""
        status = manuscript_data.get('status', '').lower()
        
        if 'completed' in status or 'published' in status:
            return 7 * 24  # 7 days for completed manuscripts
        elif 'under review' in status:
            return 6  # 6 hours for active manuscripts
        elif 'submitted' in status:
            return 24  # 1 day for recently submitted
        else:
            return self.default_ttl_hours
    
    async def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries"""
        try:
            cleaned_count = 0
            
            # Clean memory cache
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                cleaned_count += 1
            
            # Clean disk cache
            for category_dir in self.cache_dir.iterdir():
                if category_dir.is_dir() and category_dir.name != 'metadata':
                    for cache_file in category_dir.glob('*.cache'):
                        try:
                            entry = await self._load_cache_file(cache_file)
                            if entry and entry.is_expired:
                                cache_file.unlink()
                                cleaned_count += 1
                        except Exception:
                            continue
            
            self.stats.expired_entries += cleaned_count
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned {cleaned_count} expired cache entries")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"❌ Cache cleanup failed: {e}")
            return 0
    
    async def _enforce_size_limit(self):
        """Enforce maximum cache size by removing least recently used entries"""
        try:
            current_size = await self._calculate_cache_size()
            
            if current_size <= self.max_cache_size_mb:
                return
            
            logger.info(f"📏 Cache size ({current_size:.1f}MB) exceeds limit ({self.max_cache_size_mb}MB)")
            
            # Sort entries by last accessed time (LRU)
            entries_by_access = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            removed_count = 0
            for key, entry in entries_by_access:
                await self.invalidate(key)
                removed_count += 1
                
                # Check size again
                current_size = await self._calculate_cache_size()
                if current_size <= self.max_cache_size_mb * 0.8:  # 80% of limit
                    break
            
            logger.info(f"🗑️ Removed {removed_count} LRU entries to enforce size limit")
            
        except Exception as e:
            logger.error(f"❌ Size limit enforcement failed: {e}")
    
    async def _calculate_cache_size(self) -> float:
        """Calculate total cache size in MB"""
        try:
            total_size = 0
            
            # Calculate disk cache size
            for cache_file in self.cache_dir.rglob('*.cache'):
                if cache_file.is_file():
                    total_size += cache_file.stat().st_size
            
            return total_size / (1024 * 1024)  # Convert to MB
            
        except Exception as e:
            logger.error(f"❌ Cache size calculation failed: {e}")
            return 0.0
    
    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data"""
        try:
            # Convert data to JSON string for consistent hashing
            json_str = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except Exception:
            # Fallback to string representation
            return hashlib.sha256(str(data).encode()).hexdigest()
    
    async def _load_from_disk(self, key: str, category: str) -> Optional[CacheEntry]:
        """Load cache entry from disk"""
        try:
            cache_file = self.cache_dir / category / f"{key}.cache"
            if not cache_file.exists():
                return None
            
            return await self._load_cache_file(cache_file)
            
        except Exception as e:
            logger.debug(f"Disk cache load failed for {key}: {e}")
            return None
    
    async def _load_cache_file(self, cache_file: Path) -> Optional[CacheEntry]:
        """Load cache entry from specific file"""
        try:
            with open(cache_file, 'rb') as f:
                entry_data = pickle.load(f)
            
            # Reconstruct CacheEntry object
            entry = CacheEntry(**entry_data)
            return entry
            
        except Exception as e:
            logger.debug(f"Cache file load failed: {e}")
            return None
    
    async def _save_to_disk(self, entry: CacheEntry, category: str):
        """Save cache entry to disk"""
        try:
            cache_file = self.cache_dir / category / f"{entry.key}.cache"
            cache_file.parent.mkdir(exist_ok=True)
            
            # Convert to dict for serialization
            entry_data = asdict(entry)
            
            with open(cache_file, 'wb') as f:
                pickle.dump(entry_data, f)
                
        except Exception as e:
            logger.error(f"❌ Disk cache save failed for {entry.key}: {e}")
    
    async def _remove_from_disk(self, key: str, category: str):
        """Remove cache entry from disk"""
        try:
            cache_file = self.cache_dir / category / f"{key}.cache"
            if cache_file.exists():
                cache_file.unlink()
        except Exception as e:
            logger.debug(f"Disk cache remove failed for {key}: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Update current statistics
            self.stats.total_size_mb = asyncio.create_task(self._calculate_cache_size())
            self.stats.total_entries = len(self.memory_cache)
            
            return {
                'performance': {
                    'hit_rate': self.stats.hit_rate,
                    'total_hits': self.stats.total_hits,
                    'total_misses': self.stats.total_misses,
                    'total_requests': self.stats.total_hits + self.stats.total_misses
                },
                'storage': {
                    'memory_entries': len(self.memory_cache),
                    'total_size_mb': self.stats.total_size_mb,
                    'max_size_mb': self.max_cache_size_mb,
                    'cache_directory': str(self.cache_dir)
                },
                'maintenance': {
                    'expired_entries_cleaned': self.stats.expired_entries,
                    'default_ttl_hours': self.default_ttl_hours,
                    'cleanup_interval_hours': self.cleanup_interval_hours
                },
                'categories': self._get_category_stats()
            }
            
        except Exception as e:
            logger.error(f"❌ Statistics generation failed: {e}")
            return {}
    
    def _get_category_stats(self) -> Dict[str, int]:
        """Get statistics by cache category"""
        try:
            category_stats = {}
            
            for category_dir in self.cache_dir.iterdir():
                if category_dir.is_dir() and category_dir.name != 'metadata':
                    cache_files = list(category_dir.glob('*.cache'))
                    category_stats[category_dir.name] = len(cache_files)
            
            return category_stats
            
        except Exception as e:
            logger.error(f"❌ Category stats failed: {e}")
            return {}
    
    async def shutdown(self):
        """Shutdown cache manager gracefully"""
        try:
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Final cleanup
            await self.cleanup_expired_entries()
            
            logger.info("✅ Cache manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Cache shutdown failed: {e}")


# Example usage
if __name__ == "__main__":
    async def test_smart_cache():
        # Initialize cache manager
        cache_manager = SmartCacheManager(
            cache_dir=Path("test_cache"),
            default_ttl_hours=24,
            max_cache_size_mb=100
        )
        
        # Test caching
        test_data = {
            "id": "M172838",
            "title": "Test Manuscript",
            "status": "Under Review",
            "authors": ["Author 1", "Author 2"]
        }
        
        # Cache manuscript data
        success = await cache_manager.cache_manuscript_data("M172838", test_data)
        print(f"Cache success: {success}")
        
        # Retrieve from cache
        cached_data = await cache_manager.get("manuscript_M172838", "manuscripts")
        print(f"Retrieved from cache: {cached_data is not None}")
        
        # Get statistics
        stats = cache_manager.get_cache_statistics()
        print(f"Cache hit rate: {stats['performance']['hit_rate']:.2%}")
        
        # Shutdown
        await cache_manager.shutdown()
    
    # Run test
    # asyncio.run(test_smart_cache())