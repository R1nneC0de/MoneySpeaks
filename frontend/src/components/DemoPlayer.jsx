import React from 'react'

const SCENARIOS = [
  {
    id: 'legitimate_bank_call',
    label: 'Legit Call',
    description: 'Real call — should stay green',
    color: 'text-crt-green',
    bg: 'bg-crt-green/10 hover:bg-crt-green/20',
    order: 1,
  },
  {
    id: 'bank_impersonation',
    label: 'Bank Fraud',
    description: 'Impersonates fraud dept',
    color: 'text-crt-red',
    bg: 'bg-crt-red/10 hover:bg-crt-red/20',
    order: 2,
  },
  {
    id: 'investment_scam',
    label: 'Investment Scam',
    description: 'Fake high-return pitch',
    color: 'text-crt-amber',
    bg: 'bg-crt-amber/10 hover:bg-crt-amber/20',
    order: 3,
  },
  {
    id: 'credit_card_scam',
    label: 'Credit Card Scam',
    description: 'UNTESTED — live first run',
    color: 'text-crt-red',
    bg: 'bg-crt-red/10 hover:bg-crt-red/20',
    order: 4,
  },
]

/**
 * Demo scenario buttons — retro terminal style.
 */
export default function DemoPlayer({ onRunDemo, running = false }) {
  return (
    <div className="window-panel">
      <div className="window-titlebar">
        <span>[ DEMO SCENARIOS ]</span>
        <span>■</span>
      </div>
      <div className="p-4">
        <p className="font-mono text-sm text-crt-green-dim mb-3">
          &gt; Each demo runs live inference — select scenario:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => onRunDemo(scenario.id)}
              disabled={running}
              className={`
                btn-retro ${scenario.bg}
                min-h-[64px] min-w-[64px]
                px-4 py-3
                ${scenario.color} font-mono text-lg
                disabled:opacity-40
              `}
            >
              <div className="text-lg">[&gt; RUN: {scenario.label}]</div>
              <div className="text-xs opacity-60 mt-0.5">{scenario.description}</div>
            </button>
          ))}
        </div>
        {running && (
          <div className="mt-3 font-mono text-sm text-crt-amber flex items-center gap-2">
            <span className="animate-blink">▌</span>
            Processing demo audio...
          </div>
        )}
      </div>
    </div>
  )
}
