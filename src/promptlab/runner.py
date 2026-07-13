"""Experiment runner: the spine of PromptLab.

Takes a shared question and a list of runs — each with its own provider, model,
prompt, and inference settings — executes every run against its provider, scores
each answer with a single fixed judge, computes the comparison summary, and
persists the experiment. This is exactly what the "Run Experiment" button does.

Each run's prompt is the *system* message and the shared question is the *user*
message, so you are comparing how different models/prompts answer the same thing.
"""

from __future__ import annotations

from .config import Settings
from .keystore import KeyStore
from .llm import GenParams, LLMProviderError, build_llm
from .schemas import ExperimentResult, JudgeScores, ResultRow, RunConfig
from .scoring import score_run, summarize
from .store import Store


def _error_row(config: RunConfig, message: str) -> ResultRow:
    """A placeholder row so one provider failure doesn't sink the whole experiment."""
    return ResultRow(
        label=config.label or f"{config.provider} · {config.model}",
        provider=config.provider,
        model=config.model,
        prompt=config.prompt,
        output="",
        temperature=config.temperature,
        top_p=config.top_p,
        max_tokens=config.max_tokens,
        latency_ms=0,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        cost_usd=0.0,
        judge=JudgeScores(relevance=1, clarity=1, completeness=1, rationale=""),
        judge_overall=0.0,
        error=message,
    )


def run_experiment(
    *,
    question: str,
    runs: list[RunConfig],
    reference: str = "",
    settings: Settings,
    store: Store,
    keystore: KeyStore,
) -> ExperimentResult:
    """Execute every run, score with the fixed judge, summarize, persist, return."""
    judge_llm = build_llm(
        settings.judge_model,
        keystore.get(settings.judge_provider),
        timeout=settings.llm_timeout_seconds,
    )

    rows: list[ResultRow] = []
    for cfg in runs:
        # BYOK: the caller's own per-request key wins over any server-side key.
        api_key = cfg.api_key or keystore.get(cfg.provider)
        llm = build_llm(cfg.model, api_key, timeout=settings.llm_timeout_seconds)
        params = GenParams(
            temperature=cfg.temperature if cfg.temperature is not None else settings.default_temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_tokens if cfg.max_tokens is not None else settings.default_max_tokens,
        )
        try:
            completion = llm.complete(system=cfg.prompt, user=question, params=params)
            rows.append(
                score_run(judge_llm, config=cfg, completion=completion, question=question, reference=reference)
            )
        except LLMProviderError as exc:
            rows.append(_error_row(cfg, str(exc)))

    summary = summarize(rows)
    for row in rows:
        row.is_winner = row.label == summary.best_overall

    return store.save_experiment(question=question, reference=reference, rows=rows, summary=summary)
