// One card per run — response, star rating, and metric chips. Reads as
// "compare models/prompts side by side," not a monitoring dashboard.

import ProviderIcon from './ProviderIcon.jsx'

const fmtCost = (c) => (c == null ? '—' : `$${c.toFixed(6)}`)
const fmtNum = (n) => (n == null ? '—' : n.toFixed(3))

function Stars({ value }) {
  const rounded = Math.round(value || 0)
  return (
    <span className="stars" aria-label={`${value?.toFixed(1)} out of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} className={n <= rounded ? 'star filled' : 'star'}>
          ★
        </span>
      ))}
    </span>
  )
}

export default function ResultCards({ result }) {
  const rows = result.results

  return (
    <div className="result-grid">
      {rows.map((r, i) => (
        <div key={i} className={`result-card ${r.is_winner ? 'is-winner' : ''}`}>
          <div className="result-card-head">
            <div>
              <div className="result-title">
                <ProviderIcon provider={r.provider} />
                <span className="result-label">{r.label}</span>
              </div>
              {(r.temperature != null || r.max_tokens != null) && (
                <span className="result-params">
                  {r.temperature != null ? `temp ${r.temperature}` : ''}
                  {r.temperature != null && r.max_tokens != null ? ' · ' : ''}
                  {r.max_tokens != null ? `${r.max_tokens} max` : ''}
                </span>
              )}
            </div>
            {r.is_winner && <span className="winner-pill">Best</span>}
          </div>

          {r.error ? (
            <p className="result-error">{r.error}</p>
          ) : (
            <>
              <Stars value={r.judge_overall} />
              <p className="result-output">{r.output}</p>
              {r.judge?.rationale && <p className="result-rationale">{r.judge.rationale}</p>}
              <div className="chip-row">
                {fmtNum(r.bleu) !== '—' && <span className="chip">BLEU {fmtNum(r.bleu)}</span>}
                {fmtNum(r.rouge_l) !== '—' && <span className="chip">ROUGE-L {fmtNum(r.rouge_l)}</span>}
                <span className="chip">{r.latency_ms} ms</span>
                <span className="chip">{r.total_tokens} tok</span>
                <span className="chip">{fmtCost(r.cost_usd)}</span>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  )
}
