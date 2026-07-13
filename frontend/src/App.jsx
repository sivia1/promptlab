import { useEffect, useState } from 'react'
import { getModels, runExperiment, listExperiments, getExperiment, exportUrl } from './api'
import ComparisonTable from './components/ComparisonTable.jsx'

const STARTER_PROMPTS = [
  { label: 'V1', text: 'You are a helpful assistant. Answer the question clearly.' },
  { label: 'V2', text: 'Answer briefly, in one or two sentences.' },
  { label: 'V3', text: 'Think step by step, then give a concise final answer.' },
]

export default function App() {
  const [models, setModels] = useState([])
  const [hasLlm, setHasLlm] = useState(true)
  const [model, setModel] = useState('')
  const [question, setQuestion] = useState('How do I reset my password?')
  const [reference, setReference] = useState('')
  const [prompts, setPrompts] = useState(STARTER_PROMPTS)
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getModels()
      .then((d) => {
        setModels(d.models)
        setHasLlm(d.has_llm)
        if (d.models.length) setModel(d.models[0].id)
        else setModel('gpt-4o-mini') // offline stub still runs
      })
      .catch((e) => setError(e.message))
    refreshHistory()
  }, [])

  const refreshHistory = () =>
    listExperiments()
      .then((d) => setHistory(d.experiments))
      .catch(() => {})

  const setPromptText = (i, text) =>
    setPrompts((ps) => ps.map((p, j) => (j === i ? { ...p, text } : p)))

  const addPrompt = () =>
    setPrompts((ps) => [...ps, { label: `V${ps.length + 1}`, text: '' }])

  const removePrompt = (i) =>
    setPrompts((ps) => ps.filter((_, j) => j !== i).map((p, j) => ({ ...p, label: `V${j + 1}` })))

  const run = async () => {
    setRunning(true)
    setError('')
    try {
      const payload = {
        question,
        reference,
        model,
        prompts: prompts.filter((p) => p.text.trim()),
      }
      const res = await runExperiment(payload)
      setResult(res)
      refreshHistory()
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const loadExperiment = async (id) => {
    try {
      setResult(await getExperiment(id))
    } catch (e) {
      setError(e.message)
    }
  }

  const winner = result?.results.find((r) => r.is_winner)

  return (
    <div className="app">
      <header>
        <h1>PromptLab</h1>
        <p className="tagline">
          Systematically design, compare, evaluate, and version prompts across LLMs.
        </p>
      </header>

      {!hasLlm && (
        <div className="banner">
          No API key configured — running in <strong>offline stub mode</strong>. Set
          <code> PROMPTLAB_LLM_API_KEY </code> (or a provider key) for real completions.
        </div>
      )}

      <div className="layout">
        <aside className="history">
          <h2>History</h2>
          {history.length === 0 && <p className="muted">No experiments yet.</p>}
          <ul>
            {history.map((h) => (
              <li key={h.id}>
                <button className="link" onClick={() => loadExperiment(h.id)}>
                  <span className="exp-id">#{h.id}</span>
                  <span className="exp-q">{h.question}</span>
                  <span className="exp-meta">
                    {h.winner_label ? `🏆 ${h.winner_label}` : '—'} ·{' '}
                    {h.winner_judge != null ? h.winner_judge.toFixed(2) : ''}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main>
          <section className="panel">
            <label className="field">
              <span>Question</span>
              <textarea
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </label>

            <label className="field">
              <span>Reference answer (optional — enables BLEU / ROUGE-L)</span>
              <textarea
                rows={2}
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="Leave blank to score on judge, latency, tokens, and cost only."
              />
            </label>

            <label className="field model-field">
              <span>Model</span>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {models.length === 0 && <option value="gpt-4o-mini">gpt-4o-mini (stub)</option>}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="prompts">
              <div className="prompts-head">
                <span>Prompt versions</span>
                <button className="ghost" onClick={addPrompt}>
                  + Add version
                </button>
              </div>
              {prompts.map((p, i) => (
                <div className="prompt-card" key={i}>
                  <div className="prompt-card-head">
                    <strong>{p.label}</strong>
                    {prompts.length > 1 && (
                      <button className="ghost small" onClick={() => removePrompt(i)}>
                        Remove
                      </button>
                    )}
                  </div>
                  <textarea
                    rows={3}
                    value={p.text}
                    onChange={(e) => setPromptText(i, e.target.value)}
                    placeholder="System prompt for this version…"
                  />
                </div>
              ))}
            </div>

            <button className="run" onClick={run} disabled={running}>
              {running ? 'Running…' : 'Run Experiment'}
            </button>
            {error && <p className="error">{error}</p>}
          </section>

          {result && (
            <section className="panel results">
              <div className="results-head">
                <h2>Experiment #{result.id}</h2>
                <div className="exports">
                  <a href={exportUrl(result.id, 'json')}>Download JSON</a>
                  <a href={exportUrl(result.id, 'csv')}>Download CSV</a>
                </div>
              </div>

              {winner && (
                <div className="winner-card">
                  <span className="crown-big">🏆</span>
                  <div>
                    <div className="winner-title">Winner: {winner.label}</div>
                    <div className="winner-stats">
                      Judge {winner.judge_overall.toFixed(2)} · {winner.latency_ms} ms ·{' '}
                      ${winner.cost_usd.toFixed(6)}
                    </div>
                    {winner.judge?.rationale && (
                      <div className="winner-rationale">{winner.judge.rationale}</div>
                    )}
                  </div>
                </div>
              )}

              <ComparisonTable result={result} />

              <div className="outputs">
                {result.results.map((r) => (
                  <details key={r.label} open={r.is_winner}>
                    <summary>
                      {r.is_winner && '🏆 '}
                      {r.label} — {r.error ? 'error' : `judge ${r.judge_overall.toFixed(2)}`}
                    </summary>
                    <pre>{r.error || r.output}</pre>
                  </details>
                ))}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  )
}
