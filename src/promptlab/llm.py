"""LLM clients — hybrid.

Two real integrations behind one interface:

* ``OpenAICompatLLM`` speaks the OpenAI /chat/completions shape and covers
  OpenAI, Groq, Gemini, and OpenRouter.
* ``AnthropicLLM`` speaks Claude's native Messages API (a genuinely different
  wire format: ``/v1/messages``, an ``anthropic-version`` header, ``system`` as a
  top-level field, and ``input_tokens``/``output_tokens`` usage).

Both return a ``Completion`` carrying the text plus token counts and measured
latency, so the runner can report cost uniformly. A ``StubLLM`` keeps the whole
pipeline runnable offline (and in CI) when a provider has no key.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from .catalog import PROVIDERS, resolve


@dataclass(frozen=True)
class GenParams:
    """Per-run inference knobs. None means "use the provider default"."""

    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class Completion:
    """One model response plus the metadata PromptLab scores on."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMProviderError(RuntimeError):
    """A provider call failed (rate limit, auth, network, bad request, ...)."""


class LLM(Protocol):
    def complete(self, *, system: str, user: str, params: GenParams) -> Completion: ...


class OpenAICompatLLM:
    """Any OpenAI-compatible /chat/completions endpoint (OpenAI/Groq/Gemini/OpenRouter)."""

    def __init__(self, model_id: str, api_key: str, base_url: str, *, timeout: float = 60.0):
        from openai import OpenAI

        self._model_id = model_id
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def complete(self, *, system: str, user: str, params: GenParams) -> Completion:
        from openai import OpenAIError

        kwargs: dict = {
            "model": self._model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.max_tokens is not None:
            kwargs["max_tokens"] = params.max_tokens

        started = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(**kwargs)
        except OpenAIError as exc:
            raise LLMProviderError(f"{type(exc).__name__}: {exc}") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = (resp.choices[0].message.content or "").strip()
        usage = resp.usage
        return Completion(
            text=text,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )


class AnthropicLLM:
    """Claude's native Messages API, called directly over HTTP (no SDK needed)."""

    _VERSION = "2023-06-01"

    def __init__(self, model_id: str, api_key: str, base_url: str, *, timeout: float = 60.0):
        self._model_id = model_id
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}/messages"
        self._timeout = timeout

    def complete(self, *, system: str, user: str, params: GenParams) -> Completion:
        import httpx

        body: dict = {
            "model": self._model_id,
            # Anthropic requires max_tokens; fall back to a sane default.
            "max_tokens": params.max_tokens or 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if params.temperature is not None:
            body["temperature"] = params.temperature
        if params.top_p is not None:
            body["top_p"] = params.top_p

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self._VERSION,
            "content-type": "application/json",
        }

        started = time.perf_counter()
        try:
            resp = httpx.post(self._url, json=body, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _safe_error_detail(exc.response)
            raise LLMProviderError(f"Anthropic {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        data = resp.json()
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        usage = data.get("usage", {})
        return Completion(
            text=text,
            prompt_tokens=usage.get("input_tokens", 0) or 0,
            completion_tokens=usage.get("output_tokens", 0) or 0,
            latency_ms=latency_ms,
        )


class StubLLM:
    """Deterministic offline stand-in when a provider has no key configured."""

    def __init__(self, model_id: str):
        self._model_id = model_id

    def complete(self, *, system: str, user: str, params: GenParams) -> Completion:
        started = time.perf_counter()
        text = (
            f"[stub:{self._model_id}] Placeholder answer — no API key configured for this "
            "provider. Add one in Settings to get a real completion."
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return Completion(
            text=text,
            prompt_tokens=max(1, len(system + user) // 4),
            completion_tokens=max(1, len(text) // 4),
            latency_ms=latency_ms,
        )


def _safe_error_detail(response) -> str:
    try:
        payload = response.json()
        return payload.get("error", {}).get("message", "") or str(payload)[:200]
    except Exception:  # noqa: BLE001 - error bodies are best-effort
        return response.text[:200]


def build_llm(model_id: str, api_key: str, *, timeout: float = 60.0) -> LLM:
    """Return the right client for ``model_id``; StubLLM when no key is available."""
    model = resolve(model_id)
    provider = PROVIDERS[model.provider]
    if not api_key:
        return StubLLM(model_id)
    if provider.kind == "anthropic":
        return AnthropicLLM(model.id, api_key, provider.base_url, timeout=timeout)
    return OpenAICompatLLM(model.id, api_key, provider.base_url, timeout=timeout)
