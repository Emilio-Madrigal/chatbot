from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from config import Config
from typing import Optional
import json

class WhatsAppService:
    def __init__(self):
        self.account_sid = Config.TWILIO_ACCOUNT_SID
        self.auth_token = Config.TWILIO_AUTH_TOKEN
        self.whatsapp_number = Config.TWILIO_WHATSAPP_NUMBER
        
        # Inicializar cliente de Twilio
        self.client = Client(self.account_sid, self.auth_token)
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Formatea el número de teléfono para Twilio (debe incluir código de país)"""
        # Si ya tiene formato whatsapp:, lo deja así
        if phone_number.startswith('whatsapp:'):
            return phone_number
        # Si no, agrega el prefijo whatsapp:
        if not phone_number.startswith('+'):
            # Asume que es un número mexicano si no tiene +
            phone_number = f"+52{phone_number}"
        return f"whatsapp:{phone_number}"
    
    def send_text_message(self, to_number: str, message: str):
        """Envía un mensaje de texto a través de Twilio"""
        try:
            to = self._format_phone_number(to_number)
            message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to
            )
            print(f"Mensaje enviado via Twilio. SID: {message.sid}")
            return {"status": "sent", "sid": message.sid}
        except TwilioRestException as e:
            print(f"Error enviando mensaje via Twilio: {e}")
            return None
        except Exception as e:
            print(f"Error inesperado enviando mensaje: {e}")
            return None
    
    def send_template_message(self, to_number: str, template_name: str, language_code: str = "es", components: list = None, content_sid: str = None):
        """
        Envía un mensaje usando una plantilla verificada de WhatsApp a través de Twilio (PRODUCCIÓN)
        
        Args:
            to_number: Número de teléfono del destinatario
            template_name: Nombre de la plantilla aprobada (opcional si usas content_sid)
            language_code: Código de idioma (por defecto "es")
            components: Lista de componentes con parámetros para la plantilla
            content_sid: Content SID de la plantilla en Twilio (recomendado para producción)
        """
        try:
            from twilio.rest import Client
            to = self._format_phone_number(to_number)
            
            # Si se proporciona content_sid, usar Content API de Twilio (recomendado)
            if content_sid:
                # Construir variables para la plantilla
                content_variables = {}
                if components:
                    for component in components:
                        if component.get('type') == 'body' and 'parameters' in component:
                            params = []
                            for param in component['parameters']:
                                if param.get('type') == 'text':
                                    params.append(param.get('text', ''))
                            # Twilio espera las variables como JSON string
                            if params:
                                content_variables = json.dumps({str(i+1): param for i, param in enumerate(params)})
                
                # Usar Content API de Twilio
                message = self.client.messages.create(
                    content_sid=content_sid,
                    from_=self.whatsapp_number,
                    to=to,
                    content_variables=content_variables if content_variables else None
                )
            else:
                # Método alternativo: usar messaging_service con template
                # Nota: Esto requiere configuración adicional en Twilio
                message = self.client.messages.create(
                    from_=self.whatsapp_number,
                    to=to,
                    body=f"[Plantilla: {template_name}]"  # Fallback - usar content_sid en producción
                )
            
            print(f"Plantilla enviada via Twilio. SID: {message.sid}")
            return {"status": "sent", "sid": message.sid}
        except TwilioRestException as e:
            print(f"Error enviando plantilla via Twilio: {e}")
            print("Nota: En producción, asegúrate de usar content_sid de plantillas aprobadas")
            return None
        except Exception as e:
            print(f"Error inesperado enviando plantilla: {e}")
            return None
    
    def send_interactive_buttons(self, to_number: str, header_text: str, body_text: str, buttons: list):
        """
        Envía mensaje con botones interactivos
        Nota: Twilio no soporta botones interactivos nativos como Meta.
        Se envía como mensaje de texto con opciones numeradas.
        """
        if len(buttons) > 3:
            raise ValueError("WhatsApp solo permite maximo 3 botones")
        
        # Construir mensaje con opciones numeradas (Twilio no soporta botones interactivos)
        message_text = f"{header_text}\n\n{body_text}\n\n"
        for i, button in enumerate(buttons, 1):
            message_text += f"{i}. {button['title']}\n"
        message_text += "\nResponde con el número de la opción deseada."
        
        return self.send_text_message(to_number, message_text)
    
    def send_list_message(self, to_number: str, header_text: str, body_text: str, button_text: str, sections: list):
        """
        Envía mensaje con lista
        Nota: Twilio no soporta listas interactivas nativas como Meta.
        Se envía como mensaje de texto con opciones numeradas.
        """
        message_text = f"{header_text}\n\n{body_text}\n\n"
        
        option_number = 1
        for section in sections:
            if 'title' in section:
                message_text += f"\n{section['title']}\n"
            for row in section.get('rows', []):
                title = row.get('title', '')
                description = row.get('description', '')
                message_text += f"{option_number}. {title}"
                if description:
                    message_text += f" - {description}"
                message_text += "\n"
                option_number += 1
        
        message_text += "\nResponde con el número de la opción deseada."
        
        return self.send_text_message(to_number, message_text)
    
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
    
    def send_date_selection(self, to_number: str, fechas_disponibles: list = None):
        from datetime import datetime, timedelta
        
        # Si se proporcionan fechas dinámicas, usarlas; sino generar fechas por defecto
        if fechas_disponibles and len(fechas_disponibles) > 0:
            buttons = []
            for i, fecha_ts in enumerate(fechas_disponibles[:3]):  # Máximo 3 botones
                if hasattr(fecha_ts, 'strftime'):
                    fecha_str = fecha_ts.strftime('%Y-%m-%d')
                    fecha_display = fecha_ts.strftime('%d/%m')
                else:
                    fecha_str = fecha_ts
                    fecha_display = fecha_ts
                
                buttons.append({
                    "id": f"fecha_{fecha_str}",
                    "title": fecha_display
                })
        else:
            # Fechas por defecto (próximos 3 días laborables)
            today = datetime.now()
            buttons = []
            
            for i in range(1, 4):
                date = today + timedelta(days=i)
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
    
    def send_time_selection(self, to_number: str, fecha_seleccionada: str, horarios_disponibles: list = None):
        from datetime import datetime
        
        # Si se proporcionan horarios dinámicos, usarlos; sino usar horarios por defecto
        if horarios_disponibles and len(horarios_disponibles) > 0:
            buttons = []
            for i, slot in enumerate(horarios_disponibles[:3]):  # Máximo 3 botones
                hora_inicio = slot.get('horaInicio', slot.get('inicio', ''))
                hora_fin = slot.get('horaFin', slot.get('fin', ''))
                
                # Formatear hora para mostrar
                try:
                    hora_obj = datetime.strptime(hora_inicio, '%H:%M')
                    hora_display = hora_obj.strftime('%I:%M %p').lstrip('0')
                except:
                    hora_display = hora_inicio
                
                buttons.append({
                    "id": f"hora_{hora_inicio}",
                    "title": hora_display
                })
            
            if not buttons:
                # Fallback a horarios por defecto si no hay disponibles
                buttons = [
                    {"id": "hora_09:00", "title": "9:00 AM"},
                    {"id": "hora_11:00", "title": "11:00 AM"},
                    {"id": "hora_14:00", "title": "2:00 PM"}
                ]
        else:
            # Horarios por defecto
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
