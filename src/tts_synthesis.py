

import os
import uuid
import requests
from config.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, NGROK_URL



def generate_speech_file(text: str) -> str:
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"

    headers = {
        "xi-api-key":   ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability":        0.5,   # balanced expressiveness
            "similarity_boost": 0.8    # high voice fidelity
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()   # raise immediately on API error

    os.makedirs("static/audio", exist_ok=True)   # create dir if first run

    filename = f"resp_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join("static/audio", filename)

    # Write raw binary MP3 content to disk.
    with open(filepath, "wb") as f:
        f.write(response.content)

    return filename



def speak_and_get_url(text: str) -> str:
    
    filename = generate_speech_file(text)
    return f"{NGROK_URL}/static/audio/{filename}"


def speak_and_get_local_url(text: str) -> str:
    
    filename = generate_speech_file(text)
    return f"/static/audio/{filename}"