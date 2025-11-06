import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Twilio Credentials
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")  # Formato: whatsapp:+14155238886
    TWILIO_WEBHOOK_TOKEN = os.getenv("TWILIO_WEBHOOK_TOKEN", "default_webhook_token")
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH = 'serviceAccountKey.json'
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    
    # Configuración general
    TIMEZONE = 'America/Mexico_City'  # esto despues debe ser dinamico a la zona horaria del paciente
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # Mantener compatibilidad con código antiguo (deprecated)
    WHATSAPP_TOKEN = TWILIO_AUTH_TOKEN
    WHATSAPP_VERIFY_TOKEN = TWILIO_WEBHOOK_TOKEN