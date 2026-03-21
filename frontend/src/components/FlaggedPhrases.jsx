import React from 'react'

const FLAG_COLORS = {
  urgency: 'bg-red-500/20 text-red-300 border-red-500/30',
  fear_induction: 'bg-red-500/20 text-red-300 border-red-500/30',
  false_authority: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  sympathy_exploitation: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  isolation_tactics: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  anger_pressure: 'bg-red-500/20 text-red-300 border-red-500/30',
}

const DEFAULT_COLOR = 'bg-slate-500/20 text-slate-300 border-slate-500/30'

/**
 * Displays flagged phrases and tone indicators as pill badges.
 */
export default function FlaggedPhrases({ flags = [] }) {
  if (flags.length === 0) {
    return (
      <div className="bg-surface-800 rounded-2xl p-6">
        <h3 className="text-lg font-semibold mb-4">Flagged Indicators</h3>
        <p className="text-gray-500 text-sm">No suspicious indicators detected yet.</p>
      </div>
    )
  }

  // Deduplicate flags by text
  const unique = []
  const seen = new Set()
  for (const flag of flags) {
    const key = flag.text.toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      unique.push(flag)
    }
  }

  return (
    <div className="bg-surface-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-4">
        Flagged Indicators
        <span className="ml-2 text-sm font-normal text-gray-400">
          ({unique.length})
        </span>
      </h3>
      <div className="flex flex-wrap gap-2">
        {unique.map((flag, i) => {
          const colorKey = flag.text.toLowerCase().replace(/\s+/g, '_')
          const colorClass = FLAG_COLORS[colorKey] || DEFAULT_COLOR

          return (
            <span
              key={`${flag.text}-${i}`}
              className={`
                px-3 py-1.5 rounded-full text-sm font-medium
                border ${colorClass}
                transition-all duration-300
              `}
            >
              {flag.text}
            </span>
          )
        })}
      </div>
    </div>
  )
}
