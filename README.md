# 🏛️ AI Property Sales Assistant

> An AI-powered real estate voice assistant that handles phone calls and browser conversations automatically — collecting lead information, scoring leads, and recommending properties in English, Hindi, and Marathi.

---

## 📌 What This Project Does

When a customer calls your Twilio phone number **or** visits your website, this AI assistant:

1. **Greets the customer** and starts a natural conversation
2. **Asks structured questions** — city, budget, property type, purpose
3. **Detects the language** automatically — English, Hindi, or Marathi
4. **Extracts information** using rule-based logic first, then Groq LLM for anything indirect
5. **Collects the phone number** (always asked last — less intrusive)
6. **Saves a scored lead** — Hot 🔥 / Warm 🌡️ / Cold ❄️ — to JSON and CSV
7. **Recommends matching properties** based on budget, city, and type
8. Works **24 hours a day**, no human agent needed

---

## 🗂️ Project Structure

```
AI_Property_Assistant/
│
├── main.py                    # FastAPI server — all HTTP routes live here
├── assistant.py               # The brain — full conversation logic
├── groq_integration.py        # Connects to Groq API (Llama 3 LLM)
├── stt_whisper.py             # Speech-to-text for web browser (Whisper AI)
├── tts_synthesis.py           # Text-to-speech for web browser (ElevenLabs)
├── admin_dashboard.py         # Admin panel to view live sessions
│
├── config/
│   └── config.py              # Loads all API keys from .env file
│
├── src/
│   ├── data/
│   │   ├── lead_store.py      # Save, score, and export leads
│   │   ├── property_data.py   # Property database + matching engine
│   │   ├── conversation_store.py  # Save every message to disk
│   │   └── live_store.py      # Real-time session data for dashboard
│   │
│   └── utils/
│       ├── rag_integration.py # Keyword-based RAG for free-form Q&A
│       ├── error_handling.py  # Reusable error utilities
│       └── audio_processing.py
│
├── static/
│   └── index.html             # Browser chat UI (mic + text input)
│
├── leads.json                 # All saved leads (auto-generated)
├── leads.csv                  # Leads export for Excel (auto-generated)
├── conversations.json         # Full conversation history (auto-generated)
├── requirements.txt           # Python dependencies
└── .env                       # Your API keys (NEVER commit this to Git)
```

---

## 🔁 How It Works — Full Flow

### 📱 Phone Call Path

```
Customer dials the Twilio number
        ↓
Twilio receives the call
(Twilio is a cloud phone service — it owns the phone number)
        ↓
Twilio sends HTTP request to our server
"Someone just called — what should I say?"
        ↓
main.py → /answer-call
Builds a TwiML XML response:
"Say this greeting. Then listen for speech."
Sends XML back to Twilio
        ↓
Twilio speaks the greeting to the caller
"Hi, I am your property assistant. How can I help you?"
        ↓
Caller speaks their response
        ↓
Twilio automatically converts caller's voice → text
(Twilio has its own built-in STT — NO Whisper needed here)
        ↓
Twilio sends POST request to main.py → /process-recording
with two things:
  SpeechResult = "I want to buy a 2BHK in Mumbai"
  CallSid      = "CA1234xyz"  ← unique ID for this call
        ↓
assistant.py → Rule-based extraction runs first
               Then Groq LLM fills gaps if needed
               Final reply text is returned
        ↓
main.py builds TwiML response:
<Say> reply text </Say>
<Redirect> /answer-call </Redirect>  ← keeps the loop going
        ↓
Twilio converts reply text → voice using its own built-in TTS
(NO ElevenLabs needed here — Twilio speaks directly)
        ↓
Caller hears the reply on their phone
        ↓
Loop continues until caller says "bye" or "thanks"
        ↓
main.py sends <Hangup/> in TwiML
Call ends. Lead saved to leads.json and leads.csv
```

---

### 🌐 Web Browser Path

```
User speaks into mic
        ↓
Browser records .webm audio file
(using browser's built-in MediaRecorder API)
        ↓
stt_whisper.py → Whisper AI model converts audio → text
(Groq Whisper API, model: whisper-large-v3)
        ↓
assistant.py → Rule-based extraction runs first
               Then Groq LLM fills gaps if needed
               Final reply text is returned
        ↓
tts_synthesis.py → ElevenLabs converts reply text → MP3 file
(saved to static/audio/ folder)
        ↓
Browser downloads and plays the MP3 audio to the user
```

---

### 🧠 The Brain — What Happens Inside `assistant.py`

Every single message — from phone or browser — goes through the same 10-step logic:

