"""Lexical overlap metrics: BLEU and ROUGE-L.

Self-contained, dependency-free implementations so PromptLab has real n-gram and
LCS scores without pulling in nltk/rouge-score. These live in one small module
on purpose — if they ever earn a home in a shared eval library, they lift out
cleanly.

Both compare a candidate answer against a reference and return a float in
[0, 1]. They are only meaningful when a reference answer is provided; with no
reference the runner skips them.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _ngrams(tokens: list[str], n: int) -> Counter[tuple[str, ...]]:
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def bleu(candidate: str, reference: str, *, max_n: int = 4, epsilon: float = 0.1) -> float:
    """Sentence-level BLEU with a brevity penalty and method-1 smoothing.

    Two adjustments make this behave sensibly on single short answers rather than
    document corpora:

    * The n-gram order is capped at the candidate length, so a 3-word answer is
      never punished for lacking 4-grams it cannot contain.
    * Only *zero-count* precisions are smoothed, and gently (NLTK's "method 1":
      a zero numerator becomes ``epsilon`` rather than a full add-1). Blunt add-1
      smoothing inflates BLEU on tiny unrelated strings; this doesn't.
    """
    cand = _tokens(candidate)
    ref = _tokens(reference)
    if not cand or not ref:
        return 0.0

    order = min(max_n, len(cand))
    log_precisions = []
    for n in range(1, order + 1):
        cand_ngrams = _ngrams(cand, n)
        ref_ngrams = _ngrams(ref, n)
        overlap = sum(min(c, ref_ngrams[g]) for g, c in cand_ngrams.items())
        total = max(1, sum(cand_ngrams.values()))
        numerator = overlap if overlap > 0 else epsilon
        log_precisions.append(math.log(numerator / total))

    geo_mean = math.exp(sum(log_precisions) / order)
    brevity = 1.0 if len(cand) >= len(ref) else math.exp(1 - len(ref) / len(cand))
    return round(brevity * geo_mean, 4)


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Length of the longest common subsequence (classic DP)."""
    prev = [0] * (len(b) + 1)
    for token_a in a:
        curr = [0]
        for j, token_b in enumerate(b, start=1):
            if token_a == token_b:
                curr.append(prev[j - 1] + 1)
            else:
                curr.append(max(prev[j], curr[j - 1]))
        prev = curr
    return prev[-1]


def rouge_l(candidate: str, reference: str, *, beta: float = 1.2) -> float:
    """ROUGE-L F-measure based on the longest common subsequence.

    beta weights recall over precision (the standard ROUGE default favours
    recall), matching the reference implementation's F_lcs formula.
    """
    cand = _tokens(candidate)
    ref = _tokens(reference)
    if not cand or not ref:
        return 0.0

    lcs = _lcs_length(cand, ref)
    if lcs == 0:
        return 0.0

    precision = lcs / len(cand)
    recall = lcs / len(ref)
    beta_sq = beta * beta
    f = ((1 + beta_sq) * precision * recall) / (recall + beta_sq * precision)
    return round(f, 4)
