#!/usr/bin/env python3
"""
MULTI-LAYER CACHING SYSTEM (V1.0 SPEC COMPLIANCE)
=================================================

Implements the "Multi-layer caching for optimal performance" requirement
from PROJECT_SPECIFICATIONS.md v1.0, line 1019.

Layer Architecture:
- Layer 1: In-Memory (fastest, session-only)
- Layer 2: SQLite (persistent, local)
- Layer 3: File System (large objects)
- Layer 4: Redis (future - distributed/API responses)
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import threading
import sqlite3

from .cache_manager import CacheManager
from .redis_cache import create_redis_layer, APIResponseCache


class MultiLayerCache:
    """Multi-layer caching system as specified in v1.0 architecture."""
    
    def __init__(self, cache_dir: Path = None, test_mode: bool = None, redis_url: str = None):
        """Initialize all cache layers."""
        # Layer 1: In-memory cache (fastest)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.memory_lock = threading.Lock()
        self.memory_max_size = 1000  # Configurable
        
        # Layer 2: SQLite persistent cache
        self.sqlite_cache = CacheManager(cache_dir, test_mode)
        
        # Layer 3: File system cache for large objects
        if self.sqlite_cache.test_mode:
            # Use same temp directory for file cache in test mode
            self.fs_cache_dir = self.sqlite_cache.cache_dir / "file_cache"
        else:
            if cache_dir:
                self.fs_cache_dir = Path(cache_dir) / "file_cache"
            else:
                self.fs_cache_dir = Path("cache") / "file_cache"
        self.fs_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Layer 4: Redis for API responses and distributed caching
        self.redis_cache = create_redis_layer(redis_url)
        if self.redis_cache:
            self.api_cache = APIResponseCache(self.redis_cache)
        else:
            self.api_cache = None
        
        mode_indicator = "🧪 TEST MODE" if self.sqlite_cache.test_mode else "✅ PRODUCTION MODE"
        print(f"{mode_indicator} - Multi-layer cache initialized:")
        print(f"   📱 Layer 1: In-memory (max {self.memory_max_size} items)")
        print(f"   💾 Layer 2: SQLite ({self.sqlite_cache.db_path})")
        print(f"   📁 Layer 3: File system ({self.fs_cache_dir})")
        if self.redis_cache and self.redis_cache.enabled:
            print(f"   🌐 Layer 4: Redis (active)")
        else:
            print(f"   🌐 Layer 4: Redis (not available)")
    
    def _compute_cache_key(self, key_components: Dict[str, Any]) -> str:
        """Generate consistent cache key from components."""
        key_string = json.dumps(key_components, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    # LAYER 1: IN-MEMORY CACHE
    
    def _get_from_memory(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get item from in-memory cache (Layer 1)."""
        with self.memory_lock:
            if cache_key in self.memory_cache:
                cached_item = self.memory_cache[cache_key]
                
                # Check expiry
                if 'expires_at' in cached_item:
                    if datetime.now() > datetime.fromisoformat(cached_item['expires_at']):
                        del self.memory_cache[cache_key]
                        return None
                
                # Update access time
                cached_item['last_accessed'] = datetime.now().isoformat()
                return cached_item['data']
            
            return None
    
    def _set_to_memory(self, cache_key: str, data: Any, ttl_seconds: int = 300):
        """Set item in in-memory cache (Layer 1)."""
        with self.memory_lock:
            # Evict oldest items if at capacity
            if len(self.memory_cache) >= self.memory_max_size:
                # Simple LRU eviction
                oldest_key = min(
                    self.memory_cache.keys(),
                    key=lambda k: self.memory_cache[k].get('last_accessed', '1970-01-01')
                )
                del self.memory_cache[oldest_key]
            
            # Store with metadata
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            self.memory_cache[cache_key] = {
                'data': data,
                'cached_at': datetime.now().isoformat(),
                'last_accessed': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            }
    
    # LAYER 3: FILE SYSTEM CACHE
    
    def _get_from_filesystem(self, cache_key: str) -> Optional[Any]:
        """Get large object from file system cache (Layer 3)."""
        cache_file = self.fs_cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check expiry
                if 'expires_at' in cached_data:
                    if datetime.now() > datetime.fromisoformat(cached_data['expires_at']):
                        cache_file.unlink()
                        return None
                
                return cached_data['data']
            except (json.JSONDecodeError, KeyError):
                # Corrupted cache file
                cache_file.unlink()
                return None
        
        return None
    
    def _set_to_filesystem(self, cache_key: str, data: Any, ttl_seconds: int = 3600):
        """Set large object in file system cache (Layer 3)."""
        cache_file = self.fs_cache_dir / f"{cache_key}.json"
        
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        cached_data = {
            'data': data,
            'cached_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cached_data, f, indent=2)
    
    # PUBLIC API - CASCADE THROUGH LAYERS
    
    def get(self, cache_type: str, key_components: Dict[str, Any]) -> Optional[Any]:
        """
        Get data from cache, checking layers in order of speed.
        
        Args:
            cache_type: Type of data ('referee', 'manuscript', 'institution', etc.)
            key_components: Dict of key components to generate cache key
        
        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self._compute_cache_key({
            'type': cache_type,
            **key_components
        })
        
        # Layer 1: Check in-memory cache first (fastest)
        result = self._get_from_memory(cache_key)
        if result is not None:
            print(f"   💾 Cache hit: Layer 1 (memory) - {cache_type}")
            return result
        
        # Layer 2: Check SQLite cache
        if cache_type == 'referee':
            email = key_components.get('email')
            if email:
                result = self.sqlite_cache.get_referee(email)
                if result:
                    # Promote to Layer 1
                    self._set_to_memory(cache_key, result.__dict__)
                    print(f"   💾 Cache hit: Layer 2 (SQLite) - {cache_type}")
                    return result
        
        elif cache_type == 'manuscript':
            manuscript_id = key_components.get('manuscript_id')
            journal = key_components.get('journal')
            if manuscript_id and journal:
                result = self.sqlite_cache.get_manuscript(manuscript_id, journal)
                if result:
                    # Promote to Layer 1
                    self._set_to_memory(cache_key, result.__dict__)
                    print(f"   💾 Cache hit: Layer 2 (SQLite) - {cache_type}")
                    return result
        
        elif cache_type == 'institution':
            domain = key_components.get('domain')
            if domain:
                result = self.sqlite_cache.get_institution_from_domain(domain)
                if result:
                    # Promote to Layer 1
                    self._set_to_memory(cache_key, {'institution': result[0], 'country': result[1]})
                    print(f"   💾 Cache hit: Layer 2 (SQLite) - {cache_type}")
                    return result
        
        # Layer 3: Check file system for large objects
        if cache_type in ['large_document', 'extracted_text', 'analysis_results']:
            result = self._get_from_filesystem(cache_key)
            if result is not None:
                # Promote to Layer 1 if small enough
                if isinstance(result, dict) and len(json.dumps(result)) < 10000:  # < 10KB
                    self._set_to_memory(cache_key, result)
                print(f"   💾 Cache hit: Layer 3 (filesystem) - {cache_type}")
                return result
        
        # Layer 4: Redis for API responses and shared data
        if cache_type == 'api_response' and self.redis_cache and self.redis_cache.enabled:
            endpoint = key_components.get('endpoint')
            params = key_components.get('params', {})
            if endpoint:
                result = self.api_cache.get_api_response(endpoint, params)
                if result:
                    print(f"   💾 Cache hit: Layer 4 (Redis) - {cache_type}")
                    return result
        elif self.redis_cache and self.redis_cache.enabled:
            result = self.redis_cache.get(cache_key)
            if result:
                print(f"   💾 Cache hit: Layer 4 (Redis) - {cache_type}")
                return result
        
        print(f"   ❌ Cache miss: {cache_type}")
        return None
    
    def set(self, cache_type: str, key_components: Dict[str, Any], data: Any, 
           ttl_seconds: int = 3600):
        """
        Set data in appropriate cache layers.
        
        Args:
            cache_type: Type of data being cached
            key_components: Dict of key components to generate cache key
            data: Data to cache
            ttl_seconds: Time to live in seconds
        """
        cache_key = self._compute_cache_key({
            'type': cache_type,
            **key_components
        })
        
        # Determine data size for layer selection
        data_size = len(json.dumps(data) if not isinstance(data, str) else data)
        
        # Layer 1: Always cache small frequently accessed items
        if data_size < 50000:  # < 50KB
            self._set_to_memory(cache_key, data, min(ttl_seconds, 300))  # Max 5 min in memory
        
        # Layer 2: SQLite for structured data
        if cache_type == 'referee' and hasattr(data, 'email'):
            # Let the SQLite cache handle referee storage
            pass  # Already handled by update_referee method
        elif cache_type == 'manuscript' and isinstance(data, dict):
            # Let the SQLite cache handle manuscript storage
            pass  # Already handled by update_manuscript method
        elif cache_type == 'institution':
            domain = key_components.get('domain')
            if domain and isinstance(data, dict):
                self.sqlite_cache.cache_institution(
                    domain, 
                    data.get('institution', ''), 
                    data.get('country', '')
                )
        
        # Layer 3: File system for large objects
        if data_size > 10000 or cache_type in ['large_document', 'extracted_text']:
            self._set_to_filesystem(cache_key, data, ttl_seconds)
        
        # Layer 4: Redis for distributed/API responses
        if cache_type == 'api_response' and self.redis_cache and self.redis_cache.enabled:
            endpoint = key_components.get('endpoint')
            params = key_components.get('params', {})
            if endpoint:
                self.api_cache.cache_api_response(endpoint, params, data, ttl_seconds)
        elif self.redis_cache and self.redis_cache.enabled and cache_type in ['api_response', 'shared_data', 'referee_search']:
            self.redis_cache.set(cache_key, data, ttl_seconds)
        
        print(f"   ✅ Cached: {cache_type} ({data_size} bytes)")
    
    def invalidate(self, cache_type: str, key_components: Dict[str, Any]):
        """Invalidate cached data across all layers."""
        cache_key = self._compute_cache_key({
            'type': cache_type,
            **key_components
        })
        
        # Layer 1: Remove from memory
        with self.memory_lock:
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
        
        # Layer 3: Remove from filesystem
        cache_file = self.fs_cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            cache_file.unlink()
        
        # Layer 4: Remove from Redis
        if self.redis_cache and self.redis_cache.enabled:
            self.redis_cache.delete(cache_key)
        
        # Layer 2: SQLite removal depends on data type
        # (Individual methods handle this)
        
        print(f"   🗑️ Invalidated: {cache_type}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        # Layer 1 stats
        memory_count = len(self.memory_cache)
        memory_size = sum(
            len(json.dumps(item['data'])) 
            for item in self.memory_cache.values()
        )
        
        # Layer 3 stats
        fs_files = list(self.fs_cache_dir.glob("*.json"))
        fs_count = len(fs_files)
        fs_size = sum(f.stat().st_size for f in fs_files)
        
        # Layer 2 stats from SQLite
        sqlite_stats = self.sqlite_cache.get_cache_statistics()
        
        return {
            'layer_1_memory': {
                'count': memory_count,
                'size_bytes': memory_size,
                'max_items': self.memory_max_size
            },
            'layer_2_sqlite': sqlite_stats,
            'layer_3_filesystem': {
                'count': fs_count,
                'size_bytes': fs_size,
                'directory': str(self.fs_cache_dir)
            },
            'layer_4_redis': self.redis_cache.get_stats() if self.redis_cache and self.redis_cache.enabled else {'status': 'disabled'}
        }
    
    def cleanup_expired(self):
        """Clean up expired entries across all layers."""
        print("🧹 Cleaning up expired cache entries...")
        
        # Layer 1: Memory cleanup (happens automatically on access)
        expired_memory = 0
        with self.memory_lock:
            keys_to_remove = []
            for key, item in self.memory_cache.items():
                if 'expires_at' in item:
                    if datetime.now() > datetime.fromisoformat(item['expires_at']):
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.memory_cache[key]
                expired_memory += 1
        
        # Layer 3: File system cleanup
        expired_fs = 0
        for cache_file in self.fs_cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                if 'expires_at' in cached_data:
                    if datetime.now() > datetime.fromisoformat(cached_data['expires_at']):
                        cache_file.unlink()
                        expired_fs += 1
            except:
                # Corrupted file
                cache_file.unlink()
                expired_fs += 1
        
        # Layer 2: SQLite cleanup (let CacheManager handle this)
        expired_sqlite = self.sqlite_cache.clear_old_cache(days=7)
        
        print(f"   Layer 1: {expired_memory} expired memory entries")
        print(f"   Layer 2: {expired_sqlite[0]} expired SQLite entries") 
        print(f"   Layer 3: {expired_fs} expired file cache entries")
    
    def cleanup_test_cache(self):
        """Clean up test cache (only in test mode)."""
        if self.sqlite_cache.test_mode:
            self.sqlite_cache.cleanup_test_cache()


# Integration with existing ExtractorCacheMixin
class EnhancedExtractorCacheMixin:
    """Enhanced cache mixin with multi-layer support."""
    
    def init_enhanced_cache(self, journal_name: str, test_mode: bool = None):
        """Initialize enhanced multi-layer cache."""
        self.multi_cache = MultiLayerCache(test_mode=test_mode)
        self.journal_name = journal_name
        self.run_id = self.multi_cache.sqlite_cache.start_extraction_run(journal_name)
        self.extraction_stats = {
            'manuscripts_extracted': 0,
            'new_manuscripts': 0,
            'updated_manuscripts': 0,
            'new_referees': 0,
            'errors': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def get_cached_data(self, data_type: str, **key_components) -> Optional[Any]:
        """Get data from multi-layer cache."""
        result = self.multi_cache.get(data_type, key_components)
        
        if result:
            self.extraction_stats['cache_hits'] += 1
        else:
            self.extraction_stats['cache_misses'] += 1
        
        return result
    
    def cache_data(self, data_type: str, data: Any, ttl_seconds: int = 3600, **key_components):
        """Cache data in multi-layer system."""
        self.multi_cache.set(data_type, key_components, data, ttl_seconds)
    
    def finish_enhanced_extraction(self, metadata: Dict[str, Any] = None):
        """Finish extraction with enhanced statistics."""
        # Add cache statistics
        cache_stats = self.multi_cache.get_cache_stats()
        cache_efficiency = (
            self.extraction_stats['cache_hits'] / 
            (self.extraction_stats['cache_hits'] + self.extraction_stats['cache_misses'])
            if (self.extraction_stats['cache_hits'] + self.extraction_stats['cache_misses']) > 0
            else 0
        )
        
        enhanced_metadata = {
            **(metadata or {}),
            'cache_efficiency': cache_efficiency,
            'cache_stats': cache_stats,
            'multi_layer_enabled': True
        }
        
        self.multi_cache.sqlite_cache.update_extraction_stats(
            self.run_id, self.extraction_stats
        )
        self.multi_cache.sqlite_cache.finish_extraction_run(
            self.run_id, enhanced_metadata
        )
        
        print(f"\n📊 ENHANCED CACHE STATISTICS:")
        print(f"   🎯 Cache Efficiency: {cache_efficiency:.1%}")
        print(f"   💾 Cache Hits: {self.extraction_stats['cache_hits']}")
        print(f"   ❌ Cache Misses: {self.extraction_stats['cache_misses']}")
        print(f"   📱 Layer 1 (Memory): {cache_stats['layer_1_memory']['count']} items")
        print(f"   💿 Layer 2 (SQLite): {cache_stats['layer_2_sqlite']['total_referees']} referees")
        print(f"   📁 Layer 3 (File): {cache_stats['layer_3_filesystem']['count']} files")
        
        # Layer 4: Redis
        redis_stats = cache_stats.get('layer_4_redis', {})
        if redis_stats.get('status') == 'enabled':
            print(f"   🌐 Layer 4 (Redis): {redis_stats.get('keys_count', 0)} keys, {redis_stats.get('memory_used', 'unknown')}")
        else:
            print(f"   🌐 Layer 4 (Redis): {redis_stats.get('status', 'disabled')}")
        
        # Cleanup test cache if in test mode
        if hasattr(self, 'multi_cache'):
            self.multi_cache.cleanup_test_cache()