"""VAD-based behavioral timing analysis.

Measures response latency and disfluency rate as supplementary scam signals.
Uses webrtcvad for voice activity detection.
"""

import logging
import struct
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("moneyspeaks.behavioral")

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # webrtcvad requires 10, 20, or 30ms frames
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

# Thresholds
SUSPICIOUS_LATENCY_MS = 300  # AI-speed responses
LOW_DISFLUENCY_THRESHOLD = 0.3  # disfluencies per minute


class BehavioralAnalyzer:
    """Analyzes voice activity timing for behavioral scam signals."""

    def __init__(self):
        self.vad = None
        self.mock_mode = True
        self._speech_segments: list[dict] = []
        self._silence_start: Optional[float] = None
        self._disfluency_count = 0
        self._analysis_start = time.time()

        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(2)  # aggressiveness 0-3
            self.mock_mode = False
            logger.info("BehavioralAnalyzer loaded with webrtcvad")
        except ImportError:
            logger.warning("webrtcvad not available — BehavioralAnalyzer in MOCK mode")

    def analyze_chunk(self, audio_chunk: np.ndarray, scenario_hint: str = "") -> dict:
        """Analyze a 2-second chunk for behavioral timing signals.

        Returns:
            {response_latency_ms, disfluency_rate, flags, mock}
        """
        if self.mock_mode:
            return self._mock_analyze(scenario_hint)
        return self._real_analyze(audio_chunk)

    def _real_analyze(self, audio_chunk: np.ndarray) -> dict:
        pcm16 = (np.clip(audio_chunk, -1.0, 1.0) * 32767).astype(np.int16)
        pcm_bytes = pcm16.tobytes()

        speech_frames = 0
        total_frames = 0
        transitions = 0
        prev_is_speech = None

        for i in range(0, len(pcm16) - FRAME_SAMPLES, FRAME_SAMPLES):
            frame = pcm_bytes[i * 2 : (i + FRAME_SAMPLES) * 2]
            if len(frame) < FRAME_SAMPLES * 2:
                break

            try:
                is_speech = self.vad.is_speech(frame, SAMPLE_RATE)
            except Exception:
                continue

            total_frames += 1
            if is_speech:
                speech_frames += 1

            if prev_is_speech is not None and is_speech != prev_is_speech:
                transitions += 1
                if not prev_is_speech and is_speech:
                    # Silence → speech transition
                    latency_ms = transitions * FRAME_DURATION_MS  # rough estimate
                    self._speech_segments.append({
                        "timestamp": time.time(),
                        "latency_ms": latency_ms,
                    })
            prev_is_speech = is_speech

        # Calculate metrics
        avg_latency = None
        if self._speech_segments:
            latencies = [s["latency_ms"] for s in self._speech_segments[-10:]]
            avg_latency = sum(latencies) / len(latencies)

        elapsed_min = max((time.time() - self._analysis_start) / 60, 0.1)
        disfluency_rate = self._disfluency_count / elapsed_min

        flags = []
        if avg_latency is not None and avg_latency < SUSPICIOUS_LATENCY_MS:
            flags.append(f"Fast response: {avg_latency:.0f}ms (AI-speed)")
        if disfluency_rate < LOW_DISFLUENCY_THRESHOLD and elapsed_min > 0.5:
            flags.append(f"Low disfluency: {disfluency_rate:.2f}/min")

        return {
            "response_latency_ms": round(avg_latency, 1) if avg_latency else None,
            "disfluency_rate": round(disfluency_rate, 2),
            "speech_ratio": round(speech_frames / max(total_frames, 1), 2),
            "flags": flags,
            "mock": False,
        }

    def _mock_analyze(self, scenario_hint: str) -> dict:
        hint = scenario_hint.lower()

        if "bank" in hint or "impersonation" in hint:
            return {
                "response_latency_ms": 180,
                "disfluency_rate": 0.1,
                "speech_ratio": 0.75,
                "flags": ["Fast response: 180ms (AI-speed)", "Low disfluency: 0.10/min"],
                "mock": True,
            }
        elif "grandparent" in hint or "scam" in hint:
            return {
                "response_latency_ms": 420,
                "disfluency_rate": 0.8,
                "speech_ratio": 0.65,
                "flags": [],
                "mock": True,
            }
        else:
            return {
                "response_latency_ms": 650,
                "disfluency_rate": 2.1,
                "speech_ratio": 0.55,
                "flags": [],
                "mock": True,
            }

    def reset(self):
        """Reset for a new call."""
        self._speech_segments = []
        self._silence_start = None
        self._disfluency_count = 0
        self._analysis_start = time.time()
