
import re
import json

from src.groq_integration import chat_with_gpt
from src.data.lead_store import save_lead, calculate_lead_score
from src.data.property_data import format_recommendations
from src.utils.rag_integration import get_relevant_context
from src.data.live_store import update_live
from src.data.conversation_store import save_message



conversation_store  = {}   
profile_store       = {}   
intro_done_store    = {}   
lead_saved_store    = {}   

EXIT_PHRASES = ["bye", "exit", "stop", "end", "thank you", "thanks"]



def clear_history(conversation_id: str) -> None:
    
    conversation_store.pop(conversation_id, None)
    profile_store.pop(conversation_id, None)
    intro_done_store.pop(conversation_id, None)
    lead_saved_store.pop(conversation_id, None)



def is_bad_transcription(text: str) -> bool:
    
    text = (text or "").strip().lower()
    noise_words = {"", ".", "...", "tak", "like", "go"}
    return text in noise_words or len(text) <= 2



def detect_language(text: str) -> str:
    
    text = (text or "").lower()

    marathi_words = ["aahe", "kay", "tumhala", "pahije", "majha", "mala"]
    hindi_words   = ["hai", "kya", "ka", "ki", "mera", "mujhe", "chahiye", "budget"]

    # Check Marathi first — it has more distinctive markers than Hindi.
    if any(word in text for word in marathi_words):
        return "Marathi"

    if any(word in text for word in hindi_words):
        return "Hindi"

    return "English"




def words_to_digits(text: str) -> str:
    
    mapping = {
        "zero": "0", "oh": "0", "o": "0",
        "one": "1", "won": "1",
        "two": "2", "to": "2", "too": "2",
        "three": "3",
        "four": "4", "for": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8", "ate": "8",
        "nine": "9",
    }

    cleaned = text.lower().replace(",", " ").replace(".", " ").replace("-", " ")
    return "".join(
        word if word.isdigit() else mapping.get(word, "")
        for word in cleaned.split()
    )



def safe_json(text: str) -> dict:
    
    try:
        start = text.find("{")
        end   = text.rfind("}") + 1

        if start == -1 or end == 0:
            return {}

        return json.loads(text[start:end])
    except Exception:
        return {}




