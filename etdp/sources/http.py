"""Search provider interface and shared HTTP helpers (retries with exponential back-off)."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

USER_AGENT = "taxonomy_builder/1.0 (research software; mailto:{email})"


@dataclass
class SearchResult:
    """A bibliographic record returned by a search provider."""

    id: str
    title: str = ""
    doi: Optional[str] = None
    year: Optional[int] = None
    abstract: str = ""
    pdf_urls: list[str] = field(default_factory=list)
    landing_url: Optional[str] = None


class Throttle:
    """Ensures a minimum interval between consecutive requests (provider rate limits)."""

    def __init__(self, min_interval_s: float) -> None:
        self.min_interval_s = min_interval_s
        self._last = 0.0

    def wait(self) -> None:
        delay = self._last + self.min_interval_s - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


class TransientHTTPError(RuntimeError):
    """HTTP 429 or 5xx – worth retrying."""


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, (TransientHTTPError, requests.ConnectionError, requests.Timeout))


MAX_RETRY_AFTER_S = 300.0


def _retry_after_seconds(resp: requests.Response) -> Optional[float]:
    """Seconds requested by a ``Retry-After`` header (numeric form), if any."""
    value = resp.headers.get("Retry-After", "").strip()
    try:
        return min(float(value), MAX_RETRY_AFTER_S) if value else None
    except ValueError:
        return None


@retry(retry=retry_if_exception(_is_transient), wait=wait_exponential(multiplier=2, min=4, max=120),
       stop=stop_after_attempt(6), reraise=True)
def http_get(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None,
             timeout: float = 60.0, stream: bool = False) -> requests.Response:
    """GET with patient retries for connection errors, timeouts, HTTP 429 and 5xx.

    Waits grow exponentially (4, 8, 16, 32, 64 s; 6 attempts, about 2 minutes in total);
    a ``Retry-After`` header sent with HTTP 429 is honoured before the next attempt."""
    resp = requests.get(url, params=params, headers=headers, timeout=timeout, stream=stream)
    if resp.status_code == 429 or resp.status_code >= 500:
        wait = _retry_after_seconds(resp)
        if resp.status_code == 429:
            logger.warning("HTTP 429 (rate limit) from %s; waiting before retrying%s", url.split("?")[0],
                           f" ({wait:.0f} s requested)" if wait else "")
        if wait:
            time.sleep(wait)
        raise TransientHTTPError(f"HTTP {resp.status_code} for {url.split('?')[0]}")
    return resp


def get_json(url: str, *, params: Optional[dict] = None, headers: Optional[dict] = None,
             timeout: float = 60.0) -> Any:
    resp = http_get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class SearchProvider(ABC):
    """Interface implemented by every literature search back-end."""

    name: str = "abstract"

    @abstractmethod
    def search(self, query: str, limit: int, year_range: Optional[tuple[int, int]] = None) -> list[SearchResult]:
        """Return up to ``limit`` results, in relevance order, restricted to open access when possible."""


class FallbackSearchProvider(SearchProvider):
    """Uses ``primary``; if a search fails (e.g. persistent HTTP 429), the same query is sent to
    ``fallback``. After ``max_failures`` consecutive failures the primary is skipped for the rest
    of the run, so rate-limit waits are not repeated for every query."""

    def __init__(self, primary: SearchProvider, fallback: SearchProvider, max_failures: int = 2) -> None:
        self.primary = primary
        self.fallback = fallback
        self.max_failures = max_failures
        self.failures = 0
        self.name = f"{primary.name}+{fallback.name}"

    def search(self, query: str, limit: int, year_range: Optional[tuple[int, int]] = None) -> list[SearchResult]:
        if self.failures < self.max_failures:
            try:
                results = self.primary.search(query, limit, year_range)
                self.failures = 0
                return results
            except Exception as exc:  # noqa: BLE001 – any failure of the primary triggers the fallback
                self.failures += 1
                logger.warning("%s search failed (%s); using %s for this query%s", self.primary.name, exc,
                               self.fallback.name,
                               " and for the rest of the run" if self.failures >= self.max_failures else "")
        return self.fallback.search(query, limit, year_range)
