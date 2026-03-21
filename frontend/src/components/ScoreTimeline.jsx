import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

/**
 * Real-time line chart showing deepfake score and composite score over time.
 */
export default function ScoreTimeline({ data = [] }) {
  if (data.length === 0) {
    return (
      <div className="bg-surface-800 rounded-2xl p-6">
        <h3 className="text-lg font-semibold mb-4">Score Timeline</h3>
        <div className="h-48 flex items-center justify-center text-gray-500">
          Waiting for audio data...
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface-800 rounded-2xl p-6">
      <h3 className="text-lg font-semibold mb-4">Score Timeline</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#252833" />
          <XAxis
            dataKey="time"
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            tickLine={false}
            ticks={[0, 0.4, 0.7, 1]}
          />
          <Tooltip
            contentStyle={{
              background: '#1a1d27',
              border: '1px solid #252833',
              borderRadius: 8,
              color: '#f1f5f9',
            }}
          />
          {/* Risk thresholds */}
          <ReferenceLine y={0.7} stroke="#ef4444" strokeDasharray="5 5" label="" />
          <ReferenceLine y={0.4} stroke="#f59e0b" strokeDasharray="5 5" label="" />

          <Line
            type="monotone"
            dataKey="deepfake"
            stroke="#8b5cf6"
            strokeWidth={2}
            dot={false}
            name="Deepfake Score"
          />
          <Line
            type="monotone"
            dataKey="composite"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
            name="Composite Risk"
          />
          <Line
            type="monotone"
            dataKey="escalation"
            stroke="#f59e0b"
            strokeWidth={1.5}
            dot={false}
            name="Escalation"
            strokeDasharray="4 4"
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-purple-500 inline-block" /> Deepfake
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-red-500 inline-block" /> Composite
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-yellow-500 inline-block" style={{ borderBottom: '1px dashed' }} /> Escalation
        </span>
      </div>
    </div>
  )
}
