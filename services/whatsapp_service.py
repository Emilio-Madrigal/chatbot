import requests
import json
from config import Config

class WhatsAppService:
    def __init__(self):
        self.token=Config.WHATSAPP_TOKEN
        self.phone=Config.PHONE_NUMBER_ID
        self.api_url=Config.WHATSAPP_API_URL

        self.headers={'Authorization': f'Bearer {self.token}','Content-Type': 'application/json'}

    def enviar_text_m(self,numero: str,mensaje:str):
        payload={
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "text",
            "text":{"body": mensaje}
        }
        return self._send_request(payload)
    
    def enviar_b(self,numero:str,encabezado_text:str,cuerpo_text:str,botones:list):
        if len(botones)>3:
            raise ValueError("emilio recuerda que solo 3 botones ")
        botones_i=[]
        for boton in botones:
            botones_i.append({
                "type":"reply",
                "reply":{
                    "id": boton['id'],
                    "title": boton['title'][:20]#limite de caracteres
                }
            })

            payload={
                "messaging_product": "whatsapp",
                "to": numero,
                "type":"interactive",
                "interactive":{
                    "type":"button",
                    "header":{"type":"text","text": encabezado_text},
                    "body":{"text": cuerpo_text},
                    "action":{"buttons": botones_i}
                }
            }
            return self._send_message(payload)
    def enviar_lista_m(self,numero:str,encabezado_text:str,cuerpo_text:str,boton_text:str,secciones:list):
        payload={
            "messaging_product": "whatsapp",
            "to":numero,
            "type":"list",
            "interactive":{
                "header":{"type":"text","text":encabezado_text},
                "body":{"text":cuerpo_text},
                "action":{
                    "button": boton_text,
                    "sections": secciones
                }
            }
            
        }
        return self._send_message(payload)
    def _enviar_m(self,payload):
        try:
            response=requests.post(self.api_url,json=payload,headers=self.headers)
            result=response.json()
            if response.status_code==200:
                print(f"se envio el mensaje")
                return result
            else:
                print(f"error al enviar mensaje: {result}")
                return None

        except Exception as e:
            print(f"{e}")
            return None