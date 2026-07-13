import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { listExperiments, getExperiment, exportUrl } from '../api'
import ResultCards from '../components/ResultCards.jsx'
import ComparisonSummary from '../components/ComparisonSummary.jsx'

export default function History() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [experiments, setExperiments] = useState([])
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listExperiments()
      .then((d) => setExperiments(d.experiments))
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (id) {
      getExperiment(id)
        .then(setDetail)
        .catch((e) => setError(e.message))
    } else {
      setDetail(null)
    }
  }, [id])

  return (
    <>
      <header className="hero">
        <h1 className="page-title">History</h1>
        <p className="tagline">Every experiment you&apos;ve run, newest first.</p>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="history-layout">
        <aside className="history-list">
          {experiments.length === 0 && <p className="muted">No experiments yet.</p>}
          <ul>
            {experiments.map((e) => (
              <li key={e.id}>
                <button
                  className={`link ${String(e.id) === id ? 'selected' : ''}`}
                  onClick={() => navigate(`/experiments/${e.id}`)}
                >
                  <span className="exp-id">#{e.id}</span>
                  <span className="exp-q">{e.question}</span>
                  <span className="exp-meta">
                    {e.num_runs} runs · {e.best_overall ? `🏆 ${e.best_overall}` : '—'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <div className="history-detail">
          {!detail && <p className="muted">Select an experiment to see its results.</p>}
          {detail && (
            <>
              <div className="results-head">
                <h2>#{detail.id} — {detail.question}</h2>
                <div className="exports">
                  <a href={exportUrl(detail.id, 'json')}>JSON</a>
                  <a href={exportUrl(detail.id, 'csv')}>CSV</a>
                </div>
              </div>
              <ComparisonSummary summary={detail.summary} />
              <ResultCards result={detail} />
            </>
          )}
        </div>
      </div>
    </>
  )
}
