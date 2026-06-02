"""Centralized Redis connection pool for caching and task queues."""
import redis.asyncio as redis_async
from bot.config import settings

_redis_pool: redis_async.Redis | None = None


async def get_redis() -> redis_async.Redis:
    """Get or create a shared Redis connection pool.
    
    Returns a singleton Redis client backed by a connection pool,
    avoiding per-request TCP connection overhead.
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis_async.from_url(
            settings.redis_url,
            decode_responses=False,
            max_connections=10,
        )
    return _redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool gracefully."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None
