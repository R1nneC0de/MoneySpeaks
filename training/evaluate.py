"""Evaluate fine-tuned wav2vec2 deepfake detector.

Computes Equal Error Rate (EER) on held-out test sets:
  - ASVspoof 5 eval partition
  - In-the-Wild dataset
  - ElevenLabs held-out voices (9-12)

Usage:
    python training/evaluate.py --checkpoint training/outputs/checkpoints/deepfake_wav2vec2.pt
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("moneyspeaks.evaluate")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "datasets" / "data"


def compute_eer(genuine_scores, spoof_scores):
    """Compute Equal Error Rate.

    Args:
        genuine_scores: array of scores for genuine (real) samples
        spoof_scores: array of scores for spoof (fake) samples

    Returns:
        eer: Equal Error Rate
        threshold: EER threshold
    """
    all_scores = np.concatenate([genuine_scores, spoof_scores])
    all_labels = np.concatenate([
        np.ones(len(genuine_scores)),
        np.zeros(len(spoof_scores)),
    ])

    thresholds = np.linspace(0, 1, 1000)
    far_list = []  # False Acceptance Rate
    frr_list = []  # False Rejection Rate

    for thresh in thresholds:
        # FAR: spoof samples accepted as genuine (score < thresh)
        far = np.mean(spoof_scores < thresh)
        # FRR: genuine samples rejected (score >= thresh)
        frr = np.mean(genuine_scores >= thresh)
        far_list.append(far)
        frr_list.append(frr)

    far_arr = np.array(far_list)
    frr_arr = np.array(frr_list)

    # Find EER: where FAR ≈ FRR
    diff = np.abs(far_arr - frr_arr)
    eer_idx = np.argmin(diff)
    eer = (far_arr[eer_idx] + frr_arr[eer_idx]) / 2
    threshold = thresholds[eer_idx]

    return eer, threshold


def evaluate_checkpoint(checkpoint_path: str):
    """Run full evaluation suite on a checkpoint."""
    try:
        import torch
        import torchaudio
        from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
    except ImportError:
        logger.error("Missing dependencies. Install torch, torchaudio, transformers.")
        return

    ckpt = Path(checkpoint_path)
    if not ckpt.exists():
        logger.warning(f"Checkpoint not found: {ckpt}")
        logger.info("Running mock evaluation with random scores...")
        run_mock_evaluation()
        return

    logger.info(f"Loading checkpoint: {ckpt}")
    processor = Wav2Vec2FeatureExtractor.from_pretrained("facebook/wav2vec2-base")
    model = Wav2Vec2ForSequenceClassification.from_pretrained(
        "facebook/wav2vec2-base", num_labels=2,
    )
    model.load_state_dict(torch.load(ckpt, map_location="cpu"))
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    # Evaluate on each test set
    test_sets = {
        "ASVspoof5 Eval": {
            "genuine": DATA_DIR / "asvspoof5" / "eval" / "bonafide",
            "spoof": DATA_DIR / "asvspoof5" / "eval" / "spoof",
        },
        "ElevenLabs Held-out": {
            "genuine": None,  # No genuine in EL set
            "spoof": DATA_DIR / "elevenlabs" / "test",
        },
    }

    results = {}

    for name, dirs in test_sets.items():
        logger.info(f"\n--- Evaluating: {name} ---")

        genuine_scores = []
        spoof_scores = []

        for label, data_dir in [("genuine", dirs.get("genuine")), ("spoof", dirs.get("spoof"))]:
            if data_dir is None or not data_dir.exists():
                logger.warning(f"  {label} directory not found: {data_dir}")
                continue

            audio_files = list(data_dir.glob("*.wav")) + list(data_dir.glob("*.mp3")) + list(data_dir.glob("*.flac"))
            logger.info(f"  {label}: {len(audio_files)} files")

            for audio_file in audio_files:
                try:
                    waveform, sr = torchaudio.load(str(audio_file))
                    if sr != 16000:
                        waveform = torchaudio.transforms.Resample(sr, 16000)(waveform)
                    if waveform.shape[0] > 1:
                        waveform = waveform.mean(dim=0, keepdim=True)

                    # Truncate to 4s
                    max_len = 16000 * 4
                    if waveform.shape[1] > max_len:
                        waveform = waveform[:, :max_len]

                    inputs = processor(
                        waveform.squeeze().numpy(),
                        sampling_rate=16000,
                        return_tensors="pt",
                    )

                    with torch.no_grad():
                        logits = model(inputs.input_values.to(device)).logits
                        probs = torch.softmax(logits, dim=-1)
                        fake_score = probs[0, 1].item()

                    if label == "genuine":
                        genuine_scores.append(fake_score)
                    else:
                        spoof_scores.append(fake_score)

                except Exception as e:
                    logger.warning(f"  Error processing {audio_file.name}: {e}")

        if genuine_scores and spoof_scores:
            eer, threshold = compute_eer(
                np.array(genuine_scores), np.array(spoof_scores)
            )
            results[name] = {
                "eer": round(eer * 100, 2),
                "threshold": round(threshold, 4),
                "n_genuine": len(genuine_scores),
                "n_spoof": len(spoof_scores),
            }
            logger.info(f"  EER: {eer * 100:.2f}% at threshold {threshold:.4f}")
        else:
            logger.warning(f"  Insufficient data for EER computation")

    # Save results
    output_path = BASE_DIR / "outputs" / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved: {output_path}")

    return results


def run_mock_evaluation():
    """Mock evaluation with synthetic scores for demo/testing."""
    logger.info("=== Mock Evaluation ===")

    # Simulate reasonable scores
    np.random.seed(42)
    genuine_scores = np.random.beta(2, 8, size=100)  # Mostly low fake scores
    spoof_scores = np.random.beta(8, 2, size=100)  # Mostly high fake scores

    eer, threshold = compute_eer(genuine_scores, spoof_scores)

    results = {
        "Mock Evaluation": {
            "eer": round(eer * 100, 2),
            "threshold": round(threshold, 4),
            "n_genuine": len(genuine_scores),
            "n_spoof": len(spoof_scores),
            "mock": True,
        }
    }

    logger.info(f"Mock EER: {eer * 100:.2f}% at threshold {threshold:.4f}")

    output_path = BASE_DIR / "outputs" / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved: {output_path}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoneySpeaks model evaluation")
    parser.add_argument(
        "--checkpoint",
        default=str(BASE_DIR / "outputs" / "checkpoints" / "deepfake_wav2vec2.pt"),
    )
    parser.add_argument("--mock", action="store_true", help="Run mock evaluation only")
    args = parser.parse_args()

    if args.mock:
        run_mock_evaluation()
    else:
        evaluate_checkpoint(args.checkpoint)
