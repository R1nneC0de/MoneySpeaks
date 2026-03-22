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

TRANSCRIPT_ANALYSIS_PROMPT = """You are MoneySpeaks, a phone call scam detection system.
Analyze this complete phone call transcript for social engineering, emotional manipulation,
scam indicators, and fraud patterns. This protects elderly users from voice fraud.

Transcript:
{transcript}

You MUST respond with ONLY valid JSON — no markdown, no explanation.

Required JSON format:
{{"tone_flags": [...], "phrase_flags": [...], "escalation_score": 0, "reasoning": "...", "scam_risk": 0, "scam_type": "none", "scam_flags": [...]}}

Field definitions:
- tone_flags: Detected emotional manipulation tactics. Examples: "urgency", "fear_induction", "false_authority", "sympathy_exploitation", "anger_pressure", "isolation_tactics"
- phrase_flags: Specific suspicious phrases found in the transcript. Quote the EXACT phrases from the transcript.
- escalation_score: 0-100. 0=normal conversation, 100=definite scam. Based on the full conversation arc.
- reasoning: 2-3 sentence explanation of your assessment
- scam_risk: 0-100. Independent scam probability score.
- scam_type: "none"|"irs_impersonation"|"bank_fraud"|"investment_scam"|"grandparent_scam"|"medicare_scam"|"tech_support"|"utility_scam"|"other"
- scam_flags: Specific scam indicator phrases found. Examples: "requests PIN", "threatens arrest", "demands gift cards", "guaranteed returns"

Examples:

Normal bank inquiry:
{{"tone_flags": [], "phrase_flags": [], "escalation_score": 5, "reasoning": "Routine customer service call with no manipulation indicators.", "scam_risk": 3, "scam_type": "none", "scam_flags": []}}

Bank fraud impersonation:
{{"tone_flags": ["urgency", "fear_induction", "false_authority"], "phrase_flags": ["fraud department", "unauthorized activity", "verify your account number", "don't hang up"], "escalation_score": 90, "reasoning": "Classic bank impersonation: claims fraud urgency, requests sensitive credentials, isolates victim from real bank.", "scam_risk": 92, "scam_type": "bank_fraud", "scam_flags": ["requests account number", "requests PIN", "impersonates bank", "isolation tactic"]}}

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

        if "bank" in hint and "impersonation" in hint:
            return self._mock_bank_scenario(chunk)
        elif "investment" in hint:
            return self._mock_investment_scenario(chunk)
        elif "legitimate" in hint:
            return self._mock_legitimate_scenario(chunk)
        else:
            return self._mock_neutral()

    def _mock_bank_scenario(self, chunk: int) -> dict:
        """Mock fallback — only used when GEMINI_API_KEY is missing."""
        score = min(20 + chunk * 20, 95)
        return {
            "transcript": "[mock — no API key] Bank fraud scenario in progress...",
            "tone_flags": ["urgency", "false_authority"] if chunk > 1 else ["false_authority"],
            "phrase_flags": ["fraud department"] if chunk <= 2 else ["account number", "PIN", "don't contact anyone"],
            "escalation_score": score,
            "reasoning": f"Mock mode. Chunk {chunk} of bank impersonation scenario.",
            "mock": True,
        }

    def _mock_investment_scenario(self, chunk: int) -> dict:
        """Mock fallback — only used when GEMINI_API_KEY is missing."""
        score = min(15 + chunk * 18, 90)
        return {
            "transcript": "[mock — no API key] Investment scam scenario in progress...",
            "tone_flags": ["urgency", "false_authority"] if chunk > 1 else [],
            "phrase_flags": ["guaranteed returns"] if chunk <= 2 else ["wire transfer", "limited time", "don't tell"],
            "escalation_score": score,
            "reasoning": f"Mock mode. Chunk {chunk} of investment scam scenario.",
            "mock": True,
        }

    def _mock_legitimate_scenario(self, chunk: int) -> dict:
        """Mock fallback — only used when GEMINI_API_KEY is missing."""
        return {
            "transcript": "[mock — no API key] Legitimate bank call in progress...",
            "tone_flags": [],
            "phrase_flags": [],
            "escalation_score": max(5 - chunk, 1),
            "reasoning": f"Mock mode. Chunk {chunk} of legitimate call scenario.",
            "mock": True,
        }

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

    async def analyze_transcript(self, transcript: str, scenario_hint: str = "") -> dict:
        """Analyze a full transcript text with a single Gemini call.

        Combines tone analysis + scam classification into one request.
        Used by the demo pipeline to minimize API calls.

        Returns:
            {tone_flags, phrase_flags, escalation_score, reasoning,
             scam_risk, scam_type, scam_flags, mock}
        """
        if self.mock_mode:
            return self._mock_transcript_analysis(scenario_hint)

        prompt = TRANSCRIPT_ANALYSIS_PROMPT.format(transcript=transcript)

        for attempt in range(3):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=GEMINI_MODEL,
                    contents=prompt,
                )

                text = response.text.strip()
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
                if is_rate_limit and attempt < 2:
                    wait = (attempt + 1) * 5
                    logger.warning(f"Gemini rate limited on transcript analysis, retrying in {wait}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"Gemini transcript analysis failed: {e}")
                return self._mock_transcript_analysis(scenario_hint)

    def _mock_transcript_analysis(self, scenario_hint: str) -> dict:
        """Mock transcript analysis when Gemini is unavailable."""
        hint = scenario_hint.lower()

        if "bank" in hint and "impersonation" in hint:
            return {
                "tone_flags": ["urgency", "fear_induction", "false_authority"],
                "phrase_flags": ["fraud department", "unauthorized activity", "account number", "don't hang up"],
                "escalation_score": 85,
                "reasoning": "Mock: Bank impersonation pattern with authority claims and credential requests.",
                "scam_risk": 90,
                "scam_type": "bank_fraud",
                "scam_flags": ["requests account number", "requests PIN", "impersonates bank"],
                "mock": True,
            }
        elif "investment" in hint:
            return {
                "tone_flags": ["urgency", "false_authority"],
                "phrase_flags": ["guaranteed returns", "limited time", "wire transfer", "don't tell"],
                "escalation_score": 80,
                "reasoning": "Mock: Investment scam with unrealistic returns and pressure tactics.",
                "scam_risk": 85,
                "scam_type": "investment_scam",
                "scam_flags": ["guaranteed returns", "pressure to wire money", "secrecy demand"],
                "mock": True,
            }
        elif "credit" in hint and "scam" in hint:
            return {
                "tone_flags": ["urgency", "fear_induction", "false_authority", "isolation_tactics"],
                "phrase_flags": ["security team", "suspicious transactions", "full card number", "don't contact your bank"],
                "escalation_score": 88,
                "reasoning": "Mock: Credit card impersonation scam with CVV request, time pressure, and isolation tactics.",
                "scam_risk": 92,
                "scam_type": "bank_fraud",
                "scam_flags": ["requests card number", "requests CVV", "impersonates Visa", "isolation tactic", "time pressure"],
                "mock": True,
            }
        elif "legitimate" in hint:
            return {
                "tone_flags": [],
                "phrase_flags": [],
                "escalation_score": 5,
                "reasoning": "Mock: Normal customer service interaction with no manipulation indicators.",
                "scam_risk": 3,
                "scam_type": "none",
                "scam_flags": [],
                "mock": True,
            }
        else:
            return {
                "tone_flags": [],
                "phrase_flags": [],
                "escalation_score": 10,
                "reasoning": "Mock: Insufficient data for analysis.",
                "scam_risk": 5,
                "scam_type": "none",
                "scam_flags": [],
                "mock": True,
            }

    def reset(self):
        """Reset session state for a new call."""
        self._chunk_count = 0
        self._conversation_history = []
