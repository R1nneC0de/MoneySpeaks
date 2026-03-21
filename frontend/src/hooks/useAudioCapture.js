import { useState, useRef, useCallback, useEffect } from 'react'

const SAMPLE_RATE = 16000
const CHUNK_DURATION = 2 // seconds
const CHUNK_SIZE = SAMPLE_RATE * CHUNK_DURATION

/**
 * Browser mic capture → 16kHz mono PCM16 → WebSocket to backend.
 */
export function useAudioCapture(wsUrl = 'ws://localhost:8000/ws/audio') {
  const [isCapturing, setIsCapturing] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const streamRef = useRef(null)
  const contextRef = useRef(null)
  const processorRef = useRef(null)
  const bufferRef = useRef(new Float32Array(0))

  const startCapture = useCallback(async () => {
    try {
      setError(null)

      // Connect WebSocket
      const ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      await new Promise((resolve, reject) => {
        ws.onopen = resolve
        ws.onerror = () => reject(new Error('WebSocket connection failed'))
        setTimeout(() => reject(new Error('WebSocket timeout')), 5000)
      })

      // Get mic stream
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream

      // Set up AudioContext for resampling to 16kHz mono
      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })
      contextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (e) => {
        if (ws.readyState !== WebSocket.OPEN) return

        const inputData = e.inputBuffer.getChannelData(0)

        // Accumulate samples
        const newBuffer = new Float32Array(bufferRef.current.length + inputData.length)
        newBuffer.set(bufferRef.current)
        newBuffer.set(inputData, bufferRef.current.length)
        bufferRef.current = newBuffer

        // Send 2-second chunks
        while (bufferRef.current.length >= CHUNK_SIZE) {
          const chunk = bufferRef.current.slice(0, CHUNK_SIZE)
          bufferRef.current = bufferRef.current.slice(CHUNK_SIZE)

          // Convert float32 [-1,1] to int16 PCM
          const pcm16 = new Int16Array(chunk.length)
          for (let i = 0; i < chunk.length; i++) {
            pcm16[i] = Math.max(-32768, Math.min(32767, Math.round(chunk[i] * 32767)))
          }
          ws.send(pcm16.buffer)
        }
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsCapturing(true)
    } catch (err) {
      setError(err.message)
      stopCapture()
    }
  }, [wsUrl])

  const stopCapture = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }
    if (contextRef.current) {
      contextRef.current.close()
      contextRef.current = null
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    bufferRef.current = new Float32Array(0)
    setIsCapturing(false)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => stopCapture()
  }, [stopCapture])

  return { isCapturing, error, startCapture, stopCapture }
}
