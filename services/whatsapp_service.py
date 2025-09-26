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
    def enviar_main_menu(self,numero:str):
        buttons = [
            {"id": "agendar_cita", "title": "Agendar Cita"},
            {"id": "ver_citas", "title": "Ver Mis Citas"},
        ]
        return self.enviar_b(numero, "Menú Principal", "Selecciona una opción:", buttons)
    def enviar_menu_gestion(self,numero:str):
        buttons=[
            {"id": "reagendar_cita", "title": "Reagendar Cita"},
            {"id": "cancelar_cita", "title": "Cancelar Cita"},
            {"id": "volver", "title": "Regresar al Menú Principal"}
        ]
        return self.enviar_b(numero,"Gestión de Citas","¿Qué te gustaría hacer?",buttons)
    def enviar_fechas(self,numero:str):
        from datetime import datetime,timedelta

        today=datetime.now()
        buttons=[]
        # aqui necesitamos firebase despues lo hago
    
    def escoger_horarios(self,numero:str,fecha:str,horarios:list):#esto se va a tener que adaptar a lo de arriba cuando este
        sections=[
            {
                "title": f"Horarios disponibles para {fecha}",
                "rows":[
                    {
                        "id": horario,
                        "title": horario,
                        "description": f"Reserva tu cita para las {horario}"
                    }for horario in horarios
                ]
            }
        ]
        return self.enviar_lista_m(numero,"Selecciona un Horario","Elige un horario disponible para tu cita.","Ver Horarios",sections)
    #los horarios y fechas estan en pausas por mientras

    def send_confirmation_message(self, to_number: str, cita, is_new=True):

        fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        if is_new:
            emoji = "✅"
            action = "AGENDADA"
        else:
            emoji = "🔄"
            action = "REAGENDADA"
        
        message = f"""{emoji} *CITA {action} EXITOSAMENTE*

        👤 *Cliente:* {cita.nombre_cliente}
        📅 *Fecha:* {fecha_formatted}
        ⏰ *Hora:* {cita.hora}
        📝 *Motivo:* {cita.descripcion}

        Te enviaré un recordatorio 1 día antes de tu cita.

        ¡Gracias por usar nuestro servicio!"""
        
        return self.send_text_message(to_number, message)