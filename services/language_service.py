"""
SISTEMA DE ADAPTACIÓN DE IDIOMA
J.RNF19: Adaptación del contenido de mensajes según idioma preferido del paciente
"""

from database.models import PacienteRepository
from database.database import FirebaseConfig
from typing import Dict, Optional

class LanguageService:
    """
    Servicio para adaptar mensajes según el idioma preferido del paciente
    """
    
    def __init__(self):
        self.paciente_repo = PacienteRepository()
        self.db = FirebaseConfig.get_db()
        self.messages = {
            'es': {
                'registration': '¡Bienvenido a Densora!',
                'appointment_created': 'Cita agendada exitosamente',
                'appointment_cancelled': 'Cita cancelada',
                'appointment_rescheduled': 'Cita reagendada',
                'payment_confirmed': 'Pago confirmado',
                'reminder_24h': 'Recordatorio: Tienes una cita mañana',
                'reminder_2h': 'Recordatorio: Tu cita es en 2 horas',
                'review_request': '¿Cómo fue tu experiencia?',
                'otp': 'Tu código de verificación es',
                'help': '¿Necesitas ayuda?',
                'menu': 'Menú principal'
            },
            'en': {
                'registration': 'Welcome to Densora!',
                'appointment_created': 'Appointment scheduled successfully',
                'appointment_cancelled': 'Appointment cancelled',
                'appointment_rescheduled': 'Appointment rescheduled',
                'payment_confirmed': 'Payment confirmed',
                'reminder_24h': 'Reminder: You have an appointment tomorrow',
                'reminder_2h': 'Reminder: Your appointment is in 2 hours',
                'review_request': 'How was your experience?',
                'otp': 'Your verification code is',
                'help': 'Need help?',
                'menu': 'Main menu'
            }
        }
    
    def get_patient_language(self, paciente_id: str) -> str:
        """
        Obtiene el idioma preferido del paciente
        
        Prioridad:
        1. Preferencia guardada en perfil
        2. Idioma del navegador (localStorage)
        3. Español por defecto
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if paciente:
                # Verificar preferencia en perfil
                paciente_data = self.db.collection('pacientes').document(paciente_id).get()
                if paciente_data.exists:
                    data = paciente_data.to_dict()
                    language = data.get('preferredLanguage') or data.get('idioma')
                    if language in ['es', 'en']:
                        return language
            
            # Por defecto español
            return 'es'
            
        except Exception as e:
            print(f"Error obteniendo idioma del paciente: {e}")
            return 'es'
    
    def translate_message(self, message_key: str, paciente_id: Optional[str] = None,
                         language: Optional[str] = None) -> str:
        """
        Traduce un mensaje según el idioma del paciente
        """
        # Determinar idioma
        if not language and paciente_id:
            language = self.get_patient_language(paciente_id)
        elif not language:
            language = 'es'
        
        # Obtener mensaje traducido
        return self.messages.get(language, self.messages['es']).get(message_key, message_key)
    
    def adapt_message(self, base_message: str, paciente_id: str) -> str:
        """
        Adapta un mensaje completo según el idioma del paciente
        
        Por ahora, retorna el mensaje en español (se puede mejorar con traducción automática)
        """
        language = self.get_patient_language(paciente_id)
        
        # Si el paciente prefiere inglés, traducir mensaje básico
        if language == 'en':
            # Traducciones básicas comunes
            translations = {
                'Hola': 'Hello',
                'Gracias': 'Thank you',
                'Cita': 'Appointment',
                'Cancelar': 'Cancel',
                'Reagendar': 'Reschedule',
                'Confirmar': 'Confirm',
                'Ayuda': 'Help',
                'Menú': 'Menu'
            }
            
            # Reemplazar palabras comunes
            for es, en in translations.items():
                base_message = base_message.replace(es, en)
        
        return base_message
    
    def get_localized_template(self, template_name: str, paciente_id: str,
                              variables: Dict = None) -> str:
        """
        Obtiene una plantilla localizada con variables
        """
        language = self.get_patient_language(paciente_id)
        
        templates = {
            'es': {
                'appointment_confirmation': """*CITA AGENDADA EXITOSAMENTE*

Hola {nombre},

Tu cita ha sido confirmada:

*Fecha:* {fecha}
*Hora:* {hora}
*Dentista:* {dentista}

Te enviaremos un recordatorio 24 horas antes.

¡Te esperamos!""",
                'appointment_cancelled': """*CITA CANCELADA*

Hola {nombre},

Tu cita del {fecha} a las {hora} ha sido cancelada.

¿Deseas agendar una nueva cita? Escribe *'agendar cita'*.""",
                'review_request': """*¿CÓMO FUE TU EXPERIENCIA?*

Hola {nombre},

Gracias por confiar en Densora.

Tu cita del {fecha} con {dentista} ya fue completada.

Nos encantaría conocer tu opinión.

👉 *Califica tu experiencia aquí:*
{link}

¡Gracias!"""
            },
            'en': {
                'appointment_confirmation': """*APPOINTMENT SCHEDULED SUCCESSFULLY*

Hello {nombre},

Your appointment has been confirmed:

*Date:* {fecha}
*Time:* {hora}
*Dentist:* {dentista}

We will send you a reminder 24 hours before.

See you soon!""",
                'appointment_cancelled': """*APPOINTMENT CANCELLED*

Hello {nombre},

Your appointment on {fecha} at {hora} has been cancelled.

Would you like to schedule a new appointment? Type *'schedule appointment'*.""",
                'review_request': """*HOW WAS YOUR EXPERIENCE?*

Hello {nombre},

Thank you for trusting Densora.

Your appointment on {fecha} with {dentista} has been completed.

We would love to hear your feedback.

👉 *Rate your experience here:*
{link}

Thank you!"""
            }
        }
        
        template = templates.get(language, templates['es']).get(template_name, '')
        
        # Reemplazar variables
        if variables:
            template = template.format(**variables)
        
        return template

# Instancia global
language_service = LanguageService()

