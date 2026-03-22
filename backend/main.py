"""MoneySpeaks — FastAPI backend with WebSocket audio pipeline."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).parent / ".env")

from backend.audio.processing import (
    chunk_audio,
    decode_audio_bytes,
    validate_audio,
    TARGET_SAMPLE_RATE,
)
from backend.audio.transcribe import ElevenLabsTranscriber
from backend.models.deepfake import DeepfakeDetector
from backend.models.gemini_live import GeminiLiveSession
from backend.models.composite import composite_risk
from backend.classifier.scam_intent import ScamIntentClassifier
from backend.classifier.behavioral import BehavioralAnalyzer
from backend.auth import get_current_user, get_user_profile, update_user_profile, MOCK_MODE as AUTH_MOCK

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("moneyspeaks")

app = FastAPI(title="MoneySpeaks", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Model instances (created once) ---
deepfake_detector = DeepfakeDetector()
gemini_session = GeminiLiveSession()
scam_classifier = ScamIntentClassifier()
behavioral_analyzer = BehavioralAnalyzer()
transcriber = ElevenLabsTranscriber()

# --- WebSocket connection manager ---
class ConnectionManager:
    def __init__(self):
        self.dashboard_clients: list[WebSocket] = []
        self.active_scenario: Optional[str] = None

    async def connect_dashboard(self, ws: WebSocket):
        await ws.accept()
        self.dashboard_clients.append(ws)
        logger.info(f"Dashboard client connected. Total: {len(self.dashboard_clients)}")

    def disconnect_dashboard(self, ws: WebSocket):
        self.dashboard_clients.remove(ws)
        logger.info(f"Dashboard client disconnected. Total: {len(self.dashboard_clients)}")

    async def broadcast(self, data: dict):
        dead = []
        for client in self.dashboard_clients:
            try:
                await client.send_json(data)
            except Exception:
                dead.append(client)
        for client in dead:
            self.dashboard_clients.remove(client)


manager = ConnectionManager()


# --- Audio pipeline processing ---
async def process_audio_chunk(chunk, scenario_hint: str = "") -> dict:
    """Run all models in parallel on a single 2-second audio chunk."""

    # Run deepfake + gemini + behavioral in parallel
    deepfake_task = asyncio.to_thread(deepfake_detector.score, chunk, scenario_hint)
    gemini_task = gemini_session.analyze_chunk(chunk, scenario_hint)
    behavioral_task = asyncio.to_thread(behavioral_analyzer.analyze_chunk, chunk, scenario_hint)

    deepfake_result, gemini_result, behavioral_result = await asyncio.gather(
        deepfake_task, gemini_task, behavioral_task
    )

    # Feed transcript to scam classifier
    transcript = gemini_result.get("transcript", "")
    scam_classifier.add_transcript(transcript)

    # Run scam intent classifier (rate-limited internally, every 20s)
    scam_result = await scam_classifier.classify()
    if scam_result is None:
        scam_result = {"risk": 0, "flags": [], "scam_type": "none", "mock": True}

    # Compute composite risk
    composite = composite_risk(deepfake_result["fake"], gemini_result)

    return {
        "timestamp": time.time(),
        "deepfake_score": deepfake_result["fake"],
        "deepfake": deepfake_result,
        "transcript": transcript,
        "gemini": {
            "tone_flags": gemini_result.get("tone_flags", []),
            "phrase_flags": gemini_result.get("phrase_flags", []),
            "escalation_score": gemini_result.get("escalation_score", 0),
            "reasoning": gemini_result.get("reasoning", ""),
        },
        "scam_intent": scam_result,
        "behavioral": behavioral_result,
        "composite": composite,
    }


# --- WebSocket: live audio input ---
@app.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket):
    """Receives raw PCM16 audio from browser mic, processes through pipeline."""
    await websocket.accept()
    logger.info("Audio WebSocket connected")

    await gemini_session.start_session()

    try:
        while True:
            data = await websocket.receive_bytes()

            # Decode incoming PCM16 audio
            audio = decode_audio_bytes(data, source_format="pcm16")
            chunks = chunk_audio(audio)

            for chunk in chunks:
                result = await process_audio_chunk(chunk, manager.active_scenario or "")
                await manager.broadcast(result)

                # Send back to audio client too
                try:
                    await websocket.send_json({"status": "processed", "composite": result["composite"]})
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info("Audio WebSocket disconnected")
    except Exception as e:
        logger.error(f"Audio WebSocket error: {e}")


# --- WebSocket: dashboard updates ---
@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    """Sends real-time score updates to the React frontend."""
    await manager.connect_dashboard(websocket)
    try:
        while True:
            # Keep connection alive, listen for control messages
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
        manager.disconnect_dashboard(websocket)


# --- User profile endpoints ---
@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user profile."""
    profile = get_user_profile(user["sub"])
    return {**user, **profile}


