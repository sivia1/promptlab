import { useEffect, useState } from 'react'
import { getProviders, getKeys, setKey, deleteKey, testKey } from '../api'
import ProviderIcon from '../components/ProviderIcon.jsx'
import { getLocalKey, setLocalKey, removeLocalKey } from '../keys.js'

export default function Settings() {
  const [providers, setProviders] = useState([])
  const [serverKeys, setServerKeys] = useState({})
  const [allowStoredKeys, setAllowStoredKeys] = useState(false)
  const [localKeys, setLocalKeys] = useState({})
  const [drafts, setDrafts] = useState({})
  const [testing, setTesting] = useState({})
  const [testResult, setTestResult] = useState({})
  const [error, setError] = useState('')

  const load = () =>
    Promise.all([getProviders(), getKeys()])
      .then(([p, k]) => {
        setProviders(p.providers)
        setAllowStoredKeys(Boolean(p.allow_stored_keys))
        setServerKeys(k.keys)
        setLocalKeys(Object.fromEntries(p.providers.map((pr) => [pr.id, getLocalKey(pr.id)])))
      })
      .catch((e) => setError(e.message))

  useEffect(() => {
    load()
  }, [])

  const saveLocal = (provider) => {
    const value = (drafts[provider] || '').trim()
    if (!value) return
    setLocalKey(provider, value)
    setLocalKeys((k) => ({ ...k, [provider]: value }))
    setDrafts((d) => ({ ...d, [provider]: '' }))
    setTestResult((t) => ({ ...t, [provider]: null }))
  }

  const removeLocal = (provider) => {
    removeLocalKey(provider)
    setLocalKeys((k) => ({ ...k, [provider]: '' }))
    setTestResult((t) => ({ ...t, [provider]: null }))
  }

  const saveServer = async (provider) => {
    const value = (drafts[provider] || '').trim()
    if (!value) return
    try {
      const { keys: updated } = await setKey(provider, value)
      setServerKeys(updated)
      setDrafts((d) => ({ ...d, [provider]: '' }))
    } catch (e) {
      setError(e.message)
    }
  }

  const removeServer = async (provider) => {
    try {
      const { keys: updated } = await deleteKey(provider)
      setServerKeys(updated)
    } catch (e) {
      setError(e.message)
    }
  }

  const test = async (provider) => {
    const key = localKeys[provider] || drafts[provider] || null
    setTesting((t) => ({ ...t, [provider]: true }))
    setTestResult((t) => ({ ...t, [provider]: null }))
    try {
      const res = await testKey(provider, key)
      setTestResult((t) => ({ ...t, [provider]: res }))
    } catch (e) {
      setTestResult((t) => ({ ...t, [provider]: { ok: false, error: e.message } }))
    } finally {
      setTesting((t) => ({ ...t, [provider]: false }))
    }
  }

  return (
    <>
      <header className="hero">
        <h1 className="page-title">Settings</h1>
        <p className="tagline">
          Add your own API key per provider — it&apos;s kept in this browser only.
        </p>
      </header>

      <div className="banner">
        Keys you paste here are saved with <code>localStorage</code> in this browser and sent only
        with the runs you start — the server never writes them to disk, logs them, or shares them
        with anyone else who opens this page.
      </div>

      {error && <p className="error">{error}</p>}

      <div className="settings-list">
        {providers.map((p) => {
          const local = localKeys[p.id]
          const server = serverKeys[p.id] || {}
          const tr = testResult[p.id]
          return (
            <div key={p.id} className="settings-card">
              <div className="settings-card-head">
                <div className="settings-provider-name">
                  <ProviderIcon provider={p.id} />
                  <span className="settings-provider">{p.label}</span>
                  {local ? (
                    <span className="key-badge ok">your key · this browser</span>
                  ) : server.configured ? (
                    <span className="key-badge ok">
                      server default {server.source === 'env' ? '(env)' : ''}
                    </span>
                  ) : (
                    <span className="key-badge none">no key</span>
                  )}
                </div>
                {p.keys_url && (
                  <a className="get-key" href={p.keys_url} target="_blank" rel="noreferrer">
                    Get a key ↗
                  </a>
                )}
              </div>

              <div className="settings-row">
                <input
                  type="password"
                  placeholder={local ? 'Replace your key…' : 'Paste your API key…'}
                  value={drafts[p.id] || ''}
                  onChange={(e) => setDrafts((d) => ({ ...d, [p.id]: e.target.value }))}
                />
                <button className="ghost" onClick={() => saveLocal(p.id)}>
                  Save in browser
                </button>
                <button
                  className="ghost"
                  onClick={() => test(p.id)}
                  disabled={(!local && !drafts[p.id]?.trim() && !server.configured) || testing[p.id]}
                >
                  {testing[p.id] ? 'Testing…' : 'Test'}
                </button>
                {local && (
                  <button className="ghost small" onClick={() => removeLocal(p.id)}>
                    Remove
                  </button>
                )}
              </div>

              {allowStoredKeys && (
                <div className="settings-row settings-row-server">
                  <span className="muted small-note">
                    This deployment also allows saving a key server-side (local self-host mode):
                  </span>
                  <button className="ghost small" onClick={() => saveServer(p.id)}>
                    Save on server
                  </button>
                  {server.configured && server.source === 'stored' && (
                    <button className="ghost small" onClick={() => removeServer(p.id)}>
                      Remove server key
                    </button>
                  )}
                </div>
              )}

              {tr && (
                <p className={tr.ok ? 'test-ok' : 'test-fail'}>
                  {tr.ok ? '✓ Key works' : `✗ ${tr.error}`}
                </p>
              )}
              <div className="settings-models">
                {p.models.map((m) => (
                  <span key={m.id} className="model-tag">
                    {m.label}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}
