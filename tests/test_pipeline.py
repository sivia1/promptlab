"""End-to-end pipeline tests using the offline StubLLM (no API key needed)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from promptlab.api import create_app
from promptlab.config import Settings
from promptlab.pricing import estimate_cost
from promptlab.runner import run_experiment
from promptlab.schemas import PromptVersion
from promptlab.store import Store


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # No keys -> StubLLM everywhere, fully deterministic.
    return Settings(db_path=tmp_path / "test.db", experiments_dir=tmp_path / "experiments")


def test_run_experiment_scores_and_picks_winner(settings: Settings):
    store = Store(settings.db_path, settings.experiments_dir)
    result = run_experiment(
        question="How do I reset my password?",
        prompts=[
            PromptVersion(label="V1", text="Answer clearly."),
            PromptVersion(label="V2", text="Answer briefly."),
        ],
        model_id="llama-3.3-70b-versatile",
        reference="Go to settings and click reset password.",
        settings=settings,
        store=store,
    )
    assert len(result.results) == 2
    assert result.winner_label in {"V1", "V2"}
    assert sum(r.is_winner for r in result.results) == 1
    for r in result.results:
        assert r.total_tokens > 0
        assert r.cost_usd >= 0.0
        assert r.bleu is not None  # reference provided -> lexical metrics computed
        assert r.rouge_l is not None


def test_experiment_is_persisted_and_reloadable(settings: Settings):
    store = Store(settings.db_path, settings.experiments_dir)
    result = run_experiment(
        question="Q?",
        prompts=[PromptVersion(label="V1", text="p")],
        model_id="gpt-4o-mini",
        settings=settings,
        store=store,
    )
    reloaded = store.get_experiment(result.id)
    assert reloaded is not None
    assert reloaded.question == "Q?"
    assert (settings.experiments_dir / f"{result.id}.json").exists()

    summaries = store.list_experiments()
    assert summaries[0].id == result.id
    assert summaries[0].num_prompts == 1


def test_cost_estimate_matches_pricing_table():
    # gpt-4o-mini: 0.00015 in / 0.00060 out per 1k tokens.
    assert estimate_cost("gpt-4o-mini", 1000, 1000) == pytest.approx(0.00075)


def test_run_endpoint(settings: Settings):
    client = TestClient(create_app(settings))
    resp = client.post(
        "/api/run",
        json={
            "question": "How do I reset my password?",
            "prompts": [{"label": "V1", "text": "Answer clearly."}],
            "model": "llama-3.3-70b-versatile",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"][0]["label"] == "V1"
    assert body["winner_label"] == "V1"


def test_run_endpoint_rejects_empty_prompts(settings: Settings):
    client = TestClient(create_app(settings))
    resp = client.post(
        "/api/run",
        json={"question": "q", "prompts": [], "model": "gpt-4o-mini"},
    )
    assert resp.status_code == 422  # pydantic min_length on prompts
