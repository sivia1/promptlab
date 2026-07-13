"""Scoring: turn one raw completion into a fully-scored ResultRow.

Combines the pieces — LLM-judge (relevance/clarity/completeness), lexical
overlap (BLEU/ROUGE-L, only when a reference exists), latency, tokens, and cost
— into the single row the comparison table renders. Kept separate from the
runner so the "how do we score an answer" logic has one home and is unit-testable
in isolation.
"""

from __future__ import annotations

from .judge import judge_answer
from .llm import Completion
from .metrics import bleu, rouge_l
from .pricing import estimate_cost
from .schemas import ResultRow


def score_answer(
    llm,
    *,
    label: str,
    model_id: str,
    question: str,
    completion: Completion,
    reference: str = "",
) -> ResultRow:
    """Score a single completion into a ResultRow."""
    verdict = judge_answer(llm, question=question, candidate=completion.text, reference=reference)

    lexical_bleu = bleu(completion.text, reference) if reference.strip() else None
    lexical_rouge = rouge_l(completion.text, reference) if reference.strip() else None

    return ResultRow(
        label=label,
        output=completion.text,
        latency_ms=completion.latency_ms,
        prompt_tokens=completion.prompt_tokens,
        completion_tokens=completion.completion_tokens,
        total_tokens=completion.total_tokens,
        cost_usd=estimate_cost(model_id, completion.prompt_tokens, completion.completion_tokens),
        judge=verdict,
        judge_overall=verdict.overall,
        bleu=lexical_bleu,
        rouge_l=lexical_rouge,
    )


def pick_winner(rows: list[ResultRow]) -> str | None:
    """Choose the winning label.

    Judge quality dominates (it's the signal that most reflects answer value);
    latency then cost break ties, since a faster/cheaper prompt of equal quality
    is the better one to ship. Errored rows can never win.
    """
    ranked = [r for r in rows if r.error is None]
    if not ranked:
        return None
    best = max(ranked, key=lambda r: (r.judge_overall, -r.latency_ms, -r.cost_usd))
    return best.label
