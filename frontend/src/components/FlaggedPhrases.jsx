import React from 'react'

/**
 * Flagged indicators as terminal-style tags — retro CRT.
 */
export default function FlaggedPhrases({ flags = [] }) {
  // Deduplicate flags by text
  const unique = []
  const seen = new Set()
  for (const flag of flags) {
    const key = (typeof flag === 'string' ? flag : flag.text).toLowerCase()
    if (!seen.has(key)) {
      seen.add(key)
      unique.push(typeof flag === 'string' ? { text: flag } : flag)
    }
  }

  return (
    <div className="window-panel">
      <div className="window-titlebar window-titlebar-amber">
        <span>[ THREAT FLAGS ] ({unique.length})</span>
        <span>■</span>
      </div>
      <div className="p-4 bg-crt-black">
        {unique.length === 0 ? (
          <p className="font-mono text-sm text-crt-green-dim">
            &gt; No suspicious indicators detected.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {unique.map((flag, i) => {
              const text = flag.text
              const isUrgent = /urgency|fear|danger|arrest|immediate/i.test(text)
              const color = isUrgent
                ? 'text-crt-red border-crt-red/40 bg-crt-red/10'
                : 'text-crt-amber border-crt-amber/40 bg-crt-amber/10'

              return (
                <span
                  key={`${text}-${i}`}
                  className={`
                    font-mono text-sm px-2 py-1
                    border ${color}
                  `}
                >
                  [!] {text}
                </span>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
