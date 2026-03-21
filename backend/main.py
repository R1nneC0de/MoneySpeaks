"""MoneySpeaks — FastAPI backend with WebSocket audio pipeline."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
from backend.models.deepfake import DeepfakeDetector
from backend.models.gemini_live import GeminiLiveSession
from backend.models.composite import composite_risk
from backend.classifier.scam_intent import ScamIntentClassifier
from backend.classifier.behavioral import BehavioralAnalyzer

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


# --- Health check ---
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "models": {
            "deepfake": {"mock": deepfake_detector.mock_mode},
            "gemini": {"mock": gemini_session.mock_mode},
            "scam_intent": {"mock": scam_classifier.mock_mode},
            "behavioral": {"mock": behavioral_analyzer.mock_mode},
        },
    }


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

    # Run scam intent classifier (rate-limited internally)
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


# --- Demo endpoint ---
DEMO_DIR = Path(__file__).parent / "demo"

DEMO_SCENARIOS = {
    "bank_impersonation": {"file": "bank_impersonation.mp3", "hint": "bank_impersonation"},
    "grandparent_scam": {"file": "grandparent_scam.mp3", "hint": "grandparent_scam"},
    "real_customer": {"file": "real_customer.mp3", "hint": "real_customer"},
}


@app.post("/demo/{scenario}")
async def run_demo(scenario: str):
    """Run a demo scenario through the live pipeline.

    Reads the MP3 file, chunks it, and processes through the same pipeline
    as live audio — no pre-computed scores.
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

    # Check if MP3 file exists — if not, use mock mode with synthetic chunks
    if mp3_path.exists():
        with open(mp3_path, "rb") as f:
            raw = f.read()
        audio = decode_audio_bytes(raw, source_format="mp3")
    else:
        logger.warning(f"Demo file {mp3_path} not found — generating synthetic chunks")
        # Generate 10 seconds of silence (5 chunks) for mock pipeline
        import numpy as np
        audio = np.zeros(TARGET_SAMPLE_RATE * 10, dtype=np.float32)

    stats = validate_audio(audio)
    logger.info(f"Demo '{scenario}': {stats}")

    chunks = chunk_audio(audio)
    results = []

    # Process each chunk with a small delay to simulate real-time
    for i, chunk in enumerate(chunks):
        result = await process_audio_chunk(chunk, config["hint"])
        result["demo_scenario"] = scenario
        result["chunk_index"] = i
        result["total_chunks"] = len(chunks)
        results.append(result)

        # Broadcast to dashboard clients
        await manager.broadcast(result)

        # Simulate real-time pacing (0.5s between chunks for demo speed)
        if i < len(chunks) - 1:
            await asyncio.sleep(0.5)

    manager.active_scenario = None
    return {
        "scenario": scenario,
        "chunks_processed": len(chunks),
        "final_composite": results[-1]["composite"] if results else None,
        "results": results,
    }


@app.post("/demo/reset")
async def reset_demo():
    """Reset all models to clean state."""
    gemini_session.reset()
    scam_classifier.reset()
    behavioral_analyzer.reset()
    manager.active_scenario = None
    return {"status": "reset"}


# --- Serve pre-cached TTS warnings ---
warnings_dir = DEMO_DIR / "warnings"
if warnings_dir.exists():
    app.mount("/warnings", StaticFiles(directory=str(warnings_dir)), name="warnings")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
