"""LLM abstraction layer.

Every [neuro] action goes through :meth:`LLMClient.structured`, which renders a prompt
template from ``prompts/``, requests JSON output, validates it against a Pydantic model
and retries (up to ``max_retries`` times) sending the validation error back to the model.
"""

from __future__ import annotations

import json
import logging
import re
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from .cache import ResponseCache, make_key

logger = logging.getLogger("taxonomy_builder.llm")

T = TypeVar("T", bound=BaseModel)

DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class LLMError(RuntimeError):
    """Raised when the LLM does not return valid output after all retries."""


class LLMTruncated(LLMError):
    """The reply was cut at ``max_output_tokens``; resending the same request would not help."""


class BudgetExceeded(RuntimeError):
    """Raised when the configured token budget is exhausted."""


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    truncated: bool = False  # the reply hit max_output_tokens
    stop_reason: str = ""    # why the model stopped (end_turn, refusal, ...), when the back-end reports it


# Kept in the cache key so that responses cached by earlier versions (which sent temperature 0)
# are still found when a run is resumed.
_LEGACY_KEY_PART = 0.0


class PromptLibrary:
    """Loads ``<name>.txt`` templates (``string.Template`` syntax, ``$variable``)."""

    def __init__(self, directory: str | Path | None = None) -> None:
        self.directory = Path(directory) if directory else DEFAULT_PROMPTS_DIR
        if not self.directory.is_dir():
            raise FileNotFoundError(f"prompts directory not found: {self.directory}")
        self._cache: dict[str, string.Template] = {}

    def template(self, name: str) -> string.Template:
        if name not in self._cache:
            path = self.directory / f"{name}.txt"
            if not path.exists():
                raise FileNotFoundError(f"prompt template not found: {path}")
            self._cache[name] = string.Template(path.read_text(encoding="utf-8"))
        return self._cache[name]

    def render(self, name: str, variables: dict[str, Any]) -> str:
        values = {k: (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1))
                  for k, v in variables.items()}
        return self.template(name).substitute(values)


def extract_json(text: str) -> Any:
    """Parse the first JSON object in ``text`` (tolerates code fences and prose)."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


class LLMClient(ABC):
    """Provider-independent LLM client with caching, retries and a token budget."""

    provider: str = "abstract"

    def __init__(
        self,
        model: str,
        max_output_tokens: int = 4096,
        cache: Optional[ResponseCache] = None,
        prompts: Optional[PromptLibrary] = None,
        max_retries: int = 3,
        token_budget: Optional[int] = None,
        tokens_used: int = 0,
        log_prompts: bool = True,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.cache = cache
        self.prompts = prompts or PromptLibrary()
        self.max_retries = max_retries
        self.token_budget = token_budget
        self.tokens_used = tokens_used
        self.tokens_by_task: dict[str, int] = {}
        self.log_prompts = log_prompts
        self.system_prompt = self.prompts.render("system", {})
        self.last_truncated = False
        # Name and variables of the task being executed (useful for logging and test doubles).
        self.current_task: Optional[str] = None
        self.current_variables: dict[str, Any] = {}

    # ------------------------------------------------------------------ provider hooks
    @abstractmethod
    def _raw_complete(self, system: str, messages: list[dict[str, str]],
                      schema: Optional[dict] = None) -> LLMResponse:
        """Send ``messages`` (roles ``user``/``assistant``) and return the reply.

        ``schema`` is the JSON schema of the expected answer; back-ends that support native
        structured output use it to constrain the reply, the others may ignore it."""

    def _is_transient(self, exc: BaseException) -> bool:
        """Return True for network/rate-limit errors worth retrying with back-off."""
        return isinstance(exc, (ConnectionError, TimeoutError))

    # ------------------------------------------------------------------ core
    def complete(self, system: str, messages: list[dict[str, str]], schema: Optional[dict] = None) -> str:
        """Return the model reply, using the on-disk cache when possible."""
        key = make_key(self.provider, self.model, _LEGACY_KEY_PART, system, messages)
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                self.last_truncated = False
                logger.debug("cache hit %s (task=%s)", key[:12], self.current_task)
                return hit["text"]
        if self.token_budget is not None and self.tokens_used >= self.token_budget:
            raise BudgetExceeded(f"token budget of {self.token_budget} exhausted")

        @retry(
            retry=retry_if_exception(self._is_transient),
            wait=wait_exponential(multiplier=2, min=2, max=60),
            stop=stop_after_attempt(6),
            reraise=True,
        )
        def _call() -> LLMResponse:
            return self._raw_complete(system, messages, schema)

        if self.log_prompts:
            logger.debug("PROMPT [%s]\n%s", self.current_task, messages[-1]["content"])
        response = _call()
        self.last_truncated, self.last_stop_reason = response.truncated, response.stop_reason
        spent = response.input_tokens + response.output_tokens
        self.tokens_used += spent
        key_task = self.current_task or "other"
        self.tokens_by_task[key_task] = self.tokens_by_task.get(key_task, 0) + spent
        if self.log_prompts:
            logger.debug("RESPONSE [%s]\n%s", self.current_task, response.text)
        if response.truncated:
            logger.warning("reply for task %s was cut at max_output_tokens (%d); raise llm.max_output_tokens "
                           "or lower taxonomy.classification_batch_size", self.current_task, self.max_output_tokens)
            return response.text  # not cached: a truncated reply must not be reused
        if self.cache is not None and response.text.strip():          # an empty reply is never cached
            self.cache.put(key, {"text": response.text, "input_tokens": response.input_tokens,
                                 "output_tokens": response.output_tokens, "task": self.current_task})
        return response.text

    def structured(self, task: str, variables: dict[str, Any], response_model: Type[T]) -> T:
        """[neuro] Run prompt template ``task`` and return a validated ``response_model``.

        On invalid output the original prompt is sent again with a short description of the
        error (the invalid reply itself is not resent, which keeps retries small)."""
        self.current_task, self.current_variables = task, variables
        prompt = self.prompts.render(task, variables)
        schema = response_model.model_json_schema()
        prompt += (
            "\n\nReturn ONLY a JSON object (no prose, no code fences) that validates against "
            f"this JSON schema:\n{json.dumps(schema, ensure_ascii=False)}"
        )
        messages: list[dict[str, str]] = [{"role": "user", "content": prompt}]
        last_error = ""
        for attempt in range(self.max_retries + 1):
            text = self.complete(self.system_prompt, messages, schema)
            try:
                return response_model.model_validate(extract_json(text))
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)
                if self.last_truncated:
                    raise LLMTruncated(f"task {task}: reply cut at max_output_tokens ({self.max_output_tokens})") from exc
                logger.warning("invalid JSON for task %s (attempt %d): %s; stop reason %r; reply starts with %r", task,
                               attempt + 1, last_error.splitlines()[0] if last_error else "",
                               self.last_stop_reason or "unknown", text.strip()[:150])
                if not text.strip() and attempt >= 1:       # the same request keeps returning nothing
                    raise LLMError(f"task {task}: empty reply (stop reason {self.last_stop_reason or 'unknown'!r})") from exc
                messages = [{"role": "user", "content": prompt + (
                    f"\n\nIMPORTANT: a previous answer was rejected ({last_error[:300]}). Return one complete, "
                    "syntactically valid JSON object: escape double quotes inside strings and keep texts short.")}]
        raise LLMError(f"task {task}: no valid output after {self.max_retries + 1} attempts: {last_error}")
