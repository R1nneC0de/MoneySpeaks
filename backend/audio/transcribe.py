"""ElevenLabs Speech-to-Text wrapper with word-level timestamps and diarization.

Uses the Scribe v1 model for accurate transcription with speaker identification.
Mock mode returns synthetic transcript data when ELEVENLABS_API_KEY is missing.
"""

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger("moneyspeaks.transcribe")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")


class ElevenLabsTranscriber:
    """Transcribes audio files with word timestamps and speaker diarization."""

    def __init__(self):
        self.mock_mode = not bool(ELEVENLABS_API_KEY)
        if self.mock_mode:
            logger.warning("No ELEVENLABS_API_KEY — ElevenLabsTranscriber in MOCK mode")
        else:
            logger.info("ElevenLabsTranscriber initialized in REAL mode")

    async def transcribe(self, audio_bytes: bytes, num_speakers: int = 2) -> dict:
        """Transcribe audio bytes with diarization and word timestamps.

        Args:
            audio_bytes: Raw audio file bytes (MP3, WAV, etc.)
            num_speakers: Expected number of speakers for diarization.

        Returns:
            {
                "text": str,           # Full transcript text
                "words": [             # Word-level details
                    {"text": str, "start": float, "end": float, "speaker_id": str},
                    ...
                ],
                "mock": bool
            }
        """
        if self.mock_mode:
            return self._mock_transcribe()
        return await self._real_transcribe(audio_bytes, num_speakers)

    async def _real_transcribe(self, audio_bytes: bytes, num_speakers: int) -> dict:
        """Call ElevenLabs Scribe v1 STT API."""
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        try:
            result = await asyncio.to_thread(
                client.speech_to_text.convert,
                model_id="scribe_v1",
                file=audio_bytes,
                language_code="en",
                num_speakers=num_speakers,
                timestamps_granularity="word",
                diarize=True,
            )

            # Filter to word entries only (skip spacing/punctuation type entries)
            words = []
            for w in result.words:
                if w.type == "word":
                    words.append({
                        "text": w.text,
                        "start": w.start,
                        "end": w.end,
                        "speaker_id": w.speaker_id or "speaker_0",
                    })

            logger.info(f"ElevenLabs STT: {len(words)} words, text length {len(result.text)}")
            return {
                "text": result.text,
                "words": words,
                "mock": False,
            }

        except Exception as e:
            logger.error(f"ElevenLabs STT failed: {e} — falling back to mock")
            return self._mock_transcribe()

    def _mock_transcribe(self) -> dict:
        """Return a mock transcript for when no API key is available."""
        mock_words = [
            {"text": "Hello,", "start": 0.5, "end": 0.8, "speaker_id": "speaker_0"},
            {"text": "this", "start": 0.9, "end": 1.0, "speaker_id": "speaker_0"},
            {"text": "is", "start": 1.05, "end": 1.15, "speaker_id": "speaker_0"},
            {"text": "the", "start": 1.2, "end": 1.3, "speaker_id": "speaker_0"},
            {"text": "fraud", "start": 1.35, "end": 1.6, "speaker_id": "speaker_0"},
            {"text": "department.", "start": 1.65, "end": 2.1, "speaker_id": "speaker_0"},
            {"text": "We've", "start": 2.3, "end": 2.5, "speaker_id": "speaker_0"},
            {"text": "detected", "start": 2.55, "end": 2.9, "speaker_id": "speaker_0"},
            {"text": "unauthorized", "start": 2.95, "end": 3.5, "speaker_id": "speaker_0"},
            {"text": "activity", "start": 3.55, "end": 3.9, "speaker_id": "speaker_0"},
            {"text": "on", "start": 3.95, "end": 4.05, "speaker_id": "speaker_0"},
            {"text": "your", "start": 4.1, "end": 4.25, "speaker_id": "speaker_0"},
            {"text": "account.", "start": 4.3, "end": 4.7, "speaker_id": "speaker_0"},
            {"text": "Oh", "start": 5.0, "end": 5.2, "speaker_id": "speaker_1"},
            {"text": "my,", "start": 5.25, "end": 5.45, "speaker_id": "speaker_1"},
            {"text": "what", "start": 5.5, "end": 5.65, "speaker_id": "speaker_1"},
            {"text": "kind", "start": 5.7, "end": 5.85, "speaker_id": "speaker_1"},
            {"text": "of", "start": 5.9, "end": 5.95, "speaker_id": "speaker_1"},
            {"text": "activity?", "start": 6.0, "end": 6.4, "speaker_id": "speaker_1"},
            {"text": "I", "start": 6.6, "end": 6.7, "speaker_id": "speaker_1"},
            {"text": "need", "start": 6.75, "end": 6.95, "speaker_id": "speaker_1"},
            {"text": "your", "start": 7.0, "end": 7.15, "speaker_id": "speaker_0"},
            {"text": "account", "start": 7.2, "end": 7.5, "speaker_id": "speaker_0"},
            {"text": "number", "start": 7.55, "end": 7.8, "speaker_id": "speaker_0"},
            {"text": "and", "start": 7.85, "end": 7.95, "speaker_id": "speaker_0"},
            {"text": "PIN", "start": 8.0, "end": 8.2, "speaker_id": "speaker_0"},
            {"text": "to", "start": 8.25, "end": 8.35, "speaker_id": "speaker_0"},
            {"text": "verify.", "start": 8.4, "end": 8.7, "speaker_id": "speaker_0"},
            {"text": "Don't", "start": 9.0, "end": 9.2, "speaker_id": "speaker_0"},
            {"text": "hang", "start": 9.25, "end": 9.4, "speaker_id": "speaker_0"},
            {"text": "up", "start": 9.45, "end": 9.55, "speaker_id": "speaker_0"},
            {"text": "or", "start": 9.6, "end": 9.7, "speaker_id": "speaker_0"},
            {"text": "call", "start": 9.75, "end": 9.9, "speaker_id": "speaker_0"},
            {"text": "anyone.", "start": 9.95, "end": 10.3, "speaker_id": "speaker_0"},
        ]
        mock_text = " ".join(w["text"] for w in mock_words)
        return {
            "text": mock_text,
            "words": mock_words,
            "mock": True,
        }
