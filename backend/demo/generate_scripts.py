"""Generate demo audio scripts and synthesize with ElevenLabs.

Run once to produce:
  - bank_impersonation.mp3
  - investment_scam.mp3
  - legitimate_bank_call.mp3

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

# Map scenario -> (voice for speaker A, voice for speaker B)
SCENARIO_VOICES = {
    "bank_impersonation": (VOICE_A, VOICE_B),       # scammer=male, victim=female
    "investment_scam": (VOICE_A, VOICE_B),           # scammer=male, victim=female
    "legitimate_bank_call": (VOICE_C, VOICE_B),      # customer=neutral, bank agent=female
    "credit_card_scam": (VOICE_B, VOICE_C),          # scammer=female, victim=neutral
}


def get_hardcoded_scripts():
    """Finance-focused demo scripts. Used as fallback or when Gemini unavailable."""
    return {
        "bank_impersonation": {
            "text": (
                "A: Hello, this is the fraud department at First National Bank. We've detected unauthorized activity on your checking account.\n"
                "B: Oh my, what kind of activity? I haven't used my card today.\n"
                "A: Someone attempted a wire transfer of three thousand dollars from your account to an overseas account. We need to verify your identity immediately to block it.\n"
                "B: Three thousand dollars? That's terrible! What do I need to do?\n"
                "A: I'll need your account number and the last four digits of your PIN so we can freeze the account and reverse the transfer.\n"
                "B: Okay, let me get my checkbook. My account number is...\n"
                "A: Please hurry, ma'am. The transfer is still processing. And whatever you do, don't hang up or call the bank on another line. That could trigger the transfer to go through.\n"
            ),
            "label": "FAKE",
        },
        "investment_scam": {
            "text": (
                "A: Good afternoon. I'm calling from Pinnacle Wealth Advisors. We have an exclusive investment opportunity for select clients in your area.\n"
                "B: Oh, an investment opportunity? What kind?\n"
                "A: It's a guaranteed high-yield bond fund returning eighteen percent annually. We've had clients double their retirement savings in just three years.\n"
                "B: Eighteen percent? That sounds almost too good to be true.\n"
                "A: I understand the skepticism, but this is a limited-time offer. We only have twelve spots left and they're filling fast. I'd need a wire transfer of five thousand dollars today to secure your position.\n"
                "B: Five thousand? I don't know, that's a lot of money to send right away.\n"
                "A: I completely understand, but the window closes at five PM today. If you miss this, the next offering won't be for another year. And you'll want to keep this between us until the returns come in. Other advisors may try to talk you out of it because they'll lose your business.\n"
            ),
            "label": "FAKE",
        },
        "legitimate_bank_call": {
            "text": (
                "A: Hi, I'm calling about a charge on my credit card statement that I don't recognize. It says Meridian Services for forty-seven dollars.\n"
                "B: Of course, I can help you with that. Can I verify your name and the last four digits of your account number?\n"
                "A: Sure, it's Michael Chen, and the last four are 8-3-1-2.\n"
                "B: Thank you, Michael. Let me pull up your account. I see the charge from Meridian Services on March 15th. That appears to be a subscription service. Would you like me to look into it further?\n"
                "A: Yes please. I don't remember signing up for any subscription.\n"
                "B: No problem. I'll open a dispute for that charge. You'll receive a provisional credit within two business days, and we'll investigate. Is there anything else I can help you with?\n"
                "A: No, that's all. Thank you so much for your help.\n"
                "B: You're welcome, Michael. Have a great day.\n"
            ),
            "label": "REAL",
        },
        "credit_card_scam": {
            "text": (
                "A: Good afternoon. This is the security team at Visa. We've flagged your credit card ending in 4-7-2-1 for suspicious overseas transactions.\n"
                "B: What? I haven't made any overseas purchases.\n"
                "A: That's exactly why we're calling. Three charges totaling two thousand eight hundred dollars were attempted from an IP address in Romania. We've temporarily frozen the transactions but need to verify your identity before we can release the hold.\n"
                "B: Oh no, what do I need to do?\n"
                "A: For security purposes, I'll need your full card number and the three-digit code on the back so I can cross-reference it with our fraud database.\n"
                "B: Um, okay. Let me grab my wallet.\n"
                "A: Please hurry. If we can't verify within the next ten minutes, the freeze will expire and those charges will go through. Also, I need to advise you not to contact your bank separately — our fraud team is already coordinating with them, and multiple inquiries could delay the resolution.\n"
                "B: Alright, the card number is...\n"
            ),
            "label": "FAKE",
        },
    }


SCRIPTS = {
    "bank_impersonation": {
        "label": "FAKE",
        "prompt": """Write a realistic two-way phone scam conversation where someone impersonates a bank's fraud department calling an elderly customer.
