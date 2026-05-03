"""
Base scraper class.

Every source-specific scraper subclasses `BaseScraper` and implements
`run() -> Iterable[RawLead]`. The base class handles:

  - Rate-limited httpx session (1 req/sec default)
  - Polite User-Agent identifying the site + contact URL
  - robots.txt check on first fetch — exits if disallowed
  - Per-source local cache (filesystem) so repeated runs don't
    re-hammer a source while you're debugging the parser
  - Pluggable retry/backoff on 5xx and connection errors

Subclasses should never instantiate httpx directly. Use `self.get(url)`.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import urllib.robotparser
from pathlib import Path
from typing import Iterable, AsyncIterable

import httpx

from scrapers.models import RawLead

log = logging.getLogger(__name__)


DEFAULT_USER_AGENT = (
    "OnlyOffMarkets-Scraper/0.2 "
    "(+https://onlyoffmarkets.com/about; hello@onlyoffmarkets.com)"
)

# Cache files older than this get cleaned up on scraper init.
_CACHE_PRUNE_AGE_SEC = 7 * 24 * 60 * 60   # 7 days
_CACHE_PRUNE_MAX_FILES = 5000              # absolute hard cap per source


class BaseScraper:
    """Override `source`, `source_name`, and `run()` in subclasses."""

    source: str = "unknown"
    source_name: str = "Unknown source"

    # Seconds between requests to the same host.
    rate_limit_sec: float = 1.0

    # How long to cache raw HTML/JSON on disk (in seconds).
    cache_ttl: int = 24 * 60 * 60  # 1 day by default

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path(".scraper_cache") / self.source
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._prune_cache()
        self._last_request_at: float = 0.0
        self._robots_checked: dict[str, bool] = {}
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    def _prune_cache(self) -> None:
        """Drop cache entries older than _CACHE_PRUNE_AGE_SEC and cap total
        files to _CACHE_PRUNE_MAX_FILES so a long-lived volume can't fill up.
        Best-effort: any IO error logs and skips pruning that file."""
        try:
            now = time.time()
            files = list(self.cache_dir.glob("*.html"))
            # Drop expired
            for f in files:
                try:
                    if now - f.stat().st_mtime > _CACHE_PRUNE_AGE_SEC:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
            # Cap total
            files = sorted(self.cache_dir.glob("*.html"), key=lambda p: p.stat().st_mtime)
            if len(files) > _CACHE_PRUNE_MAX_FILES:
                for f in files[: len(files) - _CACHE_PRUNE_MAX_FILES]:
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        pass
        except Exception as exc:
            log.debug("cache prune failed for %s: %s", self.source, exc)

    # ---------- abstract ----------

    async def run(self) -> AsyncIterable[RawLead]:
        """Subclass contract: yield one RawLead at a time."""
        raise NotImplementedError
        yield  # for type-checker

    # ---------- fetch helpers ----------

    async def _robots_ok(self, url: str) -> bool:
        """Check robots.txt once per host. Caches result."""
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        if host in self._robots_checked:
            return self._robots_checked[host]

        try:
            r = await self._client.get(f"https://{host}/robots.txt")
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(r.text.splitlines())
            allowed = rp.can_fetch(DEFAULT_USER_AGENT, url)
        except Exception as e:
            log.warning("robots.txt check failed for %s: %s — proceeding.", host, e)
            allowed = True

        self._robots_checked[host] = allowed
        if not allowed:
            log.error("Scraper %s disallowed by robots.txt at %s — skipping.", self.source, url)
        return allowed

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.rate_limit_sec:
            await asyncio.sleep(self.rate_limit_sec - elapsed)
        self._last_request_at = time.monotonic()

    def _cache_path(self, url: str) -> Path:
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.cache_dir / f"{h}.html"

    async def get(self, url: str, *, params: dict | None = None, use_cache: bool = True) -> str:
        """GET a URL with rate-limiting + on-disk cache + robots.txt check."""
        if not await self._robots_ok(url):
            raise PermissionError(f"robots.txt forbids {url}")

        cache_file = self._cache_path(url + (f"?{params}" if params else ""))
        if use_cache and cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < self.cache_ttl:
                log.debug("Cache hit (%ds old): %s", int(age), url)
                return cache_file.read_text(encoding="utf-8")

        await self._throttle()
        log.info("GET %s", url)

        for attempt in range(3):
            try:
                r = await self._client.get(url, params=params)
                r.raise_for_status()
                cache_file.write_text(r.text, encoding="utf-8")
                return r.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    raise
                log.warning("5xx attempt %d for %s: %s", attempt + 1, url, e)
            except httpx.RequestError as e:
                log.warning("connection error attempt %d for %s: %s", attempt + 1, url, e)
            await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"Failed to GET {url} after retries")

    async def close(self):
        await self._client.aclose()
