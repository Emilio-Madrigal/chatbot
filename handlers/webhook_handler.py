from flask import request
from config import Config

def handle_webhook_verification():
    verify_token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"verificanco webhook: {verify_token}")
    
    if verify_token == Config.WEBHOOK_VERIFY_TOKEN:
        print("exitosamente")
        return challenge
    else:
        print("verificación incorrecto")
        return 'Error de verificación', 403