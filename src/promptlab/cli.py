"""Command-line entry point.

``promptlab serve`` runs the API; ``promptlab run`` benchmarks one shared prompt
across several models from the terminal, so the whole pipeline is exercisable
without the frontend (handy in CI and for a quick smoke test).
"""

from __future__ import annotations

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from .catalog import resolve
from .config import load_settings
from .keystore import KeyStore
from .runner import run_experiment
from .schemas import RunConfig
from .store import Store

app = typer.Typer(add_completion=False, help="PromptLab — benchmark prompts and LLMs side by side.")
console = Console()


@app.command()
def serve() -> None:
    """Run the HTTP API for the frontend."""
    settings = load_settings()
    uvicorn.run("promptlab.api:app", host=settings.api_host, port=settings.api_port, reload=False)


@app.command()
def run(
    question: str = typer.Option(..., "--question", "-q", help="The question to answer."),
    prompt: str = typer.Option("You are a helpful assistant.", "--prompt", "-p", help="Shared system prompt."),
    model: list[str] = typer.Option(..., "--model", "-m", help="Model id (repeatable)."),
    reference: str = typer.Option("", "--reference", "-r", help="Optional gold answer."),
) -> None:
    """Benchmark one prompt across several models and print the comparison."""
    settings = load_settings()
    store = Store(settings.db_path, settings.experiments_dir)
    keystore = KeyStore(settings.keystore_path, allow_stored=settings.allow_stored_keys)

    runs = [RunConfig(provider=resolve(m).provider, model=m, prompt=prompt) for m in model]
    result = run_experiment(
        question=question,
        runs=runs,
        reference=reference,
        settings=settings,
        store=store,
        keystore=keystore,
    )

    table = Table(title=f"Experiment #{result.id}")
    for col in ("Run", "Judge", "BLEU", "ROUGE-L", "Latency", "Tokens", "Cost"):
        table.add_column(col)
    for r in result.results:
        crown = " 🏆" if r.is_winner else ""
        table.add_row(
            f"{r.label}{crown}",
            "err" if r.error else f"{r.judge_overall:.2f}",
            "—" if r.bleu is None else f"{r.bleu:.3f}",
            "—" if r.rouge_l is None else f"{r.rouge_l:.3f}",
            f"{r.latency_ms} ms",
            str(r.total_tokens),
            f"${r.cost_usd:.6f}",
        )
    console.print(table)
    s = result.summary
    console.print(
        f"[bold]Best quality:[/bold] {s.best_quality}   "
        f"[bold]Fastest:[/bold] {s.fastest}   "
        f"[bold]Cheapest:[/bold] {s.cheapest}   "
        f"[bold green]Best overall:[/bold green] {s.best_overall}"
    )


if __name__ == "__main__":
    app()
