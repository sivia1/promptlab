// BYOK key storage — lives in this browser only, never sent to the server
// except attached to the one request that uses it (see api.js:runExperiment).
// Nothing here ever touches a server-side file or database.
const STORAGE_KEY = 'promptlab:byok-keys'

function readAll() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeAll(keys) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(keys))
}

export const getLocalKey = (provider) => readAll()[provider] || ''

export const hasLocalKey = (provider) => Boolean(getLocalKey(provider))

export const setLocalKey = (provider, key) => {
  const keys = readAll()
  keys[provider] = key.trim()
  writeAll(keys)
}

export const removeLocalKey = (provider) => {
  const keys = readAll()
  delete keys[provider]
  writeAll(keys)
}

export const getAllLocalKeys = () => readAll()
