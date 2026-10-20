"""Web search engines: Tavily (API key TAVILY_API_KEY in .env) or a SearXNG instance."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests

from ..config import WebConfig
from .fulltext import fetch_page

logger = logging.getLogger(__name__)


@dataclass
class WebPage:
    url: str
    title: str
    text: str


class WebSearch(ABC):
    @abstractmethod
    def search(self, query: str, n: int) -> list[WebPage]:
        """Up to ``n`` pages, in relevance order, with their text."""


class NoWebSearch(WebSearch):
    def search(self, query: str, n: int) -> list[WebPage]:
        return []


class TavilySearch(WebSearch):
    URL = "https://api.tavily.com/search"

    def __init__(self, cfg: WebConfig, max_chars: int) -> None:
        self.cfg, self.max_chars = cfg, max_chars
        self.key = os.environ.get("TAVILY_API_KEY", "").strip()
        if not self.key:
            raise ValueError("TAVILY_API_KEY is not set in .env (or set web.provider to searxng or none)")

    def search(self, query: str, n: int) -> list[WebPage]:
        if n <= 0:
            return []
        body = {"query": query, "max_results": n, "search_depth": "basic", "include_raw_content": True}
        if self.cfg.exclude_domains:
            body["exclude_domains"] = self.cfg.exclude_domains
        try:
            resp = requests.post(self.URL, json=body, timeout=self.cfg.request_timeout_s,
                                 headers={"Authorization": f"Bearer {self.key}"})
            resp.raise_for_status()
            results = resp.json().get("results") or []
        except Exception as exc:  # noqa: BLE001 – a failed search returns nothing
            logger.error("web search failed for %r: %s", query, exc)
            return []
        pages = []
        for r in results[:n]:
            text = (r.get("raw_content") or "").strip() or fetch_page(r.get("url", ""), self.cfg.request_timeout_s,
                                                                       self.max_chars)
            pages.append(WebPage(url=r.get("url", ""), title=r.get("title", ""), text=text[: self.max_chars]))
        return pages


class SearxngSearch(WebSearch):
    def __init__(self, cfg: WebConfig, max_chars: int) -> None:
        self.cfg, self.max_chars = cfg, max_chars

    def search(self, query: str, n: int) -> list[WebPage]:
        if n <= 0:
            return []
        try:
            resp = requests.get(self.cfg.searxng_url.rstrip("/") + "/search", params={"q": query, "format": "json"},
                                timeout=self.cfg.request_timeout_s)
            resp.raise_for_status()
            results = resp.json().get("results") or []
        except Exception as exc:  # noqa: BLE001
            logger.error("web search failed for %r: %s", query, exc)
            return []
        excluded = tuple(self.cfg.exclude_domains)
        pages = []
        for r in results:
            url = r.get("url", "")
            if not url or (excluded and any(d in url for d in excluded)):
                continue
            pages.append(WebPage(url=url, title=r.get("title", ""),
                                 text=fetch_page(url, self.cfg.request_timeout_s, self.max_chars)))
            if len(pages) >= n:
                break
        return pages
