"""Sources of documents: a scholarly database (full texts) and a web search engine."""

from __future__ import annotations

from ..config import ScholarlyConfig, WebConfig
from .fulltext import FullTextFetcher, Page, extract_pdf_pages, fetch_page, html_to_text
from .http import FallbackSearchProvider, SearchProvider, SearchResult
from .openalex import OpenAlexProvider
from .semantic_scholar import SemanticScholarProvider
from .web import NoWebSearch, SearxngSearch, TavilySearch, WebPage, WebSearch

__all__ = ["FullTextFetcher", "Page", "SearchProvider", "SearchResult", "WebPage", "WebSearch",
           "create_scholarly", "create_web", "extract_pdf_pages", "fetch_page", "html_to_text"]


def _make(name: str, cfg: ScholarlyConfig) -> SearchProvider:
    if name == "openalex":
        return OpenAlexProvider(cfg.contact_email, timeout=cfg.request_timeout_s,
                                open_access_only=cfg.open_access_only, min_interval_s=min(cfg.min_request_interval_s, 0.2))
    return SemanticScholarProvider(cfg.contact_email, timeout=cfg.request_timeout_s,
                                   open_access_only=cfg.open_access_only, min_interval_s=cfg.min_request_interval_s)


def create_scholarly(cfg: ScholarlyConfig) -> SearchProvider:
    primary = _make(cfg.provider, cfg)
    if cfg.fallback_provider == "none" or cfg.fallback_provider == cfg.provider:
        return primary
    return FallbackSearchProvider(primary, _make(cfg.fallback_provider, cfg))


def create_web(cfg: WebConfig, max_chars: int) -> WebSearch:
    if cfg.provider == "tavily":
        return TavilySearch(cfg, max_chars)
    if cfg.provider == "searxng":
        return SearxngSearch(cfg, max_chars)
    return NoWebSearch()
