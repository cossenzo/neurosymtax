"""[S] Documents: storage, chunking, retrieval from the two sources, relevant passages and object registration."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import numpy as np

from .models import DescriptionsOut, Document, DomainObject, Evidence, ObjectOut
from .names import find_registered, is_generic
from .passages import count_mentions, find_passages
from .sources.fulltext import Page

if TYPE_CHECKING:
    from .context import Context

logger = logging.getLogger(__name__)

STOPWORDS = {"a", "an", "and", "the", "of", "for", "in", "on", "to", "with", "by", "from", "at", "as", "or",
             "its", "their", "based", "using", "via", "towards", "toward"}


class TextStore:
    """Text of every document read, one JSON file per document (pages)."""

    def __init__(self, run_dir: str | Path) -> None:
        self.dir = Path(run_dir) / "texts"
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, doc_id: str) -> Path:
        return self.dir / (re.sub(r"[^A-Za-z0-9._-]", "_", doc_id)[:120] + ".json")

    def save(self, doc_id: str, pages: list[Page]) -> None:
        self._path(doc_id).write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")

    def load(self, doc_id: str) -> list[Page]:
        path = self._path(doc_id)
        if not path.exists():
            return []
        return [(int(p), str(t)) for p, t in json.loads(path.read_text(encoding="utf-8"))]


class Tokenizer:
    """tiktoken (cl100k_base) when available, otherwise about 1.3 tokens per word."""

    def __init__(self, kind: str = "tiktoken") -> None:
        self._enc = None
        if kind == "tiktoken":
            try:
                import tiktoken

                self._enc = tiktoken.get_encoding("cl100k_base")
            except Exception as exc:  # noqa: BLE001
                logger.warning("tiktoken unavailable (%s); approximate token counts", exc)

    def split(self, text: str, size: int, overlap: int) -> list[str]:
        if not text.strip():
            return []
        if self._enc is not None:
            tokens = self._enc.encode(text)
            return [self._enc.decode(tokens[i: i + size]) for i in range(0, max(len(tokens) - overlap, 1), size - overlap)]
        words = text.split(" ")
        wsize, wover = max(1, int(size / 1.3)), int(overlap / 1.3)
        return [" ".join(words[i: i + wsize]) for i in range(0, max(len(words) - wover, 1), max(1, wsize - wover))]


# --------------------------------------------------------------------------- search strings


def content_words(text: str) -> list[str]:
    return [w for w in re.sub(r"[\"'():;,.!?\[\]{}]", " ", text).split() if w.casefold() not in STOPWORDS]


def fit_query(query: str, low: int, high: int, pad_from: Iterable[str] = ()) -> str:
    """[S] A search string with between ``low`` and ``high`` keywords: cut to ``high``, or completed from
    ``pad_from`` (seed keywords, domain) up to ``low``."""
    words = content_words(query)[:high]
    have = {w.casefold() for w in words}
    for term in pad_from:
        for w in content_words(term):
            if len(words) >= low:
                break
            if w.casefold() not in have:
                words.append(w)
                have.add(w.casefold())
    return " ".join(words)


# --------------------------------------------------------------------------- retrieval (procedure Retrieve)


def _excluded(title: str, doi: str | None, ctx: "Context") -> bool:
    d = ctx.cfg.documents
    doi = (doi or "").lower().removeprefix("https://doi.org/")
    if doi and doi in {x.lower().removeprefix("https://doi.org/") for x in d.exclude_dois}:
        return True
    return any(t.casefold() in (title or "").casefold() for t in d.exclude_titles if t.strip())


def _scholarly(ctx: "Context", query: str, n: int, iteration: int) -> list[str]:
    st, cfg = ctx.state, ctx.cfg
    if n <= 0:
        return []
    # Only the search string is relaxed (the full string, then its 4 and its 2 first content words); the year range
    # of the input and the restriction to open access (a property of the provider) always apply.
    words = content_words(query)
    variants = [query]
    for k in (4, 2):
        short = " ".join(words[:k])
        if short and short not in variants and len(words) > k:
            variants.append(short)
    years = st.input.year_range
    known_dois = {d.doi for d in st.documents.values() if d.doi}
    selected: list[str] = []
    for q in variants:
        if len(selected) >= n:
            break
        try:
            results = ctx.scholarly.search(q, cfg.scholarly.scanned, years)
        except Exception as exc:  # noqa: BLE001 – a failed search moves on to the next variant
            logger.error("scholarly search failed for %r: %s", q, exc)
            continue
        for res in results:
            if len(selected) >= n:
                break
            if not res.id or res.id in st.documents or (res.doi and res.doi in known_dois):
                continue
            if _excluded(res.title, res.doi, ctx):
                logger.info("excluded by configuration: %s", res.title[:80])
                continue
            pages = ctx.fetcher.fetch(res)
            doc = Document(id=res.id, source="scholarly", title=res.title, url=res.landing_url, doi=res.doi,
                           year=res.year, query=q, iteration=iteration,
                           status="processed" if pages else "no_fulltext")
            st.documents[doc.id] = doc
            if pages:
                ctx.store.save(doc.id, pages)
                selected.append(doc.id)
                if res.doi:
                    known_dois.add(res.doi)
    logger.info("scholarly: %d full texts for %r", len(selected), query)
    return selected


def web_documents(ctx: "Context", query: str, n: int, iteration: int) -> list[str]:
    st, d = ctx.state, ctx.cfg.documents
    selected = []
    for page in ctx.web.search(query, n):
        doc_id = "web:" + hashlib.sha1(page.url.encode()).hexdigest()[:16]
        if doc_id in st.documents or _excluded(page.title, None, ctx):
            continue
        ok = len(page.text) >= d.min_page_chars
        st.documents[doc_id] = Document(id=doc_id, source="web", title=page.title, url=page.url, query=query,
                                        iteration=iteration, status="processed" if ok else "too_short")
        if ok:
            ctx.store.save(doc_id, [(1, page.text[: d.max_page_chars])])
            selected.append(doc_id)
    logger.info("web: %d pages for %r", len(selected), query)
    return selected


def retrieve(ctx: "Context", query: str, iteration: int) -> list[str]:
    """[S] Up to ``scholarly.results`` full texts and ``web.results`` pages not read before."""
    return (_scholarly(ctx, query, ctx.cfg.scholarly.results, iteration)
            + web_documents(ctx, query, ctx.cfg.web.results, iteration))


def read_chunks(ctx: "Context", doc_ids: list[str]) -> list[tuple[str, str]]:
    """[S] Every document is read in full: all its chunks, in order, as (doc id, text)."""
    d = ctx.cfg.documents
    out: list[tuple[str, str]] = []
    for doc_id in doc_ids:
        text = "\n\n".join(t for _, t in ctx.store.load(doc_id))
        out.extend((doc_id, c) for c in ctx.tokenizer.split(text, d.chunk_size_tokens, d.chunk_overlap_tokens))
    return out


# --------------------------------------------------------------------------- objects


def add_passages(ctx: "Context", obj: DomainObject, doc_ids: list[str]) -> None:
    """Add to ``obj`` the passages of ``doc_ids`` that mention it; keep the ``passages_per_object`` passages most
    relevant to the taxonomy (``rank_passages``)."""
    d = ctx.cfg.documents
    names = [obj.name, *obj.aliases]
    have = {e.quote for e in obj.evidence}
    for doc_id in doc_ids:
        pages = ctx.store.load(doc_id)
        passages, mentions = find_passages(pages, names, d.passage_max_chars, d.passages_per_object * 3)
        obj.mentions += mentions
        obj.evidence.extend(Evidence(doc_id=doc_id, quote=t, page=p or None) for p, t in passages if t not in have)
        have.update(t for _, t in passages)
    rank_passages(ctx, obj)


def rank_passages(ctx: "Context", obj: DomainObject) -> None:
    """[S] Keep the passages most similar ([N] embeddings) to what the taxonomy classifies: the meta-characteristic
    and the dimensions, so that the classifier sees evidence on every dimension rather than the longest passages."""
    limit = ctx.cfg.documents.passages_per_object
    if len(obj.evidence) <= limit:
        return
    st = ctx.state
    focus = " ".join([st.input.domain_of_objects, st.meta_characteristic or "",
                      *(f"{d.name}: {d.definition}" for d in st.taxonomy.dimensions)])
    sims = np.asarray(ctx.embedder.similarity([focus], [e.quote for e in obj.evidence])[0])
    obj.evidence = [obj.evidence[i] for i in np.argsort(-sims, kind="stable")[:limit]]


def describe_objects(ctx: "Context", objs: list[DomainObject], iteration: int) -> list[str]:
    """[N] One call per ``objects_per_description`` new objects: the LLM reports their important characteristics, in
    place of web pages. [S] The text is stored as a document of the run (source "llm") whose passages become the
    evidence of the objects that they name. Returns the ids of the documents."""
    size = ctx.cfg.documents.objects_per_description
    doc_ids = []
    for i in range(0, len(objs), size):
        group = objs[i:i + size]
        names = ", ".join(f"'{o.name}'" for o in group)
        out = ctx.llm.structured("describe_objects", {**ctx.base_vars(), "objects": names}, DescriptionsOut)
        text = "\n\n".join(d.text.strip() for d in out.descriptions if d.text.strip())
        if not text:
            continue
        doc_id = "llm:" + hashlib.sha1(names.encode()).hexdigest()[:16]
        ctx.state.documents[doc_id] = Document(id=doc_id, source="llm", title=f"LLM: {names}", query=names,
                                               iteration=iteration)
        ctx.store.save(doc_id, [(1, text)])
        doc_ids.append(doc_id)
    logger.info("llm: %d descriptions for %d objects", len(doc_ids), len(objs))
    return doc_ids


def register_objects(ctx: "Context", found: list[ObjectOut], doc_ids: list[str], iteration: int,
                     role: str = "building", limit: int | None = None) -> list[str]:
    """[S] Merge the candidates by name; keep the named instances whose name occurs in the text read; known objects
    receive the new passages; all new objects are registered, the most mentioned first (``limit`` only in the
    evaluation, Step 16). The characteristics of the new objects are reported by the LLM, several objects per call
    (``describe_objects``). Returns the ids of the new objects."""
    st = ctx.state
    groups: list[ObjectOut] = []
    for o in found:
        if not o.instance or not o.name.strip() or is_generic(o.name):
            continue
        g = next((g for g in groups if find_registered({"x": DomainObject(id="x", name=g.name, aliases=g.aliases)},
                                                        [o.name, *o.aliases])), None)
        if g is None:
            groups.append(o.model_copy(deep=True))
        else:
            g.aliases = list(dict.fromkeys(g.aliases + [a for a in [o.name, *o.aliases] if a != g.name]))
            if len(o.description) > len(g.description):
                g.description = o.description
    pages = {doc_id: ctx.store.load(doc_id) for doc_id in doc_ids}
    candidates = []
    for g in groups:
        names = [g.name, *g.aliases]
        known = find_registered(st.objects, names)
        if known is not None:
            add_passages(ctx, known, doc_ids)
            continue
        mentions = sum(count_mentions(p, names) for p in pages.values())
        if mentions:
            candidates.append((mentions, g))
    candidates.sort(key=lambda x: -x[0])
    new = []
    for _, g in candidates[:limit]:
        obj = DomainObject(id=st.new_object_id(), name=g.name.strip(), aliases=[a for a in g.aliases if a.strip()],
                           description=g.description, iteration=iteration, role=role)
        st.objects[obj.id] = obj
        new.append(obj)
    own = describe_objects(ctx, new, iteration) if new else []
    for o in new:
        add_passages(ctx, o, doc_ids + own)
    logger.info("%d candidate objects; %d new objects registered", len(groups), len(new))
    return [o.id for o in new]