def extract_rule_based(text: str, profile: dict) -> dict:
    
    lower = text.lower()

    # ── CITY ──────────────────────────────────────────────────────
    if   "mumbai"    in lower or "bombay"    in lower: profile["city"] = "Mumbai"
    elif "pune"      in lower:                         profile["city"] = "Pune"
    elif "delhi"     in lower:                         profile["city"] = "Delhi"
    elif "bangalore" in lower or "bengaluru" in lower: profile["city"] = "Bangalore"

    # ── INTENT ────────────────────────────────────────────────────
    if   "buy"      in lower or "purchase" in lower: profile["intent"] = "buy"
    elif "rent"     in lower:                         profile["intent"] = "rent"
    elif "sell"     in lower:                         profile["intent"] = "sell"

    # ── PROPERTY TYPE ─────────────────────────────────────────────
    if   "1bhk" in lower or "1 bhk" in lower or "one bhk"   in lower: profile["type"] = "1BHK"
    elif "2bhk" in lower or "2 bhk" in lower or "two bhk"   in lower: profile["type"] = "2BHK"
    elif "3bhk" in lower or "3 bhk" in lower or "three bhk" in lower: profile["type"] = "3BHK"
    elif "villa"     in lower:                                          profile["type"] = "villa"
    elif "plot"      in lower:                                          profile["type"] = "plot"
    elif "flat"      in lower or "apartment" in lower:                  profile["type"] = "apartment"

    # ── PURPOSE ───────────────────────────────────────────────────
    if   "investment" in lower or "invest" in lower:  profile["purpose"] = "investment"
    elif "self"       in lower or "family" in lower \
      or "personal"   in lower:                        profile["purpose"] = "self-use"

    # ── URGENCY ───────────────────────────────────────────────────
    if   "urgent"     in lower or "immediate" in lower: profile["urgency"] = "immediate"
    elif "this week"  in lower:                          profile["urgency"] = "this week"
    elif "this month" in lower:                          profile["urgency"] = "this month"

    # ── HANDOFF ───────────────────────────────────────────────────
    # If the caller asks for an agent, callback, or site visit, flag it.
    # final_response() will skip recommendations and just confirm expert callback.
    if any(w in lower for w in ["call me", "callback", "agent", "visit"]):
        profile["handoff_required"] = True

    
    is_phone_message = bool(re.search(r"\b[6-9]\d{9}\b", lower))

    
    if not profile.get("budget") and not is_phone_message:

        
        budget_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|lacs|crore|cr)\b",
            lower
        )

        if budget_match:
            number = budget_match.group(1)
            unit   = budget_match.group(2)
            unit = "lakh" if unit in ("lakh", "lakhs", "lac", "lacs") else "crore"
            profile["budget"] = f"{number} {unit}"

        else:
            
            bare_match = re.search(r"\b(\d{2,})\b", lower)
            if bare_match:
                number = bare_match.group(1)

                
                if not re.match(r"^(19|20)\d{2}$", number):
                    profile["budget"] = f"{number} lakh"

    
    phone_match = re.search(r"\b[6-9]\d{9}\b", lower)

    if phone_match:
        profile["phone"] = phone_match.group(0)
        profile.pop("partial_phone", None)   # clean up any partial accumulation

    else:
        
        spoken_digits = words_to_digits(text)
        if spoken_digits:
            existing = profile.get("partial_phone", "")
            combined = existing + spoken_digits

            if len(combined) >= 10:
                profile["phone"] = combined[-10:]      # take the last 10 digits
                profile.pop("partial_phone", None)
            elif len(combined) >= 3:
                profile["partial_phone"] = combined    # save for next turn

    return profile




def extract_with_llm(user_text: str, profile: dict) -> dict:
    
    prompt = f"""
Extract real estate lead details from this message.

Existing profile:
{json.dumps(profile)}

User message:
{user_text}

Return only JSON with these keys:
name, phone, city, intent, type, budget, purpose, urgency, handoff_required

Rules:
intent = buy/rent/sell/null
type = 1BHK/2BHK/3BHK/apartment/villa/plot/null
purpose = self-use/investment/null
handoff_required = true if user wants callback, site visit, agent, or expert
missing value = null
"""

    try:
        response = chat_with_gpt(prompt)
        data = safe_json(response)

        for key, value in data.items():
            if value not in [None, "", "null", "None"]:

                
                if key == "budget" and profile.get("phone") and str(value) == profile.get("phone"):
                    continue

                profile[key] = value

    except Exception as e:
        print("LLM extraction failed:", e)   # log but don't crash the call

    return profile



def extract_info(text: str, profile: dict) -> dict:
    
    profile = extract_rule_based(text, profile)
    profile = extract_with_llm(text, profile)

    score, quality = calculate_lead_score(profile)
    profile["lead_score"]   = score
    profile["lead_quality"] = quality

    return profile



def is_complete(profile: dict) -> bool:
    
    return all(profile.get(k) for k in ["intent", "city", "budget", "type", "phone"])


