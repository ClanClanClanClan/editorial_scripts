#!/usr/bin/env python3
"""
REDIS CACHE LAYER (V1.0 SPEC COMPLIANCE)
=========================================

Implements "Redis-compatible caching for API responses" requirement
from PROJECT_SPECIFICATIONS.md v1.0, line 127.

This provides Layer 4 caching for the multi-layer cache system.
Currently optional - can be enabled when Redis is available.
"""

import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import logging

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class RedisCache:
    """Redis-compatible cache layer for API responses and distributed caching."""
    
    def __init__(self, redis_url: str = 'redis://localhost:6379', 
                 prefix: str = 'editorial_cache'):
        """
        Initialize Redis cache connection.
        
        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
        """
        self.prefix = prefix
        self.redis_client = None
        self.enabled = False
        
        if not REDIS_AVAILABLE:
            logging.warning("Redis not available - install redis-py for distributed caching")
            return
        
        try:
            self.redis_client = redis.from_url(redis_url)
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            print(f"✅ Redis cache connected: {redis_url}")
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}")
            self.enabled = False
    
    def _make_key(self, key: str) -> str:
        """Create namespaced Redis key."""
        return f"{self.prefix}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get data from Redis cache."""
        if not self.enabled:
            return None
        
        try:
            redis_key = self._make_key(key)
            cached_data = self.redis_client.get(redis_key)
            
            if cached_data:
                return json.loads(cached_data.decode('utf-8'))
            
            return None
        except Exception as e:
            logging.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl_seconds: int = 3600):
        """Set data in Redis cache with TTL."""
        if not self.enabled:
            return False
        
        try:
            redis_key = self._make_key(key)
            serialized_data = json.dumps(data)
            
            if ttl_seconds > 0:
                self.redis_client.setex(redis_key, ttl_seconds, serialized_data)
            else:
                self.redis_client.set(redis_key, serialized_data)
            
            return True
        except Exception as e:
            logging.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis cache."""
        if not self.enabled:
            return False
        
        try:
            redis_key = self._make_key(key)
            return bool(self.redis_client.delete(redis_key))
        except Exception as e:
            logging.error(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        if not self.enabled:
            return False
        
        try:
            redis_key = self._make_key(key)
            return bool(self.redis_client.exists(redis_key))
        except Exception as e:
            logging.error(f"Redis exists error: {e}")
            return False
    
    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        if not self.enabled:
            return 0
        
        try:
            redis_pattern = self._make_key(pattern)
            keys = self.redis_client.keys(redis_pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logging.error(f"Redis clear pattern error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if not self.enabled:
            return {
                'status': 'disabled',
                'reason': 'Redis not available or connection failed'
            }
        
        try:
            info = self.redis_client.info()
            keys_count = len(self.redis_client.keys(f"{self.prefix}:*"))
            
            return {
                'status': 'enabled',
                'connection': 'active',
                'keys_count': keys_count,
                'memory_used': info.get('used_memory_human', 'unknown'),
                'uptime_seconds': info.get('uptime_in_seconds', 0),
                'redis_version': info.get('redis_version', 'unknown')
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }


class APIResponseCache:
    """Specialized Redis cache for API responses (v1.0 spec compliance)."""
    
    def __init__(self, redis_cache: RedisCache):
        """Initialize with Redis cache instance."""
        self.redis_cache = redis_cache
        self.default_ttl = 300  # 5 minutes for API responses
    
    def cache_api_response(self, endpoint: str, params: Dict[str, Any], 
                          response: Any, ttl_seconds: int = None):
        """
        Cache API response as specified in v1.0 requirements.
        
        Args:
            endpoint: API endpoint path
            params: Request parameters
            response: Response data to cache
            ttl_seconds: Cache TTL (defaults to 5 minutes)
        """
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl
        
        # Create cache key from endpoint and parameters
        param_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"api:{endpoint}:{param_hash}"
        
        # Add metadata
        cached_response = {
            'data': response,
            'endpoint': endpoint,
            'params': params,
            'cached_at': datetime.now().isoformat(),
            'ttl_seconds': ttl_seconds
        }
        
        success = self.redis_cache.set(cache_key, cached_response, ttl_seconds)
        
        if success:
            print(f"   📡 Cached API response: {endpoint} (TTL: {ttl_seconds}s)")
        
        return success
    
    def get_api_response(self, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """Get cached API response."""
        param_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"api:{endpoint}:{param_hash}"
        
        cached_response = self.redis_cache.get(cache_key)
        
        if cached_response:
            print(f"   📡 API cache hit: {endpoint}")
            return cached_response['data']
        
        return None
    
    def invalidate_endpoint(self, endpoint: str):
        """Invalidate all cached responses for an endpoint."""
        pattern = f"api:{endpoint}:*"
        cleared = self.redis_cache.clear_pattern(pattern)
        print(f"   🗑️ Invalidated {cleared} cached responses for {endpoint}")
        return cleared


# Integration with multi-layer cache
def create_redis_layer(redis_url: str = None) -> Optional[RedisCache]:
    """Create Redis cache layer if available."""
    if redis_url is None:
        redis_url = 'redis://localhost:6379'
    
    redis_cache = RedisCache(redis_url)
    
    if redis_cache.enabled:
        return redis_cache
    else:
        print("⚠️ Redis cache layer not available - continuing with SQLite + filesystem layers")
        return None


# Usage example for v1.0 spec compliance:
"""
# In multi_layer_cache.py, add Redis as Layer 4:

def __init__(self, cache_dir: Path = None, redis_url: str = None):
    # ... existing layers ...
    
    # Layer 4: Redis for API responses and distributed caching
    self.redis_cache = create_redis_layer(redis_url)
    if self.redis_cache:
        self.api_cache = APIResponseCache(self.redis_cache)
        print(f"   🌐 Layer 4: Redis (distributed caching)")
    else:
        self.api_cache = None
        print(f"   🌐 Layer 4: Redis (not available)")

def get(self, cache_type: str, key_components: Dict[str, Any]) -> Optional[Any]:
    # ... existing layers 1-3 ...
    
    # Layer 4: Redis for API responses
    if cache_type == 'api_response' and self.redis_cache:
        endpoint = key_components.get('endpoint')
        params = key_components.get('params', {})
        if endpoint:
            result = self.api_cache.get_api_response(endpoint, params)
            if result:
                print(f"   💾 Cache hit: Layer 4 (Redis) - {cache_type}")
                return result
    
    return None

def set(self, cache_type: str, key_components: Dict[str, Any], data: Any, ttl_seconds: int = 3600):
    # ... existing layers 1-3 ...
    
    # Layer 4: Redis for API responses
    if cache_type == 'api_response' and self.redis_cache:
        endpoint = key_components.get('endpoint')
        params = key_components.get('params', {})
        if endpoint:
            self.api_cache.cache_api_response(endpoint, params, data, ttl_seconds)
"""