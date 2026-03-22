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

# Voice IDs: each scenario uses two distinct voices for the two speakers
VOICE_A = "Ock0AL5DBkvTUDePt4Hm"  # Male / authoritative
VOICE_B = "oO7sLA3dWfQXsKeSAjpA"  # Female / older
VOICE_C = "fVVjLtJgnQI61CoImgHU"  # Neutral / friendly

SCRIPTS = {
    "bank_impersonation": {
        "label": "FAKE",
        "prompt": """Write a realistic two-way phone scam conversation where someone impersonates a bank's fraud department calling an elderly person.
The scammer should claim to be from the fraud department, create urgency about unauthorized activity,
request account number and PIN, and pressure the victim not to contact anyone else.
The victim should sound confused and worried, gradually complying.
Keep it under 45 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = scammer, B = victim).
Example:
A: Hello, this is the fraud department.
B: Oh my, what's going on?""",
    },
    "grandparent_scam": {
        "label": "FAKE",
        "prompt": """Write a realistic two-way grandparent scam phone conversation.
The scammer pretends to be a grandchild in distress, claims to be in jail or had an accident,
asks for money urgently via gift cards, and begs the victim not to tell other family members.
The grandparent should sound concerned and loving, gradually agreeing to help.
Keep it under 45 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = scammer, B = grandparent).
Example:
A: Grandma? It's me...
B: Who is this?""",
    },
    "real_customer": {
        "label": "REAL",
        "prompt": """Write a normal, legitimate two-way phone conversation.
A caller phones about a scheduled appointment, confirms details politely, mentions they might be late.
The receptionist is friendly and helpful.
Keep it under 30 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = caller, B = receptionist).
Example:
A: Hi, I'm calling about my appointment.
B: Of course, let me look that up.""",
    },
}

# Map scenario -> (voice for speaker A, voice for speaker B)
SCENARIO_VOICES = {
    "bank_impersonation": (VOICE_A, VOICE_B),  # scammer=male, victim=female
    "grandparent_scam": (VOICE_A, VOICE_B),    # scammer=male, grandparent=female
    "real_customer": (VOICE_C, VOICE_B),        # caller=neutral, receptionist=female
}


def generate_scripts_with_gemini():
    """Use Gemini to write scam/legitimate scripts."""
    try:
        from google import genai
    except ImportError:
        print("google-genai not installed. Using hardcoded scripts.")
        return get_hardcoded_scripts()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY. Using hardcoded scripts.")
        return get_hardcoded_scripts()

    client = genai.Client(api_key=api_key)

    scripts = {}
    for name, config in SCRIPTS.items():
        print(f"Generating script: {name}...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=config["prompt"],
            )
            scripts[name] = {
                "text": response.text,
                "label": config["label"],
            }
            print(f"  Done: {len(response.text)} chars")
        except Exception as e:
            print(f"  Gemini failed: {e}")
            print("  Falling back to hardcoded scripts for all remaining.")
            return get_hardcoded_scripts()

    return scripts


def get_hardcoded_scripts():
    """Fallback scripts when no API key is available."""
    return {
        "bank_impersonation": {
            "text": (
                "A: Hello, this is the fraud department at your bank. We've detected some unauthorized activity on your account.\n"
                "B: Oh my goodness, what kind of activity?\n"
                "A: It appears someone is attempting to transfer funds out of your savings. We need to verify your identity immediately to stop it.\n"
                "B: Oh no, that's terrible. What do I need to do?\n"
                "A: I'll need your account number and the last four digits of your PIN so we can secure your funds right away.\n"
                "B: Okay, let me find my card.\n"
                "A: Please hurry, ma'am. The transfer is still in progress. And please don't hang up or contact anyone else. This is time-sensitive.\n"
            ),
            "label": "FAKE",
        },
        "grandparent_scam": {
            "text": (
                "A: Grandma? It's me... I'm in trouble.\n"
                "B: Who is this? Tommy, is that you? You sound different.\n"
                "A: Yeah, it's me. I hurt my nose in the accident. I'm at the police station, Grandma.\n"
                "B: Oh my Lord, are you okay? What happened?\n"
                "A: I got into a car accident and they're saying I need bail money right away. Can you go to the store and get some gift cards? I need about two thousand dollars.\n"
                "B: Of course, sweetheart. Let me get my purse.\n"
                "A: And Grandma, please, please don't tell Mom and Dad. They'll be so upset with me. I'm so scared.\n"
            ),
            "label": "FAKE",
        },
        "real_customer": {
            "text": (
                "A: Hi, I'm calling about the appointment we scheduled for next Tuesday at 2pm.\n"
                "B: Of course! Let me pull that up. Yes, I see it right here. Tuesday the 25th at 2 o'clock.\n"
                "A: Perfect. I just wanted to confirm and let you know I might be a few minutes late. Traffic has been terrible this week.\n"
                "B: That's no problem at all. We'll have everything ready for you whenever you arrive.\n"
                "A: Great, thank you so much. I'll see you then!\n"
                "B: Sounds good. Have a wonderful day!\n"
            ),
            "label": "REAL",
        },
    }


def _parse_dialogue(text: str) -> list:
    """Parse A:/B: formatted dialogue into list of (speaker, line) tuples."""
    lines = []
    for raw_line in text.strip().split("\n"):
        raw_line = raw_line.strip()
        if raw_line.startswith("A:"):
            lines.append(("A", raw_line[2:].strip()))
        elif raw_line.startswith("B:"):
            lines.append(("B", raw_line[2:].strip()))
        elif raw_line:
            # No prefix — append to previous speaker or default to A
            if lines:
                prev_speaker, prev_text = lines[-1]
                lines[-1] = (prev_speaker, prev_text + " " + raw_line)
            else:
                lines.append(("A", raw_line))
    return lines


def synthesize_with_elevenlabs(scripts: dict):
    """Synthesize scripts to MP3 using ElevenLabs API with two voices per scenario."""
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
        print(f"Synthesizing: {name} -> {output_path}")

        voice_a, voice_b = SCENARIO_VOICES.get(name, (VOICE_A, VOICE_B))
        dialogue = _parse_dialogue(script["text"])

        if not dialogue:
            print(f"  No dialogue parsed for {name}, skipping")
            continue

        # Synthesize each line with the correct voice, collect raw MP3 bytes
        mp3_parts = []
        for speaker, line in dialogue:
            voice_id = voice_a if speaker == "A" else voice_b
            try:
                audio = client.text_to_speech.convert(
                    text=line,
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                )
                part = b"".join(audio)
                mp3_parts.append(part)
                print(f"  [{speaker}] {line[:50]}... ({len(part)} bytes)")
            except Exception as e:
                print(f"  Failed line [{speaker}]: {e}")

        if not mp3_parts:
            print(f"  No audio generated for {name}")
            continue

        # Merge by concatenating MP3 frames (MP3 is frame-based, concat works)
        with open(output_path, "wb") as f:
            for part in mp3_parts:
                f.write(part)
        print(f"  Saved: {output_path} ({len(mp3_parts)} segments)")


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
