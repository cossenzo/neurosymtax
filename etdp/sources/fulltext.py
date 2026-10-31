"""Full text of articles (open-access PDFs) and of web pages (HTML or PDF)."""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Optional

import requests

from ..config import ScholarlyConfig
from .http import USER_AGENT, SearchResult, get_json

logger = logging.getLogger(__name__)

Page = tuple[int, str]  # (1-based page number, text)


def extract_pdf_pages(data: bytes) -> list[Page]:
    import pymupdf

    pages: list[Page] = []
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        for i, page in enumerate(pdf, start=1):
            text = page.get_text("text") or ""
            pages.append((i, re.sub(r"-\n(?=[a-z])", "", text)))
    return pages


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "header", "svg", "form"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article", "td"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def fetch_page(url: str, timeout: float, max_chars: int) -> str:
    """Text of a web page or of a PDF reached through the web ('' when it cannot be read)."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (research software)"})
        if resp.status_code != 200:
            return ""
        kind = resp.headers.get("Content-Type", "").lower()
        if "pdf" in kind or resp.content[:5] == b"%PDF-":
            return "\n\n".join(t for _, t in extract_pdf_pages(resp.content))[:max_chars]
        return html_to_text(resp.text)[:max_chars]
    except Exception as exc:  # noqa: BLE001 – an unreadable page is skipped
        logger.debug("page not read %s: %s", url, exc)
        return ""


class FullTextFetcher:
    """Downloads open-access PDFs (links of the database, then Unpaywall) and extracts their text."""

    def __init__(self, cfg: ScholarlyConfig, min_chars: int) -> None:
        self.cfg = cfg
        self.min_chars = min_chars
        self.headers = {"User-Agent": USER_AGENT.format(email=cfg.contact_email), "Accept": "application/pdf,*/*;q=0.8"}

    def _unpaywall(self, doi: str) -> list[str]:
        try:
            data = get_json(f"https://api.unpaywall.org/v2/{doi}", params={"email": self.cfg.contact_email},
                            timeout=self.cfg.request_timeout_s)
        except Exception:  # noqa: BLE001
            return []
        urls = []
        for loc in [data.get("best_oa_location") or {}] + list(data.get("oa_locations") or []):
            url = (loc or {}).get("url_for_pdf")
            if url and url not in urls:
                urls.append(url)
        return urls

    def _pdf(self, url: str) -> Optional[list[Page]]:
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.cfg.pdf_timeout_s, stream=True)
            if resp.status_code != 200:
                return None
            data, size = [], 0
            for chunk in resp.iter_content(65536):
                size += len(chunk)
                if size > self.cfg.max_pdf_mb * 1024 * 1024:
                    return None
                data.append(chunk)
            raw = b"".join(data)
            if raw[:5] != b"%PDF-":
                return None
            pages = extract_pdf_pages(raw)
        except Exception as exc:  # noqa: BLE001 – try the next link
            logger.debug("PDF not read %s: %s", url, exc)
            return None
        return pages if sum(len(t) for _, t in pages) >= self.min_chars else None

    def fetch(self, result: SearchResult) -> Optional[list[Page]]:
        urls = list(result.pdf_urls)
        if self.cfg.unpaywall_fallback and result.doi:
            urls += [u for u in self._unpaywall(result.doi) if u not in urls]
        for url in urls:
            pages = self._pdf(url)
            if pages:
                return pages
        return None
