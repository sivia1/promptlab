"""HTTP API for the React frontend.

Small and boring on purpose: run an experiment, list history, fetch one
experiment, and export it. All the real work lives in the runner/store — the API
just validates input, wires in settings, and serializes.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .catalog import available_models
from .config import Settings, load_settings
from .runner import run_experiment
from .schemas import RunRequest
from .store import Store


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    store = Store(settings.db_path, settings.experiments_dir)

    app = FastAPI(title="PromptLab", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # All routes live under /api so the Vite dev server can proxy a single prefix
    # (matching the sibling tools' frontend convention).
    api = APIRouter(prefix="/api")

    @api.get("/health")
    def health() -> dict:
        return {"status": "ok", "has_llm": settings.has_llm()}

    @api.get("/models")
    def models() -> dict:
        avail = available_models(settings)
        return {
            "models": [
                {"id": m.id, "label": m.label, "provider": m.provider} for m in avail
            ],
            "has_llm": settings.has_llm(),
        }

    @api.post("/run")
    def run(req: RunRequest) -> dict:
        if not req.prompts:
            raise HTTPException(status_code=400, detail="At least one prompt is required.")
        result = run_experiment(
            question=req.question,
            prompts=req.prompts,
            model_id=req.model,
            reference=req.reference,
            settings=settings,
            store=store,
        )
        return result.model_dump()

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
            ["label", "judge_overall", "relevance", "clarity", "completeness",
             "bleu", "rouge_l", "latency_ms", "total_tokens", "cost_usd", "is_winner"]
        )
        for r in result.results:
            writer.writerow(
                [r.label, r.judge_overall, r.judge.relevance, r.judge.clarity,
                 r.judge.completeness, r.bleu, r.rouge_l, r.latency_ms,
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
