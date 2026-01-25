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
    
from services.chatbot_translations import TRANSLATIONS

class LanguageService:
    """
    Servicio para adaptar mensajes según el idioma preferido del paciente
    """
    
    def __init__(self):
        self.paciente_repo = PacienteRepository()
        self.db = FirebaseConfig.get_db()
        self.translations = TRANSLATIONS
    
    def get_patient_language(self, paciente_id: str) -> str:
        """
        Obtiene el idioma preferido del paciente con caché simple
        """
        if not paciente_id:
            return 'es'
            
        try:
            # Primero intentar buscar en repositorio (generalmente cacheable)
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if paciente and hasattr(paciente, 'preferredLanguage'):
                lang = getattr(paciente, 'preferredLanguage', None)
                if lang in ['es', 'en']:
                    return lang
            
            # Si no, buscar directamente en Firestore
            paciente_data = self.db.collection('pacientes').document(paciente_id).get()
            if paciente_data.exists:
                data = paciente_data.to_dict()
                language = data.get('preferredLanguage') or data.get('idioma')
                if language in ['es', 'en']:
                    return language
            
            return 'es'
        except Exception as e:
            print(f"Error obteniendo idioma del paciente: {e}")
            return 'es'
            
    def get_language_from_session(self, context: Dict) -> str:
        """
        Obtiene el idioma desde el contexto de la sesión o datos del usuario
        """
        # 1. Context variable
        if context.get('language'):
            return context.get('language')
            
        # 2. User data in context
        user_data = context.get('user_data', {})
        if user_data.get('preferredLanguage'):
             return user_data.get('preferredLanguage')
             
        # 3. Default
        return 'es'

    def t(self, key: str, language: str = 'es', **kwargs) -> str:
        """
        Obtiene una traducción por su clave con soporte para formato
        """
        # Asegurar idioma válido
        if language not in ['es', 'en']:
            language = 'es'
            
        # Obtener diccionario de idioma
        lang_dict = self.translations.get(language, self.translations['es'])
        
        # Obtener texto
        text = lang_dict.get(key)
        
        # Si no existe en el idioma, buscar en español (fallback)
        if text is None:
            text = self.translations['es'].get(key, key)
            
        # Formatear si hay argumentos
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
                
        return text

    def translate_message(self, message_key: str, paciente_id: Optional[str] = None,
                         language: Optional[str] = None) -> str:
        """
        Compatibilidad: Traduce un mensaje según el idioma del paciente
        """
        if not language and paciente_id:
            language = self.get_patient_language(paciente_id)
        elif not language:
            language = 'es'
            
        return self.t(message_key, language)
    
    def adapt_message(self, base_message: str, paciente_id: str) -> str:
        """
        Adapta un mensaje completo según el idioma del paciente
        """
        language = self.get_patient_language(paciente_id)
        
        if language == 'en':
            # Mapeo de frases comunes no cubiertas por claves específicas
            common_phrases = {
                'Hola': 'Hello',
                'Gracias': 'Thank you',
                'Cita': 'Appointment',
                'Cancelar': 'Cancel',
                'Reagendar': 'Reschedule',
                'Confirmar': 'Confirm',
                'Ayuda': 'Help',
                'Menú': 'Menu',
                'Dentista': 'Dentist',
                'Consultorio': 'Clinic',
                'Precio': 'Price',
                'Fecha': 'Date',
                'Hora': 'Time'
            }
            
            for es, en in common_phrases.items():
                base_message = base_message.replace(es, en)
        
        return base_message

    def get_localized_template(self, template_name: str, paciente_id: str,
                              variables: Dict = None) -> str:
        """
        Obtiene una plantilla localizada con variables (Compatibilidad)
        """
        # Mapear nombres de templates antiguos a nuevas claves si es necesario
        # Por ahora mantenemos el método antiguo para compatibilidad con código existente que no se actualice
        language = self.get_patient_language(paciente_id)
        
        # Usar las templates originales hardcoded aquí por seguridad si no están en translations
        # O idealmente migrarlas a translations, pero por brevedad las dejo aquí
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
        
        if variables:
            template = template.format(**variables)
        
        return template

# Instancia global
language_service = LanguageService()

