"""General-purpose performance caching layer for extraction operations."""

import hashlib
import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CacheStrategy(Enum):
    """Cache storage strategies."""

    MEMORY = "memory"
    FILE = "file"
    REDIS = "redis"
    MULTI_TIER = "multi_tier"


class CachePolicy(Enum):
    """Cache eviction policies."""

    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    LFU = "lfu"  # Least Frequently Used


@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""

    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def touch(self):
        """Update access time and count."""
        self.accessed_at = time.time()
        self.access_count += 1


class MemoryCache:
    """In-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: int | None = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: dict[str, CacheEntry] = {}
        self.access_order: list[str] = []
        self.lock = threading.RLock()

    def _evict_lru(self):
        """Evict least recently used items."""
        while len(self.cache) >= self.max_size and self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]

    def _evict_expired(self):
        """Evict expired items."""
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
        for key in expired_keys:
            self.delete(key)

    def get(self, key: str) -> Any | None:
        """Get item from cache."""
        with self.lock:
            self._evict_expired()

            if key not in self.cache:
                return None

            entry = self.cache[key]
            if entry.is_expired():
                self.delete(key)
                return None

            entry.touch()

            # Move to end of access order (most recently used)
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None, metadata: dict | None = None):
        """Set item in cache."""
        with self.lock:
            current_time = time.time()
            ttl_to_use = ttl if ttl is not None else self.default_ttl

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                accessed_at=current_time,
                access_count=1,
                ttl_seconds=ttl_to_use,
                metadata=metadata or {},
            )

            # Remove existing entry if present
            is_update = key in self.cache
            if is_update:
                if key in self.access_order:
                    self.access_order.remove(key)

            # If adding a new entry would exceed max_size, evict first
            if not is_update and len(self.cache) >= self.max_size:
                self._evict_lru()

            self.cache[key] = entry
            self.access_order.append(key)

    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                return True
            return False

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()

    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_entries = len(self.cache)
            expired_count = sum(1 for entry in self.cache.values() if entry.is_expired())

            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "max_size": self.max_size,
                "memory_usage_estimate": sum(
                    len(str(entry.value)) for entry in self.cache.values()
                ),
            }


class FileCache:
    """File-based cache with JSON serialization."""

    def __init__(self, cache_dir: Path, default_ttl: int | None = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.lock = threading.RLock()

    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Hash key to avoid filesystem issues
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Any | None:
        """Get item from file cache."""
        with self.lock:
            file_path = self._get_file_path(key)

            if not file_path.exists():
                return None

            try:
                with open(file_path) as f:
                    data = json.load(f)

                entry = CacheEntry(**data)

                if entry.is_expired():
                    file_path.unlink(missing_ok=True)
                    return None

                # Update access info
                entry.touch()
                with open(file_path, "w") as f:
                    json.dump(entry.__dict__, f)

                return entry.value

            except (json.JSONDecodeError, FileNotFoundError, KeyError):
                file_path.unlink(missing_ok=True)
                return None

    def set(self, key: str, value: Any, ttl: int | None = None, metadata: dict | None = None):
        """Set item in file cache."""
        with self.lock:
            file_path = self._get_file_path(key)
            current_time = time.time()
            ttl_to_use = ttl if ttl is not None else self.default_ttl

            entry = CacheEntry(
                key=key,
                value=value,
                created_at=current_time,
                accessed_at=current_time,
                access_count=1,
                ttl_seconds=ttl_to_use,
                metadata=metadata or {},
            )

            try:
                with open(file_path, "w") as f:
                    json.dump(entry.__dict__, f)
            except (TypeError, ValueError):
                # Handle non-serializable objects
                pass

    def delete(self, key: str) -> bool:
        """Delete item from file cache."""
        with self.lock:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                return True
            return False

    def clear(self):
        """Clear all cache files."""
        with self.lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink(missing_ok=True)

    def cleanup_expired(self):
        """Remove expired cache files."""
        with self.lock:
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    with open(cache_file) as f:
                        data = json.load(f)

                    entry = CacheEntry(**data)
                    if entry.is_expired():
                        cache_file.unlink()

                except (json.JSONDecodeError, KeyError, FileNotFoundError):
                    cache_file.unlink(missing_ok=True)


class RedisCache:
    """Redis-based cache implementation."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int | None = None,
        key_prefix: str = "ecc:",
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("Redis not available. Install with: pip install redis")

        self.redis_client = redis.from_url(redis_url)
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Any | None:
        """Get item from Redis cache."""
        redis_key = self._make_key(key)
        try:
            data = self.redis_client.get(redis_key)
            if data:
                return json.loads(data)
            return None
        except (json.JSONDecodeError, redis.RedisError):
            return None

    def set(self, key: str, value: Any, ttl: int | None = None, metadata: dict | None = None):
        """Set item in Redis cache."""
        redis_key = self._make_key(key)
        ttl_to_use = ttl if ttl is not None else self.default_ttl

        try:
            data = json.dumps(value)
            if ttl_to_use:
                self.redis_client.setex(redis_key, ttl_to_use, data)
            else:
                self.redis_client.set(redis_key, data)
        except (TypeError, ValueError, redis.RedisError):
            pass

    def delete(self, key: str) -> bool:
        """Delete item from Redis cache."""
        redis_key = self._make_key(key)
        try:
            return bool(self.redis_client.delete(redis_key))
        except redis.RedisError:
            return False

    def clear(self):
        """Clear all keys with prefix."""
        pattern = f"{self.key_prefix}*"
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except redis.RedisError:
            pass


