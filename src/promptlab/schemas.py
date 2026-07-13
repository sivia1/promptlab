"""Pydantic models — the contract between the API, the runner, and storage.

An experiment now compares independent *runs*: each run picks its own provider,
model, prompt, and inference settings, all answering one shared question. That
makes an experiment able to compare models, prompts, and parameters at once.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JudgeScores(BaseModel):
    """LLM-judge verdict for a single answer (each axis 1-5)."""

    relevance: float
    clarity: float
    completeness: float
    rationale: str = ""

    @property
    def overall(self) -> float:
        return round((self.relevance + self.clarity + self.completeness) / 3, 2)


class RunConfig(BaseModel):
    """One thing to run: a provider + model + prompt + optional inference knobs."""

    provider: str = Field(..., description="Provider id, e.g. 'openai' or 'anthropic'.")
    model: str = Field(..., description="Model id from the catalog, e.g. 'gpt-4o-mini'.")
    prompt: str = Field(..., description="System prompt for this run.")
    label: str = Field("", description="Display label; defaults to 'Provider · Model'.")
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    api_key: str | None = Field(
        None,
        description=(
            "BYOK: this caller's own key for this run's provider, sent fresh with "
            "every request. Used only for this one call — never persisted to disk, "
            "logged, or echoed back in any response. Falls back to a server-side "
            "key (env var, or the stored file if PROMPTLAB_ALLOW_STORED_KEYS=true) "
            "when omitted."
        ),
    )


class RunRequest(BaseModel):
    """Payload for POST /run."""

    question: str = Field(..., description="The user question every run answers.")
    reference: str = Field("", description="Optional gold answer; enables BLEU/ROUGE.")
    runs: list[RunConfig] = Field(..., min_length=1)


class ResultRow(BaseModel):
    """A scored answer for one run."""

    label: str
    provider: str
    model: str
    prompt: str
    output: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    judge: JudgeScores
    judge_overall: float
    bleu: float | None = None
    rouge_l: float | None = None
    is_winner: bool = False
    error: str | None = None


class ComparisonSummary(BaseModel):
    """Per-dimension winners across the runs — the 'story' of the experiment."""

    best_quality: str | None = None  # highest judge score
    fastest: str | None = None  # lowest latency
    cheapest: str | None = None  # lowest cost
    best_overall: str | None = None  # quality first, then speed, then cost


class ExperimentResult(BaseModel):
    """A full experiment: the request, every scored run, and the summary."""

    id: int
    created_at: str = Field(default_factory=_now)
    question: str
    reference: str = ""
    results: list[ResultRow]
    summary: ComparisonSummary

    @property
    def winner_label(self) -> str | None:
        return self.summary.best_overall


class ExperimentSummary(BaseModel):
    """Compact row for the history page."""

    id: int
    created_at: str
    question: str
    num_runs: int
    models: list[str] = Field(default_factory=list)
    best_overall: str | None = None
