"""Gemini Live session manager for affective tone analysis.

Real mode: persistent WebSocket to Gemini 2.5 Flash with native audio input.
Mock mode: returns hardcoded analysis when GEMINI_API_KEY is missing.
"""

import asyncio
import base64
import json
import logging
import os
import random
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("moneyspeaks.gemini_live")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are MoneySpeaks, a real-time phone call scam detection system.
You analyze audio from phone calls to detect social engineering, emotional manipulation,
and scam indicators. You protect elderly users from voice fraud.

After each audio segment, you MUST respond with ONLY valid JSON — no markdown, no explanation.

Required JSON format:
{"transcript": "...", "tone_flags": [...], "phrase_flags": [...], "escalation_score": 0, "reasoning": "..."}

Field definitions:
- transcript: Best-effort transcription of what was said in this audio segment
- tone_flags: List of detected emotional manipulation tactics. Examples: "urgency", "fear_induction", "false_authority", "sympathy_exploitation", "anger_pressure", "isolation_tactics"
- phrase_flags: List of specific suspicious phrases detected. Examples: "act now", "don't tell anyone", "verify your account", "you owe", "warrant for your arrest", "gift cards"
- escalation_score: 0-100 integer. 0=normal conversation, 100=definite scam. Score based on cumulative evidence across the conversation.
- reasoning: 1-2 sentence explanation of your assessment

Examples:

Audio: Normal greeting, someone asking about business hours
{"transcript": "Hi, I was wondering what time you close today?", "tone_flags": [], "phrase_flags": [], "escalation_score": 5, "reasoning": "Normal conversational inquiry with no suspicious indicators."}

Audio: Caller claiming to be IRS demanding immediate payment
{"transcript": "This is the IRS. You owe back taxes and a warrant will be issued for your arrest if you don't pay now with gift cards.", "tone_flags": ["urgency", "fear_induction", "false_authority"], "phrase_flags": ["you owe", "warrant for your arrest", "gift cards", "pay now"], "escalation_score": 95, "reasoning": "Classic IRS impersonation scam with multiple high-confidence indicators: authority claim, arrest threat, gift card payment demand."}

Audio: Emotional caller claiming to be a grandchild in trouble
{"transcript": "Grandma, please don't tell mom and dad. I'm in jail and I need bail money right away.", "tone_flags": ["sympathy_exploitation", "urgency", "isolation_tactics"], "phrase_flags": ["don't tell", "I need money", "right away"], "escalation_score": 85, "reasoning": "Grandparent scam pattern: emotional distress, secrecy demand, urgent money request."}

