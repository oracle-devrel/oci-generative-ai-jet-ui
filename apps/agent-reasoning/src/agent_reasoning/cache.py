"""Lightweight response cache for agent reasoning.

Caches LLM responses by (model, strategy, query) tuple to avoid
redundant calls during benchmarking, testing, and repeated queries.
Thread-safe with TTL expiration.
"""

import hashlib
import threading
import time
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """A cached response with metadata."""

    response: str
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0


class ResponseCache:
    """Thread-safe LRU cache with TTL for agent responses.

    Args:
        max_size: Maximum number of entries (default 256)
        ttl: Time-to-live in seconds (default 3600 = 1 hour)
        enabled: Whether caching is active (default True)
    """

    def __init__(self, max_size=256, ttl=3600, enabled=True):
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self.max_size = max_size
        self.ttl = ttl
        self.enabled = enabled
        self._hits = 0
        self._misses = 0

    def _make_key(self, model: str, strategy: str, query: str) -> str:
        """Create a deterministic cache key."""
        raw = f"{model}|{strategy}|{query}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, model: str, strategy: str, query: str) -> str | None:
        """Look up a cached response. Returns None on miss."""
        if not self.enabled:
            return None
        key = self._make_key(model, strategy, query)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() - entry.created_at > self.ttl:
                del self._cache[key]
                self._misses += 1
                return None
            entry.hit_count += 1
            self._hits += 1
            return entry.response

    def put(self, model: str, strategy: str, query: str, response: str) -> None:
        """Store a response in the cache."""
        if not self.enabled:
            return
        key = self._make_key(model, strategy, query)
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Evict oldest entry
                oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]
            self._cache[key] = CacheEntry(response=response)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0.0,
                "enabled": self.enabled,
            }
