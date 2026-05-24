

import json
import os
from datetime import datetime


CONVERSATIONS_FILE = "conversations.json"




def _load() -> dict:
    
    if not os.path.exists(CONVERSATIONS_FILE):
        return {}

    try:
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        
        return {}


def _save(data: dict) -> None:
    
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)



def save_message(
    conversation_id: str,
    role: str,
    content: str,
    profile: dict = None
) -> None:
    
    data = _load()

    # First message for this conversation? Start a fresh list.
    if conversation_id not in data:
        data[conversation_id] = []

    data[conversation_id].append({
        "time":    datetime.now().isoformat(timespec="seconds"),  # e.g. "2024-04-23T20:17:00"
        "role":    role,
        "message": content,
        "profile": profile or {}   # never store None in JSON
    })

    _save(data)


def get_all_conversations() -> dict:
    
    return _load()