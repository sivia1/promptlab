"""Persistence: SQLite + a JSON mirror per experiment.

SQLite is the source of truth for history; each experiment is also written to
``experiments/<id>.json`` so a run is inspectable (and diffable) without a DB
browser. No ORM — the schema is small and the SQL is clearer than a mapping
layer would be.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schemas import ComparisonSummary, ExperimentResult, ExperimentSummary, ResultRow

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    question     TEXT NOT NULL,
    reference    TEXT NOT NULL DEFAULT '',
    best_quality TEXT,
    fastest      TEXT,
    cheapest     TEXT,
    best_overall TEXT
);
CREATE TABLE IF NOT EXISTS results (
    experiment_id     INTEGER NOT NULL REFERENCES experiments(id) ON DELETE CASCADE,
    label             TEXT NOT NULL,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    prompt            TEXT NOT NULL,
    output            TEXT NOT NULL,
    temperature       REAL,
    top_p             REAL,
    max_tokens        INTEGER,
    latency_ms        INTEGER NOT NULL,
    prompt_tokens     INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens      INTEGER NOT NULL,
    cost_usd          REAL NOT NULL,
    judge_overall     REAL NOT NULL,
    judge_json        TEXT NOT NULL,
    bleu              REAL,
    rouge_l           REAL,
    is_winner         INTEGER NOT NULL DEFAULT 0,
    error             TEXT
);
"""


class Store:
    """Thin data-access layer over a single SQLite file."""

    def __init__(self, db_path: Path, experiments_dir: Path):
        self.db_path = Path(db_path)
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # --- writes ---

    def save_experiment(
        self,
        *,
        question: str,
        reference: str,
        rows: list[ResultRow],
        summary: ComparisonSummary,
    ) -> ExperimentResult:
        cur = self._conn.execute(
            "INSERT INTO experiments (created_at, question, reference, best_quality, fastest, "
            "cheapest, best_overall) VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)",
            (question, reference, summary.best_quality, summary.fastest,
             summary.cheapest, summary.best_overall),
        )
        exp_id = int(cur.lastrowid)
        for r in rows:
            self._conn.execute(
                "INSERT INTO results (experiment_id, label, provider, model, prompt, output, "
                "temperature, top_p, max_tokens, latency_ms, prompt_tokens, completion_tokens, "
                "total_tokens, cost_usd, judge_overall, judge_json, bleu, rouge_l, is_winner, error) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    exp_id, r.label, r.provider, r.model, r.prompt, r.output,
                    r.temperature, r.top_p, r.max_tokens, r.latency_ms, r.prompt_tokens,
                    r.completion_tokens, r.total_tokens, r.cost_usd, r.judge_overall,
                    r.judge.model_dump_json(), r.bleu, r.rouge_l, int(r.is_winner), r.error,
                ),
            )
        self._conn.commit()

        result = self.get_experiment(exp_id)
        assert result is not None
        (self.experiments_dir / f"{exp_id}.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        return result

    # --- reads ---

    def get_experiment(self, exp_id: int) -> ExperimentResult | None:
        exp = self._conn.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,)).fetchone()
        if exp is None:
            return None
        rows = self._conn.execute(
            "SELECT * FROM results WHERE experiment_id = ? ORDER BY rowid", (exp_id,)
        ).fetchall()
        return ExperimentResult(
            id=exp["id"],
            created_at=exp["created_at"],
            question=exp["question"],
            reference=exp["reference"],
            results=[self._row_to_result(r) for r in rows],
            summary=ComparisonSummary(
                best_quality=exp["best_quality"],
                fastest=exp["fastest"],
                cheapest=exp["cheapest"],
                best_overall=exp["best_overall"],
            ),
        )

    def list_experiments(self, limit: int = 50) -> list[ExperimentSummary]:
        exps = self._conn.execute(
            "SELECT * FROM experiments ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for e in exps:
            models = self._conn.execute(
                "SELECT DISTINCT model FROM results WHERE experiment_id = ? ORDER BY rowid",
                (e["id"],),
            ).fetchall()
            out.append(
                ExperimentSummary(
                    id=e["id"],
                    created_at=e["created_at"],
                    question=e["question"],
                    num_runs=len(models),
                    models=[m["model"] for m in models],
                    best_overall=e["best_overall"],
                )
            )
        return out

    @staticmethod
    def _row_to_result(r: sqlite3.Row) -> ResultRow:
        return ResultRow(
            label=r["label"],
            provider=r["provider"],
            model=r["model"],
            prompt=r["prompt"],
            output=r["output"],
            temperature=r["temperature"],
            top_p=r["top_p"],
            max_tokens=r["max_tokens"],
            latency_ms=r["latency_ms"],
            prompt_tokens=r["prompt_tokens"],
            completion_tokens=r["completion_tokens"],
            total_tokens=r["total_tokens"],
            cost_usd=r["cost_usd"],
            judge=json.loads(r["judge_json"]),
            judge_overall=r["judge_overall"],
            bleu=r["bleu"],
            rouge_l=r["rouge_l"],
            is_winner=bool(r["is_winner"]),
            error=r["error"],
        )