def next_question(profile: dict, lang: str = "English") -> str | None:
    
    if lang == "Hindi":
        questions = {
            "intent":  "Aap property buy, rent ya sell karna chahte ho?",
            "city":    "Aapko property kis city mein chahiye?",
            "budget":  "Aapka budget kitna hai? Jaise fifty lakh ya sixty lakh.",
            "type":    "Aapko kaunsi property chahiye? Jaise 1BHK, 2BHK, villa ya plot.",
            "purpose": "Ye self-use ke liye hai ya investment ke liye?",
            "phone":   "Please apna 10 digit phone number dheere dheere bataye.",
        }
    elif lang == "Marathi":
        questions = {
            "intent":  "Tumhala property buy, rent ki sell karaychi aahe?",
            "city":    "Tumhala property kontya city madhe pahije?",
            "budget":  "Tumcha budget kiti aahe? Udaharanarth fifty lakh kiwa sixty lakh.",
            "type":    "Tumhala kontya type chi property pahije? Jaise 1BHK, 2BHK, villa kiwa plot.",
            "purpose": "He self-use sathi aahe ki investment sathi?",
            "phone":   "Kripaya tumcha 10 digit phone number halu halu sanga.",
        }
    else:
        questions = {
            "intent":  "Are you looking to buy, rent, or sell a property?",
            "city":    "Which city are you looking in?",
            "budget":  "What is your budget? For example, fifty lakh or sixty lakh.",
            "type":    "What type of property do you want? For example, 1BHK, 2BHK, villa, or plot.",
            "purpose": "Is this for self-use or investment?",
            "phone":   "Please share your 10 digit phone number slowly, digit by digit.",
        }

    # Ask in priority order — first missing field wins.
    for field in ["intent", "city", "budget", "type", "purpose"]:
        if not profile.get(field):
            return questions[field]

    # Phone last — handle partial accumulation.
    if not profile.get("phone"):
        partial = profile.get("partial_phone")
        if partial:
            remaining = 10 - len(partial)
            return f"I got {partial}. Please tell me the remaining {remaining} digits slowly."
        return questions["phone"]

    return None   # all fields collected — caller gets final response




def save_if_ready(profile: dict, conversation_id: str) -> dict | None:
    
    if not is_complete(profile):
        return None

    if lead_saved_store.get(conversation_id):
        return None   # already saved — skip

    profile["summary"] = (
        f"{profile.get('intent')} {profile.get('type')} in {profile.get('city')} "
        f"with budget {profile.get('budget')}."
    )

    saved = save_lead(profile)
    lead_saved_store[conversation_id] = True   # mark as saved so we don't save twice
    return saved



def final_response(profile: dict) -> str:
    
    recommendations = format_recommendations(profile)

    if profile.get("handoff_required"):
        return (
            "Thank you. I have saved your requirement. "
            "Our property expert will call you shortly."
        )

    return (
        "Thank you. I have saved your requirement. "
        f"You are looking to {profile.get('intent')} a {profile.get('type')} "
        f"in {profile.get('city')} with budget {profile.get('budget')}. "
        f"Lead quality is {profile.get('lead_quality')} with score {profile.get('lead_score')}. "
        f"{recommendations} "
        "A property expert can contact you soon."
    )




