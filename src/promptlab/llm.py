"""LLM client.

A thin wrapper over any OpenAI-compatible chat endpoint. Unlike a plain text
completion, PromptLab needs the *token usage* back on every call so the runner
can report cost — so `complete()` returns a `Completion` carrying the text plus
prompt/completion token counts and the measured latency.

The client is provider-agnostic: it resolves a model to a provider via the
catalog, then points the same OpenAI SDK at that provider's base URL with the
right key. A `StubLLM` keeps the whole pipeline runnable offline (and in CI)
without any key.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .catalog import PROVIDER_BASE_URLS, ModelInfo, _api_key_for, resolve
from .config import Settings


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
    """The configured LLM provider failed (rate limit, auth, network, ...)."""


class OpenAICompatLLM:
    """Calls an OpenAI-compatible /chat/completions endpoint for one model."""

    def __init__(self, model: ModelInfo, api_key: str, base_url: str, *, timeout: float = 30.0):
        # Imported lazily so the package imports without the openai dependency
        # (e.g. when only the StubLLM is used).
        from openai import OpenAI

        self._model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)

    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> Completion:
        from openai import OpenAIError

        started = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self._model.id,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except OpenAIError as exc:
            raise LLMProviderError(f"LLM provider error: {exc}") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)

        text = (resp.choices[0].message.content or "").strip()
        usage = resp.usage
        return Completion(
            text=text,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )


class StubLLM:
    """Deterministic offline stand-in so the pipeline runs without any API key.

    Produces a canned answer and rough-but-plausible token counts, so every
    downstream metric (cost, latency, lexical overlap) has real numbers to chew
    on in tests and demos. Judge quality claims should use a real model.
    """

    def __init__(self, model: ModelInfo):
        self._model = model

    def complete(self, *, system: str, user: str, temperature: float = 0.0) -> Completion:
        started = time.perf_counter()
        text = (
            f"[stub:{self._model.id}] "
            "This is a deterministic placeholder answer used when no API key is "
            "configured. Set PROMPTLAB_LLM_API_KEY to get real completions."
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Approximate tokens as ~4 chars/token so cost/token columns are non-zero.
        return Completion(
            text=text,
            prompt_tokens=max(1, len(system + user) // 4),
            completion_tokens=max(1, len(text) // 4),
            latency_ms=latency_ms,
        )


def build_llm(model_id: str, settings: Settings):
    """Return a client for `model_id`, falling back to the stub when no key exists."""
    model = resolve(model_id)
    key = _api_key_for(model.provider, settings)
    if not key:
        return StubLLM(model)
    return OpenAICompatLLM(
        model,
        api_key=key,
        base_url=PROVIDER_BASE_URLS[model.provider],
        timeout=settings.llm_timeout_seconds,
    )
