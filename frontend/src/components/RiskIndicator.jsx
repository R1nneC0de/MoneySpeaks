import React from 'react'

const LEVELS = {
  low: {
    color: 'bg-risk-low',
    glow: 'shadow-[0_0_60px_rgba(34,197,94,0.4)]',
    ring: 'ring-risk-low/30',
    label: 'SAFE',
    sublabel: 'No threats detected',
    animation: '',
  },
  medium: {
    color: 'bg-risk-medium',
    glow: 'shadow-[0_0_60px_rgba(245,158,11,0.4)]',
    ring: 'ring-risk-medium/30',
    label: 'CAUTION',
    sublabel: 'Suspicious activity detected',
    animation: 'animate-pulse-slow',
  },
  high: {
    color: 'bg-risk-high',
    glow: 'shadow-[0_0_80px_rgba(239,68,68,0.5)]',
    ring: 'ring-risk-high/30',
    label: 'DANGER',
    sublabel: 'High risk — consider hanging up',
    animation: 'animate-pulse-fast',
  },
}

/**
 * Traffic light risk indicator — occupies dominant screen space.
 * Designed for elderly users: large, clear, color-coded.
 */
export default function RiskIndicator({ level = 'low', score = 0, reasoning = '' }) {
  const config = LEVELS[level] || LEVELS.low

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Main traffic light */}
      <div
        className={`
          w-48 h-48 md:w-56 md:h-56 rounded-full
          ${config.color} ${config.glow} ${config.animation}
          ring-8 ${config.ring}
          flex items-center justify-center
          transition-all duration-500
        `}
        role="status"
        aria-label={`Risk level: ${config.label}`}
      >
        <span className="text-display font-extrabold text-white drop-shadow-lg">
          {config.label === 'SAFE' ? '✓' : config.label === 'CAUTION' ? '!' : '✕'}
        </span>
      </div>

      {/* Label */}
      <div className="text-center">
        <h2 className="text-hero font-bold tracking-wide">{config.label}</h2>
        <p className="text-lg text-gray-300 mt-1">{config.sublabel}</p>
      </div>

      {/* Score bar */}
      <div className="w-full max-w-xs">
        <div className="h-3 bg-surface-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${config.color} transition-all duration-700 rounded-full`}
            style={{ width: `${Math.round(score * 100)}%` }}
          />
        </div>
        <p className="text-sm text-gray-400 mt-1 text-center">
          Risk score: {Math.round(score * 100)}%
        </p>
      </div>

      {/* Reasoning */}
      {reasoning && (
        <p className="text-sm text-gray-400 text-center max-w-sm italic">
          {reasoning}
        </p>
      )}
    </div>
  )
}
