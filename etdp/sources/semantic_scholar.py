"""Semantic Scholar search provider. https://api.semanticscholar.org/api-docs/graph"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .http import USER_AGENT, SearchProvider, SearchResult, Throttle, get_json

logger = logging.getLogger(__name__)

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,year,externalIds,openAccessPdf,abstract,url"


def parse_paper(paper: dict) -> SearchResult:
    """Convert one Semantic Scholar paper record into a :class:`SearchResult`.

    Besides the open-access PDF link, an arXiv preprint (when the paper has an arXiv id)
    is added as a full-text source, which greatly increases the share of usable records."""
    ids = paper.get("externalIds") or {}
    pdf_urls: list[str] = []
    pdf = (paper.get("openAccessPdf") or {}).get("url")
    if pdf:
        pdf_urls.append(pdf)
    arxiv = ids.get("ArXiv")
    if arxiv:
        pdf_urls.append(f"https://arxiv.org/pdf/{arxiv}")
    doi = ids.get("DOI")
    return SearchResult(
        id=str(paper.get("paperId", "")),
        title=paper.get("title") or "",
        doi=doi.lower() if doi else None,
        year=paper.get("year"),
        abstract=paper.get("abstract") or "",
        pdf_urls=pdf_urls,
        landing_url=paper.get("url"),
    )


class SemanticScholarProvider(SearchProvider):
    name = "semantic_scholar"

    def __init__(self, contact_email: str, timeout: float = 60.0, open_access_only: bool = False,
                 min_interval_s: float = 1.1) -> None:
        self.contact_email = contact_email
        self.timeout = timeout
        self.open_access_only = open_access_only
        self.throttle = Throttle(min_interval_s)
        self.api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip() or None
        if not self.api_key:
            logger.warning("SEMANTIC_SCHOLAR_API_KEY not set: unauthenticated requests share a public "
                           "rate limit and are often refused (HTTP 429)")

    def search(self, query: str, limit: int, year_range: Optional[tuple[int, int]] = None) -> list[SearchResult]:
        headers = {"User-Agent": USER_AGENT.format(email=self.contact_email)}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        results: list[SearchResult] = []
        offset = 0
        while len(results) < limit:
            batch = min(100, limit - len(results))
            params = {"query": query, "fields": FIELDS, "limit": batch, "offset": offset}
            if self.open_access_only:
                params["openAccessPdf"] = ""
            if year_range:
                params["year"] = f"{year_range[0]}-{year_range[1]}"
            self.throttle.wait()
            data = get_json(API_URL, params=params, headers=headers, timeout=self.timeout)
            papers = data.get("data") or []
            results.extend(parse_paper(p) for p in papers)
            if len(papers) < batch or data.get("next") is None:
                break
            offset += batch
        logger.info("Semantic Scholar: %d results for %r (year=%s, open_access_only=%s)",
                    len(results), query, year_range, self.open_access_only)
        return results[:limit]
