import React, { useEffect, useRef, useState, useCallback } from 'react'
import RiskIndicator from './components/RiskIndicator'
import ScoreTimeline from './components/ScoreTimeline'
import FlaggedPhrases from './components/FlaggedPhrases'
import LiveTranscript from './components/LiveTranscript'
import DemoPlayer from './components/DemoPlayer'
import TrustedContact from './components/TrustedContact'
import { useAudioCapture } from './hooks/useAudioCapture'
import { useDashboard } from './hooks/useDashboard'
import { useAuth } from './auth/AuthProvider'

// Warning text shown on screen
const WARNING_TEXT = {
  high: 'DANGER! This call is very likely a scam. Hang up immediately and call your bank directly.',
  medium: 'CAUTION: Some parts of this call seem suspicious. Stay alert.',
}

export default function App() {
  const audioRef = useRef(null)
  const [audioTime, setAudioTime] = useState(0)
  const { isCapturing, error: captureError, startCapture, stopCapture } = useAudioCapture()

  const handleAudioUrl = useCallback((url) => {
    if (audioRef.current) {
      // Don't restart if already playing
      if (!audioRef.current.paused && audioRef.current.src) return
      audioRef.current.src = url
      audioRef.current.play().catch((e) => console.warn('Audio playback failed:', e))
    }
  }, [])

  const handleBeforeDemo = useCallback(() => {
    // Stop any playing audio and reset time
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      audioRef.current.src = ''
    }
    setAudioTime(0)
  }, [])

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
    transcriptData,
    analysisData,
    demoScenario,
  } = useDashboard('ws://localhost:8000/ws/dashboard', {
    onAudioUrl: handleAudioUrl,
    onBeforeDemo: handleBeforeDemo,
  })

  const {
    isAuthenticated, isLoading, user, profile, mockMode,
    login, logout, updateProfile, addTrustedContact, removeTrustedContact, notifyContacts,
  } = useAuth()

  const prevLevelRef = useRef('low')
  const [warningText, setWarningText] = useState('')
  const [bankNumber, setBankNumber] = useState('')
  const [showBankInput, setShowBankInput] = useState(false)

  // Audio timeupdate handler
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    const onTimeUpdate = () => setAudioTime(audio.currentTime)
    audio.addEventListener('timeupdate', onTimeUpdate)
    return () => audio.removeEventListener('timeupdate', onTimeUpdate)
  }, [])

  // Sync bank number from profile
  useEffect(() => {
    if (profile?.bank_number) {
      setBankNumber(profile.bank_number)
    }
  }, [profile])

  // Show warning text on level transitions
  useEffect(() => {
    const prev = prevLevelRef.current
    const curr = compositeLevel
    prevLevelRef.current = curr

    const escalated =
      (prev === 'low' && (curr === 'medium' || curr === 'high')) ||
      (prev === 'medium' && curr === 'high')

    if (escalated && WARNING_TEXT[curr]) {
      setWarningText(WARNING_TEXT[curr])
    } else if (curr === 'low') {
      setWarningText('')
    }
  }, [compositeLevel])

  const score = latestUpdate?.composite?.score ?? 0
  const reasoning = latestUpdate?.gemini?.reasoning
    ?? analysisData?.reasoning
    ?? ''

  return (
    <div className="min-h-screen bg-crt-black text-crt-green font-mono crt-screen relative">
      {/* CRT scanline overlay */}
      <div className="crt-overlay" />

      {/* Hidden audio element for demo playback */}
      <audio ref={audioRef} preload="auto" />

      {/* OS-style status bar */}
      <header className="border-b-2 border-crt-border px-4 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="font-pixel text-xs text-crt-green">
              ░░ MONEYSPEAKS v1.0 ░░
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 font-mono text-sm">
              <span className={connected ? 'text-crt-green' : 'text-crt-red'}>
                [{connected ? '■' : '□'}]
              </span>
              <span className={connected ? 'text-crt-green' : 'text-crt-red'}>
                {connected ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>
            {isAuthenticated ? (
              <div className="flex items-center gap-2 font-mono text-sm">
                <span className="text-crt-green-dim">{user?.name || user?.email || 'USER'}</span>
                {mockMode && <span className="text-crt-amber text-xs">[DEMO]</span>}
                <button onClick={logout} className="text-crt-green-dim hover:text-crt-green">
                  [LOGOUT]
                </button>
              </div>
            ) : (
              <button
                onClick={login}
                className="btn-retro bg-crt-green/10 text-crt-green px-3 py-1 text-sm"
              >
                [LOGIN]
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-4">
        {/* Warning banner */}
        {warningText && (
          <div className={`mb-4 px-4 py-3 font-mono text-lg text-center border-2 animate-pulse-fast ${
            compositeLevel === 'high'
              ? 'border-crt-red text-crt-red bg-crt-red/10'
              : 'border-crt-amber text-crt-amber bg-crt-amber/10'
          }`}>
            ⚠ {warningText}
          </div>
        )}

        {/* Row 1: Demo scenarios (full width) */}
        <div className="mb-4">
          <DemoPlayer onRunDemo={runDemo} running={demoRunning} />
        </div>

        {/* Row 2: Score LEFT + Transcript RIGHT */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 mb-4">
          {/* Left column — Risk + Actions */}
          <div className="lg:col-span-5 space-y-4">
            <RiskIndicator level={compositeLevel} score={score} reasoning={reasoning} />

            {/* Action buttons */}
            <div className="window-panel">
              <div className="window-titlebar">
                <span>[ ACTIONS ]</span>
                <span>■</span>
              </div>
              <div className="p-4 space-y-3">
                {/* Hang up and call bank */}
                {compositeLevel === 'high' && bankNumber && (
                  <a
                    href={`tel:${bankNumber}`}
                    className="btn-retro block w-full bg-crt-red/20 text-crt-red
                               text-center px-4 py-3 text-lg min-h-[48px]"
                  >
                    [!! HANG UP & CALL MY BANK !!]
                  </a>
                )}

                {/* Set bank number */}
                {!bankNumber && (
                  <div>
                    {showBankInput ? (
                      <div className="flex gap-2">
                        <input
                          type="tel"
                          placeholder="Bank phone number"
                          value={bankNumber}
                          onChange={(e) => setBankNumber(e.target.value)}
                          className="input-retro flex-1"
                        />
                        <button
                          onClick={() => {
                            updateProfile({ bank_number: bankNumber })
                            setShowBankInput(false)
                          }}
                          className="btn-retro bg-crt-green/10 text-crt-green px-3"
                        >
                          [OK]
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowBankInput(true)}
                        className="btn-retro w-full bg-crt-panel text-crt-green-dim px-4 py-2 text-sm"
                      >
                        [Set bank number for quick dial]
                      </button>
                    )}
                  </div>
                )}

                {/* Mic capture */}
                <button
                  onClick={isCapturing ? stopCapture : startCapture}
                  className={`btn-retro w-full px-4 py-3 text-lg min-h-[48px] ${
                    isCapturing
                      ? 'bg-crt-red/20 text-crt-red'
                      : 'bg-crt-green/10 text-crt-green'
                  }`}
                >
                  {isCapturing ? '[■ STOP LISTENING]' : '[▶ START LISTENING]'}
                </button>

                {captureError && (
                  <p className="text-crt-red text-sm text-center">{captureError}</p>
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

          {/* Right column — Transcript */}
          <div className="lg:col-span-7">
            <LiveTranscript
              transcriptData={transcriptData}
              analysisData={analysisData}
              audioTime={audioTime}
              lines={transcriptLines}
            />
          </div>
        </div>

        {/* Row 3: Analytics — charts and flags side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          <ScoreTimeline data={scoreHistory} />
          <FlaggedPhrases flags={allFlags} />
        </div>

        {/* Behavioral info */}
        {latestUpdate?.behavioral && (
          <div className="window-panel mb-4">
            <div className="window-titlebar">
              <span>[ BEHAVIORAL ANALYSIS ]</span>
              <span>■</span>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-3 gap-4 text-center font-mono">
                <div>
                  <p className="text-2xl text-crt-green">
                    {latestUpdate.behavioral.response_latency_ms ?? '—'}
                    <span className="text-sm text-crt-green-dim">ms</span>
                  </p>
                  <p className="text-xs text-crt-green-dim">Response latency</p>
                </div>
                <div>
                  <p className="text-2xl text-crt-green">
                    {latestUpdate.behavioral.disfluency_rate ?? '—'}
                    <span className="text-sm text-crt-green-dim">/min</span>
                  </p>
                  <p className="text-xs text-crt-green-dim">Disfluency rate</p>
                </div>
                <div>
                  <p className="text-2xl text-crt-green">
                    {latestUpdate.behavioral.speech_ratio != null
                      ? `${Math.round(latestUpdate.behavioral.speech_ratio * 100)}%`
                      : '—'}
                  </p>
                  <p className="text-xs text-crt-green-dim">Speech ratio</p>
                </div>
              </div>
              {latestUpdate.behavioral.flags?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {latestUpdate.behavioral.flags.map((f, i) => (
                    <span key={i} className="font-mono text-sm text-crt-amber border border-crt-amber/40 bg-crt-amber/10 px-2 py-1">
                      [!] {f}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t-2 border-crt-border px-4 py-2 mt-4">
        <p className="text-center font-mono text-xs text-crt-green-dark">
          MoneySpeaks — HackDuke 2026 Finance Track — Protecting elderly users from voice fraud
        </p>
      </footer>
    </div>
  )
}
