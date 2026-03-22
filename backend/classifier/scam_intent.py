"""Zero-shot LLM-based scam intent classifier.

Runs on accumulated transcript every 15-30 seconds (not every 2s chunk).
Real mode: uses Gemini text API.
Mock mode: keyword-based heuristic scoring.
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("moneyspeaks.scam_intent")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

CLASSIFICATION_PROMPT = """You are a scam detection classifier. Analyze this phone call transcript for scam indicators.

Transcript (last 60 seconds):
{transcript}

Classify this call. Respond with ONLY valid JSON:
{{"risk": 0-100, "flags": ["list of specific suspicious indicators"], "scam_type": "none|irs_impersonation|bank_fraud|grandparent_scam|medicare_scam|tech_support|utility_scam|other", "reasoning": "brief explanation"}}

Be conservative — only flag high-confidence indicators. Normal business calls should score below 20."""

# Scam keyword patterns for mock mode
SCAM_PATTERNS = {
    "irs_impersonation": ["irs", "tax", "warrant", "arrest", "back taxes"],
    "bank_fraud": ["account", "verify", "pin", "unauthorized", "fraud department", "suspicious activity"],
    "grandparent_scam": ["grandma", "grandpa", "bail", "accident", "don't tell", "gift card"],
    "medicare_scam": ["medicare", "insurance", "coverage", "benefits", "social security number"],
    "tech_support": ["computer", "virus", "microsoft", "remote access", "infected"],
    "utility_scam": ["power", "shut off", "disconnect", "overdue", "utility"],
}

URGENCY_PHRASES = [
    "act now", "immediately", "right away", "don't hang up", "time sensitive",
    "last chance", "expire", "limited time", "urgent", "emergency",
]

ISOLATION_PHRASES = [
    "don't tell", "keep this between us", "don't call", "don't contact",
    "this is confidential", "secret",
]


class ScamIntentClassifier:
    """Classifies scam intent from rolling transcript."""

    def __init__(self):
        self.mock_mode = not GEMINI_API_KEY
        self._last_run = 0
        self._run_interval = 20  # seconds between classifications
        self._transcript_buffer = ""

        if self.mock_mode:
            logger.warning("No API keys — ScamIntentClassifier in MOCK mode")

    def add_transcript(self, text: str):
        """Append new transcript text to the rolling buffer."""
        if text and text != "...":
            self._transcript_buffer += " " + text
            # Keep last ~500 words (roughly 60s of speech)
            words = self._transcript_buffer.split()
            if len(words) > 500:
                self._transcript_buffer = " ".join(words[-500:])

    def should_run(self) -> bool:
        """Check if enough time has passed since last classification."""
        return time.time() - self._last_run >= self._run_interval

    async def classify(self) -> Optional[dict]:
        """Run classification on accumulated transcript.

        Returns None if not enough time has passed or no transcript.
        """
        if not self.should_run():
            return None
        if not self._transcript_buffer.strip():
            return None

        self._last_run = time.time()

        if self.mock_mode:
            return self._mock_classify()
        return await self._real_classify()

    def _mock_classify(self) -> dict:
        text = self._transcript_buffer.lower()
        max_risk = 0
        all_flags = []
        detected_type = "none"

        for scam_type, keywords in SCAM_PATTERNS.items():
            matches = [kw for kw in keywords if kw in text]
            if matches:
                risk = min(len(matches) * 25, 90)
                if risk > max_risk:
                    max_risk = risk
                    detected_type = scam_type
                all_flags.extend(matches)

        # Check urgency and isolation phrases
        urgency = [p for p in URGENCY_PHRASES if p in text]
        isolation = [p for p in ISOLATION_PHRASES if p in text]
        all_flags.extend(urgency)
        all_flags.extend(isolation)

        if urgency:
            max_risk = min(max_risk + 15, 100)
        if isolation:
            max_risk = min(max_risk + 20, 100)

        return {
            "risk": max_risk,
            "flags": list(set(all_flags)),
            "scam_type": detected_type,
            "reasoning": f"Mock classification: {len(all_flags)} indicators detected.",
            "mock": True,
        }

    async def _real_classify(self) -> dict:
        prompt = CLASSIFICATION_PROMPT.format(transcript=self._transcript_buffer[-2000:])

        try:
            return await self._classify_with_gemini(prompt)
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self._mock_classify()

    async def _classify_with_gemini(self, prompt: str) -> dict:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        result = json.loads(text)
        result["mock"] = False
        return result

    def reset(self):
        """Reset for a new call."""
        self._transcript_buffer = ""
        self._last_run = 0
