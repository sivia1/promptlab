"""End-to-end pipeline tests using the offline StubLLM (no API keys needed)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from promptlab.api import create_app
from promptlab.config import Settings
from promptlab.keystore import KeyStore
from promptlab.pricing import estimate_cost
from promptlab.runner import run_experiment
from promptlab.schemas import RunConfig
from promptlab.store import Store


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Isolated paths and no keys -> StubLLM everywhere, fully deterministic.
    return Settings(
        db_path=tmp_path / "test.db",
        experiments_dir=tmp_path / "experiments",
        keystore_path=tmp_path / "keys.json",
    )


def _runs():
    return [
        RunConfig(provider="openai", model="gpt-4o-mini", prompt="Answer clearly."),
        RunConfig(provider="anthropic", model="claude-haiku-4-5-20251001", prompt="Answer briefly."),
        RunConfig(provider="groq", model="llama-3.1-8b-instant", prompt="Think step by step."),
    ]


def test_run_experiment_scores_and_summarizes(settings: Settings):
    store = Store(settings.db_path, settings.experiments_dir)
    keystore = KeyStore(settings.keystore_path)
    result = run_experiment(
        question="How do I reset my password?",
        runs=_runs(),
        reference="Go to settings and click reset password.",
        settings=settings,
        store=store,
        keystore=keystore,
    )
    assert len(result.results) == 3
    # Every dimension has a winner among the three runs.
    assert result.summary.best_overall in {r.label for r in result.results}
    assert result.summary.fastest is not None
    assert result.summary.cheapest is not None
    assert sum(r.is_winner for r in result.results) == 1
    for r in result.results:
        assert r.provider
        assert r.model
        assert r.total_tokens > 0
        assert r.bleu is not None  # reference provided -> lexical metrics computed
        assert r.rouge_l is not None


def test_labels_default_to_provider_model(settings: Settings):
    store = Store(settings.db_path, settings.experiments_dir)
    keystore = KeyStore(settings.keystore_path)
    result = run_experiment(
        question="Q?",
        runs=[RunConfig(provider="openai", model="gpt-4o", prompt="p")],
        settings=settings,
        store=store,
        keystore=keystore,
    )
    assert result.results[0].label == "openai · gpt-4o"


def test_experiment_is_persisted_and_reloadable(settings: Settings):
    store = Store(settings.db_path, settings.experiments_dir)
    keystore = KeyStore(settings.keystore_path)
    result = run_experiment(
        question="Q?",
        runs=_runs(),
        settings=settings,
        store=store,
        keystore=keystore,
    )
    reloaded = store.get_experiment(result.id)
    assert reloaded is not None
    assert reloaded.question == "Q?"
    assert (settings.experiments_dir / f"{result.id}.json").exists()

    summaries = store.list_experiments()
    assert summaries[0].id == result.id
    assert summaries[0].num_runs == 3


def test_cost_estimate_matches_pricing_table():
    # gpt-4o-mini: 0.00015 in / 0.00060 out per 1k tokens.
    assert estimate_cost("gpt-4o-mini", 1000, 1000) == pytest.approx(0.00075)


def test_keystore_roundtrip_and_masking(tmp_path: Path):
    ks = KeyStore(tmp_path / "keys.json")
    assert ks.status()["openai"]["configured"] is False
    ks.set("openai", "sk-test-abcd1234")
    status = ks.status()["openai"]
    assert status["configured"] is True
    assert status["masked"] == "…1234"  # never the raw key
    assert status["source"] == "stored"
    ks.delete("openai")
    assert ks.status()["openai"]["configured"] is False


def test_providers_endpoint_lists_models_and_config(settings: Settings):
    client = TestClient(create_app(settings))
    body = client.get("/api/providers").json()
    ids = {p["id"] for p in body["providers"]}
    assert {"openai", "anthropic", "gemini", "groq", "openrouter"} <= ids
    anthropic = next(p for p in body["providers"] if p["id"] == "anthropic")
    assert anthropic["configured"] is False
    assert any(m["id"] == "claude-3-5-sonnet-latest" for m in anthropic["models"])
    assert body["judge"]["provider"] == "groq"


def test_set_key_via_api_disabled_by_default(settings: Settings):
    # Secure by default: a fresh deployment can't persist a pasted key server-side.
    client = TestClient(create_app(settings))
    resp = client.put("/api/keys/openai", json={"key": "sk-live-9999"})
    assert resp.status_code == 403


def test_set_key_via_api_when_enabled(settings: Settings):
    settings.allow_stored_keys = True
    client = TestClient(create_app(settings))
    resp = client.put("/api/keys/openai", json={"key": "sk-live-9999"})
    assert resp.status_code == 200
    assert resp.json()["keys"]["openai"]["masked"] == "…9999"


def test_run_uses_byok_key_over_server_key(settings: Settings, monkeypatch):
    # A per-request api_key must win over any server-side key, and never leak
    # into the response. Patch build_llm to capture what key it was actually
    # called with, instead of hitting a real provider over the network.
    import promptlab.runner as runner_module

    seen_keys = []

    def fake_build_llm(model_id, api_key, *, timeout=60.0):
        seen_keys.append(api_key)
        from promptlab.llm import StubLLM

        return StubLLM(model_id)

    monkeypatch.setattr(runner_module, "build_llm", fake_build_llm)

    store = Store(settings.db_path, settings.experiments_dir)
    keystore = KeyStore(settings.keystore_path)  # empty: no server-side key for groq
    result = run_experiment(
        question="q",
        runs=[
            RunConfig(
                provider="groq",
                model="llama-3.1-8b-instant",
                prompt="p",
                api_key="gsk-caller-supplied",
            )
        ],
        settings=settings,
        store=store,
        keystore=keystore,
    )
    assert "gsk-caller-supplied" in seen_keys  # the run's own client used the BYOK key
    assert "gsk-caller-supplied" not in result.model_dump_json()  # never echoed back


def test_run_endpoint(settings: Settings):
    client = TestClient(create_app(settings))
    resp = client.post(
        "/api/run",
        json={
            "question": "How do I reset my password?",
            "runs": [
                {"provider": "openai", "model": "gpt-4o-mini", "prompt": "Answer clearly."},
                {"provider": "groq", "model": "llama-3.1-8b-instant", "prompt": "Answer briefly."},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 2
    assert body["summary"]["best_overall"] is not None


def test_run_endpoint_rejects_empty_runs(settings: Settings):
    client = TestClient(create_app(settings))
    resp = client.post("/api/run", json={"question": "q", "runs": []})
    assert resp.status_code == 422  # pydantic min_length on runs
