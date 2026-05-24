

import os
import time
import shutil
import asyncio
import traceback
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import PlainTextResponse, Response, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse


from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.assistant import handle_conversation_text, handle_conversation_audio, clear_history
from src.stt_whisper import transcribe_audio
from src.data.lead_store import load_leads, export_leads_csv
from src.data.live_store import get_live

import uvicorn



limiter = Limiter(key_func=get_remote_address)

app = FastAPI()

app.state.limiter = limiter


app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.mount("/static", StaticFiles(directory="static"), name="static")



ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "changeme-set-in-env")


def require_api_key(request: Request):
    
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != ADMIN_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized — invalid or missing API key. "
                   "Send: Authorization: Bearer <your-key>"
        )



async def cleanup_audio_files():
    
    audio_dir = Path("static/audio")
    while True:
        await asyncio.sleep(1800)   # sleep 30 minutes, then run cleanup
        if audio_dir.exists():
            now = time.time()
            deleted = 0
            for f in audio_dir.glob("*.mp3"):
                
                if now - f.stat().st_mtime > 1800:
                    try:
                        f.unlink()
                        deleted += 1
                    except Exception:
                        pass    # if a file is locked or already gone, skip it
            if deleted:
                print(f"Audio cleanup: removed {deleted} old MP3 files from static/audio/")


@app.on_event("startup")
async def startup_event():
    
    asyncio.create_task(cleanup_audio_files())



@app.get("/")
async def root():
    
    return {"status": "AI Property Voice Assistant running"}



@app.get("/live")
async def live_data():
    
    return JSONResponse(get_live())


@app.get("/leads", dependencies=[Depends(require_api_key)])
async def get_leads():
    
    return JSONResponse({"leads": load_leads()})


@app.get("/export-leads", dependencies=[Depends(require_api_key)])
async def export_leads():
    
    csv_file = export_leads_csv()
    return FileResponse(csv_file, media_type="text/csv", filename="leads.csv")


@app.get("/stats")
async def get_stats():
    
    leads = load_leads()
    if not leads:
        return JSONResponse({"total": 0, "hot": 0, "warm": 0, "cold": 0, "avg_score": 0})

    hot  = sum(1 for lead in leads if lead.get("lead_quality") == "Hot")
    warm = sum(1 for lead in leads if lead.get("lead_quality") == "Warm")
    cold = sum(1 for lead in leads if lead.get("lead_quality") == "Cold")

    
    scores = [lead.get("lead_score", 0) for lead in leads if lead.get("lead_score") is not None]
    avg    = round(sum(scores) / len(scores)) if scores else 0

    return JSONResponse({
        "total":     len(leads),
        "hot":       hot,
        "warm":      warm,
        "cold":      cold,
        "avg_score": avg
    })



@app.post("/voice-input")
@limiter.limit("10/minute")
async def voice_input(
    request: Request,               # required by slowapi — do not remove
    file: UploadFile = File(...),
    session_id: str = Form("web-user")
):
    
    file_path = None

    try:
        os.makedirs("temp_audio", exist_ok=True)

        filename  = file.filename or "audio.webm"
        file_path = os.path.join("temp_audio", filename)

        # Stream the uploaded file to disk.
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        user_text   = transcribe_audio(file_path)
        print("Transcribed:", user_text)

        ai_response = handle_conversation_text(
            user_text=user_text,
            conversation_id=session_id
        )

        
        from src.assistant import profile_store
        profile = profile_store.get(session_id, {})

        return JSONResponse({
            "user_text": user_text,
            "response":  ai_response,
            "language":  profile.get("language", "English"),
            "profile": {
                "intent":       profile.get("intent"),
                "city":         profile.get("city"),
                "budget":       profile.get("budget"),
                "type":         profile.get("type"),
                "purpose":      profile.get("purpose"),
                "phone":        profile.get("phone"),
                "lead_score":   profile.get("lead_score", 0),
                "lead_quality": profile.get("lead_quality", "Cold"),
            }
        })

    except Exception as e:
        print("/voice-input ERROR:", str(e))
        traceback.print_exc()

        # Return 500 with a safe fallback — never let an exception leave
        # the browser with no response.
        return JSONResponse(
            {
                "user_text": "",
                "response":  "Sorry, something went wrong.",
                "language":  "English",
                "profile":   {}
            },
            status_code=500
        )

    finally:
        # Always clean up the temp file — even if transcription failed.
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@app.post("/ask")
@limiter.limit("20/minute")
async def ask_text(
    request: Request,               # required by slowapi — do not remove
    text: str = Form(...),
    session_id: str = Form("web-user")
):
    
    
    if not text or not text.strip():
        return JSONResponse({"response": "Please say or type something.", "profile": {}})

    try:
        ai_response = handle_conversation_text(
            user_text=text.strip(),
            conversation_id=session_id
        )

        from src.assistant import profile_store
        profile = profile_store.get(session_id, {})

        return JSONResponse({
            "user_text": text.strip(),
            "response":  ai_response,
            "language":  profile.get("language", "English"),
            "profile": {
                "intent":       profile.get("intent"),
                "city":         profile.get("city"),
                "budget":       profile.get("budget"),
                "type":         profile.get("type"),
                "purpose":      profile.get("purpose"),
                "phone":        profile.get("phone"),
                "lead_score":   profile.get("lead_score", 0),
                "lead_quality": profile.get("lead_quality", "Cold"),
            }
        })

    except Exception as e:
        print("/ask ERROR:", str(e))
        traceback.print_exc()
        return JSONResponse(
            {"response": "Sorry, something went wrong.", "profile": {}},
            status_code=500
        )


@app.post("/reset-chat")
async def reset_chat(session_id: str = Form("web-user")):
    
    clear_history(session_id)
    return JSONResponse({"status": "reset"})




@app.api_route("/answer-call", methods=["GET", "POST"])
async def answer_call(request: Request):
    
    print("TWILIO HIT /answer-call | Method:", request.method)

    resp   = VoiceResponse()
    gather = resp.gather(
        input="speech",
        action="/process-recording",   # where to send the transcription
        method="POST",
        speechTimeout="auto"           # Twilio auto-detects when caller stops speaking
    )

    gather.say("Hi, I am your property assistant. How can I help you?")
    resp.redirect("/answer-call")      # if no speech → ask again

    return Response(content=str(resp), media_type="text/xml")


@app.post("/process-recording", response_class=PlainTextResponse)
async def process_recording(
    SpeechResult: str = Form(None),
    CallSid: str = Form(...)
):
    
    print("TWILIO HIT /process-recording | CallSid:", CallSid, "| Speech:", SpeechResult)

    user_text = SpeechResult or ""

    try:
        reply_text, should_hang_up = handle_conversation_audio(user_text, CallSid)
    except Exception as e:
        print("ERROR in /process-recording:", str(e))
        traceback.print_exc()

        # On error — apologise and loop back (don't drop the call silently).
        resp = VoiceResponse()
        resp.say("Sorry, something went wrong.")
        resp.redirect("/answer-call")
        return str(resp)

    resp = VoiceResponse()
    resp.say(reply_text)

    if should_hang_up:
        resp.hangup()                  # caller said bye → end the call
    else:
        resp.redirect("/answer-call")  # keep the loop going

    return str(resp)



if __name__ == "__main__":
    print("Starting AI Property Voice Assistant...")

    
    uvicorn.run(app, host="0.0.0.0", port=8000)