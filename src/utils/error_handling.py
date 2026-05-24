"""
error_handling.py
------------------
Centralised error logging utility for the voice assistant.

WHY A SEPARATE FILE FOR THIS?
    Without this, every file would either:
      a) silently swallow errors (bad — hard to debug)
      b) repeat the same logging boilerplate everywhere (messy)

    One function here means the log format is consistent across the
    entire project, and you only need to change it in one place.

HOW LOGGING WORKS IN PYTHON:
    Python's built-in logging module has 5 levels (lowest → highest):
        DEBUG    → detailed dev info, not shown in production
        INFO     → normal operational messages ("server started")
        WARNING  → something unexpected but recoverable
        ERROR    → something failed, needs attention   ← we use this
        CRITICAL → system cannot continue

    basicConfig(level=INFO) means INFO and above are printed.
    Setting it to WARNING in production would silence INFO noise.

WHERE THIS IS USED:
    Any try/except block in the project can call handle_error(e, context)
    instead of writing logging.error() manually each time.
    Returns a safe, user-friendly string that can be spoken back to
    the caller — never exposes internal error details.
"""

import logging

# Configure the root logger once at module level.
# Format includes timestamp and log level so logs are easy to read.
# NOTE: In production, you would write logs to a file by adding:
#   filename="app.log", filemode="a"
# to basicConfig, so logs survive server restarts.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",   # e.g. 2024-04-23 20:17:00  [ERROR]  Error in transcribe: ...
    datefmt="%Y-%m-%d %H:%M:%S"
)


def handle_error(e: Exception, context: str = "") -> str:
    """
    Log an exception with context and return a safe user-facing message.

    Parameters
    ----------
    e : Exception
        The exception that was caught.
    context : str, optional
        A short label saying where the error happened.
        Example: "transcribe_audio", "save_lead", "process_recording"
        Makes logs much easier to search when debugging.

    Returns
    -------
    str
        A generic, safe message to send back to the caller.
        We never return the real error message to the user because:
          1. It may contain sensitive internal details (file paths, keys).
          2. Raw exception text is confusing spoken aloud on a voice call.

    Example usage
    -------------
        try:
            result = transcribe_audio(path)
        except Exception as e:
            return handle_error(e, context="transcribe_audio")
    """
    logging.error(f"Error in {context}: {str(e)}")
    return "Sorry, something went wrong. Please try again."