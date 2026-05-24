

from openai import OpenAI
from config.config import GROQ_API_KEY


client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)



def clean_transcription(text: str) -> str:
    
    text = (text or "").strip()

    fixes = {
        # City name variants Whisper commonly produces
        "Bombay":  "Mumbai",
        "bombay":  "Mumbai",
        "Mombai":  "Mumbai",
        "Mumbye":  "Mumbai",

        # BHK variants — normalise to the token extract_rule_based() expects
        "One BHK": "1BHK",
        "one BHK": "1BHK",
        "one bhk": "1BHK",
        "Two BHK": "2BHK",
        "two BHK": "2BHK",
        "two bhk": "2BHK",
    }

    for wrong, right in fixes.items():
        text = text.replace(wrong, right)

    return text




def transcribe_audio(file_path: str) -> str:
    
    try:
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file,
                temperature=0,   # deterministic — no creative transcription
                prompt=(
                    "English-only real estate conversation. Expected words include: "
                    "buy, rent, property, flat, apartment, house, Mumbai, Pune, budget, "
                    "50 lakh, 60 lakh, 1BHK, 2BHK, phone number."
                )
            )

        return clean_transcription(transcription.text)

    except Exception as e:
        print("STT Error:", str(e))
        return ""   # safe fallback — never crash the call on a transcription failure