"""
API Rate Limiter
"""
import asyncio
from datetime import datetime
from typing import Optional
import redis.asyncio as redis


class RateLimiter:
    """Rate limiter for external API calls"""

    def __init__(
        self,
        redis_url: str,
        max_calls_per_minute: int = 60,
        key_prefix: str = "rate_limit",
    ):
        self.redis = redis.from_url(redis_url)
        self.max_calls = max_calls_per_minute
        self.key_prefix = key_prefix

    async def acquire(self, resource: str = "default") -> bool:
        """
        Try to acquire a rate limit slot.
        Returns True if allowed, False if rate limited.
        """
        key = f"{self.key_prefix}:{resource}:{datetime.now().strftime('%Y%m%d%H%M')}"

        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 60)

        if count > self.max_calls:
            return False
        return True

    async def wait_and_acquire(self, resource: str = "default") -> None:
        """Wait until a slot is available"""
        while not await self.acquire(resource):
            await asyncio.sleep(1)

    async def close(self):
        """Close Redis connection"""
        await self.redis.close()


class APICache:
    """Cache for API responses"""

    def __init__(self, redis_url: str, ttl_seconds: int = 86400):
        self.redis = redis.from_url(redis_url)
        self.ttl = ttl_seconds

    async def get(self, key: str) -> Optional[str]:
        """Get cached value"""
        return await self.redis.get(f"cache:{key}")

    async def set(self, key: str, value: str) -> None:
        """Set cached value"""
        await self.redis.setex(f"cache:{key}", self.ttl, value)

    async def delete(self, key: str) -> None:
        """Delete cached value"""
        await self.redis.delete(f"cache:{key}")

    async def close(self):
        """Close Redis connection"""
        await self.redis.close()
