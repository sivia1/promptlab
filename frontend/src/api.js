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

export const getModels = () => request('/api/models')

export const runExperiment = (payload) =>
  request('/api/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const listExperiments = () => request('/api/experiments')

export const getExperiment = (id) => request(`/api/experiments/${id}`)

export const exportUrl = (id, fmt) => `${BASE}/api/experiments/${id}/export.${fmt}`
