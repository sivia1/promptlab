"""Pydantic models — the contract between the API, the runner, and storage.

One canonical shape for a prompt version, a scored result, and a whole
experiment. Everything the frontend renders is one of these serialized to JSON.
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


class PromptVersion(BaseModel):
    """One labelled prompt under test."""

    label: str = Field(..., description="Short id shown in the table, e.g. 'V1' or 'A'.")
    text: str = Field(..., description="The prompt template / system text to run.")


class RunRequest(BaseModel):
    """Payload for POST /run."""

    question: str = Field(..., description="The user question every prompt answers.")
    prompts: list[PromptVersion] = Field(..., min_length=1)
    model: str = Field(..., description="Model id from the catalog, e.g. 'gpt-4o-mini'.")
    reference: str = Field("", description="Optional gold answer; enables BLEU/ROUGE.")


class ResultRow(BaseModel):
    """A scored answer for one prompt version."""

    label: str
    output: str
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


class ExperimentResult(BaseModel):
    """A full run: the request, every scored row, and the winner."""

    id: int
    created_at: str = Field(default_factory=_now)
    question: str
    model: str
    reference: str = ""
    results: list[ResultRow]
    winner_label: str | None = None


class ExperimentSummary(BaseModel):
    """Compact row for the history sidebar."""

    id: int
    created_at: str
    question: str
    model: str
    num_prompts: int
    winner_label: str | None = None
    winner_judge: float | None = None
