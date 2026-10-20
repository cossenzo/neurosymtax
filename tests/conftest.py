"""Test doubles: a scripted LLM that answers every prompt from a small fake world, and fake sources (no network)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import pytest

from etdp.config import AppConfig, InputSpec
from etdp.embeddings import HashingEmbedder
from etdp.llm import LLMClient, LLMResponse, PromptLibrary, ResponseCache
from etdp.sources.http import SearchProvider, SearchResult
from etdp.sources.web import WebPage, WebSearch

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"

# Ground truth: dimension -> (characteristics, perspective)
WORLD = {
    "Pricing": (["Free", "Paid"], "Business"),
    "Market sides": (["Two-sided", "Multi-sided"], "Business"),
    "Governance": (["Open", "Closed"], "Technology"),
    "Hosting": (["Cloud", "On-premise"], "Technology"),
}
ATTR = {a: d for d, (chars, _) in WORLD.items() for a in chars}


def obj_line(name: str, attrs: list[str]) -> str:
    return f"OBJECT {name}: {name} is a digital platform with {', '.join(attrs)} features."


def concept_line(dim: str) -> str:
    return f"CONCEPT {dim} | {', '.join(WORLD[dim][0])}: the literature classifies platforms by {dim.lower()}."


SCHOLARLY = {
    "S1": [obj_line("Alpha Market", ["Free", "Two-sided", "Open", "Cloud"]),
           obj_line("Beta Hub", ["Paid", "Multi-sided", "Closed", "On-premise"])],
    "S2": [obj_line("Gamma Exchange", ["Free", "Multi-sided", "Closed", "Cloud"]),
           obj_line("Delta Store", ["Paid", "Two-sided", "Open", "On-premise"])],
    "S3": [concept_line("Pricing"), concept_line("Governance")],
    "S4": [concept_line("Market sides"), concept_line("Hosting")],
    "S5": [obj_line("Epsilon Network", ["Free", "Two-sided", "Closed", "On-premise"])],
    "S6": [obj_line("Zeta Place", ["Paid", "Multi-sided", "Open", "Cloud"])],
    "S7": [obj_line("Eta Links", ["Paid", "Two-sided", "Closed", "Cloud"])],
    "S8": [obj_line("Theta Mall", ["Free", "Multi-sided", "Open", "On-premise"])],
}


def pages(doc_id: str) -> list[tuple[int, str]]:
    return [(i + 1, line) for i, line in enumerate(SCHOLARLY[doc_id])]


class FakeScholarly(SearchProvider):
    name = "fake"

    def search(self, query: str, limit: int, year_range=None) -> list[SearchResult]:
        return [SearchResult(id=k, title=f"Article {k}", pdf_urls=["x"]) for k in SCHOLARLY][:limit]


class FakeFetcher:
    def fetch(self, result: SearchResult):
        return pages(result.id)


class FakeWeb(WebSearch):
    def search(self, query: str, n: int) -> list[WebPage]:
        return []


class ScriptedLLM(LLMClient):
    """Deterministic answers from the fake world. Hooks: ``propose_hook(stage, variables, attempt)`` returns the
    operations to answer (or None); ``judge_pass``; ``classify_hook(object_name, dimension_view)`` returns a cell
    dict or None; ``fail_on`` raises once on a task (to test resume)."""

    provider = "scripted"

    def __init__(self, cache_dir: Optional[Path] = None, fail_on: Optional[str] = None, **kw: Any) -> None:
        super().__init__(model="scripted", cache=ResponseCache(cache_dir) if cache_dir else None,
                         prompts=PromptLibrary(PROMPTS), **kw)
        self.fail_on = fail_on
        self.calls: dict[str, int] = {}
        self.requests: dict[str, list] = {}
        self.propose_hook = None
        self.classify_hook = None
        self.judge_pass = True
        self.approach = "e"
        self.entry = "6"
        self._q = 0

    def _raw_complete(self, system, messages, schema=None) -> LLMResponse:
        task, v = self.current_task, self.current_variables
        self.calls[task] = self.calls.get(task, 0) + 1
        self.requests.setdefault(task, []).append(v)
        if self.fail_on == task:
            self.fail_on = None
            raise RuntimeError(f"simulated crash in {task}")
        return LLMResponse(json.dumps(getattr(self, "_" + task)(v)), 50, 50)

    # ------------------------------------------------------------------ tasks
    def _meta_characteristic(self, v):
        return {"meta_characteristic": "How digital platforms create and capture value."}

    def _meta_review(self, v):
        return {"keep": True, "reason": "fits the purpose"}

    def _formulate_query(self, v):
        self._q += 1
        return {"query": f"digital platform objects query{self._q}"}

    def _extract_objects(self, v):
        out = []
        for line in v["text"].splitlines():
            m = re.match(r"OBJECT ([^:]+): (.*)", line)
            if m:
                out.append({"name": m.group(1), "description": m.group(2), "instance": True})
        return {"objects": out}

    def _describe_objects(self, v):
        names = re.findall(r"'([^']+)'", v["objects"])
        return {"descriptions": [{"name": n, "text": f"{n} is a digital platform with Free features."} for n in names]}

    def _extract_concepts(self, v):
        out = []
        for line in v["text"].splitlines():
            m = re.match(r"CONCEPT ([^|]+) \| ([^:]+):", line)
            if m:
                dim = m.group(1).strip()
                out.append({"kind": "dimension", "name": dim, "definition": f"{dim} of the platform"})
                for c in m.group(2).split(", "):
                    out.append({"kind": "characteristic", "name": c, "dimension": dim})
        return {"concepts": out}

    def _classify_objects(self, v):
        dims = v["taxonomy"] if isinstance(v["taxonomy"], list) else []
        res = []
        for o in v["objects"]:
            text = " ".join(o["passages"])
            cells = []
            for d in dims:
                cell = {"dimension_id": d["id"], "value": "no_information"}
                for c in d["characteristics"]:
                    if re.search(rf"(?<![\w-]){re.escape(c['name'])}(?![\w-])", text):
                        cell = {"dimension_id": d["id"], "value": c["id"]}
                if self.classify_hook:
                    forced = self.classify_hook(o["name"], d)
                    if forced is not None:
                        cell = {"dimension_id": d["id"], **forced}
                cells.append(cell)
            codes = []
            if v["coding"] == "yes":
                known = {d["name"] for d in dims}
                for attr, dim in ATTR.items():
                    if dim not in known and re.search(rf"(?<![\w-]){re.escape(attr)}(?![\w-])", text):
                        codes.append({"label": attr, "definition": f"{dim} is {attr}"})
            res.append({"object_id": o["id"], "cells": cells, "codes": codes})
        return {"objects": res}

    def _propose_operations(self, v):
        stage = "e" if "codes" in v else "c" if "concepts" in v else "r"
        attempt = sum(1 for x in self.requests["propose_operations"] if x is v)
        if self.propose_hook:
            ops = self.propose_hook(stage, v, attempt)
            if ops is not None:
                return {"operations": ops}
        tax = v["taxonomy"] if isinstance(v["taxonomy"], list) else []
        present = {d["name"]: d for d in tax}
        ops = []
        if stage == "e" and isinstance(v["codes"], list):
            by_dim: dict[str, list] = {}
            for c in v["codes"]:
                by_dim.setdefault(ATTR[c["code"]], []).append(c["object"])
            for dim, objs in by_dim.items():
                if dim not in present:
                    chars, persp = WORLD[dim]
                    ops.append({"op": "add_dimension", "name": dim, "definition": f"{dim} of the platform",
                                "application_rule": f"choose the {dim.lower()} stated", "perspective": persp,
                                "characteristics": [{"name": a, "definition": f"{dim} is {a}"} for a in chars],
                                "evidence": sorted(set(objs))})
        elif stage == "c":
            for c in v["concepts"]:
                if c["kind"] == "dimension" and c["name"] not in present and c["name"] in WORLD:
                    chars, persp = WORLD[c["name"]]
                    ops.append({"op": "add_dimension", "name": c["name"], "definition": c["definition"],
                                "application_rule": "choose the one stated", "perspective": persp,
                                "characteristics": [{"name": a} for a in chars], "evidence": [c["id"]]})
                    present[c["name"]] = {}
        return {"operations": ops}

    def _judge_subjective(self, v):
        conds = ["concise", "robust", "comprehensive", "extendible", "explanatory"]
        return {"evaluations": [{"condition": c, "passed": self.judge_pass, "justification": "scripted",
                                 "suggestions": [] if self.judge_pass else [f"improve {c}"]} for c in conds]}

    def _choose_approach(self, v):
        return {"choice": self.approach, "reason": "scripted"}

    def _choose_entry(self, v):
        choice = self.entry.get(v["exit"], "6") if isinstance(self.entry, dict) else self.entry
        return {"choice": choice, "reason": "scripted"}

    def _baseline(self, v):
        return {"meta_characteristic": "value creation",
                "dimensions": [{"name": d, "perspective": p, "definition": d, "application_rule": "stated",
                                "characteristics": [{"name": a} for a in chars]} for d, (chars, p) in WORLD.items()]}


@pytest.fixture
def cfg(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate({
        "llm": {"model": "test", "cache_dir": str(tmp_path / "cache")},
        "embeddings": {"backend": "hashing"},
        "scholarly": {"results": 2},
        "web": {"provider": "none", "results": 0},
        "documents": {"tokenizer": "approx", "min_page_chars": 10},
        "evaluation": {"new_objects": 2},
        "limits": {"max_iterations": 8},
        "output": {"dir": str(tmp_path / "output")},
    })


@pytest.fixture
def inp() -> InputSpec:
    return InputSpec(observed_phenomenon="Digital platforms", target_user_groups=["Researchers"],
                     intended_purposes=["Classify platforms"], purpose_type="identification_and_structuring",
                     domain_of_objects="Digital platforms", perspectives=["Business", "Technology"],
                     seed_keywords=["platform"])


@pytest.fixture
def make(cfg, inp):
    from etdp.pipeline import Pipeline

    counter = {"n": 0}

    def _make(llm: Optional[ScriptedLLM] = None, config: Optional[AppConfig] = None, run_input=None):
        counter["n"] += 1
        return Pipeline.create(config or cfg, run_input or inp, run_id=f"run{counter['n']}", llm=llm or ScriptedLLM(),
                               embedder=HashingEmbedder(), scholarly=FakeScholarly(), fetcher=FakeFetcher(),
                               web=FakeWeb())
    return _make
