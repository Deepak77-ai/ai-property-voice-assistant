

import os
from groq import Groq
from dotenv import load_dotenv


load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))



def generate_response(prompt: str, history: list = None) -> str:
    
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI real-estate voice assistant. "
                    "Reply shortly, naturally, and ask only one question at a time."
                ),
            }
        ]

        # Append conversation history (if provided) before the current prompt.
        if history:
            for msg in history:
                if msg.get("role") in ["user", "assistant"]:   # skip any malformed entries
                    messages.append({
                        "role":    msg["role"],
                        "content": msg["content"],
                    })

        # Current prompt always goes last — it's what we want the LLM to respond to.
        messages.append({
            "role":    "user",
            "content": prompt,
        })

        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=0.6,   # balanced: natural but not random
            max_tokens=250,    # short enough to speak aloud comfortably
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        # Log the error but never crash the call — return a safe fallback.
        print("Groq Error:", str(e))
        return "Sorry, I am having trouble generating a response right now."




def chat_with_gpt(prompt: str, history: list = None) -> str:
    
    return generate_response(prompt, history)