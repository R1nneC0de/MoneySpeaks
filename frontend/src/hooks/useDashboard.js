import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * Manages WebSocket connection to /ws/dashboard and state for all score data.
 */
export function useDashboard(wsUrl = 'ws://localhost:8000/ws/dashboard', { onAudioUrl, onBeforeDemo } = {}) {
  const [connected, setConnected] = useState(false)
  const [latestUpdate, setLatestUpdate] = useState(null)
  const [scoreHistory, setScoreHistory] = useState([])
  const [transcriptLines, setTranscriptLines] = useState([])
  const [allFlags, setAllFlags] = useState([])
  const [compositeLevel, setCompositeLevel] = useState('low')
  const [demoRunning, setDemoRunning] = useState(false)
  const wsRef = useRef(null)
  const pingRef = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // Keep-alive ping
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'pong') return

        setLatestUpdate(data)

        // Notify about demo audio URL (first chunk of a demo)
        if (data.audio_url && onAudioUrl) {
          onAudioUrl(data.audio_url)
        }

        // Append to score history
        setScoreHistory((prev) => {
          const next = [...prev, {
            time: new Date(data.timestamp * 1000).toLocaleTimeString(),
            deepfake: data.deepfake_score,
            composite: data.composite?.score ?? 0,
            escalation: (data.gemini?.escalation_score ?? 0) / 100,
          }]
          // Keep last 60 data points
          return next.slice(-60)
        })

        // Append transcript
        if (data.transcript && data.transcript !== '...') {
          setTranscriptLines((prev) => {
            const next = [...prev, {
              text: data.transcript,
              timestamp: data.timestamp,
              level: data.composite?.level ?? 'low',
              flags: [
                ...(data.gemini?.phrase_flags ?? []),
                ...(data.scam_intent?.flags ?? []),
              ],
            }]
            return next.slice(-50)
          })
        }

        // Collect all flags
        const newFlags = [
          ...(data.gemini?.tone_flags ?? []),
          ...(data.gemini?.phrase_flags ?? []),
          ...(data.scam_intent?.flags ?? []),
          ...(data.behavioral?.flags ?? []),
        ]
        if (newFlags.length > 0) {
          setAllFlags((prev) => {
            const combined = [...prev, ...newFlags.map((f) => ({
              text: f,
              timestamp: data.timestamp,
            }))]
            return combined.slice(-30)
          })
        }

        setCompositeLevel(data.composite?.level ?? 'low')
      } catch (e) {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      setConnected(false)
      clearInterval(pingRef.current)
      // Auto-reconnect after 2s
      setTimeout(connect, 2000)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [wsUrl])

  const disconnect = useCallback(() => {
    clearInterval(pingRef.current)
    wsRef.current?.close()
    setConnected(false)
  }, [])

  const reset = useCallback(() => {
    setLatestUpdate(null)
    setScoreHistory([])
    setTranscriptLines([])
    setAllFlags([])
    setCompositeLevel('low')
  }, [])

  const runDemo = useCallback(async (scenario) => {
    reset()
    // Prepare audio element synchronously inside user gesture (before any await)
    if (onBeforeDemo) onBeforeDemo()
    setDemoRunning(true)
    try {
      const res = await fetch(`/demo/${scenario}`, { method: 'POST' })
      const data = await res.json()
      return data
    } finally {
      setDemoRunning(false)
    }
  }, [reset])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    connected,
    latestUpdate,
    scoreHistory,
    transcriptLines,
    allFlags,
    compositeLevel,
    demoRunning,
    runDemo,
    reset,
  }
}