class MultiTierCache:
    """Multi-tier cache with memory -> file -> redis fallback."""

    def __init__(
        self,
        memory_cache: MemoryCache,
        file_cache: FileCache,
        redis_cache: RedisCache | None = None,
    ):
        self.memory_cache = memory_cache
        self.file_cache = file_cache
        self.redis_cache = redis_cache
        self.tiers = [memory_cache, file_cache]
        if redis_cache:
            self.tiers.append(redis_cache)

    def get(self, key: str) -> Any | None:
        """Get from cache, checking tiers in order."""
        for i, cache in enumerate(self.tiers):
            value = cache.get(key)
            if value is not None:
                # Promote to higher tiers
                for j in range(i):
                    self.tiers[j].set(key, value)
                return value
        return None

    def set(self, key: str, value: Any, ttl: int | None = None, metadata: dict | None = None):
        """Set in all cache tiers."""
        for cache in self.tiers:
            cache.set(key, value, ttl, metadata)

    def delete(self, key: str) -> bool:
        """Delete from all cache tiers."""
        deleted = False
        for cache in self.tiers:
            if cache.delete(key):
                deleted = True
        return deleted

    def clear(self):
        """Clear all cache tiers."""
        for cache in self.tiers:
            cache.clear()


class PerformanceCache:
    """Main performance cache interface with multiple strategies."""

    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.MEMORY,
        cache_dir: Path | None = None,
        redis_url: str | None = None,
        max_memory_size: int = 1000,
        default_ttl: int | None = 3600,
    ):  # 1 hour default
        self.strategy = strategy
        self.default_ttl = default_ttl

        if strategy == CacheStrategy.MEMORY:
            self.cache = MemoryCache(max_memory_size, default_ttl)

        elif strategy == CacheStrategy.FILE:
            if cache_dir is None:
                cache_dir = Path.cwd() / ".cache" / "ecc"
            self.cache = FileCache(cache_dir, default_ttl)

        elif strategy == CacheStrategy.REDIS:
            if redis_url is None:
                redis_url = "redis://localhost:6379"
            self.cache = RedisCache(redis_url, default_ttl)

        elif strategy == CacheStrategy.MULTI_TIER:
            memory = MemoryCache(max_memory_size, default_ttl)
            if cache_dir is None:
                cache_dir = Path.cwd() / ".cache" / "ecc"
            file_cache = FileCache(cache_dir, default_ttl)

            redis_cache = None
            if redis_url and REDIS_AVAILABLE:
                try:
                    redis_cache = RedisCache(redis_url, default_ttl)
                except Exception:
                    pass  # Redis not available

            self.cache = MultiTierCache(memory, file_cache, redis_cache)

        else:
            raise ValueError(f"Unknown cache strategy: {strategy}")

    def get(self, key: str) -> Any | None:
        """Get item from cache."""
        return self.cache.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None, metadata: dict | None = None):
        """Set item in cache."""
        self.cache.set(key, value, ttl, metadata)

    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        return self.cache.delete(key)

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()

    def cached(self, ttl: int | None = None, key_func: Callable | None = None):
        """Decorator for caching function results."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # Default key generation
                    key_parts = [func.__name__]
                    if args:
                        key_parts.extend(str(arg) for arg in args)
                    if kwargs:
                        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

                # Try to get from cache
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute function and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result

            return wrapper

        return decorator

    def memoize(self, ttl: int | None = None):
        """Simple memoization decorator."""
        return self.cached(ttl)


# Convenience functions and decorators
def create_cache(strategy: CacheStrategy = CacheStrategy.MEMORY, **kwargs) -> PerformanceCache:
    """Create a performance cache with specified strategy."""
    return PerformanceCache(strategy, **kwargs)


def cached_operation(cache: PerformanceCache, ttl: int | None = None):
    """Decorator for caching operation results."""
    return cache.cached(ttl)


# Domain-specific cache helpers for extraction operations
class ExtractionCache:
    """Specialized cache for extraction operations."""

    def __init__(self, cache: PerformanceCache):
        self.cache = cache

    def cache_popup_content(self, url: str, content: str, ttl: int = 300):
        """Cache popup content for 5 minutes by default."""
        key = f"popup:{hashlib.md5(url.encode()).hexdigest()}"
        self.cache.set(key, content, ttl)

    def get_popup_content(self, url: str) -> str | None:
        """Get cached popup content."""
        key = f"popup:{hashlib.md5(url.encode()).hexdigest()}"
        return self.cache.get(key)

    def cache_email_lookup(self, popup_url: str, email: str, ttl: int = 3600):
        """Cache email extraction result."""
        key = f"email:{hashlib.md5(popup_url.encode()).hexdigest()}"
        self.cache.set(key, email, ttl)

    def get_cached_email(self, popup_url: str) -> str | None:
        """Get cached email for popup URL."""
        key = f"email:{hashlib.md5(popup_url.encode()).hexdigest()}"
        return self.cache.get(key)

    def cache_referee_data(self, referee_name: str, data: dict[str, Any], ttl: int = 86400):
        """Cache referee data for 24 hours."""
        key = f"referee:{hashlib.md5(referee_name.encode()).hexdigest()}"
        self.cache.set(key, data, ttl)

    def get_cached_referee(self, referee_name: str) -> dict[str, Any] | None:
        """Get cached referee data."""
        key = f"referee:{hashlib.md5(referee_name.encode()).hexdigest()}"
        return self.cache.get(key)

    def cache_manuscript_status(self, manuscript_id: str, status: str, ttl: int = 1800):
        """Cache manuscript status for 30 minutes."""
        key = f"status:{manuscript_id}"
        self.cache.set(key, status, ttl)

    def get_cached_status(self, manuscript_id: str) -> str | None:
        """Get cached manuscript status."""
        key = f"status:{manuscript_id}"
        return self.cache.get(key)


# Usage examples and integration patterns
def create_extraction_cache(strategy: CacheStrategy = CacheStrategy.MULTI_TIER) -> ExtractionCache:
    """Create a cache optimized for extraction operations."""
    base_cache = create_cache(
        strategy=strategy,
        max_memory_size=2000,
        default_ttl=3600,  # 1 hour
        cache_dir=Path.cwd() / ".cache" / "extraction",
    )
    return ExtractionCache(base_cache)
