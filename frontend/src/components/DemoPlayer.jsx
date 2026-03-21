import React from 'react'

const SCENARIOS = [
  {
    id: 'real_customer',
    label: 'Real Customer',
    description: 'Legitimate call — should stay green',
    color: 'bg-green-600 hover:bg-green-500',
    order: 1,
  },
  {
    id: 'bank_impersonation',
    label: 'Bank Fraud',
    description: 'Impersonates fraud department',
    color: 'bg-red-600 hover:bg-red-500',
    order: 2,
  },
  {
    id: 'grandparent_scam',
    label: 'Grandparent Scam',
    description: 'Emotional manipulation attack',
    color: 'bg-orange-600 hover:bg-orange-500',
    order: 3,
  },
]

/**
 * Demo scenario buttons — triggers live inference on pre-generated audio.
 */
export default function DemoPlayer({ onRunDemo, running = false }) {
  return (
    <div className="bg-surface-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-2">Demo Scenarios</h3>
      <p className="text-sm text-gray-400 mb-4">
        Each demo runs live inference — no pre-computed scores.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {SCENARIOS.map((scenario) => (
          <button
            key={scenario.id}
            onClick={() => onRunDemo(scenario.id)}
            disabled={running}
            className={`
              ${scenario.color}
              min-h-[64px] min-w-[64px]
              px-4 py-3 rounded-xl
              text-white font-semibold text-base
              transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              active:scale-95
            `}
          >
            <div className="text-lg">{scenario.label}</div>
            <div className="text-xs opacity-80 mt-0.5">{scenario.description}</div>
          </button>
        ))}
      </div>
      {running && (
        <div className="mt-3 text-sm text-yellow-400 flex items-center gap-2">
          <span className="animate-spin inline-block w-4 h-4 border-2 border-yellow-400 border-t-transparent rounded-full" />
          Processing demo audio...
        </div>
      )}
    </div>
  )
}
