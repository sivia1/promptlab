"""Model catalog: which models exist, who serves them, and what they cost.

Every model PromptLab can run against is declared here once. A model knows its
provider (which decides the base URL and which API key to use) and its token
pricing (so the runner can report cost without a second source of truth). Adding
a model is a one-line change here — nothing else in the codebase hard-codes a
model name.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings

# OpenAI-compatible base URLs. Groq and Gemini both expose an OpenAI-shaped
# /chat/completions endpoint, so a single client talks to all three.
PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


@dataclass(frozen=True)
class ModelInfo:
    """A runnable model: its id, provider, and USD price per 1K tokens."""

    id: str
    provider: str
    label: str
    input_per_1k: float
    output_per_1k: float


# Prices are USD per 1K tokens, taken from each provider's public pricing.
# They are estimates for reporting only — never billed against.
MODELS: dict[str, ModelInfo] = {
    "gpt-4o-mini": ModelInfo("gpt-4o-mini", "openai", "GPT-4o mini", 0.00015, 0.00060),
    "gpt-4o": ModelInfo("gpt-4o", "openai", "GPT-4o", 0.00250, 0.01000),
    "llama-3.3-70b-versatile": ModelInfo(
        "llama-3.3-70b-versatile", "groq", "Llama 3.3 70B (Groq)", 0.00059, 0.00079
    ),
    "llama-3.1-8b-instant": ModelInfo(
        "llama-3.1-8b-instant", "groq", "Llama 3.1 8B (Groq)", 0.00005, 0.00008
    ),
    "gemini-2.0-flash": ModelInfo(
        "gemini-2.0-flash", "gemini", "Gemini 2.0 Flash", 0.00010, 0.00040
    ),
}


def resolve(model_id: str) -> ModelInfo:
    """Look up a model, raising a clear error if it is unknown."""
    try:
        return MODELS[model_id]
    except KeyError:
        known = ", ".join(sorted(MODELS))
        raise ValueError(f"Unknown model {model_id!r}. Known models: {known}") from None


def _api_key_for(provider: str, settings: Settings) -> str:
    """The most specific key available for a provider, falling back to the generic one."""
    specific = {
        "openai": settings.openai_api_key,
        "groq": settings.groq_api_key,
        "gemini": settings.gemini_api_key,
    }.get(provider, "")
    return specific or settings.llm_api_key


def available_models(settings: Settings) -> list[ModelInfo]:
    """Models whose provider has a usable API key configured."""
    return [m for m in MODELS.values() if _api_key_for(m.provider, settings)]
