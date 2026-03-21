import React, { useRef, useEffect } from 'react'

const LEVEL_STYLES = {
  low: 'border-l-risk-low/30',
  medium: 'border-l-risk-medium/40',
  high: 'border-l-risk-high/50 bg-red-500/5',
}

/**
 * Rolling transcript with flagged words highlighted.
 */
export default function LiveTranscript({ lines = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  if (lines.length === 0) {
    return (
      <div className="bg-surface-800 rounded-2xl p-6">
        <h3 className="text-lg font-semibold mb-4">Live Transcript</h3>
        <div className="h-48 flex items-center justify-center text-gray-500">
          Transcript will appear here during analysis...
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-4">Live Transcript</h3>
      <div className="max-h-64 overflow-y-auto space-y-2 pr-2">
        {lines.map((line, i) => (
          <div
            key={i}
            className={`
              border-l-4 pl-3 py-1.5 rounded-r
              ${LEVEL_STYLES[line.level] || LEVEL_STYLES.low}
              transition-all duration-300
            `}
          >
            <p className="text-sm leading-relaxed">
              {highlightFlags(line.text, line.flags)}
            </p>
            <span className="text-xs text-gray-500">
              {new Date(line.timestamp * 1000).toLocaleTimeString()}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

function highlightFlags(text, flags = []) {
  if (!flags.length) return text

  // Build regex from all flag phrases
  const escaped = flags.map((f) => f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const pattern = new RegExp(`(${escaped.join('|')})`, 'gi')
  const parts = text.split(pattern)

  return parts.map((part, i) => {
    const isFlag = flags.some((f) => f.toLowerCase() === part.toLowerCase())
    if (isFlag) {
      return (
        <mark key={i} className="bg-red-500/30 text-red-200 px-1 rounded font-medium">
          {part}
        </mark>
      )
    }
    return part
  })
}
