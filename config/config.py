

import os
from dotenv import load_dotenv


load_dotenv()



GROQ_API_KEY = os.getenv("GROQ_API_KEY")


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")


NGROK_URL = os.getenv("NGROK_URL")
