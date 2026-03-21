"""wav2vec2 deepfake detection wrapper with mock/real toggle."""

import logging
import os
import time
import random

import numpy as np

logger = logging.getLogger("moneyspeaks.deepfake")

CHECKPOINT_PATH = os.environ.get(
    "DEEPFAKE_CHECKPOINT_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "checkpoints", "deepfake_wav2vec2.pt"),
)


class DeepfakeDetector:
    """Scores audio chunks for synthetic speech artifacts.

    Mock mode: returns controlled scores based on scenario hints.
    Real mode: loads fine-tuned wav2vec2 checkpoint and runs inference.
    """

    def __init__(self):
        self.mock_mode = True
        self.model = None
        self.processor = None
        self._try_load_model()

    def _try_load_model(self):
        if not os.path.exists(CHECKPOINT_PATH):
            logger.warning(f"No checkpoint at {CHECKPOINT_PATH} — running in MOCK mode")
            return

        try:
            import torch
            from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

            logger.info(f"Loading deepfake checkpoint from {CHECKPOINT_PATH}")
            self.processor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-base")

            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(
                "facebook/wav2vec2-base", num_labels=2
            )
            state_dict = torch.load(CHECKPOINT_PATH, map_location="cpu")
            self.model.load_state_dict(state_dict)
            self.model.eval()
            self.mock_mode = False
            logger.info("Deepfake detector loaded in REAL mode")
        except Exception as e:
            logger.error(f"Failed to load model: {e} — falling back to MOCK mode")
            self.mock_mode = True

    def score(self, audio_chunk: np.ndarray, scenario_hint: str = "") -> dict:
        """Score a 2-second audio chunk.

        Returns:
            {"real": float, "fake": float, "mock": bool}
        """
        if self.mock_mode:
            return self._mock_score(scenario_hint)
        return self._real_score(audio_chunk)

    def _mock_score(self, scenario_hint: str) -> dict:
        hint = scenario_hint.lower()
        noise = random.uniform(-0.05, 0.05)

        if "bank" in hint or "impersonation" in hint:
            fake_score = 0.85 + noise
        elif "grandparent" in hint or "scam" in hint:
            fake_score = 0.72 + noise
        elif "real" in hint or "customer" in hint or "legitimate" in hint:
            fake_score = 0.12 + noise
        else:
            fake_score = 0.5 + noise

        fake_score = max(0.0, min(1.0, fake_score))
        return {
            "real": round(1.0 - fake_score, 4),
            "fake": round(fake_score, 4),
            "mock": True,
        }

    def _real_score(self, audio_chunk: np.ndarray) -> dict:
        import torch

        inputs = self.processor(
            audio_chunk, sampling_rate=16000, return_tensors="pt", padding=True
        )
        with torch.no_grad():
            logits = self.model(**inputs).logits
            probs = torch.softmax(logits, dim=-1).squeeze()

        return {
            "real": round(probs[0].item(), 4),
            "fake": round(probs[1].item(), 4),
            "mock": False,
        }
