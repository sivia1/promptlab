"""Provider and model catalog.

The one place that declares which providers exist, how to reach them, which
models they serve, and what those models cost. A provider is either
``openai_compat`` (spoken to with the OpenAI /chat/completions shape — OpenAI,
Groq, Gemini, and OpenRouter all fit this) or ``anthropic`` (Claude's native
Messages API, which is a different wire format).

Adding a model is a one-line edit to ``MODELS`` here — nothing else in the
codebase hard-codes a model name. Prices are USD per 1K tokens and are estimates
for reporting only; verify them against your own account before trusting a cost
figure.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderInfo:
    """A provider: how to reach it and how its API speaks."""

    id: str
    label: str
    kind: str  # "openai_compat" | "anthropic"
    base_url: str
    # Where a user creates a key, shown in the Settings page.
    keys_url: str = ""


PROVIDERS: dict[str, ProviderInfo] = {
    "openai": ProviderInfo(
        "openai", "OpenAI", "openai_compat",
        "https://api.openai.com/v1", "https://platform.openai.com/api-keys",
    ),
    "anthropic": ProviderInfo(
        "anthropic", "Anthropic", "anthropic",
        "https://api.anthropic.com/v1", "https://console.anthropic.com/settings/keys",
    ),
    "gemini": ProviderInfo(
        "gemini", "Google Gemini", "openai_compat",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "https://aistudio.google.com/apikey",
    ),
    "groq": ProviderInfo(
        "groq", "Groq", "openai_compat",
        "https://api.groq.com/openai/v1", "https://console.groq.com/keys",
    ),
    "openrouter": ProviderInfo(
        "openrouter", "OpenRouter", "openai_compat",
        "https://openrouter.ai/api/v1", "https://openrouter.ai/keys",
    ),
}


@dataclass(frozen=True)
class ModelInfo:
    """A runnable model: id, its provider, label, and USD price per 1K tokens."""

    id: str
    provider: str
    label: str
    input_per_1k: float
    output_per_1k: float


# USD per 1K tokens. Estimates for reporting — edit to match current pricing.
# NOTE: prices for the newest models below (GPT-5 family, Gemini 3.x, Claude
# Sonnet 5 / Opus 4.8, and everything past Llama 3.x on Groq) are best-effort
# placeholders — confirm against each provider's live pricing page before
# trusting a cost figure for those rows.
MODELS: dict[str, ModelInfo] = {
    # --- OpenAI ---
    "gpt-5": ModelInfo("gpt-5", "openai", "GPT-5", 0.00125, 0.01),
    "gpt-5-mini": ModelInfo("gpt-5-mini", "openai", "GPT-5 mini", 0.00025, 0.002),
    "gpt-5-nano": ModelInfo("gpt-5-nano", "openai", "GPT-5 nano", 0.00005, 0.0004),
    "gpt-4.1": ModelInfo("gpt-4.1", "openai", "GPT-4.1", 0.002, 0.008),
    "gpt-4.1-mini": ModelInfo("gpt-4.1-mini", "openai", "GPT-4.1 mini", 0.0004, 0.0016),
    "gpt-4.1-nano": ModelInfo("gpt-4.1-nano", "openai", "GPT-4.1 nano", 0.0001, 0.0004),
    "o3-mini": ModelInfo("o3-mini", "openai", "o3-mini", 0.0011, 0.0044),
    "gpt-4o": ModelInfo("gpt-4o", "openai", "GPT-4o", 0.0025, 0.01),
    "gpt-4o-mini": ModelInfo("gpt-4o-mini", "openai", "GPT-4o mini", 0.00015, 0.0006),
    # --- Anthropic (native Messages API) ---
    "claude-opus-4-8": ModelInfo("claude-opus-4-8", "anthropic", "Claude Opus 4.8", 0.015, 0.075),
    "claude-sonnet-5": ModelInfo("claude-sonnet-5", "anthropic", "Claude Sonnet 5", 0.003, 0.015),
    "claude-haiku-4-5-20251001": ModelInfo(
        "claude-haiku-4-5-20251001", "anthropic", "Claude Haiku 4.5", 0.001, 0.005
    ),
    "claude-3-5-sonnet-latest": ModelInfo(
        "claude-3-5-sonnet-latest", "anthropic", "Claude 3.5 Sonnet", 0.003, 0.015
    ),
    # --- Google Gemini (OpenAI-compatible endpoint) ---
    "gemini-2.5-pro": ModelInfo(
        "gemini-2.5-pro", "gemini", "Gemini 2.5 Pro", 0.00125, 0.005
    ),
    "gemini-3.5-flash": ModelInfo(
        "gemini-3.5-flash", "gemini", "Gemini 3.5 Flash", 0.0001, 0.0004
    ),
    "gemini-3.1-flash": ModelInfo(
        "gemini-3.1-flash", "gemini", "Gemini 3.1 Flash", 0.0001, 0.0004
    ),
    "gemini-2.0-flash": ModelInfo("gemini-2.0-flash", "gemini", "Gemini 2.0 Flash", 0.0001, 0.0004),
    # --- Groq (fast inference; hosts open-weight models from several labs) ---
    "llama-3.3-70b-versatile": ModelInfo(
        "llama-3.3-70b-versatile", "groq", "Llama 3.3 70B", 0.00059, 0.00079
    ),
    "llama-3.1-8b-instant": ModelInfo(
        "llama-3.1-8b-instant", "groq", "Llama 3.1 8B", 0.00005, 0.00008
    ),
    "meta-llama/llama-4-maverick-17b-128e-instruct": ModelInfo(
        "meta-llama/llama-4-maverick-17b-128e-instruct", "groq", "Llama 4 Maverick", 0.0002, 0.0006
    ),
    "meta-llama/llama-4-scout-17b-16e-instruct": ModelInfo(
        "meta-llama/llama-4-scout-17b-16e-instruct", "groq", "Llama 4 Scout", 0.00011, 0.00034
    ),
    "deepseek-r1-distill-llama-70b": ModelInfo(
        "deepseek-r1-distill-llama-70b", "groq", "DeepSeek R1 Distill Llama 70B", 0.00075, 0.00099
    ),
    "qwen/qwen3-32b": ModelInfo("qwen/qwen3-32b", "groq", "Qwen3 32B", 0.00029, 0.00059),
    "openai/gpt-oss-120b": ModelInfo(
        "openai/gpt-oss-120b", "groq", "GPT-OSS 120B (Groq)", 0.00015, 0.00075
    ),
    "openai/gpt-oss-20b": ModelInfo(
        "openai/gpt-oss-20b", "groq", "GPT-OSS 20B (Groq)", 0.0001, 0.0005
    ),
    "moonshotai/kimi-k2-instruct": ModelInfo(
        "moonshotai/kimi-k2-instruct", "groq", "Kimi K2", 0.001, 0.003
    ),
    "gemma2-9b-it": ModelInfo("gemma2-9b-it", "groq", "Gemma 2 9B", 0.0002, 0.0002),
    # --- OpenRouter (one key, many models via an OpenAI-compatible gateway) ---
    "openai/gpt-4o-mini": ModelInfo(
        "openai/gpt-4o-mini", "openrouter", "GPT-4o mini (OpenRouter)", 0.00015, 0.0006
    ),
    "anthropic/claude-sonnet-5": ModelInfo(
        "anthropic/claude-sonnet-5", "openrouter", "Claude Sonnet 5 (OpenRouter)", 0.003, 0.015
    ),
    "google/gemini-2.5-pro": ModelInfo(
        "google/gemini-2.5-pro", "openrouter", "Gemini 2.5 Pro (OpenRouter)", 0.00125, 0.005
    ),
}


def resolve(model_id: str) -> ModelInfo:
    """Look up a model, raising a clear error if it is unknown."""
    try:
        return MODELS[model_id]
    except KeyError:
        known = ", ".join(sorted(MODELS))
        raise ValueError(f"Unknown model {model_id!r}. Known models: {known}") from None


def models_for(provider_id: str) -> list[ModelInfo]:
    """Every model served by a provider, in declared order."""
    return [m for m in MODELS.values() if m.provider == provider_id]
