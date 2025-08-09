# backend/services/redis_client.py
"""
Singleton async Upstash Redis client for the app.
Uses environment variables provided by Upstash:
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
If not present, Redis.from_env() will attempt env-based discovery.
"""

import os
from typing import Optional
from upstash_redis.asyncio import Redis

_redis: Optional[Redis] = None

def get_redis_sync() -> Redis:
    """Return a singleton Redis client (synchronous accessor for module-level usage)."""
    global _redis
    if _redis is None:
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if url and token:
            _redis = Redis(url=url, token=token)
        else:
            # fallback to automatic env loader
            _redis = Redis.from_env()
    return _redis

# async-friendly alias
async def get_redis() -> Redis:
    return get_redis_sync()
