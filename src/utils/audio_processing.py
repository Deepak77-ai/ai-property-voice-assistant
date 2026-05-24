"""
audio_processing.py
--------------------
Utility for converting audio files to WAV format before transcription.

WHY WAV?
    Whisper (the speech-to-text model used in stt_whisper.py) can handle
    many formats, but WAV is uncompressed and has no codec dependency.
    Converting first gives consistent, reliable input to the transcriber.

WHY pydub?
    pydub wraps ffmpeg in a clean Python API. A single line handles any
    input format — webm, mp3, ogg, m4a, etc. — without format-specific code.

DEPENDENCY:
    pydub needs ffmpeg installed on the system.
    On Ubuntu: sudo apt install ffmpeg
    On Windows: download from https://ffmpeg.org and add to PATH.
    Listed in requirements.txt so it's clear to anyone setting up the project.
"""

from pydub import AudioSegment


def convert_to_wav(input_path: str, output_path: str) -> None:
    """
    Convert any audio file to WAV format and save it to output_path.

    Parameters
    ----------
    input_path : str
        Path to the source audio file (webm, mp3, ogg, m4a, etc.)
        The format is auto-detected by pydub/ffmpeg — no need to specify.

    output_path : str
        Path where the converted WAV file will be saved.
        Should end in ".wav" by convention.

    WHY from_file() instead of from_wav() / from_mp3()?
        from_file() lets ffmpeg detect the codec automatically.
        This means the function works for any format the caller uploads
        (webm from browser, mp3 from a phone, etc.) without any changes here.

    NOTE:
        This function is currently not called anywhere in the project —
        main.py passes audio directly to transcribe_audio() in stt_whisper.py,
        which handles its own format internally via the Groq Whisper API.
        This utility exists as a fallback for local Whisper or other STT
        engines that strictly require WAV input.
    """
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format="wav")