@app.put("/api/me")
async def update_me(request: Request, user: dict = Depends(get_current_user)):
    """Update current user profile (bank number, trusted contacts)."""
    body = await request.json()
    profile = update_user_profile(user["sub"], body)
    return profile


@app.post("/api/me/trusted-contacts")
async def add_trusted_contact(request: Request, user: dict = Depends(get_current_user)):
    """Add a trusted contact to the user's profile."""
    body = await request.json()
    name = body.get("name", "").strip()
    phone = body.get("phone", "").strip()
    if not name or not phone:
        return JSONResponse(status_code=400, content={"error": "Name and phone are required"})

    profile = get_user_profile(user["sub"])
    contacts = profile.get("trusted_contacts", [])
    contacts.append({"name": name, "phone": phone})
    profile["trusted_contacts"] = contacts
    return {"contacts": contacts}


@app.delete("/api/me/trusted-contacts/{index}")
async def remove_trusted_contact(index: int, user: dict = Depends(get_current_user)):
    """Remove a trusted contact by index."""
    profile = get_user_profile(user["sub"])
    contacts = profile.get("trusted_contacts", [])
    if 0 <= index < len(contacts):
        removed = contacts.pop(index)
        profile["trusted_contacts"] = contacts
        return {"removed": removed, "contacts": contacts}
    return JSONResponse(status_code=404, content={"error": "Contact not found"})


@app.post("/api/notify")
async def notify_trusted_contacts(request: Request, user: dict = Depends(get_current_user)):
    """Send notification to all trusted contacts about a flagged call.

    In mock mode, just logs the notification. Real mode would send SMS.
    """
    body = await request.json()
    risk_level = body.get("risk_level", "high")
    profile = get_user_profile(user["sub"])
    contacts = profile.get("trusted_contacts", [])

    if not contacts:
        return JSONResponse(status_code=400, content={"error": "No trusted contacts configured"})

    notifications = []
    for contact in contacts:
        # In production: send SMS via Twilio/similar
        logger.info(f"NOTIFY {contact['name']} ({contact['phone']}): flagged call, risk={risk_level}")
        notifications.append({
            "contact": contact["name"],
            "phone": contact["phone"],
            "status": "sent" if not AUTH_MOCK else "mock_sent",
        })

    return {"notifications": notifications}


# --- Health check (updated) ---
@app.get("/health")
async def health_updated():
    return {
        "status": "ok",
        "models": {
            "deepfake": {"mock": deepfake_detector.mock_mode},
            "gemini": {"mock": gemini_session.mock_mode},
            "scam_intent": {"mock": scam_classifier.mock_mode},
            "behavioral": {"mock": behavioral_analyzer.mock_mode},
            "auth": {"mock": AUTH_MOCK},
        },
    }


# --- Demo endpoint ---
DEMO_DIR = Path(__file__).parent / "demo"

DEMO_SCENARIOS = {
    "bank_impersonation": {"file": "bank_impersonation.mp3", "hint": "bank_impersonation"},
    "investment_scam": {"file": "investment_scam.mp3", "hint": "investment_scam"},
    "legitimate_bank_call": {"file": "legitimate_bank_call.mp3", "hint": "legitimate_bank_call"},
    "credit_card_scam": {"file": "credit_card_scam.mp3", "hint": "credit_card_scam"},
}


