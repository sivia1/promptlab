// Thin fetch wrapper around the PromptLab backend.
// BASE is empty by default so requests hit the Vite dev proxy (same origin).
const BASE = import.meta.env.VITE_API_BASE || ''

async function request(path, options = {}) {
  const res = await fetch(BASE + path, options)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail)
  }
  return res.json()
}

const jsonBody = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

// --- catalog ---
export const getProviders = () => request('/api/providers')

// --- keys ---
// BYOK: keys live in the browser (see keys.js) and are only ever sent attached
// to the request that uses them. `testKey` verifies a key with one live call
// without persisting it anywhere. Stored server-side keys (setKey/deleteKey)
// only work when the deployment opts in via PROMPTLAB_ALLOW_STORED_KEYS=true.
export const getKeys = () => request('/api/keys')
export const testKey = (provider, key) =>
  request(`/api/keys/${provider}/test`, jsonBody('POST', key ? { key } : {}))
export const setKey = (provider, key) => request(`/api/keys/${provider}`, jsonBody('PUT', { key }))
export const deleteKey = (provider) => request(`/api/keys/${provider}`, { method: 'DELETE' })

// --- experiments ---
export const runExperiment = (payload) => request('/api/run', jsonBody('POST', payload))
export const listExperiments = () => request('/api/experiments')
export const getExperiment = (id) => request(`/api/experiments/${id}`)
export const exportUrl = (id, fmt) => `${BASE}/api/experiments/${id}/export.${fmt}`
