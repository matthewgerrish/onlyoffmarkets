"""
Tiny cache wrapper. Redis if available, in-process dict otherwise.

NWMLS doesn't love apps hitting them hard. Use it.
"""
from __future__ import annotations

import time
import json
import asyncio
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from config import settings


class _MemCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            v = self._data.get(key)
            if not v:
                return None
            exp, payload = v
            if time.time() > exp:
                self._data.pop(key, None)
                return None
            return payload

    async def setex(self, key: str, ttl: int, value: str) -> None:
        async with self._lock:
            self._data[key] = (time.time() + ttl, value)

    async def delete(self, *keys: str) -> None:
        async with self._lock:
            for k in keys:
                self._data.pop(k, None)


class Cache:
    def __init__(self) -> None:
        self._redis = None
        self._mem = _MemCache()

    async def _conn(self):
        if self._redis is not None:
            return self._redis
        if aioredis is None:
            return None
        try:
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            await r.ping()
            self._redis = r
            return r
        except Exception:
            return None  # fall back to memory

    async def get_json(self, key: str) -> Any | None:
        r = await self._conn()
        raw = await (r.get(key) if r else self._mem.get(key))
        return json.loads(raw) if raw else None

    async def set_json(self, key: str, ttl: int, value: Any) -> None:
        r = await self._conn()
        payload = json.dumps(value, default=str)
        if r:
            await r.setex(key, ttl, payload)
        else:
            await self._mem.setex(key, ttl, payload)

    async def invalidate_prefix(self, prefix: str) -> None:
        r = await self._conn()
        if r:
            keys = [k async for k in r.scan_iter(match=f"{prefix}*")]
            if keys:
                await r.delete(*keys)
        else:
            async with self._mem._lock:
                for k in [k for k in self._mem._data if k.startswith(prefix)]:
                    self._mem._data.pop(k, None)


cache = Cache()
