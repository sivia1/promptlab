"""Experiment runner: the spine of PromptLab.

Takes a question, a set of prompt versions, and a model; runs every prompt
through the model; scores each answer; marks the winner; and persists the whole
experiment. This is exactly the loop the "Run Experiment" button triggers.

Each prompt version's `text` is used as the *system* prompt and the shared
question as the *user* message — so you're comparing how different system
instructions answer the same question.
"""

from __future__ import annotations

from .config import Settings
from .llm import LLMProviderError, build_llm
from .schemas import ExperimentResult, PromptVersion, ResultRow
from .scoring import pick_winner, score_answer
from .store import Store


def run_experiment(
    *,
    question: str,
    prompts: list[PromptVersion],
    model_id: str,
    reference: str = "",
    settings: Settings,
    store: Store,
) -> ExperimentResult:
    """Run every prompt version against `model_id`, score, persist, return."""
    llm = build_llm(model_id, settings)
    judge = build_llm(settings.judge_model, settings)

    rows: list[ResultRow] = []
    for pv in prompts:
        try:
            completion = llm.complete(system=pv.text, user=question)
            row = score_answer(
                judge,
                label=pv.label,
                model_id=model_id,
                question=question,
                completion=completion,
                reference=reference,
            )
        except LLMProviderError as exc:
            # A provider failure on one prompt shouldn't sink the whole run; the
            # row is recorded with an error so the UI can show what happened.
            row = ResultRow(
                label=pv.label,
                output="",
                latency_ms=0,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                judge={"relevance": 1, "clarity": 1, "completeness": 1, "rationale": ""},
                judge_overall=0.0,
                error=str(exc),
            )
        rows.append(row)

    winner = pick_winner(rows)
    for row in rows:
        row.is_winner = row.label == winner

    return store.save_experiment(
        question=question,
        model=model_id,
        reference=reference,
        rows=rows,
        winner_label=winner,
    )
