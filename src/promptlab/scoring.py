"""Scoring: turn one raw completion into a fully-scored ResultRow, and rank runs.

Combines LLM-judge (relevance/clarity/completeness), lexical overlap (BLEU /
ROUGE-L, only when a reference exists), latency, tokens, and cost into the row a
result card renders — then computes the per-dimension winners for the comparison
summary. The judge is always the fixed referee passed in by the runner, never the
model under test.
"""

from __future__ import annotations

from .judge import judge_answer
from .llm import Completion
from .metrics import bleu, rouge_l
from .pricing import estimate_cost
from .schemas import ComparisonSummary, ResultRow, RunConfig


def score_run(
    judge_llm,
    *,
    config: RunConfig,
    completion: Completion,
    question: str,
    reference: str = "",
) -> ResultRow:
    """Score a single completion into a ResultRow."""
    verdict = judge_answer(judge_llm, question=question, candidate=completion.text, reference=reference)
    has_ref = bool(reference.strip())

    return ResultRow(
        label=config.label or f"{config.provider} · {config.model}",
        provider=config.provider,
        model=config.model,
        prompt=config.prompt,
        output=completion.text,
        temperature=config.temperature,
        top_p=config.top_p,
        max_tokens=config.max_tokens,
        latency_ms=completion.latency_ms,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        total_tokens=completion.total_tokens,
        cost_usd=estimate_cost(config.model, completion.prompt_tokens, completion.completion_tokens),
        judge=verdict,
        judge_overall=verdict.overall,
        bleu=bleu(completion.text, reference) if has_ref else None,
        rouge_l=rouge_l(completion.text, reference) if has_ref else None,
    )


def summarize(rows: list[ResultRow]) -> ComparisonSummary:
    """Compute per-dimension winners. Errored rows are ineligible."""
    ok = [r for r in rows if r.error is None]
    if not ok:
        return ComparisonSummary()

    best_quality = max(ok, key=lambda r: r.judge_overall)
    fastest = min(ok, key=lambda r: r.latency_ms)
    cheapest = min(ok, key=lambda r: r.cost_usd)
    # Overall: quality dominates; a faster then cheaper run breaks ties, since an
    # equally-good answer that is quicker and cheaper is the one worth shipping.
    best_overall = max(ok, key=lambda r: (r.judge_overall, -r.latency_ms, -r.cost_usd))

    return ComparisonSummary(
        best_quality=best_quality.label,
        fastest=fastest.label,
        cheapest=cheapest.label,
        best_overall=best_overall.label,
    )
