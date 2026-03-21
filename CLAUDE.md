# VoiceGuard — HackDuke 2026 · Finance Track

Real-time voice scam detector protecting elderly users from AI-powered phone fraud.
Combines acoustic deepfake detection (wav2vec2), affective tone analysis (Gemini Live),
and social engineering phrase classification to score calls as they happen.

---

## Project Overview

**Problem:** Generative AI has made voice cloning trivially cheap ($0 and 3 seconds of
audio). Scammers impersonate banks, IRS agents, grandchildren, and doctors. Elderly users
have no tool to verify whether the voice on the phone is real. Enterprise tools (Pindrop,
Reality Defender) protect banks — nobody protects the person receiving the call.

**Solution:** A browser-based companion app. User plays a suspicious call on speaker.
The app captures ambient audio via mic, runs it through three parallel signal layers,
and surfaces a single red/amber/green trust indicator with plain-language warnings
spoken aloud via ElevenLabs TTS.

**Target user:** Adults 60+ receiving suspicious calls. Secondary: bank call center
agents (agent-assist dashboard variant).

**HackDuke track:** Finance · Financial accessibility, security, efficiency.

---

## Tech Stack

| Layer | Tool | Role |
|---|---|---|
| Deepfake detection | wav2vec2 (fine-tuned) | Acoustic synthesis artifact scoring |
| Affective analysis | Gemini 2.5 Flash Live | Emotional tone + conversation arc reasoning |
| TTS warnings | ElevenLabs | Spoken alerts to user + training data generation |
| Audio capture | WebAudio API + WebSocket | Browser mic → FastAPI backend |
| Backend | FastAPI + asyncio | Parallel model orchestration |
| Frontend | React + Recharts | Real-time dashboard + adaptive UI |
| Deployment | DigitalOcean Gradient AI | Model inference endpoint |
| Auth | Auth0 | User profiles + trusted contact flows |
| Scam registry (stretch) | Solana | Immutable community threat log |

---

## Repository Structure

```
voiceguard/
├── CLAUDE.md                  ← this file
├── backend/
│   ├── main.py                ← FastAPI app, WebSocket endpoints
│   ├── models/
│   │   ├── deepfake.py        ← wav2vec2 inference wrapper
│   │   └── gemini_live.py     ← Gemini Live session manager
│   ├── classifier/
│   │   ├── scam_intent.py     ← LLM-based phrase + intent scorer
│   │   └── behavioral.py      ← VAD-based response latency analysis
│   ├── audio/
│   │   └── processing.py      ← chunk splitting, codec augmentation
│   └── demo/
│       ├── generate_scripts.py ← Gemini → ElevenLabs data generation
│       ├── bank_impersonation.mp3
│       ├── grandparent_scam.mp3
│       └── real_customer.mp3
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── RiskIndicator.jsx     ← traffic light, main signal
│   │   │   ├── LiveTranscript.jsx    ← rolling transcript with flags
│   │   │   ├── ScoreTimeline.jsx     ← Recharts deepfake score over time
│   │   │   ├── FlaggedPhrases.jsx    ← highlighted social engineering markers
│   │   │   ├── TrustedContact.jsx    ← post-call family notification
│   │   │   └── DemoPlayer.jsx        ← pre-generated scenario controls
│   │   └── hooks/
│   │       ├── useAudioCapture.js    ← WebAudio API mic → WebSocket
│   │       └── useDashboard.js       ← incoming score state management
│   └── public/
├── training/
│   ├── finetune_wav2vec2.py   ← fine-tuning script (run before hackathon)
│   ├── datasets/
│   │   ├── download_asvspoof5.sh
│   │   └── generate_elevenlabs.py   ← 400 training + 100 test clips
│   └── evaluate.py            ← EER on In-the-Wild held-out set
└── scripts/
    ├── setup.sh
    └── demo.sh                ← triggers demo scenario playback
```

---

## Architecture

### Audio pipeline (real-time)

```
Browser mic (WebAudio API)
    → 2s audio chunks via WebSocket
    → FastAPI /ws/audio endpoint
    → [PARALLEL]
        ├── wav2vec2 fine-tuned
        │     └── deepfake_score: 0.0–1.0
        └── Gemini Live session (persistent)
              └── {tone_flags, phrase_flags, risk_reasoning}
    → composite_risk(deepfake_score, gemini_flags)
    → broadcast to React dashboard via /ws/dashboard
    → [IF HIGH RISK] ElevenLabs TTS warning spoken to user
```

### Demo pipeline (controlled real-time)

```
DemoPlayer button click
    → POST /demo/{scenario}
    → backend reads demo/{scenario}.mp3 as byte stream
    → feeds into SAME pipeline as live mic audio
    → scores update on dashboard in real time
    → judges see live inference, not pre-computed results
```

No pre-computed scores. The audio input is controlled; the inference is live.

---

## Models

### wav2vec2 deepfake detector

- **Base:** `facebook/wav2vec2-base` (HuggingFace)
- **Fine-tune strategy:**
  - Stage 1: freeze transformer, train classification head on ASVspoof 5 + MLAAD English
  - Stage 2: unfreeze top 4 layers, fine-tune with CodecFake + ElevenLabs samples (10% mix)
  - Augmentation: G.711 codec compression, RIR room impulse response, -5 to +20dB SNR noise
- **Training data:**
  - ASVspoof 5 (2024) — crowdsourced, diverse devices, adversarial attacks
  - MLAAD — 38 languages, 82 TTS models
  - CodecFake subset A2 — VALL-E X / neural codec TTS specifically
  - ElevenLabs generated — 400 clips across voices 1–8 (voices 9–12 held out)
  - LibriSpeech genuine speech — paired real samples
- **Test / demo set:** ASVspoof 5 eval + In-the-Wild (held out, never seen during training)
- **Output:** `{real: float, fake: float}` per 2s chunk

### Gemini Live session

- **Model:** `gemini-2.5-flash-native-audio-preview-12-2025`
- **Session:** persistent WebSocket, maintained per call
- **Capabilities used:**
  - Native audio input — no STT preprocessing step
  - Affective dialog — emotional tone detection
  - Proactive audio — only fires when risk detected
  - Full conversation memory — reasons over full call arc
- **System prompt:** see `backend/models/gemini_live.py` → `SYSTEM_PROMPT`
- **Output:** `{tone_flags: [], phrase_flags: [], escalation_score: 0–100, reasoning: str}`

### Scam intent classifier

- **Approach:** zero-shot Claude / Gemini with structured system prompt
- **Input:** rolling 60s transcript window
- **Training data:** 300 synthetic scam transcripts (generated by Gemini) + 300 legitimate
- **Categories:** IRS impersonation, bank fraud, grandparent scam, Medicare scam,
  tech support, utility scam
- **Output:** `{risk: 0–100, flags: [], scam_type: str}`

### Behavioral timing (novel signal)

- **What:** VAD-based response latency measurement
- **Signal:** KBA answer latency < 300ms = suspicious (AI-speed), disfluency rate < 0.3/min
- **Dataset:** 50 human + 50 ElevenLabs responses to security questions, self-collected
- **Library:** `webrtcvad` for voice activity detection

---

## Demo Scenarios

Three pre-generated audio files in `backend/demo/`. Generated before the hackathon:
scripts written by Gemini, audio synthesized by ElevenLabs voices 9–12 (never seen by model).

| File | Label | Voice | What it tests |
|---|---|---|---|
| `bank_impersonation.mp3` | FAKE | ElevenLabs voice 9 | wav2vec2 + authority/urgency flags |
| `grandparent_scam.mp3` | FAKE | ElevenLabs voice 11 | Gemini affective analysis (performed distress) |
| `real_customer.mp3` | REAL | ElevenLabs voice 12* | True negative — should stay green |

*Voice 12 is ElevenLabs-generated but playing a legitimate customer — tests whether
the system correctly discriminates on content + behavior, not just voice origin.

**Demo order:**
1. Run `real_customer.mp3` first — calibrates judges, green result
2. Run `bank_impersonation.mp3` — wav2vec2 flags fast, Gemini flags urgency arc
3. Run `grandparent_scam.mp3` — harder case, Gemini's affective analysis carries it

---

## UI Design

### Core principles (elderly demographic)
- Single traffic light occupies 60% of screen — red / amber / green, no numbers
- All warnings spoken aloud via ElevenLabs TTS — user may not be looking at screen
- One large action button: "Hang up and call my bank" — pre-stores user's real bank number
- Font inherits system accessibility settings — no separate large-text toggle
- Button targets minimum 64×64px (WCAG 2.5.5)

