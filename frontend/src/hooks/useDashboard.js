import { useState, useRef, useCallback, useEffect } from 'react'

/**
 * Manages WebSocket connection to /ws/dashboard and state for all score data.
 *
 * Handles two message protocols:
 * - New demo protocol: demo_start → chunk_update → demo_end
 * - Legacy live mic protocol: flat score objects (no type field)
 */
export function useDashboard(wsUrl = 'ws://localhost:8000/ws/dashboard', { onAudioUrl, onBeforeDemo } = {}) {
  const [connected, setConnected] = useState(false)
  const [latestUpdate, setLatestUpdate] = useState(null)
  const [scoreHistory, setScoreHistory] = useState([])
  const [transcriptLines, setTranscriptLines] = useState([])
  const [allFlags, setAllFlags] = useState([])
  const [compositeLevel, setCompositeLevel] = useState('low')
  const [demoRunning, setDemoRunning] = useState(false)

  // New demo protocol state
  const [transcriptData, setTranscriptData] = useState(null)  // {text, words}
  const [analysisData, setAnalysisData] = useState(null)       // Gemini analysis
  const [demoScenario, setDemoScenario] = useState(null)

  const wsRef = useRef(null)
  const pingRef = useRef(null)
  const mountedRef = useRef(false)
  const callbacksRef = useRef({ onAudioUrl, onBeforeDemo })

  // Keep callbacks ref current without triggering reconnects
  useEffect(() => {
    callbacksRef.current = { onAudioUrl, onBeforeDemo }
  }, [onAudioUrl, onBeforeDemo])

  useEffect(() => {
    mountedRef.current = true
    let reconnectTimer = null

    function connect() {
      if (!mountedRef.current) return
      if (wsRef.current?.readyState === WebSocket.OPEN ||
          wsRef.current?.readyState === WebSocket.CONNECTING) return

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return }
        setConnected(true)
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

          // --- New demo protocol ---
          if (data.type === 'demo_start') {
            setTranscriptData(data.transcript)
            setAnalysisData(null) // No analysis yet — it arrives progressively
            setDemoScenario(data.scenario)
            // Trigger audio playback
            if (data.audio_url && callbacksRef.current.onAudioUrl) {
              callbacksRef.current.onAudioUrl(data.audio_url)
            }
            return
          }

          if (data.type === 'chunk_update') {
            setLatestUpdate(data)

            // Update score history for chart
            setScoreHistory((prev) => {
              const next = [...prev, {
                time: new Date(data.timestamp * 1000).toLocaleTimeString(),
                deepfake: data.deepfake_score,
                composite: data.composite?.score ?? 0,
              }]
              return next.slice(-60)
            })

            // Progressive analysis — update analysisData and accumulate flags
            if (data.analysis) {
              setAnalysisData(data.analysis)

              // Collect all current flags from this chunk's progressive analysis
              const chunkFlags = [
                ...(data.analysis.tone_flags ?? []),
                ...(data.analysis.phrase_flags ?? []),
                ...(data.analysis.scam_flags ?? []),
                ...(data.behavioral?.flags ?? []),
              ]
              if (chunkFlags.length > 0) {
                setAllFlags(chunkFlags.map((f) => ({
                  text: f,
                  timestamp: data.timestamp,
                })))
              }
            }

            setCompositeLevel(data.composite?.level ?? 'low')
            return
          }

          if (data.type === 'demo_end') {
            setDemoRunning(false)
            return
          }

          // --- Legacy live mic protocol (no type field) ---
          setLatestUpdate(data)

          if (data.audio_url && callbacksRef.current.onAudioUrl) {
            callbacksRef.current.onAudioUrl(data.audio_url)
          }

          setScoreHistory((prev) => {
            const next = [...prev, {
              time: new Date(data.timestamp * 1000).toLocaleTimeString(),
              deepfake: data.deepfake_score,
              composite: data.composite?.score ?? 0,
              escalation: (data.gemini?.escalation_score ?? 0) / 100,
            }]
            return next.slice(-60)
          })

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
        if (mountedRef.current) {
          reconnectTimer = setTimeout(connect, 2000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      mountedRef.current = false
      clearTimeout(reconnectTimer)
      clearInterval(pingRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }
      setConnected(false)
    }
  }, [wsUrl])

  const reset = useCallback(() => {
    setLatestUpdate(null)
    setScoreHistory([])
    setTranscriptLines([])
    setAllFlags([])
    setCompositeLevel('low')
    setTranscriptData(null)
    setAnalysisData(null)
    setDemoScenario(null)
  }, [])

  const runDemo = useCallback(async (scenario) => {
    reset()
    if (callbacksRef.current.onBeforeDemo) callbacksRef.current.onBeforeDemo()
    setDemoRunning(true)
    try {
      const res = await fetch(`/demo/${scenario}`, { method: 'POST' })
      const data = await res.json()
      return data
    } finally {
      setDemoRunning(false)
    }
  }, [reset])

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
    // New demo protocol state
    transcriptData,
    analysisData,
    demoScenario,
  }
}
