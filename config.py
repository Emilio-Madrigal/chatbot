import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    WHATSAPP_TOKEN=os.getenv("WHATSAPP_TOKEN")
    WHATSAPP_VERIFY_TOKEN=os.getenv("WHATSAPP_VERIFY_TOKEN")
    PHONE_NUMBER_ID=os.getenv("PHONE_NUMBER_ID")
    WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    FIREBASE_CREDENTIALS_PATH = 'serviceAccountKey.json'
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    TIMEZONE = 'America/Mexico_City'# esto despues debe ser dinamico a la zona horaria del paciente
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('FLASK_ENV') == 'development'