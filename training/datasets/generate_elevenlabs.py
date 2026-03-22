"""Generate ElevenLabs training clips for deepfake detection fine-tuning.

Produces 400 training clips (voices 1-8) + 100 test clips (voices 9-12).
Voices 9-12 are held out from training — used only for demo/evaluation.

Requires ELEVENLABS_API_KEY environment variable.
"""

import os
import sys
import json
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")
except ImportError:
    pass

OUTPUT_DIR = Path(__file__).parent / "data" / "elevenlabs"

# Sample sentences for TTS generation — diverse content for robust detection
SENTENCES = [
    "Hello, I'm calling about your account. There's been some suspicious activity.",
    "Your social security number has been compromised. You need to act now.",
    "Hi grandma, it's me. I'm in trouble and I need your help.",
    "This is the IRS. You owe back taxes and must pay immediately.",
    "Your computer has been infected with a virus. Don't turn it off.",
    "We're calling from your bank's fraud department about unauthorized charges.",
    "Your Medicare coverage is about to expire unless you verify your information.",
    "I'm calling to confirm your appointment scheduled for next Tuesday.",
    "Hi, I wanted to check on the status of my order from last week.",
    "Good morning, this is Dr. Johnson's office calling about your test results.",
    "Your electricity will be shut off in one hour unless you make a payment.",
    "Don't tell anyone about this call. This is a confidential matter.",
    "Please hold while I transfer you to our secure verification department.",
    "We need to verify your identity. Can you confirm your date of birth?",
    "There's been a warrant issued for your arrest. This is your final notice.",
    "Your grandson was in an accident. He needs bail money right away.",
    "I'm calling about your car's extended warranty that's about to expire.",
    "Can you go to the nearest store and purchase some gift cards for me?",
    "This call is being recorded for quality assurance purposes.",
    "Hi, just calling to let you know dinner will be ready at six tonight.",
]

# ElevenLabs voice IDs
# Training uses all 3 voices; test holds them out in different combinations
TRAINING_VOICES = {
    "voice_1": "Ock0AL5DBkvTUDePt4Hm",
    "voice_2": "oO7sLA3dWfQXsKeSAjpA",
    "voice_3": "fVVjLtJgnQI61CoImgHU",
}
TEST_VOICES = {
    "voice_test_1": "Ock0AL5DBkvTUDePt4Hm",
    "voice_test_2": "oO7sLA3dWfQXsKeSAjpA",
    "voice_test_3": "fVVjLtJgnQI61CoImgHU",
}


def generate_clips(voices: dict, output_subdir: str, clips_per_voice: int):
    """Generate TTS clips for a set of voices."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print(f"No ELEVENLABS_API_KEY — creating placeholder metadata for {output_subdir}")
        create_placeholder_metadata(voices, output_subdir, clips_per_voice)
        return

    try:
        from elevenlabs import ElevenLabs
    except ImportError:
        print("elevenlabs not installed. Run: pip install elevenlabs")
        create_placeholder_metadata(voices, output_subdir, clips_per_voice)
        return

    client = ElevenLabs(api_key=api_key)
    out_dir = OUTPUT_DIR / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = []
    clip_count = 0

    for voice_name, voice_id in voices.items():
        for i in range(clips_per_voice):
            sentence = SENTENCES[i % len(SENTENCES)]
            filename = f"{voice_name}_clip_{i:03d}.mp3"
            filepath = out_dir / filename

            print(f"  [{clip_count + 1}] {voice_name} → {filename}")

            try:
                audio = client.text_to_speech.convert(
                    text=sentence,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                )
                with open(filepath, "wb") as f:
                    for chunk in audio:
                        f.write(chunk)

                metadata.append({
                    "filename": filename,
                    "voice": voice_name,
                    "voice_id": voice_id,
                    "text": sentence,
                    "label": "spoof",  # All ElevenLabs clips are synthetic
                })
                clip_count += 1
                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"    ERROR: {e}")

    # Save metadata
    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved metadata: {meta_path} ({len(metadata)} clips)")


def create_placeholder_metadata(voices: dict, output_subdir: str, clips_per_voice: int):
    """Create metadata file without actual audio (for mock training)."""
    out_dir = OUTPUT_DIR / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = []
    for voice_name in voices:
        for i in range(clips_per_voice):
            metadata.append({
                "filename": f"{voice_name}_clip_{i:03d}.mp3",
                "voice": voice_name,
                "text": SENTENCES[i % len(SENTENCES)],
                "label": "spoof",
                "placeholder": True,
            })

    meta_path = out_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Created placeholder metadata: {meta_path} ({len(metadata)} entries)")


if __name__ == "__main__":
    print("=== MoneySpeaks: ElevenLabs Training Data Generator ===\n")

    print(f"Output directory: {OUTPUT_DIR}\n")

    # Training clips: 400 total (50 per voice × 8 voices)
    print("Generating training clips (voices 1-8)...")
    generate_clips(TRAINING_VOICES, "train", clips_per_voice=50)

    print()

    # Test clips: 100 total (25 per voice × 4 voices)
    print("Generating test clips (voices 9-12, held out)...")
    generate_clips(TEST_VOICES, "test", clips_per_voice=25)

    print("\nDone!")
