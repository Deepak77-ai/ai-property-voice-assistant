
import json
import csv
import os
from datetime import datetime

LEADS_FILE = "leads.json"
CSV_FILE   = "leads.csv"


LEAD_FIELDS = [
    "created_at",
    "name",
    "phone",
    "city",
    "intent",
    "property_type",
    "budget",
    "purpose",
    "urgency",
    "lead_score",
    "lead_quality",
    "summary",
    "handoff_required",
]



def _load_leads() -> list:
    
    if not os.path.exists(LEADS_FILE):
        return []

    try:
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []




def load_leads() -> list:
    
    return _load_leads()


def calculate_lead_score(profile: dict) -> tuple[int, str]:
    """
    Score a lead from 0–100 based on how much info has been collected.

    Parameters
    ----------
    profile : dict
        The caller's profile built up during the conversation.

    Returns
    -------
    (score, quality) : tuple
        score   → int between 0 and 100
        quality → "Hot", "Warm", or "Cold"

    WHY PHONE IS WORTH THE MOST (30 pts)?
        A lead with no phone number cannot be contacted.
        All other info becomes useless without it.
    """
    score = 0

    score += 30 if profile.get("phone")   else 0   # Can we call them?
    score += 15 if profile.get("city")    else 0   # Where do they want property?
    score += 15 if profile.get("intent")  else 0   # Buy / rent / sell?
    score += 15 if profile.get("budget")  else 0   # Can they afford it?
    score += 10 if profile.get("type")    else 0   # What kind of property?
    score += 10 if profile.get("purpose") else 0   # Self-use or investment?
    score +=  5 if profile.get("urgency") else 0   # How soon do they need it?

    if score >= 75:
        quality = "Hot"
    elif score >= 45:
        quality = "Warm"
    else:
        quality = "Cold"

    return score, quality


def save_lead(profile: dict) -> dict:
    """
    Build a clean lead dict from the caller's profile, save it to
    leads.json, and immediately sync leads.csv.

    Parameters
    ----------
    profile : dict
        Raw profile collected by assistant.py during the conversation.
        May contain extra internal keys — we extract only what we need.

    Returns
    -------
    dict
        The saved lead record (useful for building the final response
        message back to the caller).

    NOTE: We re-calculate score here (not just copy profile["lead_score"])
    to ensure the final saved score is always fresh and consistent,
    even if the profile score was set at an earlier point in the call.
    """
    leads = _load_leads()
    score, quality = calculate_lead_score(profile)

    # Build a clean, flat lead record — only the fields we care about.
    lead = {
        "created_at":      datetime.now().isoformat(timespec="seconds"),
        "name":            profile.get("name", ""),
        "phone":           profile.get("phone", ""),
        "city":            profile.get("city", ""),
        "intent":          profile.get("intent", ""),
        "property_type":   profile.get("type", ""),      # 'type' is a Python builtin; rename to 'property_type'
        "budget":          profile.get("budget", ""),
        "purpose":         profile.get("purpose", ""),
        "urgency":         profile.get("urgency", ""),
        "lead_score":      score,
        "lead_quality":    quality,
        "summary":         profile.get("summary", ""),
        "handoff_required": profile.get("handoff_required", False),
    }

    leads.append(lead)

    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    # Keep the CSV in sync every time a new lead is saved.
    export_leads_csv()

    return lead


def export_leads_csv() -> str:
    """
    Write all leads from leads.json into leads.csv.

    Called automatically by save_lead() after every new lead.
    Also called directly by main.py for the /export-leads endpoint
    so the sales team can download a fresh CSV at any time.

    Returns
    -------
    str
        Path to the CSV file ("leads.csv").

    WHY DictWriter?
        It lets us map dict keys → CSV columns by name, so the column
        order is always controlled by LEAD_FIELDS, regardless of the
        order keys appear in the dict.

    WHY newline="" in open()?
        Required by Python's csv module on Windows to avoid writing an
        extra blank line between every row.
    """
    leads = _load_leads()

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_FIELDS)
        writer.writeheader()

        for lead in leads:
            # extrasaction is "ignore" by default in DictWriter, but we
            # explicitly pick only LEAD_FIELDS to be safe and consistent.
            writer.writerow({field: lead.get(field, "") for field in LEAD_FIELDS})

    return CSV_FILE