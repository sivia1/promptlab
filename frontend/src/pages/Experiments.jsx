import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProviders, runExperiment, exportUrl } from '../api'
import RunCard from '../components/RunCard.jsx'
import ResultCards from '../components/ResultCards.jsx'
import ComparisonSummary from '../components/ComparisonSummary.jsx'
import { hasLocalKey, getLocalKey } from '../keys.js'

const DEFAULT_PROMPT = 'You are a helpful assistant. Answer the question clearly.'

// Seed the first three runs across different providers so the first screen tells
// the story ("same question, different models") without any setup.
const seedRuns = (providers) => {
  const pick = (pid) => providers.find((p) => p.id === pid)
  const seeds = ['openai', 'anthropic', 'gemini']
  return seeds.map((pid) => {
    const p = pick(pid) || providers[0]
    return {
      provider: p?.id ?? 'openai',
      model: p?.models?.[0]?.id ?? 'gpt-4o-mini',
      prompt: DEFAULT_PROMPT,
    }
  })
}

export default function Experiments() {
  const [providers, setProviders] = useState([])
  const [judge, setJudge] = useState(null)
  const [anyConfigured, setAnyConfigured] = useState(true)
  const [question, setQuestion] = useState('How do I reset my password?')
  const [reference, setReference] = useState('')
  const [runs, setRuns] = useState([])
  const [result, setResult] = useState(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    getProviders()
      .then((d) => {
        // "configured" means usable right now — either the server has a default
        // key (env var) or this browser holds its own BYOK key for it.
        const withByok = d.providers.map((p) => ({
          ...p,
          configured: p.configured || hasLocalKey(p.id),
        }))
        setProviders(withByok)
        setJudge(d.judge)
        setAnyConfigured(withByok.some((p) => p.configured))
        setRuns(seedRuns(withByok))
      })
      .catch((e) => setError(e.message))
  }, [])

  const patchRun = (i, patch) =>
    setRuns((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)))

  const addRun = () =>
    setRuns((rs) => {
      const p = providers[0]
      return [...rs, { provider: p?.id ?? 'openai', model: p?.models?.[0]?.id ?? '', prompt: DEFAULT_PROMPT }]
    })

  const removeRun = (i) => setRuns((rs) => rs.filter((_, j) => j !== i))

  const run = async () => {
    setRunning(true)
    setError('')
    try {
      // BYOK: attach each run's browser-held key fresh, per request — never
      // saved anywhere on the way in, and the API never echoes it back out.
      const runsWithKeys = runs.map((r) => ({ ...r, api_key: getLocalKey(r.provider) || undefined }))
      const res = await runExperiment({ question, reference, runs: runsWithKeys })
      setResult(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <header className="hero">
        <h1 className="page-title">Benchmark prompts &amp; LLMs, side by side</h1>
        <p className="tagline">
          One question. Different models, prompts, and settings. See what actually wins.
        </p>
      </header>

      {!anyConfigured && (
        <div className="banner">
          No provider keys configured — runs return <strong>stub responses</strong>. Add your own key
          in <Link to="/settings">Settings</Link> (kept in this browser only) to benchmark real
          models.
        </div>
      )}

      <section className="workspace">
        <label className="field">
          <span>Question</span>
          <textarea rows={2} value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>

        <label className="field">
          <span>Correct answer (optional)</span>
          <textarea
            rows={2}
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="If you know the ideal answer, paste it here to also score how closely each response matches it. Leave blank to score on judge quality, latency, tokens, and cost only."
          />
        </label>

        <div className="prompts-head">
          <span>Runs to compare</span>
          <button className="ghost" onClick={addRun}>
            + Add run
          </button>
        </div>

        <div className="run-grid">
          {runs.map((r, i) => (
            <RunCard
              key={i}
              run={r}
              index={i}
              providers={providers}
              onChange={patchRun}
              onRemove={removeRun}
              canRemove={runs.length > 1}
            />
          ))}
        </div>

        <div className="run-row">
          <button className="run" onClick={run} disabled={running || runs.length === 0}>
            {running ? 'Running…' : 'Run Experiment'}
          </button>
          {judge && (
            <p className="judge-note">
              Judged by <strong>{judge.model}</strong> — one neutral referee scores every answer.
            </p>
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </section>

      {result && (
        <section className="results">
          <div className="results-head">
            <h2>Results</h2>
            <div className="exports">
              <a href={exportUrl(result.id, 'json')}>Download JSON</a>
              <a href={exportUrl(result.id, 'csv')}>Download CSV</a>
            </div>
          </div>
          <ComparisonSummary summary={result.summary} />
          <ResultCards result={result} />
        </section>
      )}
    </>
  )
}
