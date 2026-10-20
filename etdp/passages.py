"""[symbolic] Passages of the articles that mention an object, and the frequency of its mentions.

The passages are the only evidence the classifier sees about an object (see ``classify.py``).
"""

from __future__ import annotations

import re

from .sources.fulltext import Page

_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9\"'(\[])")


def name_pattern(names: list[str]) -> re.Pattern:
    """Whole-word, case-insensitive pattern for any of ``names`` (spaces and hyphens are interchangeable)."""
    parts = []
    for n in sorted({" ".join(n.split()) for n in names if n and len(n.strip()) >= 2}, key=len, reverse=True):
        words = [re.escape(w) for w in re.split(r"[\s\-]+", n) if w]
        if words:
            parts.append(r"[\s\-]+".join(words))
    if not parts:
        return re.compile(r"(?!x)x")
    return re.compile(r"(?<![\w])(?:" + "|".join(parts) + r")(?![\w])", re.IGNORECASE)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_passages(pages: list[Page], names: list[str], max_chars: int, limit: int) -> tuple[list[tuple[int, str]], int]:
    """Return ``(passages, mentions)``: up to ``limit`` distinct passages (a sentence with the next one, at most
    ``max_chars`` characters) that mention one of ``names``, and the total number of mentions in ``pages``.

    The most informative passages (longest first) are kept."""
    pattern = name_pattern(names)
    mentions = 0
    found: dict[str, int] = {}
    for page, text in pages:
        flat = text.replace("\n\n", " \n ").replace("\n", " ")
        sentences = [s for s in _SENTENCE_END.split(flat) if s.strip()]
        for i, sentence in enumerate(sentences):
            hits = len(pattern.findall(sentence))
            if not hits:
                continue
            mentions += hits
            passage = _clean(sentence)
            if len(passage) < max_chars // 2 and i + 1 < len(sentences):
                passage = _clean(passage + " " + sentences[i + 1])
            if len(passage) > max_chars:
                m = pattern.search(passage)
                start = max(0, (m.start() if m else 0) - max_chars // 3)
                passage = passage[start : start + max_chars].strip()
            found.setdefault(passage, page)
    ranked = sorted(found.items(), key=lambda kv: len(kv[0]), reverse=True)[:limit]
    return [(page, text) for text, page in ranked], mentions


def count_mentions(pages: list[Page], names: list[str]) -> int:
    pattern = name_pattern(names)
    return sum(len(pattern.findall(text.replace("\n", " "))) for _, text in pages)