The scammer should claim to be from the fraud department, create urgency about an unauthorized wire transfer,
request account number and PIN, and pressure the victim not to hang up or call the bank directly.
The victim should sound confused and worried, gradually complying.
Keep it under 45 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = scammer, B = victim).
Example:
A: Hello, this is the fraud department at your bank.
B: Oh my, what's going on?""",
    },
    "investment_scam": {
        "label": "FAKE",
        "prompt": """Write a realistic two-way phone scam conversation where a scammer pitches a fake high-return investment to an elderly person.
The scammer should claim to be from an investment firm, promise guaranteed 18% returns,
pressure for an immediate wire transfer, create urgency with a limited-time offer,
and discourage the victim from consulting other financial advisors.
The victim should be interested but hesitant about sending money so quickly.
Keep it under 45 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = scammer, B = victim).
Example:
A: Good afternoon, I'm calling from Pinnacle Wealth Advisors.
B: Oh, what's this about?""",
    },
    "legitimate_bank_call": {
        "label": "REAL",
        "prompt": """Write a normal, legitimate two-way phone conversation between a customer calling their bank about an unrecognized charge on their credit card statement.
The customer politely asks about the charge, the bank agent verifies their identity,
looks up the transaction, and opens a dispute. Everything is professional and routine.
Keep it under 30 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = customer, B = bank agent).
Example:
A: Hi, I'm calling about a charge on my statement I don't recognize.
B: Of course, I can help with that.""",
    },
    "credit_card_scam": {
        "label": "FAKE",
        "prompt": """Write a realistic two-way phone scam conversation where someone impersonates a credit card company's security team calling an elderly person.
The scammer should claim to be from Visa's security team, describe suspicious overseas transactions,
create urgency about a time-limited fraud hold, request the full card number and CVV code,
and warn the victim not to contact their bank separately.
The victim should be alarmed and gradually complying.
Keep it under 45 seconds of speech total.
IMPORTANT: Format EXACTLY as alternating lines prefixed with A: or B: (A = scammer, B = victim).
Example:
A: Good afternoon, this is the security team at Visa.
B: Oh, what's going on?""",
    },
}


def generate_scripts_with_gemini():
    """Use Gemini to write finance-focused demo scripts."""
    try:
        from google import genai
    except ImportError:
        print("google-genai not installed. Using fallback scripts.")
        return get_hardcoded_scripts()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No GEMINI_API_KEY. Using fallback scripts.")
        return get_hardcoded_scripts()

    client = genai.Client(api_key=api_key)

    # Start with hardcoded scripts as base — legitimate call ALWAYS uses
    # the hardcoded version so we control exactly what's in it.
    hardcoded = get_hardcoded_scripts()
    scripts = {}

    for name, config in SCRIPTS.items():
        # Skip legitimate call — Gemini tends to generate scripts where
        # the agent asks for full card numbers / maiden names, which our
        # system correctly flags as suspicious. Use the known-safe hardcoded version.
        if config["label"] == "REAL":
            print(f"Using hardcoded script: {name} (safe baseline)")
            scripts[name] = hardcoded[name]
            continue

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
            print(f"  Using hardcoded fallback for {name}")
            if name in hardcoded:
                scripts[name] = hardcoded[name]

    # Ensure all scenarios are present (fill from hardcoded)
    for name in hardcoded:
        if name not in scripts:
            scripts[name] = hardcoded[name]

    return scripts


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
                print(f"  [{speaker}] {line[:60]}... ({len(part)} bytes)")
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
        print("No ELEVENLABS_API_KEY — skipping warning phrases.")
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
