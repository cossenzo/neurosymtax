"""Concrete LLM back-ends: OpenAI, Anthropic and Google Gemini.

API keys are read from ``OPENAI_API_KEY``, ``ANTHROPIC_API_KEY`` and ``GEMINI_API_KEY``.
SDKs are imported lazily so that only the selected provider must be installed.
"""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any, Optional

from .base import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


def _accepts(func: Any, name: str) -> bool:
    """True if the SDK method ``func`` accepts keyword ``name`` (SDK signatures change over time)."""
    try:
        params = inspect.signature(func).parameters
    except (TypeError, ValueError):
        return True
    return name in params or any(p.kind == p.VAR_KEYWORD for p in params.values())


def _require_key(var: str) -> str:
    key = os.environ.get(var, "").strip()
    if not key:
        raise RuntimeError(f"environment variable {var} is not set (see .env.example)")
    return key


class OpenAIClient(LLMClient):
    provider = "openai"

    def __init__(self, *args: Any, timeout: float = 120.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        import openai

        self._openai = openai
        self._client = openai.OpenAI(api_key=_require_key("OPENAI_API_KEY"), timeout=timeout)

    def _is_transient(self, exc: BaseException) -> bool:
        o = self._openai
        return isinstance(exc, (o.APIConnectionError, o.APITimeoutError, o.RateLimitError,
                                o.InternalServerError)) or super()._is_transient(exc)

    def _raw_complete(self, system: str, messages: list[dict[str, str]],
                      schema: Optional[dict] = None) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "response_format": {"type": "json_object"},
            "max_completion_tokens": self.max_output_tokens,
        }
        resp = self._client.chat.completions.create(**kwargs)
        usage = resp.usage
        return LLMResponse(
            truncated=resp.choices[0].finish_reason == "length",
            stop_reason=str(resp.choices[0].finish_reason or ""),
            text=resp.choices[0].message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )


class AnthropicClient(LLMClient):
    provider = "anthropic"

    def __init__(self, *args: Any, timeout: float = 120.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=_require_key("ANTHROPIC_API_KEY"), timeout=timeout)
        # Native structured output (JSON schema enforced by the API), when the SDK supports it.
        self._structured = _accepts(self._client.messages.create, "output_config")
        try:
            from anthropic.lib._parse._transform import transform_schema

            self._transform_schema = transform_schema
        except ImportError:  # older SDK: rely on the prompt and validation retries
            self._structured = False

    def _is_transient(self, exc: BaseException) -> bool:
        a = self._anthropic
        return isinstance(exc, (a.APIConnectionError, a.APITimeoutError, a.RateLimitError,
                                a.InternalServerError)) or super()._is_transient(exc)

    def _raw_complete(self, system: str, messages: list[dict[str, str]],
                      schema: Optional[dict] = None) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "system": system,
            "messages": messages,
            "max_tokens": self.max_output_tokens,
        }
        if schema is not None and self._structured:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": self._transform_schema(schema)}}
        try:
            resp = self._client.messages.create(**kwargs)
        except self._anthropic.BadRequestError as exc:
            if "output_config" not in kwargs:
                raise
            logger.warning("structured output rejected by the API (%s); falling back to prompt-only JSON", exc)
            self._structured = False
            kwargs.pop("output_config")
            resp = self._client.messages.create(**kwargs)
        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        return LLMResponse(
            text=text,
            input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
            output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
            truncated=getattr(resp, "stop_reason", None) == "max_tokens",
            stop_reason=str(getattr(resp, "stop_reason", "") or ""),
        )


class GeminiClient(LLMClient):
    provider = "gemini"

    def __init__(self, *args: Any, timeout: float = 120.0, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from google import genai
        from google.genai import errors, types

        self._types = types
        self._errors = errors
        self._client = genai.Client(
            api_key=_require_key("GEMINI_API_KEY"),
            http_options=types.HttpOptions(timeout=int(timeout * 1000)),
        )

    def _is_transient(self, exc: BaseException) -> bool:
        e = self._errors
        if isinstance(exc, e.ServerError):
            return True
        if isinstance(exc, e.ClientError) and getattr(exc, "code", None) == 429:
            return True
        return super()._is_transient(exc)

    def _raw_complete(self, system: str, messages: list[dict[str, str]],
                      schema: Optional[dict] = None) -> LLMResponse:
        t = self._types
        contents = [
            t.Content(role="model" if m["role"] == "assistant" else "user", parts=[t.Part(text=m["content"])])
            for m in messages
        ]
        config_kwargs: dict[str, Any] = {
            "system_instruction": system,
            "response_mime_type": "application/json",
            "max_output_tokens": self.max_output_tokens,
            "automatic_function_calling": t.AutomaticFunctionCallingConfig(disable=True),
        }
        resp = self._client.models.generate_content(
            model=self.model, contents=contents, config=t.GenerateContentConfig(**config_kwargs)
        )
        usage = resp.usage_metadata
        finish = str(getattr((resp.candidates or [None])[0], "finish_reason", "") or "")
        return LLMResponse(
            truncated=finish.endswith("MAX_TOKENS"),
            stop_reason=finish,
            text=resp.text or "",
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )
