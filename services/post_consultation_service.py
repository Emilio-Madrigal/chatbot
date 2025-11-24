"""
⭐ SISTEMA DE MENSAJES POST-CONSULTA CON RESEÑAS
J.RF9: Mensaje post-consulta con enlace a reseñas (menos de 2 clics)
"""

from services.whatsapp_service import WhatsAppService
from services.message_logger import message_logger
from services.token_service import token_service
from database.models import PacienteRepository, CitaRepository
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz

class PostConsultationService:
    """
    Servicio para enviar mensajes post-consulta con enlaces a reseñas
    """
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        self.paciente_repo = PacienteRepository()
        self.cita_repo = CitaRepository()
        self.db = FirebaseConfig.get_db()
        self.timezone = pytz.timezone('America/Mexico_City')
    
    async def send_review_request(self, cita_id: str, paciente_id: str,
                                 dentista_name: str, consultorio_name: str,
                                 fecha: str):
        """
        J.RF9: Envía mensaje post-consulta con enlace directo a reseñas
        
        El enlace debe permitir calificar en menos de 2 clics
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            # Verificar si ya tiene reseña para esta cita
            reseñas_ref = self.db.collection('resenas')\
                .where('pacienteId', '==', paciente_id)\
                .where('citaId', '==', cita_id)\
                .limit(1)\
                .stream()
            
            if any(reseñas_ref):
                # Ya tiene reseña, no enviar
                return None
            
            # Generar enlace directo a reseña (con token para acceso rápido)
            review_token = token_service.generate_token({
                'action': 'review_appointment',
                'citaId': cita_id,
                'pacienteId': paciente_id
            })
            
            review_link = f"https://www.densora.com/resena/{cita_id}?token={review_token}" if review_token else f"https://www.densora.com/resena/{cita_id}"
            
            # Formatear fecha
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if isinstance(fecha, str) else fecha
            fecha_formatted = fecha_obj.strftime('%d/%m/%Y') if hasattr(fecha_obj, 'strftime') else str(fecha)
            
            mensaje = f"""⭐ *¿CÓMO FUE TU EXPERIENCIA?*

Hola {paciente.nombre or 'Paciente'},

Gracias por confiar en Densora para tu atención dental.

Tu cita del {fecha_formatted} con {dentista_name} en {consultorio_name} ya fue completada.

Nos encantaría conocer tu opinión. Tu feedback nos ayuda a mejorar.

👉 *Califica tu experiencia aquí:*
{review_link}

Solo toma 30 segundos y nos ayuda mucho.

¡Gracias por tu tiempo! 😊"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='post_consultation_review_request',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            # Registrar que se envió solicitud de reseña
            self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('citas')\
                .document(cita_id)\
                .update({
                    'reviewRequestSent': True,
                    'reviewRequestSentAt': datetime.now(self.timezone)
                })
            
            return result
            
        except Exception as e:
            print(f"Error enviando solicitud de reseña: {e}")
            return None
    
    async def send_review_reminder(self, cita_id: str, paciente_id: str,
                                  days_since_appointment: int = 1):
        """
        Envía recordatorio de reseña si no se ha completado después de X días
        """
        try:
            # Verificar si ya tiene reseña
            reseñas_ref = self.db.collection('resenas')\
                .where('pacienteId', '==', paciente_id)\
                .where('citaId', '==', cita_id)\
                .limit(1)\
                .stream()
            
            if any(reseñas_ref):
                return None  # Ya tiene reseña
            
            # Verificar si ya se envió recordatorio
            cita_doc = self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('citas')\
                .document(cita_id)\
                .get()
            
            if not cita_doc.exists:
                return None
            
            cita_data = cita_doc.to_dict()
            if cita_data.get('reviewReminderSent'):
                return None  # Ya se envió recordatorio
            
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            review_link = f"https://www.densora.com/resena/{cita_id}"
            
            mensaje = f"""💬 *Recordatorio: Tu Opinión Importa*

Hola {paciente.nombre or 'Paciente'},

Aún no hemos recibido tu reseña sobre tu última cita.

Tu opinión es muy valiosa para nosotros y nos ayuda a mejorar.

👉 *Califica tu experiencia aquí:*
{review_link}

Solo toma 30 segundos.

¡Gracias! 😊"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            if result:
                # Marcar que se envió recordatorio
                self.db.collection('pacientes')\
                    .document(paciente_id)\
                    .collection('citas')\
                    .document(cita_id)\
                    .update({
                        'reviewReminderSent': True,
                        'reviewReminderSentAt': datetime.now(self.timezone)
                    })
            
            return result
            
        except Exception as e:
            print(f"Error enviando recordatorio de reseña: {e}")
            return None

# Instancia global
post_consultation_service = PostConsultationService()

