"""Generate demo audio scripts via Gemini and synthesize with ElevenLabs.

Run once before hackathon to produce:
  - bank_impersonation.mp3
  - grandparent_scam.mp3
  - real_customer.mp3

Requires GEMINI_API_KEY and ELEVENLABS_API_KEY in environment.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env so keys are available
load_dotenv(Path(__file__).parent.parent / ".env")

DEMO_DIR = Path(__file__).parent

SCRIPTS = {
    "bank_impersonation": {
        "label": "FAKE",
        "voice_id": "Ock0AL5DBkvTUDePt4Hm",
        "prompt": """Write a realistic phone scam script where someone impersonates a bank's fraud department.
The caller should:
1. Claim to be from the fraud department
2. Create urgency about unauthorized activity
3. Request account number and PIN
4. Pressure the victim not to contact anyone else
Keep it under 45 seconds of speech. Write only the scammer's dialogue, one line per utterance.""",
    },
    "grandparent_scam": {
        "label": "FAKE",
        "voice_id": "oO7sLA3dWfQXsKeSAjpA",
        "prompt": """Write a realistic grandparent scam phone script.
The caller should:
1. Pretend to be a grandchild in distress
2. Claim to be in jail or hospital
3. Ask for money urgently via gift cards
4. Beg the victim not to tell other family members
Keep it under 45 seconds. Write only the scammer's dialogue.""",
    },
    "real_customer": {
        "label": "REAL",
        "voice_id": "fVVjLtJgnQI61CoImgHU",
        "prompt": """Write a normal, legitimate phone conversation script.
The caller should:
1. Call about a scheduled appointment
2. Confirm details politely
3. Mention they might be late
4. End the call naturally
Keep it under 30 seconds. Write only the caller's dialogue.""",
    },
}


def generate_scripts_with_gemini():
    """Use Gemini to write scam/legitimate scripts."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("google-generativeai not installed. Using hardcoded scripts.")
        return get_hardcoded_scripts()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY. Using hardcoded scripts.")
        return get_hardcoded_scripts()

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")

    scripts = {}
    for name, config in SCRIPTS.items():
        print(f"Generating script: {name}...")
        response = model.generate_content(config["prompt"])
        scripts[name] = {
            "text": response.text,
            "voice_id": config["voice_id"],
            "label": config["label"],
        }
        print(f"  Done: {len(response.text)} chars")

    return scripts


def get_hardcoded_scripts():
    """Fallback scripts when no API key is available."""
    return {
        "bank_impersonation": {
            "text": (
                "Hello, this is the fraud department at your bank. "
                "We've detected unauthorized activity on your account and need to verify your identity immediately. "
                "I'll need your account number and the last four digits of your PIN to secure your funds. "
                "Please don't hang up or contact anyone else — this is time-sensitive and your savings are at risk. "
                "If you don't act now, we won't be able to prevent the unauthorized transfer."
            ),
            "voice_id": "Ock0AL5DBkvTUDePt4Hm",
            "label": "FAKE",
        },
        "grandparent_scam": {
            "text": (
                "Grandma? It's me... I'm in trouble. "
                "I got into a car accident and I'm at the police station. "
                "Please don't tell mom and dad, they'll be so upset. "
                "I need bail money right away — can you go to the store and get some gift cards? "
                "I need about two thousand dollars. Please hurry, I'm scared."
            ),
            "voice_id": "oO7sLA3dWfQXsKeSAjpA",
            "label": "FAKE",
        },
        "real_customer": {
            "text": (
                "Hi, I'm calling about the appointment we scheduled for next Tuesday at 2pm. "
                "I just wanted to confirm the time and let you know I might be a few minutes late. "
                "Traffic has been terrible this week. "
                "Great, thank you so much. I'll see you then. Have a wonderful day!"
            ),
            "voice_id": "fVVjLtJgnQI61CoImgHU",
            "label": "REAL",
        },
    }


def synthesize_with_elevenlabs(scripts: dict):
    """Synthesize scripts to MP3 using ElevenLabs API."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("No ELEVENLABS_API_KEY — skipping audio synthesis.")
        print("Demo will use mock mode for audio pipeline.")
        return

    try:
        from elevenlabs import ElevenLabs
    except ImportError:
        print("elevenlabs not installed. Skipping synthesis.")
        return

    client = ElevenLabs(api_key=api_key)

    for name, script in scripts.items():
        output_path = DEMO_DIR / f"{name}.mp3"
        print(f"Synthesizing: {name} → {output_path}")

        try:
            audio = client.text_to_speech.convert(
                text=script["text"],
                voice_id=script["voice_id"],
                model_id="eleven_multilingual_v2",
            )
            with open(output_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            print(f"  Saved: {output_path}")
        except Exception as e:
            print(f"  Failed: {e}")


def generate_warning_phrases():
    """Pre-generate TTS warning phrases for instant playback."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("No ELEVENLABS_API_KEY — TTS warnings will use browser SpeechSynthesis fallback.")
        return

    try:
        from elevenlabs import ElevenLabs
    except ImportError:
        return

    client = ElevenLabs(api_key=api_key)
    warnings_dir = DEMO_DIR / "warnings"
    warnings_dir.mkdir(exist_ok=True)

    phrases = [
        ("warning_scam", "Warning: this call shows signs of a scam. Consider hanging up."),
        ("caution_suspicious", "Caution: suspicious activity detected on this call."),
        ("not_who_they_claim", "This caller may not be who they claim to be."),
        ("hang_up_call_bank", "We recommend you hang up and call your bank directly."),
    ]

    for filename, text in phrases:
        output_path = warnings_dir / f"{filename}.mp3"
        print(f"Generating warning: {filename}")
        try:
            audio = client.text_to_speech.convert(
                text=text,
                voice_id="fVVjLtJgnQI61CoImgHU",
                model_id="eleven_multilingual_v2",
            )
            with open(output_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
        except Exception as e:
            print(f"  Failed: {e}")


if __name__ == "__main__":
    print("=== MoneySpeaks Demo Audio Generator ===\n")
    scripts = generate_scripts_with_gemini()
    synthesize_with_elevenlabs(scripts)
    generate_warning_phrases()
    print("\nDone!")
