import React, { useEffect, useRef, useState } from 'react'
import RiskIndicator from './components/RiskIndicator'
import ScoreTimeline from './components/ScoreTimeline'
import FlaggedPhrases from './components/FlaggedPhrases'
import LiveTranscript from './components/LiveTranscript'
import DemoPlayer from './components/DemoPlayer'
import TrustedContact from './components/TrustedContact'
import { useAudioCapture } from './hooks/useAudioCapture'
import { useDashboard } from './hooks/useDashboard'
import { useAuth } from './auth/AuthProvider'

// Distinct TTS warning phrases per risk level
const WARNINGS = {
  high: {
    text: 'Danger! This call is very likely a scam. Hang up immediately and call your bank directly.',
    audio: '/warnings/warning_scam.mp3',
    rate: 0.85,
    pitch: 0.9,
  },
  medium: {
    text: 'Caution. Some parts of this call seem suspicious. Stay alert and do not share personal information.',
    audio: '/warnings/caution_suspicious.mp3',
    rate: 0.95,
    pitch: 1.0,
  },
}

function speakWarning(level, lastSpokenRef) {
  const now = Date.now()
  // Don't repeat warnings within 20 seconds
  if (now - lastSpokenRef.current < 20000) return
  const config = WARNINGS[level]
  if (!config) return

  lastSpokenRef.current = now

  // Try pre-cached ElevenLabs audio first
  const audio = new Audio(config.audio)
  audio.play().catch(() => {
    // Fallback to browser SpeechSynthesis
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel() // Stop any current speech
      const utterance = new SpeechSynthesisUtterance(config.text)
      utterance.rate = config.rate
      utterance.pitch = config.pitch
      utterance.volume = 1
      speechSynthesis.speak(utterance)
    }
  })
}

// Play demo scenario audio in the browser.
// We pre-create the Audio element on the user's click (trusted gesture) and set
// src later when the backend sends the audio_url. This avoids browser autoplay blocks.
let currentDemoAudio = null
let pendingDemoAudio = null

function prepareDemoAudio() {
  stopDemoAudio()
  // Create and "warm up" an Audio element inside the user gesture
  pendingDemoAudio = new Audio()
  pendingDemoAudio.preload = 'auto'
}

function playDemoAudio(url) {
  if (!url) return
  if (pendingDemoAudio) {
    currentDemoAudio = pendingDemoAudio
    pendingDemoAudio = null
    currentDemoAudio.src = url
    currentDemoAudio.play().catch((e) => console.warn('Demo audio playback failed:', e))
  } else {
    // Fallback: try direct play (may be blocked by browser)
    currentDemoAudio = new Audio(url)
    currentDemoAudio.play().catch((e) => console.warn('Demo audio playback failed:', e))
  }
}

function stopDemoAudio() {
  if (currentDemoAudio) {
    currentDemoAudio.pause()
    currentDemoAudio = null
  }
  pendingDemoAudio = null
}

