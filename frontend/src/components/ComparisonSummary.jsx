// The "story" of an experiment: who won each dimension. Reads left-to-right as
// Best Quality · Fastest · Cheapest · Best Overall.

const CARDS = [
  { key: 'best_quality', label: 'Best Quality' },
  { key: 'fastest', label: 'Fastest' },
  { key: 'cheapest', label: 'Cheapest' },
  { key: 'best_overall', label: 'Best Overall' },
]

export default function ComparisonSummary({ summary }) {
  if (!summary) return null
  return (
    <div className="summary-grid">
      {CARDS.map((c) => (
        <div key={c.key} className={`summary-card ${c.key === 'best_overall' ? 'overall' : ''}`}>
          <div className="summary-label">{c.label}</div>
          <div className="summary-winner">{summary[c.key] || '—'}</div>
        </div>
      ))}
    </div>
  )
}