@app.post("/demo/{scenario}")
async def run_demo(scenario: str):
    """Run a demo scenario with optimized pipeline.

    New flow (minimizes API calls):
    1. ElevenLabs STT — transcribe full audio upfront (1 API call)
    2. Gemini — single analysis on full transcript (1 API call)
    3. Deepfake + Behavioral — per-chunk on audio (local, no API calls)

    Broadcasts: demo_start → chunk_updates → demo_end
    """
    if scenario not in DEMO_SCENARIOS:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown scenario. Available: {list(DEMO_SCENARIOS.keys())}"},
        )

    config = DEMO_SCENARIOS[scenario]
    mp3_path = DEMO_DIR / config["file"]

    # Reset all models for clean demo
    gemini_session.reset()
    scam_classifier.reset()
    behavioral_analyzer.reset()
    manager.active_scenario = config["hint"]

    await gemini_session.start_session()

    # Load audio
    if mp3_path.exists():
        with open(mp3_path, "rb") as f:
            raw = f.read()
        audio = decode_audio_bytes(raw, source_format="mp3")
    else:
        logger.warning(f"Demo file {mp3_path} not found — generating synthetic chunks")
        import numpy as np
        audio = np.zeros(TARGET_SAMPLE_RATE * 10, dtype=np.float32)
        raw = b""  # No bytes for STT

    stats = validate_audio(audio)
    logger.info(f"Demo '{scenario}': {stats}")

    # --- Step 1: ElevenLabs STT (full file, 1 API call) ---
    if raw:
        transcript_data = await transcriber.transcribe(raw, num_speakers=2)
    else:
        transcript_data = transcriber._mock_transcribe()
    logger.info(f"STT complete: {len(transcript_data['words'])} words, mock={transcript_data['mock']}")

    # --- Step 2: Gemini analysis on full transcript (1 API call) ---
    analysis = await gemini_session.analyze_transcript(
        transcript_data["text"], config["hint"]
    )
    logger.info(f"Gemini analysis complete: escalation={analysis.get('escalation_score')}, mock={analysis.get('mock')}")

    # --- Step 3: Broadcast demo_start (transcript + audio only, NO analysis yet) ---
    chunks = chunk_audio(audio)

    demo_start_msg = {
        "type": "demo_start",
        "scenario": scenario,
        "audio_url": f"/demo-audio/{config['file']}",
        "transcript": {
            "text": transcript_data["text"],
            "words": transcript_data["words"],
        },
        "total_chunks": len(chunks),
    }
    await manager.broadcast(demo_start_msg)

    # --- Step 4: Progressive analysis reveal across chunks ---
    # Pre-compute flag lists for progressive distribution
    all_tone_flags = analysis.get("tone_flags", [])
    all_phrase_flags = analysis.get("phrase_flags", [])
    all_scam_flags = analysis.get("scam_flags", [])
    final_escalation = analysis.get("escalation_score", 0)
    final_scam_risk = analysis.get("scam_risk", 0)
    final_scam_type = analysis.get("scam_type", "none")
    final_reasoning = analysis.get("reasoning", "")

    chunk_results = []
    for i, chunk in enumerate(chunks):
        progress = (i + 1) / len(chunks)  # e.g. 0.2, 0.4, 0.6, 0.8, 1.0

        # Flags start appearing after ~20% of audio, ramp to full at end
        flag_progress = min(1.0, max(0.0, (progress - 0.15) / 0.85))

        n_tone = int(len(all_tone_flags) * flag_progress)
        n_phrase = int(len(all_phrase_flags) * flag_progress)
        n_scam = int(len(all_scam_flags) * flag_progress)

        progressive_analysis = {
            "tone_flags": all_tone_flags[:n_tone],
            "phrase_flags": all_phrase_flags[:n_phrase],
            "escalation_score": int(final_escalation * progress),
            "reasoning": final_reasoning if i == len(chunks) - 1 else "",
            "scam_risk": int(final_scam_risk * progress),
            "scam_type": final_scam_type if progress >= 0.5 else "none",
            "scam_flags": all_scam_flags[:n_scam],
        }

        # Run deepfake + behavioral in parallel (both local)
        deepfake_task = asyncio.to_thread(deepfake_detector.score, chunk, config["hint"])
        behavioral_task = asyncio.to_thread(behavioral_analyzer.analyze_chunk, chunk, config["hint"])
        deepfake_result, behavioral_result = await asyncio.gather(deepfake_task, behavioral_task)

        # Composite risk uses progressive analysis (so it ramps up naturally)
        comp = composite_risk(deepfake_result["fake"], progressive_analysis)

        chunk_msg = {
            "type": "chunk_update",
            "chunk_index": i,
            "total_chunks": len(chunks),
            "timestamp": time.time(),
            "deepfake_score": deepfake_result["fake"],
            "deepfake": deepfake_result,
            "behavioral": behavioral_result,
            "analysis": progressive_analysis,
            "composite": comp,
        }
        chunk_results.append(chunk_msg)
        await manager.broadcast(chunk_msg)

        # Pace chunks to roughly match audio playback
        if i < len(chunks) - 1:
            await asyncio.sleep(5.0)

    # --- Step 5: Broadcast demo_end ---
    await manager.broadcast({"type": "demo_end", "scenario": scenario})

    manager.active_scenario = None
    return {
        "scenario": scenario,
        "chunks_processed": len(chunks),
        "final_composite": chunk_results[-1]["composite"] if chunk_results else None,
        "audio_url": f"/demo-audio/{config['file']}",
        "transcript": transcript_data["text"],
        "analysis": analysis,
    }


@app.post("/demo/reset")
async def reset_demo():
    """Reset all models to clean state."""
    gemini_session.reset()
    scam_classifier.reset()
    behavioral_analyzer.reset()
    manager.active_scenario = None
    return {"status": "reset"}


# --- Serve demo audio files for browser playback ---
app.mount("/demo-audio", StaticFiles(directory=str(DEMO_DIR)), name="demo-audio")

# --- Serve pre-cached TTS warnings ---
warnings_dir = DEMO_DIR / "warnings"
if warnings_dir.exists():
    app.mount("/warnings", StaticFiles(directory=str(warnings_dir)), name="warnings")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