export default function App() {
  const { isCapturing, error: captureError, startCapture, stopCapture } = useAudioCapture()
  const {
    connected,
    latestUpdate,
    scoreHistory,
    transcriptLines,
    allFlags,
    compositeLevel,
    demoRunning,
    runDemo,
    reset,
  } = useDashboard('ws://localhost:8000/ws/dashboard', {
    onAudioUrl: (url) => playDemoAudio(url),
    onBeforeDemo: () => prepareDemoAudio(),
  })
  const {
    isAuthenticated, isLoading, user, profile, mockMode,
    login, logout, updateProfile, addTrustedContact, removeTrustedContact, notifyContacts,
  } = useAuth()

  const lastSpokenRef = useRef(0)
  const prevLevelRef = useRef('low')
  const [bankNumber, setBankNumber] = useState('')
  const [showBankInput, setShowBankInput] = useState(false)

  // Sync bank number from profile
  useEffect(() => {
    if (profile?.bank_number) {
      setBankNumber(profile.bank_number)
    }
  }, [profile])

  // Speak warnings only on level transitions (low→medium, medium→high, low→high)
  useEffect(() => {
    const prev = prevLevelRef.current
    const curr = compositeLevel
    prevLevelRef.current = curr

    const escalated =
      (prev === 'low' && (curr === 'medium' || curr === 'high')) ||
      (prev === 'medium' && curr === 'high')

    if (escalated) {
      speakWarning(curr, lastSpokenRef)
    }
  }, [compositeLevel])

  const score = latestUpdate?.composite?.score ?? 0
  const reasoning = latestUpdate?.gemini?.reasoning ?? ''

  return (
    <div className="min-h-screen bg-surface-900 text-white">
      {/* Header */}
      <header className="border-b border-surface-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">MoneySpeaks</h1>
            <p className="text-sm text-gray-400">Real-time voice scam detection</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span
                className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}
                title={connected ? 'Connected' : 'Disconnected'}
              />
              <span className="text-xs text-gray-400">
                {connected ? 'Live' : 'Connecting...'}
              </span>
            </div>
            {isAuthenticated ? (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-300">{user?.name || user?.email || 'User'}</span>
                {mockMode && <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded">demo</span>}
                <button
                  onClick={logout}
                  className="text-xs text-gray-400 hover:text-white transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <button
                onClick={login}
                className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Login
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Left column — Risk indicator + actions (60% focus) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-surface-800 rounded-2xl p-8 flex flex-col items-center">
              <RiskIndicator level={compositeLevel} score={score} reasoning={reasoning} />

              {/* Action buttons */}
              <div className="mt-8 w-full space-y-3">
                {/* Hang up and call bank */}
                {compositeLevel === 'high' && bankNumber && (
                  <a
                    href={`tel:${bankNumber}`}
                    className="block w-full bg-red-600 hover:bg-red-500 text-white text-center
                               px-6 py-4 rounded-xl font-bold text-lg min-h-[64px]
                               transition-colors"
                  >
                    Hang up & call my bank
                  </a>
                )}

                {/* Set bank number */}
                {!bankNumber && (
                  <div>
                    {showBankInput ? (
                      <div className="flex gap-2">
                        <input
                          type="tel"
                          placeholder="Your bank's phone number"
                          value={bankNumber}
                          onChange={(e) => setBankNumber(e.target.value)}
                          className="flex-1 bg-surface-700 border border-gray-600 rounded-lg
                                     px-4 py-3 text-base text-white"
                        />
                        <button
                          onClick={() => {
                            updateProfile({ bank_number: bankNumber })
                            setShowBankInput(false)
                          }}
                          className="bg-blue-600 px-4 py-3 rounded-lg font-medium"
                        >
                          Save
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowBankInput(true)}
                        className="w-full bg-surface-700 hover:bg-surface-900 text-gray-300
                                   px-4 py-3 rounded-xl text-sm transition-colors"
                      >
                        Set your bank's number for quick dial
                      </button>
                    )}
                  </div>
                )}

                {/* Mic capture */}
                <button
                  onClick={isCapturing ? stopCapture : startCapture}
                  className={`
                    w-full px-6 py-4 rounded-xl font-semibold text-lg min-h-[64px]
                    transition-colors
                    ${isCapturing
                      ? 'bg-red-700 hover:bg-red-600 text-white'
                      : 'bg-blue-600 hover:bg-blue-500 text-white'}
                  `}
                >
                  {isCapturing ? 'Stop listening' : 'Start listening'}
                </button>

                {captureError && (
                  <p className="text-red-400 text-sm text-center">{captureError}</p>
                )}
              </div>
            </div>

            <TrustedContact
              riskLevel={compositeLevel}
              contacts={profile?.trusted_contacts || []}
              onAddContact={addTrustedContact}
              onRemoveContact={removeTrustedContact}
              onNotify={() => notifyContacts(compositeLevel)}
            />
          </div>

          {/* Right column — Data panels */}
          <div className="lg:col-span-7 space-y-6">
            <DemoPlayer onRunDemo={runDemo} running={demoRunning} />
            <ScoreTimeline data={scoreHistory} />
            <FlaggedPhrases flags={allFlags} />
            <LiveTranscript lines={transcriptLines} />

            {/* Behavioral info */}
            {latestUpdate?.behavioral && (
              <div className="bg-surface-800 rounded-2xl p-6">
                <h3 className="text-lg font-semibold mb-3">Behavioral Analysis</h3>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">
                      {latestUpdate.behavioral.response_latency_ms ?? '—'}
                      <span className="text-sm font-normal text-gray-400">ms</span>
                    </p>
                    <p className="text-xs text-gray-400">Response latency</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">
                      {latestUpdate.behavioral.disfluency_rate ?? '—'}
                      <span className="text-sm font-normal text-gray-400">/min</span>
                    </p>
                    <p className="text-xs text-gray-400">Disfluency rate</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">
                      {latestUpdate.behavioral.speech_ratio != null
                        ? `${Math.round(latestUpdate.behavioral.speech_ratio * 100)}%`
                        : '—'}
                    </p>
                    <p className="text-xs text-gray-400">Speech ratio</p>
                  </div>
                </div>
                {latestUpdate.behavioral.flags?.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {latestUpdate.behavioral.flags.map((f, i) => (
                      <span key={i} className="px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded-full">
                        {f}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-700 px-6 py-3 mt-8">
        <p className="text-center text-xs text-gray-500">
          MoneySpeaks — HackDuke 2026 Finance Track
        </p>
      </footer>
    </div>
  )
}
