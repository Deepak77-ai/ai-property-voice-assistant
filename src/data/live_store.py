
LIVE_DATA: dict = {}


def update_live(session_id: str, profile: dict) -> None:
    
    LIVE_DATA[session_id] = profile.copy()


def get_live() -> dict:
    
    return LIVE_DATA