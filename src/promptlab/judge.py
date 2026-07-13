"""LLM-as-judge for prompt comparison.

Where an evaluation harness judges an answer against a golden reference,
PromptLab's question is different: *given the same user question, which prompt
produced the better answer?* So the judge scores a candidate answer on three
axes that matter for prompt quality — relevance, clarity, and completeness —
on a 1-5 scale, with an optional reference answer as an anchor when one exists.

Parsing is defensive: models sometimes wrap JSON in prose or code fences, so we
extract the first balanced JSON object and clamp every score into range. With
the offline stub the judge still returns a valid neutral verdict so the pipeline
is testable end to end.
"""

from __future__ import annotations

import json
import re

from .schemas import JudgeScores

_SCORE_KEYS = ("relevance", "clarity", "completeness")

JUDGE_SYSTEM = (
    "You are a meticulous evaluator of assistant answers. You compare an answer "
    "against the user's question and score it honestly. You always reply with a "
    "single JSON object and nothing else."
)

_JUDGE_TEMPLATE = """\
Score the candidate answer to the user's question on three axes, each an integer 1-5:
- relevance: does it actually address what was asked?
- clarity: is it well-structured and easy to follow?
- completeness: does it cover the important points without padding?

Question:
{question}
{reference_block}
Candidate answer:
{candidate}

Reply with ONLY this JSON object:
{{"relevance": <1-5>, "clarity": <1-5>, "completeness": <1-5>, "rationale": "<one short sentence>"}}
"""


def _clamp_score(value: object) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1.0
    return float(min(5.0, max(1.0, number)))


def _extract_json_object(text: str) -> dict:
    """Return the first balanced {...} object in `text`, or {} if none parses."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return {}


def parse_judge_response(text: str) -> JudgeScores:
    """Turn a raw judge response into validated, clamped scores."""
    payload = _extract_json_object(text)
    scores = {k: _clamp_score(payload.get(k)) for k in _SCORE_KEYS}
    return JudgeScores(
        relevance=scores["relevance"],
        clarity=scores["clarity"],
        completeness=scores["completeness"],
        rationale=str(payload.get("rationale", ""))[:500],
    )


def _neutral_verdict() -> JudgeScores:
    return JudgeScores(
        relevance=3.0,
        clarity=3.0,
        completeness=3.0,
        rationale="Offline stub judge: neutral score (no API key configured).",
    )


def judge_answer(llm, *, question: str, candidate: str, reference: str = "") -> JudgeScores:
    """Score one candidate answer with the LLM judge."""
    # The offline stub can't produce a real verdict; short-circuit to neutral so
    # the pipeline stays runnable without inventing scores that look real.
    if type(llm).__name__ == "StubLLM":
        return _neutral_verdict()

    reference_block = f"\nReference answer (for guidance):\n{reference}\n" if reference.strip() else ""
    user = _JUDGE_TEMPLATE.format(
        question=question,
        reference_block=reference_block,
        candidate=candidate,
    )
    completion = llm.complete(system=JUDGE_SYSTEM, user=user)
    raw = completion.text if hasattr(completion, "text") else str(completion)
    return parse_judge_response(raw)


def strip_code_fences(text: str) -> str:
    """Best-effort removal of ```...``` fences some models add around JSON."""
    return re.sub(r"```[a-z]*\n?|```", "", text).strip()
