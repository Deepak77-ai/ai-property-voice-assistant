"""
conversation_memory.py
-----------------------
Simple in-memory store for per-session conversation history.

WHY THIS FILE EXISTS ALONGSIDE conversation_store.py?
    Two different purposes:

    conversation_store.py  → persists full message records to disk (JSON).
                             Each record has time, role, content, profile.
                             Used for admin review, audit trail, lead tracking.

    conversation_memory.py → holds lightweight message strings in memory
                             only, for passing as history to the LLM prompt.
                             Fast, no disk I/O, no extra fields.

    Think of it as:
        conversation_store.py  = the database (permanent record)
        conversation_memory.py = the LLM's short-term working memory

NOTE: This module is currently defined but assistant.py manages its own
    in-memory history directly (conversation_store dict inside assistant.py).
    This utility exists as a clean, reusable alternative — useful if the
    project is refactored to separate memory management from assistant logic.

Data structure:
{
    "CAxxxx...": ["User: I want a 2BHK", "Assistant: Which city?", ...],
    "web-user":  ["User: Looking to buy", ...],
}
"""

from typing import Dict, List

# Module-level dict — lives in memory for the lifetime of the server process.
# Keys   → session / call IDs
# Values → ordered list of message strings for that session
conversation_store: Dict[str, List[str]] = {}


def add_message(conversation_id: str, message: str) -> None:
    """
    Append a message string to a session's history.

    Parameters
    ----------
    conversation_id : str
        Unique ID for the call or web session.
    message : str
        The message to store. Caller decides the format —
        typically "User: <text>" or "Assistant: <text>" so the
        LLM can distinguish speakers when the list is passed as context.

    NOTE: No max-length cap here. In production you would slice to the
    last N messages before passing to the LLM to stay within token limits.
    assistant.py already does this with [-6:] when building its prompt.
    """
    if conversation_id not in conversation_store:
        conversation_store[conversation_id] = []   # first message — create the list

    conversation_store[conversation_id].append(message)


def get_history(conversation_id: str) -> List[str]:
    """
    Return the full message history for a session.

    Returns [] if the session doesn't exist yet — safe to call
    at any point without checking first.

    WHY .get() with a default?
        Cleaner than an if/else check. dict.get(key, default) returns
        the default if the key is missing, instead of raising KeyError.
    """
    return conversation_store.get(conversation_id, [])


def clear_history(conversation_id: str) -> None:
    """
    Delete the history for a session when the conversation ends.

    Called when the caller says "bye" or another exit phrase so the
    memory for that session doesn't linger in RAM indefinitely.

    WHY del instead of setting to []?
        del removes the key entirely, freeing the memory.
        Setting to [] keeps an empty list for every ended session,
        which would grow unbounded over time on a busy server.
    """
    if conversation_id in conversation_store:
        del conversation_store[conversation_id]