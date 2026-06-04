"""
Redis cache service for external API responses.

Provides a thin wrapper around Redis with JSON serialization and graceful
fallback — if Redis is unavailable, every operation silently returns None
so the caller falls through to the live API.

Usage:
    cache = RedisCache()                        # uses REDIS_URL env var
    cache = RedisCache("redis://localhost:6379") # explicit URL

    cached = cache.get("mealdb:search:chicken")
    if cached is None:
        data = fetch_from_api()
        cache.set("mealdb:search:chicken", data, ttl_seconds=86400)
"""
import json
import logging
import os
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_TTL = 86400  # 24 hours


class RedisCache:
    """Resilient Redis cache with JSON serialization."""

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = DEFAULT_TTL):
        self._url = redis_url or os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)
        self._default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None
        self._available = True  # optimistic; flips on first failure

    def _connect(self) -> Optional[redis.Redis]:
        """Lazy connection — only created on first cache operation."""
        if self._client is not None:
            return self._client
        if not self._available:
            return None
        try:
            self._client = redis.Redis.from_url(
                self._url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Verify the connection is alive
            self._client.ping()
            logger.info("Redis cache connected at %s", self._url)
            return self._client
        except (redis.ConnectionError, redis.TimeoutError, OSError) as exc:
            logger.warning("Redis unavailable, caching disabled: %s", exc)
            self._available = False
            self._client = None
            return None

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value by key. Returns None on miss or error."""
        client = self._connect()
        if client is None:
            return None
        try:
            raw = client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (redis.RedisError, json.JSONDecodeError) as exc:
            logger.warning("Cache GET failed for key '%s': %s", key, exc)
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Store a value with an expiry. Returns True on success."""
        client = self._connect()
        if client is None:
            return False
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        try:
            client.setex(key, ttl, json.dumps(value))
            return True
        except (redis.RedisError, TypeError) as exc:
            logger.warning("Cache SET failed for key '%s': %s", key, exc)
            return False

    @property
    def is_available(self) -> bool:
        """Whether Redis was reachable on last attempt."""
        return self._available
