# PromptLab

**A platform for systematically designing, comparing, evaluating, and versioning prompts across multiple LLMs.**

Prompt engineering is usually done by eyeballing outputs in a chat window. PromptLab replaces that with a repeatable experiment: write several prompt versions, run them against the same question on the model of your choice, and see them scored side by side on **LLM-judge quality, BLEU, ROUGE-L, latency, tokens, and cost** — with the winner picked automatically and every run saved so you can track how a prompt evolved.

It is the second tool in a small family of AI-systems infrastructure:

| Tool | Question it answers |
| --- | --- |
| **EvalForge** | Is my AI system good? |
| **PromptLab** | Which prompt is actually better? |
| **TraceLens** | How do I debug it in production? |

Each is an independent repo with its own deployment and CI — they share a philosophy, not a codebase.

---

## What it does

1. **Prompt editor** — enter a question and N prompt versions (V1, V2, V3…).
2. **Model selector** — run against OpenAI, Groq, or Gemini (one OpenAI-compatible client).
3. **Run experiment** — every prompt is executed and scored.
4. **Side-by-side comparison** — judge / BLEU / ROUGE-L / latency / tokens / cost per version.
5. **Winner** — highest judge score, ties broken by latency then cost.
6. **History with deltas** — every run is saved; see how judge/latency/cost moved vs the last run.
7. **Prompt Evolution** — a V1→V2→V3 timeline of performance over time.
8. **Prompt Diff** — red/green diff between two versions.
9. **Export** — download any experiment as JSON or CSV.

BLEU and ROUGE-L only apply when you provide an optional reference ("gold") answer; without one, PromptLab scores on judge + latency/tokens/cost.

---

## Quickstart

```bash
# 1. Backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # add a Groq/OpenAI/Gemini key (optional — see below)

# 2. Smoke-test the whole pipeline from the terminal
make run

# 3. Serve the API
make serve                  # http://127.0.0.1:8000

# 4. Frontend (separate terminal)
make ui                     # http://localhost:5173
```

**No API key?** Everything still runs. PromptLab falls back to a deterministic
`StubLLM`, so the UI, storage, metrics, and exports all work offline — only the
answers and judge scores are placeholders. Add a key to get real completions.

### Providers

All three providers are reached through their OpenAI-compatible endpoints, so one
client covers them. Set any of `PROMPTLAB_OPENAI_API_KEY`,
`PROMPTLAB_GROQ_API_KEY`, or `PROMPTLAB_GEMINI_API_KEY` (or the generic
`PROMPTLAB_LLM_API_KEY`) and the matching models appear in the dropdown.

---

## Architecture

```
frontend/            React + Vite (plain JSX + CSS)
src/promptlab/
  catalog.py         models: provider + pricing, declared once
  llm.py             OpenAI-compatible client (returns token usage) + offline StubLLM
  judge.py           LLM-as-judge: relevance / clarity / completeness (1-5)
  metrics.py         self-contained BLEU + ROUGE-L
  pricing.py         token counts -> USD
  scoring.py         one completion -> one fully-scored row
  runner.py          the "Run Experiment" loop
  store.py           SQLite + a JSON mirror per experiment
  api.py             FastAPI: /run, /experiments, /export
  cli.py             `promptlab serve` / `promptlab run`
```

The runner uses each prompt version as the **system** message and the shared
question as the **user** message — so you are comparing how different system
instructions answer the same thing.

---

## Development

```bash
make test         # pytest (runs fully offline via StubLLM)
make lint         # ruff
make typecheck    # mypy (advisory)
```

CI runs lint + tests on every push with no API key — the deterministic stub keeps
the suite hermetic.

## License

MIT
