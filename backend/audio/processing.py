"""Audio processing: decode, resample, chunk into 2-second segments."""

import io
import logging
import struct
import wave
from typing import List

import numpy as np

logger = logging.getLogger("moneyspeaks.audio")

TARGET_SAMPLE_RATE = 16000
CHUNK_DURATION_S = 2
CHUNK_SAMPLES = TARGET_SAMPLE_RATE * CHUNK_DURATION_S


def decode_audio_bytes(raw: bytes, source_format: str = "pcm16") -> np.ndarray:
    """Decode raw audio bytes to float32 numpy array.

    Supports:
      - pcm16: raw 16-bit signed little-endian PCM
      - wav: WAV container
      - mp3: MP3 via pydub (requires ffmpeg)
    """
    if source_format == "wav":
        return _decode_wav(raw)
    elif source_format == "mp3":
        return _decode_mp3(raw)
    else:
        # Raw PCM 16-bit signed LE
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        return samples / 32768.0


def _decode_wav(raw: bytes) -> np.ndarray:
    buf = io.BytesIO(raw)
    with wave.open(buf, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        frames = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sampwidth}")

    # Convert stereo to mono
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    # Resample if needed
    if framerate != TARGET_SAMPLE_RATE:
        samples = _resample(samples, framerate, TARGET_SAMPLE_RATE)

    return samples


def _decode_mp3(raw: bytes) -> np.ndarray:
    try:
        from pydub import AudioSegment
    except ImportError:
        raise ImportError("pydub required for MP3 decoding. Install with: pip install pydub")

    buf = io.BytesIO(raw)
    audio = AudioSegment.from_mp3(buf)
    audio = audio.set_channels(1).set_frame_rate(TARGET_SAMPLE_RATE).set_sample_width(2)
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32) / 32768.0
    return samples


def _resample(samples: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    if orig_rate == target_rate:
        return samples
    try:
        from scipy.signal import resample as scipy_resample
        num_samples = int(len(samples) * target_rate / orig_rate)
        return scipy_resample(samples, num_samples).astype(np.float32)
    except ImportError:
        # Linear interpolation fallback
        ratio = target_rate / orig_rate
        indices = np.arange(0, len(samples), 1 / ratio)
        indices = np.clip(indices, 0, len(samples) - 1)
        return np.interp(indices, np.arange(len(samples)), samples).astype(np.float32)


def chunk_audio(samples: np.ndarray, chunk_samples: int = CHUNK_SAMPLES) -> List[np.ndarray]:
    """Split audio into fixed-size chunks. Last chunk is zero-padded if short."""
    chunks = []
    for i in range(0, len(samples), chunk_samples):
        chunk = samples[i : i + chunk_samples]
        if len(chunk) < chunk_samples:
            padded = np.zeros(chunk_samples, dtype=np.float32)
            padded[: len(chunk)] = chunk
            chunk = padded
        chunks.append(chunk)
    logger.info(f"Split {len(samples)} samples into {len(chunks)} chunks of {chunk_samples}")
    return chunks


def validate_audio(samples: np.ndarray) -> dict:
    """Return basic audio stats for logging/debugging."""
    return {
        "n_samples": len(samples),
        "duration_s": round(len(samples) / TARGET_SAMPLE_RATE, 2),
        "min": round(float(samples.min()), 4),
        "max": round(float(samples.max()), 4),
        "rms": round(float(np.sqrt(np.mean(samples ** 2))), 4),
        "is_silent": bool(np.sqrt(np.mean(samples ** 2)) < 0.001),
    }


def float32_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float32 [-1, 1] array to 16-bit PCM bytes for webrtcvad."""
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)
    return pcm.tobytes()
