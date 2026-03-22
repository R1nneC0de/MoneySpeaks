import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'

/**
 * Real-time score chart — green-on-black retro CRT style.
 */
export default function ScoreTimeline({ data = [] }) {
  if (data.length === 0) {
    return (
      <div className="window-panel">
        <div className="window-titlebar">
          <span>[ DEEPFAKE SIGNAL ]</span>
          <span>■</span>
        </div>
        <div className="p-4 h-48 flex items-center justify-center font-mono text-crt-green-dim">
          &gt; Waiting for audio data...
        </div>
      </div>
    )
  }

  return (
    <div className="window-panel">
      <div className="window-titlebar">
        <span>[ DEEPFAKE SIGNAL ]</span>
        <span>■</span>
      </div>
      <div className="p-4 bg-crt-black">
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
            <XAxis
              dataKey="time"
              tick={{ fill: '#005500', fontSize: 14, fontFamily: 'VT323' }}
              tickLine={false}
              axisLine={{ stroke: '#333' }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: '#005500', fontSize: 14, fontFamily: 'VT323' }}
              tickLine={false}
              ticks={[0, 0.4, 0.7, 1]}
              axisLine={{ stroke: '#333' }}
            />
            <Tooltip
              contentStyle={{
                background: '#111',
                border: '1px solid #333',
                fontFamily: 'VT323',
                fontSize: 16,
                color: '#00ff00',
              }}
            />
            {/* Risk thresholds */}
            <ReferenceLine y={0.7} stroke="#ff0000" strokeDasharray="5 5" strokeOpacity={0.5} />
            <ReferenceLine y={0.4} stroke="#ffaa00" strokeDasharray="5 5" strokeOpacity={0.5} />

            <Line
              type="monotone"
              dataKey="deepfake"
              stroke="#00ff00"
              strokeWidth={2}
              dot={false}
              name="Deepfake"
            />
            <Line
              type="monotone"
              dataKey="composite"
              stroke="#ff0000"
              strokeWidth={2}
              dot={false}
              name="Composite"
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex gap-6 mt-2 font-mono text-sm">
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-crt-green inline-block" /> Deepfake
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-crt-red inline-block" /> Composite
          </span>
        </div>
      </div>
    </div>
  )
}
