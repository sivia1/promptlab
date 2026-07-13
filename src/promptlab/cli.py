"""Command-line entry point.

`promptlab serve` runs the API; `promptlab run` executes a quick experiment from
the terminal so the whole pipeline is exercisable without the frontend (handy in
CI and for a curl-free smoke test).
"""

from __future__ import annotations

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from .config import load_settings
from .runner import run_experiment
from .schemas import PromptVersion
from .store import Store

app = typer.Typer(add_completion=False, help="PromptLab — prompt experimentation platform.")
console = Console()


@app.command()
def serve() -> None:
    """Run the HTTP API for the frontend."""
    settings = load_settings()
    uvicorn.run("promptlab.api:app", host=settings.api_host, port=settings.api_port, reload=False)


@app.command()
def run(
    question: str = typer.Option(..., "--question", "-q", help="The question to answer."),
    prompt: list[str] = typer.Option(..., "--prompt", "-p", help="A prompt version (repeatable)."),
    model: str = typer.Option("llama-3.3-70b-versatile", "--model", "-m", help="Model id."),
    reference: str = typer.Option("", "--reference", "-r", help="Optional gold answer."),
) -> None:
    """Run one experiment and print the comparison table."""
    settings = load_settings()
    store = Store(settings.db_path, settings.experiments_dir)
    prompts = [PromptVersion(label=f"V{i+1}", text=p) for i, p in enumerate(prompt)]

    result = run_experiment(
        question=question,
        prompts=prompts,
        model_id=model,
        reference=reference,
        settings=settings,
        store=store,
    )

    table = Table(title=f"Experiment #{result.id} — {model}")
    for col in ("Prompt", "Judge", "BLEU", "ROUGE-L", "Latency", "Tokens", "Cost"):
        table.add_column(col)
    for r in result.results:
        crown = " 🏆" if r.is_winner else ""
        table.add_row(
            f"{r.label}{crown}",
            f"{r.judge_overall:.2f}",
            "—" if r.bleu is None else f"{r.bleu:.3f}",
            "—" if r.rouge_l is None else f"{r.rouge_l:.3f}",
            f"{r.latency_ms} ms",
            str(r.total_tokens),
            f"${r.cost_usd:.6f}",
        )
    console.print(table)
    if result.winner_label:
        console.print(f"[bold green]Winner: {result.winner_label}[/bold green]")


if __name__ == "__main__":
    app()
