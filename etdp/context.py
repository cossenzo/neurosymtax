"""Everything a step needs: configuration, state and the neural and symbolic services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import AppConfig
from .documents import TextStore, Tokenizer
from .embeddings import Embedder
from .llm import LLMClient
from .models import IterationRecord, RunState
from .sources import FullTextFetcher, SearchProvider, WebSearch


@dataclass
class Context:
    cfg: AppConfig
    state: RunState
    llm: LLMClient
    embedder: Embedder
    scholarly: SearchProvider
    fetcher: FullTextFetcher
    web: WebSearch
    store: TextStore
    tokenizer: Tokenizer
    run_dir: Path

    @property
    def record(self) -> IterationRecord:
        return self.state.current

    def base_vars(self) -> dict[str, Any]:
        inp, m = self.state.input, self.cfg.method
        return {
            "phenomenon": inp.phenomenon,
            "users": inp.users,
            "purpose": inp.purpose,
            "domain_of_objects": inp.domain_of_objects,
            "meta_characteristic": self.state.meta_characteristic or "",
            "perspectives": inp.perspective_names,
            "language": inp.language,
            "min_dimensions_per_perspective": m.min_dimensions_per_perspective,
            "min_characteristics_per_dimension": m.min_characteristics_per_dimension,
        }
