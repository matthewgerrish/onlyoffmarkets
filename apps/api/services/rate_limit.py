"""Tiny in-memory token-bucket rate limiter.

Keyed by (route, identity) where identity = user_id || client IP.
Per-process — fine for a single Fly machine; switch to Redis when we
scale horizontally.

Usage:
    from services.rate_limit import limiter
    limiter.check("checkout_membership", identity, max=5, per_seconds=60)
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException

log = logging.getLogger(__name__)


@dataclass
class _Bucket:
    timestamps: deque[float]


class _Limiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, route: str, identity: str, *, max: int, per_seconds: float) -> None:
        """Raise HTTPException(429) if identity is over the limit."""
        if not identity:
            identity = "_anon"
        key = f"{route}:{identity}"
        now = time.monotonic()
        cutoff = now - per_seconds
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(timestamps=deque(maxlen=max + 1))
                self._buckets[key] = bucket
            # Drop expired timestamps from the front.
            while bucket.timestamps and bucket.timestamps[0] < cutoff:
                bucket.timestamps.popleft()
            if len(bucket.timestamps) >= max:
                retry_after = max(1, int(per_seconds - (now - bucket.timestamps[0])))
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: {max} requests per {int(per_seconds)}s",
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.timestamps.append(now)


limiter = _Limiter()


def client_identity(request_or_user_id) -> str:
    """Resolve a stable identity for a request — user_id when known."""
    if isinstance(request_or_user_id, str) and request_or_user_id:
        return request_or_user_id
    # Fall back to client IP if a starlette Request was passed.
    try:
        return f"ip:{request_or_user_id.client.host}"  # type: ignore[attr-defined]
    except Exception:
        return "_anon"
