"""LLM layer: interface, back-ends and factory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config import LLMConfig
from .base import BudgetExceeded, LLMClient, LLMError, LLMResponse, LLMTruncated, PromptLibrary, extract_json
from .cache import ResponseCache

__all__ = [
    "BudgetExceeded",
    "LLMClient",
    "LLMError",
    "LLMTruncated",
    "LLMResponse",
    "PromptLibrary",
    "ResponseCache",
    "create_llm",
    "extract_json",
]


def create_llm(
    cfg: LLMConfig,
    token_budget: Optional[int] = None,
    tokens_used: int = 0,
    prompts_dir: str | Path | None = None,
    log_prompts: bool = True,
) -> LLMClient:
    """Instantiate the back-end selected in ``config.yaml`` (``llm.provider``)."""
    from .backends import AnthropicClient, GeminiClient, OpenAIClient

    if not cfg.model or cfg.model.startswith("<"):
        raise ValueError("set llm.model in config.yaml to a valid model name")
    classes = {"openai": OpenAIClient, "anthropic": AnthropicClient, "gemini": GeminiClient}
    cls = classes[cfg.provider]
    return cls(
        model=cfg.model,
        max_output_tokens=cfg.max_output_tokens,
        cache=ResponseCache(cfg.cache_dir),
        prompts=PromptLibrary(prompts_dir),
        max_retries=cfg.max_retries_invalid_json,
        token_budget=token_budget,
        tokens_used=tokens_used,
        log_prompts=log_prompts,
        timeout=cfg.request_timeout_s,
    )