```
Message arrives
        ↓
Step 1 → Is it bad audio / gibberish?
         YES → "Sorry, please say that again"
         NO  → continue
        ↓
Step 2 → Detect language
         English / Hindi / Marathi (keyword matching)
        ↓
Step 3 → First message for this session?
         YES → create empty profile in memory
        ↓
Step 4 → Run extraction pipeline (see below)
        ↓
Step 5 → Update live admin dashboard
        ↓
Step 6 → Save message to conversations.json
        ↓
Step 7 → Did user say "bye" / "thanks"?
         YES → save lead + return summary + clear session
        ↓
Step 8 → First turn and intent still unknown?
         YES → ask opening question
        ↓
Step 9 → Are all 5 required fields filled?
         YES → save lead + return property recommendations
        ↓
Step 10 → Still missing fields?
          YES → ask next missing field question
          NO  → use RAG + LLM to answer free-form question
```

---

### 🔍 The Extraction Pipeline — How Profile Fields Are Captured

Every message goes through **two layers**:

**Layer 1 — Rule-based (runs first, always)**
Fast Python `if/elif` checks and regex. Free, instant, no API call needed.

```
"mumbai" in text    →  city = "Mumbai"
"buy" in text       →  intent = "buy"
"2bhk" in text      →  type = "2BHK"
"50 lakh" in text   →  budget = "50 lakh"
[6-9]\d{9} regex    →  phone = "9876543210"
```

**Layer 2 — Groq LLM (runs after, fills the gaps)**
Only runs if fields are still empty after rule-based. Handles indirect phrasing and mixed language.

```
"mujhe Pune mein invest karna hai"
         ↓
Rule-based misses intent (no "buy"/"rent" keyword)
         ↓
Groq LLM understands:
    city    = "Pune"         ✅ filled
    purpose = "investment"   ✅ filled
    intent  = "buy"          ✅ filled by LLM (gap filled)
```

**Why both layers exist:**
- Rule-based handles ~80% of cases instantly at zero cost
- Groq LLM handles the remaining ~20% (indirect / Hindi / Marathi)
- LLM is never allowed to overwrite a value already set by rule-based

---

### 📊 Lead Scoring — How Hot/Warm/Cold Is Decided

Every lead gets a score from 0–100 based on fields collected:

| Field | Points | Why |
|-------|--------|-----|
| Phone number | 30 pts | Without it, sales team cannot call back |
| City | 15 pts | Location is critical for property matching |
| Intent (buy/rent/sell) | 15 pts | Changes the entire sales approach |
| Budget | 15 pts | Qualifies whether the lead is serious |
| Property type | 10 pts | Narrows down which properties to show |
| Purpose (self/invest) | 10 pts | Changes recommended properties |
| Urgency | 5 pts | Immediate buyers need faster follow-up |

| Score | Label | Action |
|-------|-------|--------|
| 75 and above | 🔥 Hot | Call immediately |
| 45 to 74 | 🌡️ Warm | Follow up soon |
| Below 45 | ❄️ Cold | Early research stage |

---

## 🛠️ Tech Stack

| Tool | Purpose | Why Chosen |
|------|---------|-----------|
| **FastAPI** | Web server framework | Faster than Flask, supports async, auto-generates API docs |
| **Twilio** | Phone call infrastructure | Handles real phone calls, built-in STT, TwiML webhooks |
| **Groq API** | Runs Llama 3 LLM | Up to 10x faster than OpenAI — critical for low-latency voice calls |
| **Llama 3** | AI language model | Fills extraction gaps, answers free-form property questions |
| **Whisper** | Speech-to-text (web) | Converts browser mic audio to text — Twilio STT handles phone calls |
| **ElevenLabs** | Text-to-speech (web) | Natural voice output in browser — Twilio `<Say>` handles phone calls |
| **Ngrok** | Development tunnel | Gives local server a public URL so Twilio can reach it during testing |
| **slowapi** | Rate limiting | Prevents API bill abuse — max 10 voice requests per minute per IP |
| **python-dotenv** | Secret management | Loads API keys from `.env` file, keeps secrets out of source code |

---

## ⚙️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check — confirms server is running |
| `GET/POST` | `/answer-call` | Twilio webhook — first hit when a call comes in |
| `POST` | `/process-recording` | Twilio webhook — receives what the caller said |
| `POST` | `/voice-input` | Web browser — upload audio file, get AI reply |
| `POST` | `/ask` | Web browser — send plain text, get AI reply |
| `POST` | `/reset-chat` | Web browser — clear session and start fresh |
| `GET` | `/live` | Admin — real-time active session profiles |
| `GET` | `/leads` | Admin — all saved leads as JSON 🔒 Protected |
| `GET` | `/export-leads` | Admin — download leads.csv 🔒 Protected |
| `GET` | `/stats` | Summary counts — total, hot, warm, cold leads |

---

## 🚀 Setup & Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/yourusername/ai-property-assistant.git
cd ai-property-assistant
```

### Step 2 — Create a virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Mac/Linux
source venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
pip install slowapi  # rate limiting (add to requirements.txt if missing)
```

### Step 4 — Create your `.env` file

