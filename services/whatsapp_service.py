import requests
import json
from config import Config

class WhatsAppService:
    def __init__(self):
        self.token = Config.WHATSAPP_TOKEN
        self.phone_number_id = Config.PHONE_NUMBER_ID
        self.api_url = Config.WHATSAPP_API_URL
        
        # Headers para las peticiones HTTP
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def send_text_message(self, to_number: str, message: str):
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": message}
        }
        return self._send_message(payload)
    
    def send_template_message(self, to_number: str, template_name: str, language_code: str = "es", components: list = None):
        """
        Envía un mensaje usando una plantilla verificada de WhatsApp
        
        Args:
            to_number: Número de teléfono del destinatario
            template_name: Nombre de la plantilla aprobada en Meta
            language_code: Código de idioma (por defecto "es")
            components: Lista de componentes con parámetros para la plantilla
                        Ejemplo: [{"type": "body", "parameters": [{"type": "text", "text": "valor"}]}]
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        # Agregar componentes si se proporcionan
        if components:
            payload["template"]["components"] = components
        
        return self._send_message(payload)
    
    def send_interactive_buttons(self, to_number: str, header_text: str, body_text: str, buttons: list):
        if len(buttons) > 3:
            raise ValueError("WhatsApp solo permite maximo 3 botones")
        
        interactive_buttons = []
        for button in buttons:
            interactive_buttons.append({
                "type": "reply",
                "reply": {
                    "id": button['id'],
                    "title": button['title'][:20]  # Límite de 20 caracteres
                }
            })
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "header": {"type": "text", "text": header_text},
                "body": {"text": body_text},
                "action": {"buttons": interactive_buttons}
            }
        }
        return self._send_message(payload)
    
    def send_list_message(self, to_number: str, header_text: str, body_text: str,button_text: str, sections: list):

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header_text},
                "body": {"text": body_text},
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }
        return self._send_message(payload)
    
    def _send_message(self, payload):
        #Método privado que hace la petición HTTP a WhatsApp
        try:
            response = requests.post(self.api_url, json=payload, headers=self.headers)
            result = response.json()
            
            if response.status_code == 200:
                print(f"mensaje enviado")
                return result
            else:
                print(f"error enviando mensaje: {result}")
                return None
                
        except Exception as e:
            print(f"paso algo mas enviando el mensaje: {e}")
            return None
    
    def send_main_menu(self, to_number: str):
        buttons = [
            {"id": "agendar_cita", "title": "📅 Agendar Cita"},
            {"id": "ver_citas", "title": "👀 Ver Mis Citas"},
            {"id": "gestionar_citas", "title": "⚙️ Gestionar"}
        ]
        
        return self.send_interactive_buttons(
            to_number,
            "¡Hola! Bienvenido a densora.",
            "¿Qué te gustaría hacer hoy?",
            buttons
        )
    
    def send_management_menu(self, to_number: str):
        buttons = [
            {"id": "reagendar_cita", "title": "🔄 Reagendar"},
            {"id": "cancelar_cita", "title": "❌ Cancelar"},
            {"id": "volver_menu", "title": "🏠 Menú Principal"}
        ]
        
        return self.send_interactive_buttons(
            to_number,
            "⚙️ Gestionar Citas",
            "¿Qué deseas realizar?",
            buttons
        )
    
    def send_date_selection(self, to_number: str):
        from datetime import datetime, timedelta
        
        today = datetime.now()
        buttons = []
        
        for i in range(1, 4):
            date = today + timedelta(days=i)
            #omitir fines de semana desdepues meto qque se pueda elegir cualquier dia
            while date.weekday() >= 5:
                date += timedelta(days=1)
            
            buttons.append({
                "id": f"fecha_{date.strftime('%Y-%m-%d')}",
                "title": date.strftime('%d/%m')
            })
        
        return self.send_interactive_buttons(
            to_number,
            "📅 Selecciona una Fecha",
            "¿Cuándo te gustaría agendar tu cita?",
            buttons
        )
    
    def send_time_selection(self, to_number: str, fecha_seleccionada: str):
        from datetime import datetime
        buttons = [
            {"id": "hora_09:00", "title": "9:00 AM"},
            {"id": "hora_11:00", "title": "11:00 AM"},
            {"id": "hora_14:00", "title": "2:00 PM"}
        ]
        
        fecha_formatted = datetime.strptime(fecha_seleccionada, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        return self.send_interactive_buttons(
            to_number,
            "⏰ Selecciona una Hora",
            f"Fecha elegida: *{fecha_formatted}*\n¿A qué hora prefieres tu cita?",
            buttons
        )
    
    def send_citas_list(self, to_number: str, citas: list, action_type: str = "ver"):
        from datetime import datetime
        if not citas:
            return self.send_text_message(
                to_number, 
                "No tienes citas programadas actualmente.\n\nEscribe *menu* para agendar una nueva cita."
            )
        
        rows = []
        for cita in citas:
            fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
            rows.append({
                "id": f"{action_type}_{cita.id}",
                "title": f"{cita.nombre_cliente}",
                "description": f"📅 {fecha_formatted} ⏰ {cita.hora}"
            })
        
        sections = [{
            "title": "Tus Citas Programadas",
            "rows": rows
        }]
        
        action_messages = {
            "ver": "Selecciona una cita para ver sus detalles:",
            "reagendar": "Selecciona la cita que deseas reagendar:",
            "cancelar": "Selecciona la cita que deseas cancelar:"
        }
        
        return self.send_list_message(
            to_number,
            "📋 Mis Citas",
            action_messages.get(action_type, "Selecciona una cita:"),
            "Ver Citas",
            sections
        )
    
    def send_cita_details(self, to_number: str, cita):
        from datetime import datetime
        fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
        
        message = f"""📋 *DETALLES DE LA CITA*

👤 *Cliente:* {cita.nombre_cliente}
📅 *Fecha:* {fecha_formatted}
⏰ *Hora:* {cita.hora}
📝 *Descripción:* {cita.descripcion}
📊 *Estado:* {cita.estado.title()}

¿Necesitas hacer algún cambio?"""
        
        buttons = [
            {"id": f"reagendar_{cita.id}", "title": "🔄 Reagendar"},
            {"id": f"cancelar_{cita.id}", "title": "❌ Cancelar"},
            {"id": "volver_menu", "title": "🏠 Menú"}
        ]
        
        self.send_text_message(to_number, message)
        return self.send_interactive_buttons(
            to_number,
            "",
            "Opciones disponibles:",
            buttons
        )
    
    def send_confirmation_message(self, to_number: str, cita, is_new=True):
        """Envía mensaje de confirmación de cita"""
        from datetime import datetime
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