def handle_conversation_text(user_text: str, conversation_id: str = "web-user") -> str:
    """
    Process one turn of the conversation and return the assistant's reply.

    This is the single entry point called by main.py for both web (/ask, /voice-input)
    and phone (Twilio webhook /process-recording) interactions.

    TURN LOGIC (in order):
        1. Validate input — bad transcription? Ask to repeat.
        2. Detect language.
        3. Extract info from message → update profile.
        4. Update live store (admin dashboard sees current profile).
        5. Save user message to conversation history (disk + memory).
        6. Exit phrase? Save lead + return summary + clear session.
        7. First turn + no intent yet? Ask the opening question.
        8. Profile complete? Save lead + return final response.
        9. Profile incomplete? Return next missing-field question.
       10. Profile complete but user still talking? Use RAG + LLM to answer.

    Parameters
    ----------
    user_text : str
        The caller's transcribed or typed message.
    conversation_id : str
        Unique session ID. Browser generates a UUID for web chat;
        Twilio provides CallSid for phone calls.

    Returns
    -------
    str
        The assistant's reply — short, natural, spoken-friendly.
    """
    user_text = (user_text or "").strip()
    print("User said:", user_text)

    # Step 1: Guard against bad audio / empty transcriptions.
    if is_bad_transcription(user_text):
        return "Sorry, I could not hear that clearly. Please say it again slowly."

    lang = detect_language(user_text)

    # Initialise session stores if this is the first message.
    if conversation_id not in profile_store:
        profile_store[conversation_id] = {}
    if conversation_id not in conversation_store:
        conversation_store[conversation_id] = []

    profile = profile_store[conversation_id]
    profile["language"] = lang

    # Step 2: Extract info and update live dashboard.
    profile = extract_info(user_text, profile)
    profile_store[conversation_id] = profile
    update_live(conversation_id, profile)

    # Step 3: Persist user message.
    conversation_store[conversation_id].append({"role": "user", "content": user_text})
    save_message(conversation_id, "user", user_text, profile)

    # Step 4: Handle exit.
    if any(phrase in user_text.lower() for phrase in EXIT_PHRASES):
        save_if_ready(profile, conversation_id)

        summary = (
            f"Thanks. Your requirement is: {profile.get('intent', 'not provided')} property, "
            f"city {profile.get('city', 'not provided')}, "
            f"budget {profile.get('budget', 'not provided')}, "
            f"type {profile.get('type', 'not provided')}, "
            f"phone {profile.get('phone', 'not provided')}."
        )

        save_message(conversation_id, "assistant", summary, profile)
        clear_history(conversation_id)
        return summary

    # Step 5: First message and intent unknown — ask the opening question.
    # (Avoids jumping straight into a structured question before the caller
    #  has said anything — makes the interaction feel more natural.)
    if not intro_done_store.get(conversation_id):
        intro_done_store[conversation_id] = True

        if not profile.get("intent"):
            response = next_question(profile, lang)
            conversation_store[conversation_id].append({"role": "assistant", "content": response})
            save_message(conversation_id, "assistant", response, profile)
            return response

    # Step 6: Lead complete — save and return final message.
    saved = save_if_ready(profile, conversation_id)
    if saved:
        response = final_response(profile)
        conversation_store[conversation_id].append({"role": "assistant", "content": response})
        save_message(conversation_id, "assistant", response, profile)
        return response

    # Step 7: Profile still incomplete — ask the next missing field.
    question = next_question(profile, lang)
    if question:
        conversation_store[conversation_id].append({"role": "assistant", "content": question})
        save_message(conversation_id, "assistant", question, profile)
        return question

    # Step 8: Profile is complete and user is asking a free-form question.
    # Use RAG to inject domain knowledge, then let the LLM respond naturally.
    rag_context = get_relevant_context(user_text)

    prompt = f"""
You are a real estate GenAI voice assistant.

Reply in {lang} language.

User profile:
{json.dumps(profile)}

Relevant real estate knowledge:
{rag_context}

User message:
{user_text}

Reply shortly and naturally.
Ask only one useful follow-up question.
Do not use markdown.
"""

    # Pass last 6 messages as context — enough history without hitting token limits.
    response = chat_with_gpt(prompt, history=conversation_store[conversation_id][-6:])

    conversation_store[conversation_id].append({"role": "assistant", "content": response})
    save_message(conversation_id, "assistant", response, profile)

    return response or "Please say that again slowly."




def handle_conversation_audio(user_text: str, conversation_id: str = "call") -> tuple[str, bool]:
    """
    Wrapper for phone call handling — same logic as text, plus hang-up signal.

    main.py calls this for Twilio webhook requests. Returns a tuple so
    main.py knows whether to hang up the call (send <Hangup> in TwiML).

    Returns
    -------
    (reply, should_hang_up) : tuple
        reply          → text to be spoken by Twilio TTS
        should_hang_up → True if the caller said an exit phrase
    """
    reply          = handle_conversation_text(user_text, conversation_id)
    should_hang_up = any(phrase in (user_text or "").lower() for phrase in EXIT_PHRASES)
    return reply, should_hang_up