Create a file named `.env` in the project root and add your keys:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_VOICE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
NGROK_URL=https://abc123.ngrok.io
ADMIN_API_KEY=your-secret-admin-key-here
```

> ⚠️ Never commit `.env` to Git. It is already listed in `.gitignore`.

### Step 5 — Run the server

```bash
python main.py
```

Server starts at: `http://localhost:8000`
Web chat UI at: `http://localhost:8000/static/index.html`

### Step 6 — For phone calls (local development only)

Start Ngrok in a separate terminal to expose your local server:

```bash
ngrok http 8000
```

Copy the `https://` URL that Ngrok gives you.
Go to your Twilio console → Phone Numbers → your number → Voice Configuration.
Set the webhook URL to: `https://your-ngrok-url.ngrok.io/answer-call`

> In production, replace Ngrok with your actual deployed server URL.

---

## 🔑 Getting API Keys

| Service | Where to get it | Free tier? |
|---------|----------------|------------|
| Groq | [console.groq.com](https://console.groq.com) | ✅ Yes — generous free tier |
| Twilio | [twilio.com/console](https://www.twilio.com/console) | ✅ Yes — trial account available |
| ElevenLabs | [elevenlabs.io](https://elevenlabs.io) | ✅ Yes — 10,000 characters/month free |
| Ngrok | [ngrok.com](https://ngrok.com) | ✅ Yes — free tier available |

---

## 🌍 Multilingual Support

The assistant automatically detects and responds in:

| Language | Detection Method |
|----------|-----------------|
| **Marathi** | Keywords: "aahe", "tumhala", "pahije", "majha" |
| **Hindi** | Keywords: "hai", "kya", "mujhe", "chahiye" |
| **English** | Default — used when no other language is detected |

Marathi is checked before Hindi because some words appear in both languages.

---

## 📁 Data Files

| File | Format | Purpose | Who uses it |
|------|--------|---------|-------------|
| `leads.json` | JSON | All saved leads with full profile | App reads at runtime |
| `leads.csv` | CSV | Same leads in spreadsheet format | Sales team opens in Excel |
| `conversations.json` | JSON | Every message from every session | Conversation history log |
| `static/audio/*.mp3` | MP3 | TTS audio files for browser playback | Auto-deleted after 30 min |

---

## 🔒 Security Features

- **API key protection** — `/leads` and `/export-leads` require `Authorization: Bearer <key>` header
- **Rate limiting** — `/voice-input` limited to 10 requests/minute per IP address
- **Unique session IDs** — each browser tab gets a UUID so sessions never overlap
- **Environment variables** — all API keys stored in `.env`, never in source code
- **Auto cleanup** — MP3 files older than 30 minutes deleted automatically

---

## 🐛 Known Bug Fixed

**The Budget-Phone Bug:**
The original budget regex `(\d+)\s*(lakh|crore)?` had an optional unit — meaning it matched ANY number including the phone number. When a caller gave their 10-digit phone number, it was being saved as the budget (e.g. "7410776326 lakh").

**Fix:** Three guards added to the budget extraction:
1. Only extract budget if it is not already filled
2. Skip if the message contains a 10-digit mobile number (starts with 6-9)
3. Require either a unit word OR at least 2 digits — single digits are ignored

---

## 📞 How Phone Numbers Are Collected

Callers on a voice call speak their number digit by digit:
*"nine eight two zero one two three four five six"*

The `words_to_digits()` function converts spoken words to digits:

```
"nine" → 9    "eight" → 8    "two" → 2    "zero" → 0
"to"   → 2    "for"   → 4    "won" → 1    "ate"  → 8
```

Digits are accumulated across multiple turns until 10 digits are collected.
If a caller pauses mid-number, the AI says: *"I got 9820. Please tell me the remaining 6 digits slowly."*

---

## 🗺️ Roadmap — What to Add Next

- [ ] Replace hardcoded `PROPERTY_DB` with a real database (PostgreSQL / MongoDB)
- [ ] Add Vector RAG (Pinecone / FAISS) when property listings exceed 200+
- [ ] WebSocket support for real-time profile updates instead of polling
- [ ] WhatsApp integration via Twilio WhatsApp API
- [ ] Admin dashboard with charts — lead trends, conversion rates
- [ ] Multi-agent support for different cities / property types

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m "Add: your feature description"`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

---


---

## 👤 Author

Built by **Deepak kawate**
- GitHub: [@yourusername](https://github.com/Deepak77-ai)
- LinkedIn: [Your LinkedIn](https://www.linkedin.com/in/deepak-kawate-a5b660343/)
---

> **Note for interviewers:** This project demonstrates end-to-end AI integration — voice STT, LLM-based extraction, lead scoring, multilingual NLP, and real-time phone call handling using Twilio webhooks. The extraction pipeline uses a two-layer approach (rule-based + LLM) to minimize API costs while maximizing accuracy.
