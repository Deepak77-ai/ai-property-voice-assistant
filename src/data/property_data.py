
import re


PROPERTY_DB = [
    {
        "city": "Mumbai", "area": "Thane",
        "type": "2BHK", "intent": "buy", "price_lakh": 60,
        "purpose": "self-use",
        "highlights": ["near metro", "family area", "good connectivity"]
    },
    {
        "city": "Mumbai", "area": "Navi Mumbai",
        "type": "1BHK", "intent": "buy", "price_lakh": 50,
        "purpose": "investment",
        "highlights": ["future growth", "near station", "rental demand"]
    },
    {
        "city": "Pune", "area": "Hinjewadi",
        "type": "2BHK", "intent": "buy", "price_lakh": 55,
        "purpose": "investment",
        "highlights": ["IT hub", "good rent", "new projects"]
    },
    {
        "city": "Pune", "area": "Wakad",
        "type": "2BHK", "intent": "buy", "price_lakh": 65,
        "purpose": "self-use",
        "highlights": ["schools nearby", "premium area", "family location"]
    },
    {
        "city": "Bangalore", "area": "Whitefield",
        "type": "2BHK", "intent": "buy", "price_lakh": 75,
        "purpose": "investment",
        "highlights": ["IT location", "metro access", "high demand"]
    },
    {
        "city": "Delhi", "area": "Dwarka",
        "type": "2BHK", "intent": "buy", "price_lakh": 80,
        "purpose": "self-use",
        "highlights": ["metro nearby", "developed area", "family friendly"]
    },
    {
        "city": "Pune", "area": "Kharadi",
        "type": "1BHK", "intent": "rent", "price_lakh": 0.35,
        "purpose": "self-use",
        "highlights": ["near offices", "ready to move", "working professionals"]
    },
]




def _budget_to_lakh(budget) -> float | None:
    """
    Convert a spoken / typed budget string into a number in lakhs.

    Examples
    --------
    "60 lakh"   → 60.0
    "60"        → 60.0   (assumes lakh by default)
    "1 crore"   → 100.0
    "1 cr"      → 100.0
    None        → None

    WHY A SEPARATE PARSER?
        The caller might say "sixty lakh", "1 crore", or just "60".
        assistant.py normalizes spoken numbers to digit strings before
        storing them in the profile, so here we only need to handle
        digit strings with optional unit words.
    """
    if not budget:
        return None

    text = str(budget).lower().replace(",", "")
    match = re.search(r"(\d+\.?\d*)", text)   
    if not match:
        return None

    amount = float(match.group(1))

    # 1 crore = 100 lakh
    if "crore" in text or " cr" in text:
        return amount * 100

    return amount   # default unit is lakh



def _score_property(prop: dict, city: str, intent: str, ptype: str,
                    purpose: str, budget: float | None) -> int:
    
    score = 0

    # City is the strongest signal — wrong city, wrong result.
    if city   and prop["city"].lower()    == city:    score += 4
    if intent and prop["intent"]          == intent:  score += 3
    if ptype  and prop["type"].upper()    == ptype:   score += 3

    # Budget: only recommend properties the caller can afford.
    if budget is not None and prop["price_lakh"] <= budget:            score += 3

    # Purpose is a soft preference — lower weight.
    if purpose and prop["purpose"]        == purpose: score += 1

    return score


def recommend_properties(profile: dict, limit: int = 3) -> list:
    
    # Normalize inputs so comparisons are case-insensitive.
    city    = str(profile.get("city",    "")).lower()
    intent  = str(profile.get("intent",  "")).lower()
    ptype   = str(profile.get("type",    "")).upper()   # "2bhk" → "2BHK"
    purpose = str(profile.get("purpose", "")).lower()
    budget  = _budget_to_lakh(profile.get("budget"))

    scored = []

    for prop in PROPERTY_DB:
        score = _score_property(prop, city, intent, ptype, purpose, budget)

        if score > 0:                   # exclude completely unrelated properties
            item = prop.copy()          # don't mutate the original PROPERTY_DB entry
            item["match_score"] = score
            scored.append(item)

    # Sort descending by score — best match first.
    scored.sort(key=lambda x: x["match_score"], reverse=True)

    return scored[:limit]



def format_recommendations(profile: dict) -> str:
    
    matches = recommend_properties(profile)

    if not matches:
        return (
            "I do not have an exact match right now, "
            "but our expert can suggest better options."
        )

    lines = []
    for prop in matches:
        highlights = ", ".join(prop["highlights"][:2])   # max 2 highlights to keep it brief
        lines.append(
            f"{prop['type']} in {prop['area']} "
            f"around {prop['price_lakh']} lakh. "
            f"Highlights: {highlights}."
        )

    return "Based on your requirement, I found these options: " + " ".join(lines)