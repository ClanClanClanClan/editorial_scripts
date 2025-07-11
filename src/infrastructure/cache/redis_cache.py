"""
Redis cache implementation
Provides async caching with automatic serialization
"""

import json
import logging
from typing import Optional, Any, List
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.exceptions import RedisError

from ...core.domain.ports import CacheService
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisCache(CacheService):
    """Redis implementation of cache service"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.client = redis_client
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize Redis connection"""
        if self._initialized:
            return
            
        if not self.client:
            self.client = redis.from_url(
                settings.redis.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.redis.max_connections
            )
            
        # Test connection
        try:
            await self.client.ping()
            self._initialized = True
            logger.info("Redis cache initialized successfully")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._initialized:
            await self.initialize()
            
        try:
            value = await self.client.get(key)
            
            if value is None:
                return None
                
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # Return as string if not JSON
                return value
                
        except RedisError as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Serialize to JSON if not string
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, default=str)
            elif not isinstance(value, str):
                value = str(value)
                
            # Use default TTL if not specified
            ttl = ttl or settings.redis.default_ttl
            
            await self.client.setex(key, ttl, value)
            
        except RedisError as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        if not self._initialized:
            await self.initialize()
            
        try:
            await self.client.delete(key)
        except RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Use SCAN to find matching keys
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
                
            if keys:
                return await self.client.delete(*keys)
            return 0
            
        except RedisError as e:
            logger.warning(f"Cache clear pattern error for {pattern}: {e}")
            return 0
            
    # Additional utility methods
    
    async def get_or_set(self, key: str, fetch_func, ttl: Optional[int] = None) -> Any:
        """Get from cache or fetch and set"""
        # Try cache first
        cached = await self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached
            
        # Fetch fresh data
        logger.debug(f"Cache miss for key: {key}")
        value = await fetch_func()
        
        # Cache the result
        await self.set(key, value, ttl)
        
        return value
        
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        if not self._initialized:
            await self.initialize()
            
        try:
            return await self.client.incrby(key, amount)
        except RedisError as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return 0
            
    async def add_to_set(self, key: str, *values: str) -> int:
        """Add values to a set"""
        if not self._initialized:
            await self.initialize()
            
        try:
            return await self.client.sadd(key, *values)
        except RedisError as e:
            logger.warning(f"Cache set add error for key {key}: {e}")
            return 0
            
    async def get_set_members(self, key: str) -> List[str]:
        """Get all members of a set"""
        if not self._initialized:
            await self.initialize()
            
        try:
            return list(await self.client.smembers(key))
        except RedisError as e:
            logger.warning(f"Cache set get error for key {key}: {e}")
            return []
            
    async def set_hash(self, key: str, mapping: dict) -> None:
        """Set multiple hash fields"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Convert values to strings
            str_mapping = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                          for k, v in mapping.items()}
            await self.client.hset(key, mapping=str_mapping)
        except RedisError as e:
            logger.warning(f"Cache hash set error for key {key}: {e}")
            
    async def get_hash(self, key: str) -> dict:
        """Get all hash fields"""
        if not self._initialized:
            await self.initialize()
            
        try:
            data = await self.client.hgetall(key)
            # Try to deserialize JSON values
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except json.JSONDecodeError:
                    result[k] = v
            return result
        except RedisError as e:
            logger.warning(f"Cache hash get error for key {key}: {e}")
            return {}
            
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self._initialized = False
            logger.info("Redis cache connection closed")


# Cache key builders

def manuscript_key(journal_code: str, manuscript_id: str) -> str:
    """Build cache key for manuscript"""
    return f"manuscript:{journal_code}:{manuscript_id}"


def referee_key(email: str) -> str:
    """Build cache key for referee"""
    return f"referee:{email}"


def referee_stats_key(referee_id: str) -> str:
    """Build cache key for referee statistics"""
    return f"referee_stats:{referee_id}"


def extraction_result_key(journal_code: str, date: datetime) -> str:
    """Build cache key for extraction result"""
    return f"extraction:{journal_code}:{date.strftime('%Y%m%d')}"


def session_key(journal_code: str, session_id: str) -> str:
    """Build cache key for browser session"""
    return f"session:{journal_code}:{session_id}"


# Global cache instance
_cache: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """Get or create global cache instance"""
    global _cache
    if _cache is None:
        _cache = RedisCache()
        await _cache.initialize()
    return _cache


async def close_cache() -> None:
    """Close global cache instance"""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None