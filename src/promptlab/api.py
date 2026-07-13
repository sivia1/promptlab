"""HTTP API for the React frontend.

Routes fall in four groups: providers/models (catalog), keys (Settings page),
run (execute an experiment), and experiments (history + export). All the real
work lives in the runner/store/keystore — the API validates input, wires in
settings, and serializes. Every route is under /api so the Vite dev server can
proxy a single prefix.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .catalog import PROVIDERS, models_for
from .config import Settings, load_settings
from .keystore import KeyStore
from .llm import GenParams, LLMProviderError, build_llm
from .runner import run_experiment
from .schemas import RunRequest
from .store import Store


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = Store(settings.db_path, settings.experiments_dir)
    keystore = KeyStore(settings.keystore_path, allow_stored=settings.allow_stored_keys)

    app = FastAPI(title="PromptLab", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    api = APIRouter(prefix="/api")

    # --- catalog ---

    @api.get("/health")
    def health() -> dict:
        configured = sum(1 for v in keystore.status().values() if v["configured"])
        return {"status": "ok", "providers_configured": configured}

    @api.get("/providers")
    def providers() -> dict:
        status = keystore.status()
        return {
            "providers": [
                {
                    "id": p.id,
                    "label": p.label,
                    "keys_url": p.keys_url,
                    "configured": status[p.id]["configured"],
                    "models": [
                        {
                            "id": m.id,
                            "label": m.label,
                            "input_per_1k": m.input_per_1k,
                            "output_per_1k": m.output_per_1k,
                        }
                        for m in models_for(p.id)
                    ],
                }
                for p in PROVIDERS.values()
            ],
            "judge": {"provider": settings.judge_provider, "model": settings.judge_model},
            "allow_stored_keys": settings.allow_stored_keys,
        }

    # --- keys (Settings page) ---

    @api.get("/keys")
    def get_keys() -> dict:
        return {"keys": keystore.status()}

    def _require_stored_keys_enabled() -> None:
        if not settings.allow_stored_keys:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Server-side key storage is disabled on this deployment "
                    "(PROMPTLAB_ALLOW_STORED_KEYS is off). Send your key per-request "
                    "(BYOK) instead — see RunConfig.api_key."
                ),
            )

    @api.put("/keys/{provider}")
    def set_key(provider: str, key: str = Body(..., embed=True)) -> dict:
        if provider not in PROVIDERS:
            raise HTTPException(status_code=404, detail=f"Unknown provider {provider!r}.")
        _require_stored_keys_enabled()
        keystore.set(provider, key)
        return {"keys": keystore.status()}

    @api.delete("/keys/{provider}")
    def delete_key(provider: str) -> dict:
        if provider not in PROVIDERS:
            raise HTTPException(status_code=404, detail=f"Unknown provider {provider!r}.")
        _require_stored_keys_enabled()
        keystore.delete(provider)
        return {"keys": keystore.status()}

    @api.post("/keys/{provider}/test")
    def test_key(provider: str, key: str | None = Body(None, embed=True)) -> dict:
        """Verify a key with one live call. Never persisted — used once and discarded.

        Pass ``key`` in the body to test a BYOK key straight from the caller's
        browser; omit it to test whatever's configured server-side (env var, or
        the stored file when stored keys are enabled).
        """
        if provider not in PROVIDERS:
            raise HTTPException(status_code=404, detail=f"Unknown provider {provider!r}.")
        effective_key = key or keystore.get(provider)
        if not effective_key:
            return {"ok": False, "error": "No key configured."}
        candidates = models_for(provider)
        if not candidates:
            return {"ok": False, "error": "No models declared for this provider."}
        llm = build_llm(candidates[0].id, effective_key, timeout=settings.llm_timeout_seconds)
        try:
            llm.complete(system="", user="ping", params=GenParams(max_tokens=1))
            return {"ok": True}
        except LLMProviderError as exc:
            return {"ok": False, "error": str(exc)}

    # --- run ---

    @api.post("/run")
    def run(req: RunRequest) -> dict:
        result = run_experiment(
            question=req.question,
            runs=req.runs,
            reference=req.reference,
            settings=settings,
            store=store,
            keystore=keystore,
        )
        return result.model_dump()

    # --- history + export ---

    @api.get("/experiments")
    def experiments(limit: int = 50) -> dict:
        return {"experiments": [e.model_dump() for e in store.list_experiments(limit)]}

    @api.get("/experiments/{exp_id}")
    def experiment(exp_id: int) -> dict:
        result = store.get_experiment(exp_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found.")
        return result.model_dump()

    @api.get("/experiments/{exp_id}/export.json")
    def export_json(exp_id: int) -> Response:
        result = store.get_experiment(exp_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found.")
        return Response(
            content=result.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="experiment-{exp_id}.json"'},
        )

    @api.get("/experiments/{exp_id}/export.csv")
    def export_csv(exp_id: int) -> Response:
        result = store.get_experiment(exp_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Experiment {exp_id} not found.")
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["label", "provider", "model", "judge_overall", "relevance", "clarity",
             "completeness", "bleu", "rouge_l", "latency_ms", "total_tokens", "cost_usd",
             "is_winner"]
        )
        for r in result.results:
            writer.writerow(
                [r.label, r.provider, r.model, r.judge_overall, r.judge.relevance,
                 r.judge.clarity, r.judge.completeness, r.bleu, r.rouge_l, r.latency_ms,
                 r.total_tokens, r.cost_usd, r.is_winner]
            )
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="experiment-{exp_id}.csv"'},
        )

    app.include_router(api)
    return app


app = create_app()