CRITICAL: Always respond with valid JSON only. No other text."""


class GeminiLiveSession:
    """Manages a persistent Gemini Live session for affective analysis."""

    def __init__(self):
        self.mock_mode = not bool(GEMINI_API_KEY)
        self.session = None
        self._chunk_count = 0
        self._conversation_history: list[dict] = []

        if self.mock_mode:
            logger.warning("No GEMINI_API_KEY — running Gemini Live in MOCK mode")
        else:
            logger.info("Gemini Live session initialized in REAL mode")

    async def start_session(self):
        """Start a persistent Gemini Live session."""
        if self.mock_mode:
            return

        try:
            from google import genai

            self.client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Gemini Live session started")
        except Exception as e:
            logger.error(f"Failed to start Gemini session: {e} — falling back to MOCK")
            self.mock_mode = True

    async def analyze_chunk(self, audio_chunk: np.ndarray, scenario_hint: str = "") -> dict:
        """Analyze a 2-second audio chunk.

        Returns:
            {transcript, tone_flags, phrase_flags, escalation_score, reasoning, mock}
        """
        self._chunk_count += 1

        if self.mock_mode:
            return self._mock_analyze(scenario_hint)
        return await self._real_analyze(audio_chunk, scenario_hint)

    def _mock_analyze(self, scenario_hint: str) -> dict:
        hint = scenario_hint.lower()
        chunk = self._chunk_count

        if "bank" in hint or "impersonation" in hint:
            return self._mock_bank_scenario(chunk)
        elif "grandparent" in hint or "scam" in hint:
            return self._mock_grandparent_scenario(chunk)
        elif "real" in hint or "customer" in hint or "legitimate" in hint:
            return self._mock_real_scenario(chunk)
        else:
            return self._mock_neutral()

    def _mock_bank_scenario(self, chunk: int) -> dict:
        phases = [
            {
                "transcript": "Hello, this is the fraud department at your bank. We've detected unauthorized activity on your account. Oh my goodness, what kind of activity?",
                "tone_flags": ["false_authority"],
                "phrase_flags": ["fraud department", "unauthorized activity"],
                "escalation_score": 35,
                "reasoning": "Caller claims bank authority and reports urgent account activity. Monitoring for further indicators.",
            },
            {
                "transcript": "Someone is attempting to transfer funds from your savings. We need to verify your identity immediately. Oh no, what do I need to do?",
                "tone_flags": ["urgency", "false_authority"],
                "phrase_flags": ["verify your identity", "transfer funds"],
                "escalation_score": 60,
                "reasoning": "Urgency combined with identity verification request. Victim is complying. Escalating risk.",
            },
            {
                "transcript": "I'll need your account number and PIN to secure your funds. Okay, let me find my card. Please hurry, the transfer is still in progress.",
                "tone_flags": ["urgency", "fear_induction"],
                "phrase_flags": ["account number", "PIN", "secure your funds"],
                "escalation_score": 85,
                "reasoning": "Requesting sensitive credentials over phone with time pressure. High-confidence scam pattern.",
            },
            {
                "transcript": "Don't hang up or contact anyone else. This is time-sensitive and we need to keep this line open to protect your savings.",
                "tone_flags": ["urgency", "fear_induction", "isolation_tactics"],
                "phrase_flags": ["don't contact anyone", "time-sensitive"],
                "escalation_score": 95,
                "reasoning": "Maximum risk: isolation demand, financial threat, urgency. Classic bank fraud script.",
            },
        ]
        idx = min(chunk - 1, len(phases) - 1)
        return {**phases[idx], "mock": True}

    def _mock_grandparent_scenario(self, chunk: int) -> dict:
        phases = [
            {
                "transcript": "Grandma? It's me, I'm in trouble. Who is this? Tommy, is that you? You sound different.",
                "tone_flags": ["sympathy_exploitation"],
                "phrase_flags": [],
                "escalation_score": 25,
                "reasoning": "Emotional opening with identity claim. Victim questioning voice difference is notable.",
            },
            {
                "transcript": "Yeah it's me, I hurt my nose in the accident. I'm at the police station. Oh my Lord, are you okay?",
                "tone_flags": ["sympathy_exploitation", "isolation_tactics"],
                "phrase_flags": ["accident", "police station"],
                "escalation_score": 55,
                "reasoning": "Excuse for voice mismatch plus distress scenario. Classic grandparent scam setup.",
            },
            {
                "transcript": "I need bail money right away. Can you get some gift cards? I need two thousand dollars. And please don't tell Mom and Dad.",
                "tone_flags": ["urgency", "sympathy_exploitation", "isolation_tactics"],
                "phrase_flags": ["gift cards", "don't tell", "right away", "bail money"],
                "escalation_score": 90,
                "reasoning": "Gift card payment request plus secrecy demand. Definitive scam indicators.",
            },
        ]
        idx = min(chunk - 1, len(phases) - 1)
        return {**phases[idx], "mock": True}

    def _mock_real_scenario(self, chunk: int) -> dict:
        phases = [
            {
                "transcript": "Hi, I'm calling about the appointment for next Tuesday at 2pm. Of course, let me pull that up. Yes, Tuesday the 25th at 2 o'clock.",
                "tone_flags": [],
                "phrase_flags": [],
                "escalation_score": 3,
                "reasoning": "Normal conversational tone between caller and receptionist. No suspicious indicators.",
            },
            {
                "transcript": "I just wanted to confirm and let you know I might be a few minutes late. Traffic has been terrible. That's no problem at all, we'll be ready for you.",
                "tone_flags": [],
                "phrase_flags": [],
                "escalation_score": 2,
                "reasoning": "Polite, low-pressure exchange. Routine scheduling conversation.",
            },
            {
                "transcript": "Great, thank you so much. I'll see you then! Sounds good, have a wonderful day!",
                "tone_flags": [],
                "phrase_flags": [],
                "escalation_score": 1,
                "reasoning": "Normal call conclusion. No risk detected.",
            },
        ]
        idx = min(chunk - 1, len(phases) - 1)
        return {**phases[idx], "mock": True}

    def _mock_neutral(self) -> dict:
        return {
            "transcript": "...",
            "tone_flags": [],
            "phrase_flags": [],
            "escalation_score": 10,
            "reasoning": "Insufficient audio for analysis.",
            "mock": True,
        }

    async def _real_analyze(self, audio_chunk: np.ndarray, scenario_hint: str = "") -> dict:
        from google.genai import types

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Convert float32 audio to raw PCM16 bytes
                pcm16 = (np.clip(audio_chunk, -1.0, 1.0) * 32767).astype(np.int16)
                audio_part = types.Part.from_bytes(
                    data=pcm16.tobytes(),
                    mime_type="audio/L16;rate=16000",
                )

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=GEMINI_MODEL,
                    contents=[
                        SYSTEM_PROMPT,
                        audio_part,
                        "Analyze this audio segment. Respond with JSON only.",
                    ],
                )

                text = response.text.strip()
                # Try to extract JSON from response
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                    text = text.strip()

                result = json.loads(text)
                result["mock"] = False
                return result

            except Exception as e:
                error_str = str(e).lower()
                is_validation = "validation" in error_str or "pydantic" in error_str
                is_rate_limit = not is_validation and (
                    "429" in str(e) or "rate" in error_str or "quota" in error_str or "resource" in error_str
                )
                if is_rate_limit and attempt < max_retries - 1:
                    wait = (attempt + 1) * 5  # 5s, 10s backoff
                    logger.warning(f"Gemini rate limited, retrying in {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"Gemini analysis failed: {e}")
                # Fall back to mock with correct scenario hint
                return self._mock_analyze(scenario_hint)

    def reset(self):
        """Reset session state for a new call."""
        self._chunk_count = 0
        self._conversation_history = []
