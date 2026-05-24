

import os
import tempfile
import requests
import speech_recognition as sr
from config.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN


def listen(recording_url: str) -> str:
    
    # Twilio serves recordings in multiple formats — request .wav explicitly.
    if not recording_url.endswith(".wav"):
        recording_url += ".wav"

    # Download the recording — Twilio requires Basic Auth.
    response = requests.get(
        recording_url,
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    )

    if response.status_code != 200:
        print("Error downloading Twilio recording:", response.text)
        return ""

    # Write audio to a named temp file — speech_recognition needs a file path.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(response.content)
        tmp_file_path = tmp_file.name

    recognizer = sr.Recognizer()

    with sr.AudioFile(tmp_file_path) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.2)   # calibrate for call noise
        audio_data = recognizer.record(source)                        # load full audio into memory

    try:
        return recognizer.recognize_google(audio_data)   # free Google Speech API, no key needed
    except Exception:
        return ""   # UnknownValueError or RequestError → safe fallback
    finally:
        os.remove(tmp_file_path)   # always clean up, even if recognition failed