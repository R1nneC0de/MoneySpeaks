import React, { useRef, useEffect, useMemo } from 'react'

/**
 * Timestamp-synced transcript with word-by-word reveal.
 *
 * Two modes:
 * - Demo mode (transcriptData + audioTime): words fade in synced to audio playback
 * - Legacy mode (lines): rolling transcript for live mic
 */
export default function LiveTranscript({
  transcriptData = null,
  analysisData = null,
  audioTime = 0,
  lines = [],
}) {
  const bottomRef = useRef(null)
  const containerRef = useRef(null)

  // Group words by speaker segments
  const segments = useMemo(() => {
    if (!transcriptData?.words?.length) return []

    const segs = []
    let current = null

    for (const word of transcriptData.words) {
      if (!current || current.speaker !== word.speaker_id) {
        current = {
          speaker: word.speaker_id,
          words: [],
        }
        segs.push(current)
      }
      current.words.push(word)
    }
    return segs
  }, [transcriptData])

  // Build set of flagged phrases for highlighting
  const flaggedPhrases = useMemo(() => {
    if (!analysisData) return []
    return [
      ...(analysisData.phrase_flags ?? []),
      ...(analysisData.scam_flags ?? []),
    ].map((f) => f.toLowerCase())
  }, [analysisData])

  // Auto-scroll to latest visible word
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [audioTime, lines])

  // Demo mode — timestamp-synced word reveal
  if (segments.length > 0) {
    return (
      <div className="window-panel h-full flex flex-col">
        <div className="window-titlebar">
          <span>[ LIVE TRANSCRIPT ]</span>
          <span>■</span>
        </div>
        <div
          ref={containerRef}
          className="flex-1 p-4 overflow-y-auto font-mono text-base min-h-[300px] max-h-[500px] bg-crt-black"
        >
          {segments.map((seg, si) => {
            const speakerColor = seg.speaker === 'speaker_0'
              ? 'text-crt-green'
              : 'text-cyan-400'
            const speakerLabel = seg.speaker === 'speaker_0'
              ? 'CALLER'
              : 'RECIPIENT'

            // Check if any word in this segment is visible
            const segVisible = seg.words.some((w) => audioTime >= w.start)
            if (!segVisible) return null

            return (
              <div key={si} className="mb-3">
                <span className={`${speakerColor} text-xs opacity-60`}>
                  [{speakerLabel}]
                </span>
                <div className={`${speakerColor} leading-relaxed`}>
                  {seg.words.map((word, wi) => {
                    const visible = audioTime >= word.start
                    const isFlagged = flaggedPhrases.some((fp) =>
                      word.text.toLowerCase().replace(/[.,!?;:]/g, '').includes(fp) ||
                      fp.includes(word.text.toLowerCase().replace(/[.,!?;:]/g, ''))
                    )

                    return (
                      <span
                        key={wi}
                        className={`
                          transition-opacity duration-200
                          ${visible ? 'opacity-100' : 'opacity-0'}
                          ${isFlagged && visible ? 'bg-crt-red/30 text-crt-red px-0.5' : ''}
                        `}
                      >
                        {word.text}{' '}
                      </span>
                    )
                  })}
                  {/* Blinking cursor after last visible word in last segment */}
                  {si === segments.length - 1 && (
                    <span className="animate-blink text-crt-green">█</span>
                  )}
                </div>
              </div>
            )
          })}
          <div ref={bottomRef} />
        </div>
      </div>
    )
  }

  // Legacy mode — rolling transcript for live mic
  if (lines.length > 0) {
    return (
      <div className="window-panel h-full flex flex-col">
        <div className="window-titlebar">
          <span>[ LIVE TRANSCRIPT ]</span>
          <span>■</span>
        </div>
        <div className="flex-1 p-4 overflow-y-auto font-mono text-base min-h-[300px] max-h-[500px] bg-crt-black">
          {lines.map((line, i) => {
            const levelColor = line.level === 'high'
              ? 'text-crt-red'
              : line.level === 'medium'
                ? 'text-crt-amber'
                : 'text-crt-green'
            return (
              <div key={i} className={`mb-2 ${levelColor}`}>
                <span className="opacity-50 text-xs">
                  [{new Date(line.timestamp * 1000).toLocaleTimeString()}]
                </span>{' '}
                {line.text}
              </div>
            )
          })}
          <span className="animate-blink text-crt-green">█</span>
          <div ref={bottomRef} />
        </div>
      </div>
    )
  }

  // Empty state
  return (
    <div className="window-panel h-full flex flex-col">
      <div className="window-titlebar">
        <span>[ LIVE TRANSCRIPT ]</span>
        <span>■</span>
      </div>
      <div className="p-4 min-h-[300px] flex items-center justify-center font-mono text-crt-green-dim bg-crt-black">
        <div className="text-center">
          <p>&gt; Awaiting audio input...</p>
          <p className="animate-blink mt-2">█</p>
        </div>
      </div>
    </div>
  )
}
