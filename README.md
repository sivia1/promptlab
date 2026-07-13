# PromptLab

**A playground to benchmark prompts _and_ LLMs side by side.**

Pick one question. Run it across different providers, models, prompts, and
inference settings — all at once — and see them scored side by side on
**LLM-judge quality, BLEU, ROUGE-L, latency, tokens, and cost**. PromptLab answers
the questions engineers actually ask: _which model is better here? is the
expensive one worth it? which prompt wins?_ — with a single neutral judge scoring
every answer so the comparison is fair.

---

## What it does

- **Mixed experiments** — each *run* picks its own provider, model, prompt, and
  temperature / top-p / max-tokens. Compare models, prompts, and settings in one
  experiment: "GPT-4o vs Claude Sonnet vs Gemini Flash on the same question."
- **Five providers** — OpenAI, Anthropic (Claude), Google Gemini, Groq, and
  OpenRouter. OpenAI/Groq/Gemini/OpenRouter go through one OpenAI-compatible
  client; Anthropic uses a native Messages-API client.
- **Fair judging** — one fixed referee model scores every answer
  (relevance / clarity / completeness), so cross-model scores are comparable.
- **Comparison summary** — Best Quality · Fastest · Cheapest · Best Overall.
- **Result cards, not a table** — one card per run: response, star rating, and
  metric chips.
- **Settings page** — add each provider's API key once; it's stored locally and
  reused. Provider pickers show which keys are configured; "Test" verifies a key
  with a live call.
- **History** — every experiment is saved and reloadable, with JSON / CSV export.

BLEU and ROUGE-L only apply when you supply an optional reference ("gold")
answer; without one, runs are scored on judge + latency / tokens / cost.

---

## Quickstart

```bash
# 1. Backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Smoke-test the whole pipeline from the terminal (offline stub if no keys)
make run

# 3. Serve the API
make serve                  # http://127.0.0.1:8100

# 4. Frontend (separate terminal)
make ui                     # http://localhost:5174
```

Then open the UI, go to **Settings**, and add at least one provider key (Groq's
free tier is a great start). The API runs on 8100 and the UI on 5174 — off the
common 8000/5173 defaults so PromptLab won't collide with another local dev
server.

**No keys?** Everything still runs. Any provider without a key returns a
deterministic `StubLLM` response, so the UI, storage, metrics, and exports all
work offline — only the answers and judge scores are placeholders.

### Configuring keys — BYOK by default

PromptLab is bring-your-own-key. Paste a provider's key into **Settings** and
it's saved with `localStorage` **in your browser only** — it's attached to
each run you start and nothing else; the server never writes it to disk, logs
it, or shares it with anyone else who opens the same deployment. That's what
makes it safe to put a real, billed key into a publicly deployed instance:
your key is only ever usable by you, in your own browser session.

Two other ways to supply a key, both server-side and off by default:

- **Environment** — `PROMPTLAB_OPENAI_API_KEY`, `PROMPTLAB_ANTHROPIC_API_KEY`,
  `PROMPTLAB_GEMINI_API_KEY`, `PROMPTLAB_GROQ_API_KEY`,
  `PROMPTLAB_OPENROUTER_API_KEY`. Read at startup; typically how you'd fund the
  judge model (`PROMPTLAB_JUDGE_PROVIDER` / `PROMPTLAB_JUDGE_MODEL`) since
  that's one small, fixed, operator-controlled cost per run.
- **Server-stored keys** — the Settings page can also save a key on the server
  itself (`.promptlab_keys.json`, gitignored), for a single-user local
  self-host who wants "paste once, reuse across restarts" without relying on
  the browser. This is **disabled by default**: set
  `PROMPTLAB_ALLOW_STORED_KEYS=true` to turn it on. Leave it off on any
  deployment other people can reach — a key saved this way would be shared by
  every visitor, since there's still no per-user auth.

> **Security note.** There is no login/auth layer — anyone who can reach a
> deployed instance can run experiments against whatever keys are in play for
> their own session (BYOK) or, if you've opted in, the server's stored/env
> keys. Precedence per run: the caller's own BYOK key wins, then the stored
> file (only if enabled), then the environment variable.

---

## Architecture

```
frontend/            React + Vite + react-router (plain JSX + CSS)
  pages/             Experiments · Settings · History
  components/        RunCard · ResultCards · ComparisonSummary
  keys.js            BYOK: localStorage key store, browser-only
src/promptlab/
  catalog.py         providers + models + pricing, declared once
  keystore.py        optional server-side key store — env fallback always on;
                      the file is gated behind allow_stored_keys (off by default)
  llm.py             hybrid: OpenAI-compatible client + native Anthropic client + StubLLM
  judge.py           fixed LLM-as-judge: relevance / clarity / completeness (1-5)
  metrics.py         self-contained BLEU + ROUGE-L
  pricing.py         token counts -> USD (per-model)
  scoring.py         one completion -> one scored run; per-dimension winners
  runner.py          the "Run Experiment" loop (one client per run, one fixed judge)
  store.py           SQLite + a JSON mirror per experiment
  api.py             FastAPI: /providers, /keys, /run, /experiments, /export
  cli.py             `promptlab serve` / `promptlab run -m modelA -m modelB …`
```

Each run's prompt is the **system** message and the shared question is the
**user** message, so you're comparing how different models/prompts answer the
same thing. Model ids and prices live in `catalog.py` — verify them against your
own account before trusting a cost figure.

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
