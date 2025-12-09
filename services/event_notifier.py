# SISTEMA CENTRALIZADO DE NOTIFICACIONES POR EVENTOS
# J.RF1: Mensajes automatizados para todos los eventos del sistema

from services.whatsapp_service import WhatsAppService
from services.message_logger import message_logger
from services.token_service import token_service
from services.retry_service import retry_service
from services.language_service import language_service
from database.models import PacienteRepository, CitaRepository
from database.database import FirebaseConfig
from datetime import datetime
from typing import Dict, Optional
import pytz

class EventNotifier:
    """
    Sistema centralizado para enviar notificaciones automáticas por WhatsApp
    basado en eventos del sistema
    """
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        self.paciente_repo = PacienteRepository()
        self.cita_repo = CitaRepository()
        self.db = FirebaseConfig.get_db()
        self.timezone = pytz.timezone('America/Mexico_City')
    
    async def notify_registration(self, paciente_id: str, telefono: str, nombre: str):
        """
        J.RF1: Notificación de registro
        J.RNF19: Adaptación de idioma
        """
        try:
            # J.RNF19: Obtener idioma del paciente
            language = language_service.get_patient_language(paciente_id)
            
            if language == 'en':
                mensaje = f"""Welcome to Densora, {nombre}!

Your account has been created successfully.

Now you can:
• Schedule dental appointments
• View your medical history
• Manage your appointments
• Rate your dentists

Need help? Type *"help"* or *"menu"*.

Thank you for trusting us!"""
            else:
                mensaje = f"""¡Bienvenido a Densora, {nombre}!

Tu cuenta ha sido creada exitosamente.

Ahora puedes:
• Agendar citas dentales
• Ver tu historial médico
• Gestionar tus citas
• Calificar a tus dentistas

¿Necesitas ayuda? Escribe *"ayuda"* o *"menu"*.

¡Gracias por confiar en nosotros!"""
            
            result = self.whatsapp.send_text_message(telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='registration',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            # Programar reintento si falló
            if not result:
                retry_service.schedule_retry(
                    paciente_id=paciente_id,
                    dentista_id=None,
                    event_type='registration',
                    message_content=mensaje,
                    original_message_id=None,
                    error='Error enviando notificación de registro'
                )
            
            return result
            
        except Exception as e:
            print(f"Error notificando registro: {e}")
            return None
    
    async def notify_appointment_created(self, cita_id: str, paciente_id: str, 
                                       fecha: str, hora: str, dentista_name: str,
                                       consultorio_name: str, motivo: str = "Consulta",
                                       dentista_id: Optional[str] = None):
        """
        J.RF1: Notificación de agendamiento
        J.RF8, J.RNF7: Verificar configuración de notificaciones
        """
        try:
            # J.RF8, J.RNF7: Verificar si se deben enviar notificaciones
            if not notification_config_service.should_send_notification(
                dentista_id=dentista_id,
                paciente_id=paciente_id,
                notification_type='change'
            ):
                print(f"Notificación de agendamiento deshabilitada para paciente {paciente_id}")
                return None
            
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            # Generar enlace de cancelación con token
            cancel_link = token_service.generate_cancel_link(cita_id, paciente_id)
            
            # J.RNF19: Obtener idioma del paciente
            language = language_service.get_patient_language(paciente_id)
            
            # Formatear fecha
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if isinstance(fecha, str) else fecha
            fecha_formatted = fecha_obj.strftime('%d/%m/%Y') if hasattr(fecha_obj, 'strftime') else str(fecha)
            
            # J.RNF19: Mensaje adaptado al idioma
            if language == 'en':
                mensaje = f"""*APPOINTMENT SCHEDULED SUCCESSFULLY*

Hello {paciente.nombre or 'Patient'},

Your appointment has been confirmed:

*Date:* {fecha_formatted}
*Time:* {hora}
*Dentist:* {dentista_name}
*Clinic:* {consultorio_name}
*Reason:* {motivo}

We will send you a reminder 24 hours before.

Need to cancel? Use this link:
{cancel_link if cancel_link else 'Contact the clinic'}

See you soon!"""
            else:
                mensaje = f"""*CITA AGENDADA EXITOSAMENTE*

Hola {paciente.nombre or 'Paciente'},

Tu cita ha sido confirmada:

*Fecha:* {fecha_formatted}
*Hora:* {hora}
*Dentista:* {dentista_name}
*Consultorio:* {consultorio_name}
# *Motivo:* {motivo}

Te enviaremos un recordatorio 24 horas antes.

¿Necesitas cancelar? Usa este enlace:
{cancel_link if cancel_link else 'Contacta con el consultorio'}

¡Te esperamos! 😊"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='appointment_created',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            # Programar reintento si falló
            if not result:
                retry_service.schedule_retry(
                    paciente_id=paciente_id,
                    dentista_id=None,
                    event_type='appointment_created',
                    message_content=mensaje,
                    original_message_id=None,
                    error='Error enviando notificación de agendamiento'
                )
            
            return result
            
        except Exception as e:
            print(f"Error notificando agendamiento: {e}")
            return None
    
    async def notify_appointment_cancelled(self, cita_id: str, paciente_id: str,
                                          fecha: str, hora: str, motivo: str = "",
                                          refund_amount: float = 0, dentista_id: Optional[str] = None):
        """
        J.RF1: Notificación de cancelación
        G.RF8, G.RNF5: Notificación por WhatsApp de cancelación
        J.RF8, J.RNF7: Verificar configuración de notificaciones
        """
        try:
            # J.RF8, J.RNF7: Verificar si se deben enviar notificaciones
            if not notification_config_service.should_send_notification(
                dentista_id=dentista_id,
                paciente_id=paciente_id,
                notification_type='change'
            ):
                print(f"Notificación de cancelación deshabilitada para paciente {paciente_id}")
                return None
            
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            # Formatear fecha
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if isinstance(fecha, str) else fecha
            fecha_formatted = fecha_obj.strftime('%d/%m/%Y') if hasattr(fecha_obj, 'strftime') else str(fecha)
            
            mensaje = f"""*CITA CANCELADA*

Hola {paciente.nombre or 'Paciente'},

Tu cita del {fecha_formatted} a las {hora} ha sido cancelada."""
            
            if motivo:
                mensaje += f"\n\n*Motivo:* {motivo}"
            
            if refund_amount > 0:
                mensaje += f"\n\n*Reembolso:* ${refund_amount:.2f}"
                mensaje += "\nEl reembolso se procesará en 3-5 días hábiles."
            
            mensaje += "\n\n¿Deseas agendar una nueva cita? Escribe *'agendar cita'*."
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='appointment_cancelled',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            # Programar reintento si falló
            if not result:
                retry_service.schedule_retry(
                    paciente_id=paciente_id,
                    dentista_id=None,
                    event_type='appointment_cancelled',
                    message_content=mensaje,
                    original_message_id=None,
                    error='Error enviando notificación de cancelación'
                )
            
            return result
            
        except Exception as e:
            print(f"Error notificando cancelación: {e}")
            return None
    
    async def notify_appointment_rescheduled(self, cita_id: str, paciente_id: str,
                                           old_date: str, old_time: str,
                                           new_date: str, new_time: str,
                                           dentista_name: str):
        """
        J.RF1: Notificación de reagendamiento
        H.RF11: Notificación por WhatsApp de reagendamiento
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            # Formatear fechas
            old_date_obj = datetime.strptime(old_date, '%Y-%m-%d') if isinstance(old_date, str) else old_date
            old_date_formatted = old_date_obj.strftime('%d/%m/%Y') if hasattr(old_date_obj, 'strftime') else str(old_date)
            
            new_date_obj = datetime.strptime(new_date, '%Y-%m-%d') if isinstance(new_date, str) else new_date
            new_date_formatted = new_date_obj.strftime('%d/%m/%Y') if hasattr(new_date_obj, 'strftime') else str(new_date)
            
            mensaje = f"""*CITA REAGENDADA*

Hola {paciente.nombre or 'Paciente'},

Tu cita ha sido reagendada:

*Anterior:*
   {old_date_formatted} a las {old_time}

*Nueva:*
   {new_date_formatted} a las {new_time}

*Dentista:* {dentista_name}

Te enviaremos un recordatorio 24 horas antes de tu nueva cita.

¿Necesitas hacer algún cambio? Escribe *'reagendar'* o *'cancelar'*."""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='appointment_rescheduled',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            # Programar reintento si falló
            if not result:
                retry_service.schedule_retry(
                    paciente_id=paciente_id,
                    dentista_id=None,
                    event_type='appointment_rescheduled',
                    message_content=mensaje,
                    original_message_id=None,
                    error='Error enviando notificación de reagendamiento'
                )
            
            return result
            
        except Exception as e:
            print(f"Error notificando reagendamiento: {e}")
            return None
    
    async def notify_payment_confirmed(self, cita_id: str, paciente_id: str,
                                     fecha: str, hora: str, amount: float,
                                     payment_method: str):
        """
        J.RF1: Notificación de confirmación de pago
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            # Formatear fecha
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if isinstance(fecha, str) else fecha
            fecha_formatted = fecha_obj.strftime('%d/%m/%Y') if hasattr(fecha_obj, 'strftime') else str(fecha)
            
            mensaje = f"""*PAGO CONFIRMADO*

Hola {paciente.nombre or 'Paciente'},

Tu pago ha sido confirmado exitosamente:

*Monto:* ${amount:.2f}
*Método:* {payment_method.title()}
*Cita:* {fecha_formatted} a las {hora}

Tu cita está asegurada. Te esperamos.

¡Gracias por tu pago!"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='payment_confirmed',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            return result
            
        except Exception as e:
            print(f"Error notificando confirmación de pago: {e}")
            return None
    
    async def notify_appointment_reassigned(self, cita_id: str, paciente_id: str,
                                          old_dentista: str, new_dentista: str,
                                          fecha: str, hora: str):
        """
        J.RF15: Notificación de reasignación de citas
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return None
            
            # Formatear fecha
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d') if isinstance(fecha, str) else fecha
            fecha_formatted = fecha_obj.strftime('%d/%m/%Y') if hasattr(fecha_obj, 'strftime') else str(fecha)
            
            mensaje = f"""🔄 *CITA REASIGNADA*

Hola {paciente.nombre or 'Paciente'},

Tu cita ha sido reasignada a otro profesional:

*Fecha:* {fecha_formatted}
*Hora:* {hora}

*Dentista Anterior:* {old_dentista}
*Nuevo Dentista:* {new_dentista}

Tu cita sigue programada para la misma fecha y hora, solo cambió el profesional que te atenderá.

¿Tienes alguna pregunta? Responde a este mensaje.

¡Te esperamos! 😊"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='appointment_reassigned',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            # Programar reintento si falló
            if not result:
                retry_service.schedule_retry(
                    paciente_id=paciente_id,
                    dentista_id=None,
                    event_type='appointment_reassigned',
                    message_content=mensaje,
                    original_message_id=None,
                    error='Error enviando notificación de reasignación'
                )
            
            return result
            
        except Exception as e:
            print(f"Error notificando reasignación: {e}")
            return None

# Instancia global
event_notifier = EventNotifier()

