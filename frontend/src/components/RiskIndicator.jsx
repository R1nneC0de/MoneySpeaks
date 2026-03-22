import React from 'react'

const LEVELS = {
  low: {
    ascii: '██ SAFE ██',
    color: 'text-crt-green',
    bg: 'bg-crt-green/10',
    border: 'border-crt-green/40',
    glow: 'shadow-[0_0_30px_rgba(0,255,0,0.2)]',
    barColor: 'bg-crt-green',
    label: 'SAFE',
    sublabel: 'No threats detected',
    animation: '',
  },
  medium: {
    ascii: '!! CAUTION !!',
    color: 'text-crt-amber',
    bg: 'bg-crt-amber/10',
    border: 'border-crt-amber/40',
    glow: 'shadow-[0_0_30px_rgba(255,170,0,0.2)]',
    barColor: 'bg-crt-amber',
    label: 'CAUTION',
    sublabel: 'Suspicious activity detected',
    animation: 'animate-pulse-slow',
  },
  high: {
    ascii: '██ DANGER ██',
    color: 'text-crt-red',
    bg: 'bg-crt-red/10',
    border: 'border-crt-red/40',
    glow: 'shadow-[0_0_40px_rgba(255,0,0,0.3)]',
    barColor: 'bg-crt-red',
    label: 'DANGER',
    sublabel: 'High risk — consider hanging up',
    animation: 'animate-pulse-fast',
  },
}

/**
 * ASCII-art terminal risk indicator — retro CRT style.
 */
export default function RiskIndicator({ level = 'low', score = 0, reasoning = '' }) {
  const config = LEVELS[level] || LEVELS.low
  const pct = Math.round(score * 100)
  const barWidth = Math.round(score * 20)
  const bar = '▓'.repeat(barWidth) + '░'.repeat(20 - barWidth)

  return (
    <div className="window-panel w-full">
      <div className={`window-titlebar ${level === 'high' ? 'window-titlebar-red' : level === 'medium' ? 'window-titlebar-amber' : ''}`}>
        <span>[ THREAT LEVEL ]</span>
        <span>■</span>
      </div>
      <div className={`p-6 ${config.bg} ${config.glow} ${config.animation}`}>
        {/* ASCII threat display */}
        <div className="text-center mb-4">
          <pre className={`text-3xl font-mono ${config.color} leading-tight`}>
{config.ascii}
          </pre>
        </div>

        {/* Score */}
        <div className="text-center mb-4">
          <span className={`font-pixel text-2xl ${config.color}`}>
            {pct}%
          </span>
          <p className={`font-mono text-lg ${config.color} opacity-70 mt-1`}>
            {config.sublabel}
          </p>
        </div>

        {/* ASCII progress bar */}
        <div className="text-center mb-4">
          <code className={`text-lg ${config.color}`}>
            [{bar}] {pct}%
          </code>
        </div>

        {/* Reasoning */}
        {reasoning && (
          <div className="border-t border-crt-border pt-3 mt-3">
            <p className="font-mono text-sm text-crt-green-dim">
              &gt; {reasoning}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
