"""OpenAlex search provider (default). https://docs.openalex.org"""

from __future__ import annotations

import logging
import os
from typing import Optional

from .http import USER_AGENT, SearchProvider, SearchResult, Throttle, get_json

logger = logging.getLogger(__name__)

API_URL = "https://api.openalex.org/works"


def reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """Rebuild an abstract from OpenAlex's ``abstract_inverted_index``."""
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        positions.extend((i, word) for i in idxs)
    return " ".join(word for _, word in sorted(positions))


def parse_work(work: dict) -> SearchResult:
    """Convert one OpenAlex work record into a :class:`SearchResult`."""
    pdf_urls: list[str] = []
    best = work.get("best_oa_location") or {}
    for loc in [best] + list(work.get("locations") or []):
        url = (loc or {}).get("pdf_url")
        if url and url not in pdf_urls:
            pdf_urls.append(url)
    oa_url = (work.get("open_access") or {}).get("oa_url")
    if oa_url and oa_url not in pdf_urls:
        pdf_urls.append(oa_url)
    doi = work.get("doi")
    if doi:
        doi = doi.replace("https://doi.org/", "").lower()
    wid = str(work.get("id", "")).rsplit("/", 1)[-1]
    return SearchResult(
        id=wid,
        title=work.get("display_name") or work.get("title") or "",
        doi=doi,
        year=work.get("publication_year"),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        pdf_urls=pdf_urls,
        landing_url=best.get("landing_page_url") or work.get("id"),
    )


class OpenAlexProvider(SearchProvider):
    name = "openalex"

    def __init__(self, contact_email: str, timeout: float = 60.0, open_access_only: bool = False,
                 min_interval_s: float = 0.2) -> None:
        self.contact_email = contact_email
        self.timeout = timeout
        self.open_access_only = open_access_only
        self.throttle = Throttle(min_interval_s)
        self.api_key = os.environ.get("OPENALEX_API_KEY", "").strip() or None

    def search(self, query: str, limit: int, year_range: Optional[tuple[int, int]] = None) -> list[SearchResult]:
        filters = ["is_oa:true"] if self.open_access_only else []
        if year_range:
            filters.append(f"publication_year:{year_range[0]}-{year_range[1]}")
        results: list[SearchResult] = []
        page = 1
        while len(results) < limit:
            per_page = min(200, limit - len(results))
            params = {"search": query, "per-page": per_page, "page": page, "mailto": self.contact_email}
            if filters:
                params["filter"] = ",".join(filters)
            if self.api_key:
                params["api_key"] = self.api_key
            self.throttle.wait()
            data = get_json(API_URL, params=params, timeout=self.timeout,
                            headers={"User-Agent": USER_AGENT.format(email=self.contact_email)})
            works = data.get("results") or []
            results.extend(parse_work(w) for w in works)
            if len(works) < per_page:
                break
            page += 1
        logger.info("OpenAlex: %d results for %r (year=%s, open_access_only=%s)",
                    len(results), query, year_range, self.open_access_only)
        return results[:limit]
