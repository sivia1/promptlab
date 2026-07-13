// One run to compare: provider ▸ model ▸ prompt ▸ optional inference settings.
// Replaces the old "V1/V2" prompt cards — a run is now a full model+prompt combo,
// so the card reads as "OpenAI · GPT-4o mini", not an anonymous version number.

import { useState } from 'react'
import ProviderIcon from './ProviderIcon.jsx'

const numOrUndef = (v) => (v === '' ? undefined : Number(v))

export default function RunCard({ run, index, providers, onChange, onRemove, canRemove }) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  const provider = providers.find((p) => p.id === run.provider)
  const models = provider ? provider.models : []

  const changeProvider = (pid) => {
    const p = providers.find((x) => x.id === pid)
    const firstModel = p && p.models.length ? p.models[0].id : ''
    onChange(index, { provider: pid, model: firstModel })
  }

  return (
    <div className="run-card">
      <div className="run-card-head">
        <span className="run-index">Run {index + 1}</span>
        {canRemove && (
          <button className="ghost small" onClick={() => onRemove(index)}>
            Remove
          </button>
        )}
      </div>

      <div className="field">
        <span>Provider</span>
        <div className="provider-picker">
          {providers.map((p) => (
            <button
              type="button"
              key={p.id}
              className={`provider-chip ${run.provider === p.id ? 'selected' : ''}`}
              onClick={() => changeProvider(p.id)}
              title={p.configured ? p.label : `${p.label} · no key configured`}
            >
              <ProviderIcon provider={p.id} />
              {p.label}
              {!p.configured && ' ·'}
            </button>
          ))}
        </div>
      </div>

      <label className="field">
        <span>Model</span>
        <select value={run.model} onChange={(e) => onChange(index, { model: e.target.value })}>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label}
            </option>
          ))}
        </select>
      </label>

      {provider && !provider.configured && (
        <p className="run-warn">
          No API key for {provider.label} — this run will return a stub response. Add one in
          Settings.
        </p>
      )}

      <label className="field">
        <span>Prompt (system)</span>
        <textarea
          rows={5}
          value={run.prompt}
          onChange={(e) => onChange(index, { prompt: e.target.value })}
          placeholder="System prompt for this run…"
        />
      </label>

      <button className="advanced-toggle" onClick={() => setShowAdvanced((v) => !v)}>
        {showAdvanced ? '▾' : '▸'} Inference settings
      </button>
      {showAdvanced && (
        <div className="advanced-grid">
          <label className="field small-field">
            <span>Temperature</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={run.temperature ?? ''}
              placeholder="0.0"
              onChange={(e) => onChange(index, { temperature: numOrUndef(e.target.value) })}
            />
          </label>
          <label className="field small-field">
            <span>Top-p</span>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={run.top_p ?? ''}
              placeholder="1.0"
              onChange={(e) => onChange(index, { top_p: numOrUndef(e.target.value) })}
            />
          </label>
          <label className="field small-field">
            <span>Max tokens</span>
            <input
              type="number"
              step="64"
              min="1"
              value={run.max_tokens ?? ''}
              placeholder="1024"
              onChange={(e) => onChange(index, { max_tokens: numOrUndef(e.target.value) })}
            />
          </label>
        </div>
      )}
    </div>
  )
}
