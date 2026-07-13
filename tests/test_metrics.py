"""Unit tests for the self-contained BLEU / ROUGE-L implementations."""

import pytest

from promptlab.metrics import bleu, rouge_l


def test_identical_text_scores_high():
    text = "reset your password from the account settings page"
    assert bleu(text, text) == pytest.approx(1.0, abs=0.05)
    assert rouge_l(text, text) == pytest.approx(1.0, abs=0.01)


def test_disjoint_text_scores_low():
    assert bleu("apples oranges bananas", "quantum tunnelling physics") < 0.2
    assert rouge_l("apples oranges bananas", "quantum tunnelling physics") == 0.0


def test_partial_overlap_between_zero_and_one():
    cand = "click reset password"
    ref = "click the reset password button on the login page"
    score = rouge_l(cand, ref)
    assert 0.0 < score < 1.0


def test_empty_inputs_are_zero():
    assert bleu("", "something") == 0.0
    assert rouge_l("something", "") == 0.0


def test_scores_are_bounded():
    for c, r in [("a b c", "a b c d"), ("x y", "y x"), ("one", "one one one")]:
        assert 0.0 <= bleu(c, r) <= 1.0
        assert 0.0 <= rouge_l(c, r) <= 1.0
