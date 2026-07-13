// Small generic marks for each provider — abstract shapes, not the real
// trademarked logos, but recognizable enough to scan a row of runs at a
// glance instead of reading provider names every time.

const ICONS = {
  openai: (
    <svg viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6" transform="rotate(60 12 12)" />
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6" transform="rotate(120 12 12)" />
    </svg>
  ),
  anthropic: (
    <svg viewBox="0 0 24 24" fill="none">
      <path
        d="M12 4l2.2 5.8L20 12l-5.8 2.2L12 20l-2.2-5.8L4 12l5.8-2.2L12 4z"
        fill="currentColor"
      />
    </svg>
  ),
  gemini: (
    <svg viewBox="0 0 24 24" fill="none">
      <path d="M12 3c0 4.5 3 7.5 7.5 7.5C15 10.5 12 13.5 12 18c0-4.5-3-7.5-7.5-7.5C9 10.5 12 7.5 12 3z" fill="currentColor" />
    </svg>
  ),
  groq: (
    <svg viewBox="0 0 24 24" fill="none">
      <path d="M13 3L5 13h5l-1 8 9-11h-6l1-7z" fill="currentColor" />
    </svg>
  ),
  openrouter: (
    <svg viewBox="0 0 24 24" fill="none">
      <circle cx="6" cy="12" r="2.2" fill="currentColor" />
      <circle cx="18" cy="6" r="2.2" fill="currentColor" />
      <circle cx="18" cy="18" r="2.2" fill="currentColor" />
      <path d="M8 12h6M8 12l6-6M8 12l6 6" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  ),
}

const FALLBACK = (
  <svg viewBox="0 0 24 24" fill="none">
    <rect x="4" y="4" width="16" height="16" rx="4" stroke="currentColor" strokeWidth="1.6" />
  </svg>
)

export default function ProviderIcon({ provider, className = '' }) {
  return (
    <span className={`provider-icon provider-icon-${provider} ${className}`}>
      {ICONS[provider] || FALLBACK}
    </span>
  )
}
