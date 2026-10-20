"""Configuration (``config.yaml``) and research input (``input.yaml``).

Every parameter of the method is defined here. The symbolic rules can be switched off one by one; the ablation
(``config_ablation.yaml``) switches them all off.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal, Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

GENERIC_PERSPECTIVE = "Perspective"
Goal = Literal["describing", "identifying", "classifying", "analyzing", "clustering"]


class _Strict(BaseModel):
    """Rejects unknown keys, so that typos in configuration files fail loudly."""

    model_config = ConfigDict(extra="forbid")


class LLMConfig(_Strict):
    provider: Literal["anthropic", "openai", "gemini"] = "anthropic"
    model: str = "<model-name>"
    max_output_tokens: int = 16384
    max_retries_invalid_json: int = 3
    cache_dir: str = ".cache/llm"
    request_timeout_s: float = 120.0


class EmbeddingsConfig(_Strict):
    backend: Literal["sentence-transformers", "openai", "gemini", "hashing"] = "sentence-transformers"
    model: str = "all-mpnet-base-v2"


class ScholarlyConfig(_Strict):
    """Scholarly database: full texts of open-access articles."""

    provider: Literal["semantic_scholar", "openalex"] = "semantic_scholar"
    fallback_provider: Literal["openalex", "semantic_scholar", "none"] = "openalex"
    contact_email: str = "you@example.com"
    results: int = Field(10, ge=0)                 # full texts read per search
    scanned: int = Field(50, ge=1)                 # records examined per search to find them
    open_access_only: bool = True
    unpaywall_fallback: bool = True
    request_timeout_s: float = 60.0
    pdf_timeout_s: float = 30.0
    max_pdf_mb: float = 40.0
    min_request_interval_s: float = Field(1.1, ge=0)


class WebConfig(_Strict):
    """Web search engine: documentation, white papers and other pages."""

    provider: Literal["tavily", "searxng", "none"] = "tavily"
    results: int = Field(10, ge=0)                 # pages read per search
    searxng_url: str = "http://localhost:8080"
    request_timeout_s: float = 30.0
    exclude_domains: list[str] = Field(default_factory=list)


class DocumentsConfig(_Strict):
    chunk_size_tokens: int = 1500
    chunk_overlap_tokens: int = 150
    passage_max_chars: int = 500
    objects_per_description: int = Field(5, ge=1)   # new objects described per LLM call
    passages_per_object: int = Field(16, ge=1)     # passages of an object shown to the classifier, most relevant first
    min_fulltext_chars: int = 1500                 # an article with less text is not used
    min_page_chars: int = 400                      # a web page with less text is not used
    max_page_chars: int = 100_000
    tokenizer: Literal["tiktoken", "approx"] = "tiktoken"
    exclude_dois: list[str] = Field(default_factory=list)    # never read (e.g., the benchmark article)
    exclude_titles: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "DocumentsConfig":
        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            raise ValueError("documents: chunk_overlap_tokens must be smaller than chunk_size_tokens")
        return self


class MethodConfig(_Strict):
    r: int = Field(2, ge=0)                        # corrections requested for a proposal of operations (R5)
    min_dimensions_per_perspective: int = Field(2, ge=1)    # O10
    min_characteristics_per_dimension: int = Field(2, ge=2)  # R5, O10
    classification_batch_size: int = Field(5, ge=1)
    min_query_words: int = Field(2, ge=1)          # search strings: few, broad keywords
    max_query_words: int = Field(5, ge=1)
    # symbolic rules; the ablation sets them to false
    symbolic_approach: bool = True     # R1–R3 (false: the LLM chooses the approach)
    verify_operations: bool = True     # R5–R6 (false: invariants and the removal of elements without objects in revisions are not applied)


class EvaluationConfig(_Strict):
    """Steps 15–16. The goals and criteria are in ``goals.py`` (Kundisch et al., 2022, Table 4); the default target
    of each criterion is set here and the researcher may override it per goal in the input file."""

    new_objects: int = Field(10, ge=1)                     # new objects identified for the evaluation (TDR 21)
    dominance_threshold: float = Field(0.9, gt=0, le=1)   # analyzing: a characteristic above it dominates a dimension
    max_groups: int = Field(10, ge=2)                      # clustering: groups tried
    targets: dict[str, float] = Field(default_factory=lambda: {
        "kappa": 0.61, "misfit_share": 0.30, "informed_share": 0.50, "distinct_profiles": 0.80,
        "discriminating_dimensions": 0.60, "cluster_silhouette": 0.25})


class LimitsConfig(_Strict):
    max_iterations: int = Field(15, ge=1)
    max_tokens_budget: Optional[int] = None


class OutputConfig(_Strict):
    dir: str = "output"
    log_prompts: bool = True


class AppConfig(_Strict):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    scholarly: ScholarlyConfig = Field(default_factory=ScholarlyConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    documents: DocumentsConfig = Field(default_factory=DocumentsConfig)
    method: MethodConfig = Field(default_factory=MethodConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


class EvaluationGoal(_Strict):
    """An evaluation goal of Kundisch et al. (2022, Table 4), optionally with targets for its criteria."""

    goal: Goal
    targets: dict[str, float] = Field(default_factory=dict)


class InputSpec(_Strict):
    """Steps 1–3 [I]: the research problem, specified by the researcher in the input file."""

    observed_phenomenon: str                                # Step 1
    target_user_groups: list[str]                           # Step 2
    intended_purposes: list[str]                            # Step 3
    purpose_type: Literal["structuring", "identification_and_structuring"]
    purpose_nature: Literal["descriptive", "normative"] = "descriptive"
    domain_of_objects: str
    evaluation_goals: list[EvaluationGoal] = Field(                                  # Step 5
        default_factory=lambda: [EvaluationGoal(goal="classifying")])
    perspectives: list[str] = Field(default_factory=list)   # second-level grouping of dimensions (TDR 12)
    meta_characteristic: Optional[str] = None               # Step 4: formulated if null
    seed_keywords: list[str] = Field(default_factory=list)
    language: str = "en"
    year_range: Optional[tuple[int, int]] = None

    @field_validator("observed_phenomenon", "domain_of_objects")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v.strip()

    @field_validator("target_user_groups", "intended_purposes")
    @classmethod
    def _not_empty_list(cls, v: list[str]) -> list[str]:
        v = [x.strip() for x in v if x and x.strip()]
        if not v:
            raise ValueError("at least one entry is required")
        return v

    @field_validator("evaluation_goals", mode="before")
    @classmethod
    def _goals(cls, v):
        """A goal may be written as its name alone or as {goal, targets}."""
        items = [{"goal": g} if isinstance(g, str) else g for g in (v or [])]
        names = [g["goal"] if isinstance(g, dict) else g.goal for g in items]
        if not items or len(set(names)) != len(names):
            raise ValueError("at least one evaluation goal, each listed once")
        return items

    @field_validator("perspectives")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        names = [" ".join(p.split()) for p in v if p and p.strip()]
        if len({n.casefold() for n in names}) != len(names):
            raise ValueError("perspectives must be unique")
        return names

    @property
    def phenomenon(self) -> str:
        return self.observed_phenomenon

    @property
    def users(self) -> str:
        return "; ".join(self.target_user_groups)

    @property
    def purpose(self) -> str:
        return "; ".join(self.intended_purposes)

    @property
    def perspective_names(self) -> list[str]:
        return self.perspectives or [GENERIC_PERSPECTIVE]


def _read_yaml(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"file not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def load_config(path: Optional[str | Path]) -> AppConfig:
    """Read ``config.yaml``; API keys are read from ``.env`` (never from the configuration)."""
    load_dotenv(Path.cwd() / ".env")
    if path is None:
        return AppConfig()
    load_dotenv(Path(path).resolve().parent / ".env")
    return AppConfig.model_validate(_read_yaml(path))


def load_input(path: str | Path) -> InputSpec:
    return InputSpec.model_validate(_read_yaml(path))