### Adaptive behavior (activates after 3 uses)
- Learns which scam types user's number has been targeted by
- Pre-loads relevant phrase patterns for detected scam category
- Trusted contact notification: opt-in SMS to family member post-flagged call

### Risk score composition
```python
def composite_risk(deepfake_score: float, gemini: dict) -> dict:
    acoustic   = deepfake_score * 0.40
    emotional  = gemini["escalation_score"] / 100 * 0.35
    linguistic = len(gemini["phrase_flags"]) / 5 * 0.25  # cap at 5 flags
    total = min(acoustic + emotional + linguistic, 1.0)
    level = "high" if total > 0.7 else "medium" if total > 0.4 else "low"
    return {"score": total, "level": level}
```

---

## Environment Variables

```bash
# backend/.env
ELEVENLABS_API_KEY=
GEMINI_API_KEY=
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
DIGITALOCEAN_INFERENCE_URL=   # deployed wav2vec2 endpoint
ANTHROPIC_API_KEY=            # fallback for scam intent classification
```

---

## Setup

```bash
# Backend
cd backend
pip install fastapi uvicorn transformers torch torchaudio \
            webrtcvad google-generativeai elevenlabs anthropic \
            python-dotenv asyncio websockets

# Frontend
cd frontend
npm install

# Run locally
uvicorn backend.main:app --reload --port 8000
cd frontend && npm run dev

# Generate demo audio (run once before hackathon)
python backend/demo/generate_scripts.py

# Fine-tune model (run on Colab, outputs checkpoint)
python training/finetune_wav2vec2.py
```

---

## Prize Targets

| Prize | Integration | Why it fits |
|---|---|---|
| **ElevenLabs** (earbuds) | TTS warnings + training data generation + demo audio | Core to the attack-and-defend loop |
| **Gemini API** (swag) | Gemini Live for affective analysis + script generation | Native audio — not a text wrapper |
| **Auth0** (headphones) | User profiles + AI agent auth (Auth0 for AI Agents) | Protects sensitive user data |
| **DigitalOcean** (mouse) | Gradient AI for wav2vec2 inference endpoint | Real deployed model, not localhost |
| **Reach Capital** (webcam + meeting) | Agent-assist reframe for credit union agents | Frontline worker AI angle |
| **Solana** (ledger) | Community scam number registry | Only if bandwidth allows |

---

## Pitch Narrative

"AI voice cloning costs $0 and takes 3 seconds of audio. Banks have enterprise tools
to detect it. Your grandmother doesn't. VoiceGuard is a companion app that monitors
calls in real time — combining acoustic deepfake detection trained specifically on
ElevenLabs voices with Gemini Live's affective analysis, which catches the emotional
manipulation that acoustic models miss entirely. It speaks warnings aloud, so you
don't need to look at a screen. And it works on the call you're already on."

**The key insight judges should leave with:** deepfake voice detection is solved at
the enterprise level. The gap is the consumer-facing application layer. We filled it.

---

## Known Limitations / Open Problems (be honest with judges)

- **Generalization:** models trained months ago degrade against new TTS tools.
  We retrain on ASVspoof 5 + CodecFake + fresh ElevenLabs samples to stay current.
- **Compression:** phone codecs (G.711) degrade deepfake artifacts. Mitigated with
  codec augmentation during training but not fully solved.
- **Real person running a scam:** wav2vec2 won't flag a real human voice.
  Gemini's linguistic + affective layer is the only signal in this case.
- **False positives:** agitated real callers may trigger emotional flags.
  Composite score weighting keeps the acoustic layer dominant.
- **iOS mic restriction:** cannot intercept native PSTN calls on iPhone.
  Demo uses ambient mic capture (phone on speaker) or direct file injection.

---

## What We Built vs Inherited

| Component | Status |
|---|---|
| wav2vec2 architecture | Inherited (Meta / Facebook) |
| ASVspoof 5 / MLAAD / CodecFake datasets | Inherited |
| Fine-tuning on phone-channel codec subset | **We built** |
| ElevenLabs training sample generation | **We built** |
| Behavioral timing / KBA latency dataset | **We built** (novel, no prior dataset) |
| Scam transcript dataset (300 synthetic) | **We built** via Gemini |
| Composite risk scoring logic | **We built** |
| Consumer-facing UI for elderly users | **We built** |
| Trusted contact escalation flow | **We built** |
| Gemini Live affective analysis integration | **We built** |
