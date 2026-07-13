"""Cost estimation.

Turns token counts into a USD estimate using the per-model prices declared in
the catalog. Kept as its own tiny module so the "how much did that prompt cost"
question has exactly one answer.
"""

from __future__ import annotations

from .catalog import resolve


def estimate_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost of one completion, rounded to 6 dp (sub-cent precision)."""
    model = resolve(model_id)
    cost = (
        prompt_tokens / 1000 * model.input_per_1k
        + completion_tokens / 1000 * model.output_per_1k
    )
    return round(cost, 6)
