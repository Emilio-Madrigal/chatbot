"""
# SISTEMA AUTOMATIZADO DE RECORDATORIOS
Scheduler mejorado para enviar recordatorios por WhatsApp
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import pytz
from database.models import CitaRepository, PacienteRepository
from database.database import FirebaseConfig
from services.whatsapp_service import WhatsAppService
from typing import List, Dict

class ReminderScheduler:
    """
    Sistema de recordatorios automatizados para citas
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone('America/Mexico_City'))
        self.whatsapp = WhatsAppService()
        self.cita_repo = CitaRepository()
        self.paciente_repo = PacienteRepository()
        self.db = FirebaseConfig.get_db()
        self.mexico_tz = pytz.timezone('America/Mexico_City')
        
    def start(self):
        """Inicia el scheduler con todas las tareas programadas"""
        
        
        # Recordatorios de citas (ejecutar cada hora)
        self.scheduler.add_job(
            func=self.send_appointment_reminders_24h,
            trigger=CronTrigger(minute=0, timezone=self.mexico_tz),  # Cada hora en punto
            id='reminders_24h',
            name='Recordatorios 24 horas antes',
            replace_existing=True
        )
        
        self.scheduler.add_job(
            func=self.send_appointment_reminders_2h,
            trigger=CronTrigger(minute=30, timezone=self.mexico_tz),  # Cada hora a los 30 minutos
            id='reminders_2h',
            name='Recordatorios 2 horas antes',
            replace_existing=True
        )
        
        # Verificar pagos pendientes (cada 6 horas)
        self.scheduler.add_job(
            func=self.check_pending_payments,
            trigger=CronTrigger(hour='*/6', timezone=self.mexico_tz),
            id='check_payments',
            name='Verificar pagos pendientes',
            replace_existing=True
        )
        
        # Recordatorios de historial médico pendiente (diario a las 10 AM)
        self.scheduler.add_job(
            func=self.remind_pending_medical_history,
            trigger=CronTrigger(hour=10, minute=0, timezone=self.mexico_tz),
            id='medical_history_reminder',
            name='Recordatorio historial médico',
            replace_existing=True
        )
        
        # Solicitud de reseñas post-cita (diario a las 6 PM)
        self.scheduler.add_job(
            func=self.request_post_appointment_reviews,
            trigger=CronTrigger(hour=18, minute=0, timezone=self.mexico_tz),
            id='review_requests',
            name='Solicitud de reseñas',
            replace_existing=True
        )
        
        # Cancelación automática de citas sin pago (cada 2 horas)
        self.scheduler.add_job(
            func=self.auto_cancel_unpaid_appointments,
            trigger=CronTrigger(hour='*/2', timezone=self.mexico_tz),
            id='auto_cancel_unpaid',
            name='Cancelar citas sin pago',
            replace_existing=True
        )
        
        # J.RF10, J.RNF15: Procesar reintentos de mensajes fallidos (cada 30 minutos)
        self.scheduler.add_job(
            func=self.process_message_retries,
            trigger=CronTrigger(minute='*/30', timezone=self.mexico_tz),  # Cada 30 minutos
            id='process_retries',
            name='Procesar reintentos de mensajes',
            replace_existing=True
        )
        
        self.scheduler.start()
        
        
    def stop(self):
        """Detiene el scheduler"""
        self.scheduler.shutdown()
        
    
    def send_appointment_reminders_24h(self):
        """Envía recordatorios 24 horas antes de las citas"""
        try:
            
            now = datetime.now(self.mexico_tz)
            target_time = now + timedelta(hours=24)
            
            # Obtener citas para mañana (con margen de +/- 1 hora)
            citas = self._get_citas_en_rango(
                start_time=target_time - timedelta(hours=1),
                end_time=target_time + timedelta(hours=1)
            )
            
            enviados = 0
            for cita in citas:
                # Verificar que no se haya enviado ya
                if self._ya_enviado_recordatorio(cita.id, '24h'):
                    continue
                
                # Obtener paciente
                paciente = self.paciente_repo.buscar_por_id(cita.paciente_id or cita.pacienteId)
                if not paciente or not paciente.telefono:
                    continue
                
                # Construir mensaje
                mensaje = self._construir_mensaje_recordatorio_24h(cita, paciente)
                
                # Enviar por WhatsApp
                result = self.whatsapp.send_text_message(
                    to_number=paciente.telefono,
                    message=mensaje
                )
                exito = result is not None and result.get('status') == 'sent'
                
                if exito:
                    # Registrar recordatorio enviado
                    self._registrar_recordatorio_enviado(cita.id, '24h')
                    enviados += 1
                    
            
            
            
        except Exception as e:
            
            import traceback
            traceback.print_exc()
    
    def send_appointment_reminders_2h(self):
        """Envía recordatorios 2 horas antes de las citas"""
        try:
            
            now = datetime.now(self.mexico_tz)
            target_time = now + timedelta(hours=2)
            
            # Obtener citas en 2 horas (con margen de +/- 30 minutos)
            citas = self._get_citas_en_rango(
                start_time=target_time - timedelta(minutes=30),
                end_time=target_time + timedelta(minutes=30)
            )
            
            enviados = 0
            for cita in citas:
                # Verificar que no se haya enviado ya
                if self._ya_enviado_recordatorio(cita.id, '2h'):
                    continue
                
                # Obtener paciente
                paciente = self.paciente_repo.buscar_por_id(cita.paciente_id or cita.pacienteId)
                if not paciente or not paciente.telefono:
                    continue
                
                # Construir mensaje
                mensaje = self._construir_mensaje_recordatorio_2h(cita, paciente)
                
                # Enviar por WhatsApp
                result = self.whatsapp.send_text_message(
                    to_number=paciente.telefono,
                    message=mensaje
                )
                exito = result is not None and result.get('status') == 'sent'
                
                if exito:
                    # Registrar recordatorio enviado
                    self._registrar_recordatorio_enviado(cita.id, '2h')
                    enviados += 1
                    
            
            
            
        except Exception as e:
            
            import traceback
            traceback.print_exc()
    
    def check_pending_payments(self):
        """Verifica pagos pendientes y envía recordatorios"""
        try:
            
            now = datetime.now(self.mexico_tz)
            
            # Obtener citas con pago pendiente
            citas_ref = self.db.collection('citas')\
                .where('paymentStatus', 'in', ['pending', 'pendiente'])\
                .where('estado', '==', 'confirmado')\
                .stream()
            
            recordatorios_enviados = 0
            for cita_doc in citas_ref:
                cita_data = cita_doc.to_dict()
                cita_id = cita_doc.id
                
                # Verificar que tenga método de pago que requiera pago previo
                metodo_pago = cita_data.get('metodoPago', '').lower()
                if metodo_pago == 'efectivo':
                    continue
                
                # Calcular tiempo restante
                payment_deadline = cita_data.get('paymentDeadline') or cita_data.get('payment_deadline')
                if not payment_deadline:
                    # Calcular deadline basado en fecha de cita y método
                    continue
                
                # Convertir deadline
                if isinstance(payment_deadline, str):
                    deadline_dt = datetime.fromisoformat(payment_deadline)
                else:
                    deadline_dt = payment_deadline
                
                # Asegurar timezone
                if deadline_dt.tzinfo is None:
                    deadline_dt = self.mexico_tz.localize(deadline_dt)
                
                horas_restantes = (deadline_dt - now).total_seconds() / 3600
                
                # Enviar recordatorio si quedan menos de 12 horas y no se ha enviado hoy
                if 0 < horas_restantes <= 12:
                    if not self._ya_enviado_recordatorio(cita_id, 'payment_reminder', hoy=True):
                        # Obtener paciente
                        paciente_id = cita_data.get('pacienteId') or cita_data.get('paciente_id')
                        paciente = self.paciente_repo.buscar_por_id(paciente_id)
                        
                        if paciente and paciente.telefono:
                            mensaje = self._construir_mensaje_pago_pendiente(cita_data, horas_restantes)
                            
                            exito = self.whatsapp.enviar_mensaje_twilio(
                                to_number=paciente.telefono,
                                message=mensaje
                            )
                            
                            if exito:
                                self._registrar_recordatorio_enviado(cita_id, 'payment_reminder')
                                recordatorios_enviados += 1
                
                # Auto-cancelar si expiró
                elif horas_restantes <= 0:
                    self._auto_cancel_cita_sin_pago(cita_id, cita_data)
            
            
            
        except Exception as e:
            
            import traceback
            traceback.print_exc()
    
    def remind_pending_medical_history(self):
        """Recuerda a pacientes completar su historial médico"""
        try:
            
            
            # Obtener pacientes sin historial médico completo
            pacientes_ref = self.db.collection('pacientes')\
                .where('historial_medico_completo', '==', False)\
                .stream()
            
            enviados = 0
            for pac_doc in pacientes_ref:
                paciente_data = pac_doc.to_dict()
                telefono = paciente_data.get('telefono')
                
                if not telefono:
                    continue
                
                # Verificar que tenga al menos una cita
                paciente_id = pac_doc.id
                citas = self.cita_repo.obtener_citas_paciente(paciente_id)
                
                if not citas:
                    continue
                
                # Verificar que no se haya enviado recordatorio en los últimos 7 días
                if self._ya_enviado_recordatorio(paciente_id, 'medical_history', dias=7):
                    continue
                
                # Construir mensaje
                nombre = paciente_data.get('nombre', 'Paciente')
                mensaje = f"""Hola {nombre},

📋 *Recordatorio de Densora*

Notamos que aún no has completado tu historial médico. Esto nos ayuda a brindarte una mejor atención.

Completa tu historial en:
👉 localhost:4321/historialMedico

Es rápido (2 minutos) y seguro. Tu información está encriptada.

¿Necesitas ayuda? Responde a este mensaje."""
                
                result = self.whatsapp.send_text_message(
                    to_number=telefono,
                    message=mensaje
                )
                exito = result is not None and result.get('status') == 'sent'
                
                if exito:
                    self._registrar_recordatorio_enviado(paciente_id, 'medical_history')
                    enviados += 1
            
            
            
        except Exception as e:
            
            import traceback
            traceback.print_exc()
    
    def request_post_appointment_reviews(self):
        """
        Solicita reseñas después de citas completadas
        J.RF9: Mensaje post-consulta con enlace a reseñas
        """
        try:
            
            now = datetime.now(self.mexico_tz)
            yesterday = now - timedelta(days=1)
            
            # Obtener citas completadas ayer
            citas_ref = self.db.collection('citas')\
                .where('estado', '==', 'completada')\
                .where('fecha', '>=', yesterday.strftime('%Y-%m-%d'))\
                .where('fecha', '<=', yesterday.strftime('%Y-%m-%d'))\
                .stream()
            
            enviados = 0
            from services.post_consultation_service import post_consultation_service
            
            for cita_doc in citas_ref:
                cita_data = cita_doc.to_dict()
                cita_id = cita_doc.id
                
                # Verificar que no tenga reseña
                if cita_data.get('tiene_resena') or cita_data.get('review_submitted'):
                    continue
                
                # Verificar que no se haya enviado solicitud
                if self._ya_enviado_recordatorio(cita_id, 'review_request'):
                    continue
                
                # Obtener paciente
                paciente_id = cita_data.get('pacienteId') or cita_data.get('paciente_id')
                if not paciente_id:
                    continue
                
                # Usar el servicio mejorado
                fecha = cita_data.get('fecha') or cita_data.get('appointmentDate', '')
                if isinstance(fecha, str):
                    fecha_str = fecha.split('T')[0] if 'T' in fecha else fecha
                else:
                    fecha_str = fecha.strftime('%Y-%m-%d') if hasattr(fecha, 'strftime') else str(fecha)
                
                result = post_consultation_service.send_review_request(
                    cita_id=cita_id,
                    paciente_id=paciente_id,
                    dentista_name=cita_data.get('dentistaName', 'tu dentista'),
                    consultorio_name=cita_data.get('consultorioName', 'Consultorio'),
                    fecha=fecha_str
                )
                
                if result:
                    self._registrar_recordatorio_enviado(cita_id, 'review_request')
                    enviados += 1
            
            
            
        except Exception as e:
            
            import traceback
            traceback.print_exc()
    
    def auto_cancel_unpaid_appointments(self):
        """Cancela automáticamente citas sin pago después del deadline"""
        try:
            
            now = datetime.now(self.mexico_tz)
            
            # Obtener citas con pago pendiente vencido
            citas_ref = self.db.collection('citas')\
                .where('paymentStatus', 'in', ['pending', 'pendiente'])\
                .where('estado', '==', 'confirmado')\
                .stream()
            
            canceladas = 0
            for cita_doc in citas_ref:
                cita_data = cita_doc.to_dict()
                cita_id = cita_doc.id
                
                # Verificar método de pago
                metodo_pago = cita_data.get('metodoPago', '').lower()
                if metodo_pago == 'efectivo':
                    continue
                
                # Verificar deadline
                payment_deadline = cita_data.get('paymentDeadline') or cita_data.get('payment_deadline')
                if not payment_deadline:
                    continue
                
                if isinstance(payment_deadline, str):
                    deadline_dt = datetime.fromisoformat(payment_deadline)
                else:
                    deadline_dt = payment_deadline
                
                if deadline_dt.tzinfo is None:
                    deadline_dt = self.mexico_tz.localize(deadline_dt)
                
                # Si expiró, cancelar
                if deadline_dt < now:
                    self._auto_cancel_cita_sin_pago(cita_id, cita_data)
                    canceladas += 1
            
            
            
        except Exception as e:
            
            import traceback
            traceback.print_exc()

    
    def _get_citas_en_rango(self, start_time: datetime, end_time: datetime) -> List:
        """Obtiene citas en un rango de tiempo específico"""
        try:
            start_date = start_time.strftime('%Y-%m-%d')
            end_date = end_time.strftime('%Y-%m-%d')
            
            citas_ref = self.db.collection('citas')\
                .where('estado', '==', 'confirmado')\
                .where('fecha', '>=', start_date)\
                .where('fecha', '<=', end_date)\
                .stream()
            
            citas_filtradas = []
            for cita_doc in citas_ref:
                cita = self.cita_repo.obtener_por_id(cita_doc.id)
                if not cita:
                    continue
                
                # Verificar hora exacta
                fecha_str = cita.fecha.strftime('%Y-%m-%d') if hasattr(cita.fecha, 'strftime') else str(cita.fecha)
                hora_str = cita.horaInicio or cita.hora or '00:00'
                
                # Parsear fecha/hora
                hora_partes = hora_str.split(':')
                hora = int(hora_partes[0])
                minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                
                fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                cita_datetime = self.mexico_tz.localize(
                    datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day, hora, minuto)
                )
                
                # Verificar si está en rango
                if start_time <= cita_datetime <= end_time:
                    citas_filtradas.append(cita)
            
            return citas_filtradas
            
        except Exception as e:
            print(f"Error obteniendo citas en rango: {e}")
            return []
    
    def _construir_mensaje_recordatorio_24h(self, cita, paciente) -> str:
        """Construye el mensaje de recordatorio 24 horas antes"""
        nombre = paciente.nombre or 'Paciente'
        fecha_str = cita.fecha.strftime('%d/%m/%Y') if hasattr(cita.fecha, 'strftime') else str(cita.fecha)
        hora_str = cita.horaInicio or cita.hora or 'N/A'
        dentista = cita.dentistaName or 'tu dentista'
        consultorio = cita.consultorioName or 'el consultorio'
        
        mensaje = f"""Hola {nombre},

*Recordatorio de Cita - Mañana*

*Fecha:* {fecha_str}
*Hora:* {hora_str}
*Dentista:* {dentista}
*Consultorio:* {consultorio}

*Dirección:* {cita.direccion or 'Ver en la app'}

*Recomendaciones:*
• Llega 10 minutos antes
• Trae tu identificación
• Cepilla tus dientes antes de asistir

¿Necesitas reagendar? Responde *"reagendar"*

¡Te esperamos!"""
        
        return mensaje
    
    def _construir_mensaje_recordatorio_2h(self, cita, paciente) -> str:
        """Construye el mensaje de recordatorio 2 horas antes"""
        nombre = paciente.nombre or 'Paciente'
        hora_str = cita.horaInicio or cita.hora or 'N/A'
        dentista = cita.dentistaName or 'tu dentista'
        
        mensaje = f"""Hola {nombre},

*Tu cita es en 2 HORAS*

*Hora:* {hora_str}
*Dentista:* {dentista}

*No olvides:*
* Llegar 10 min antes
* Traer identificación
* Cepillar tus dientes

¡Nos vemos pronto!"""
        
        return mensaje
    
    def _construir_mensaje_pago_pendiente(self, cita_data: Dict, horas_restantes: float) -> str:
        """Construye mensaje de pago pendiente"""
        if horas_restantes <= 2:
            urgencia = "¡MUY URGENTE!"
        elif horas_restantes <= 6:
            urgencia = "¡URGENTE!"
        else:
            urgencia = ""
        
        horas_enteras = int(horas_restantes)
        minutos = int((horas_restantes - horas_enteras) * 60)
        
        tiempo_text = f"{horas_enteras}h {minutos}min" if horas_enteras > 0 else f"{minutos} minutos"
        
        mensaje = f"""{urgencia} *Pago Pendiente*

Tu cita del {cita_data.get('fecha', 'N/A')} a las {cita_data.get('horaInicio', 'N/A')} tiene pago pendiente.

*Tiempo restante:* {tiempo_text}

Si no confirmas el pago, tu cita será CANCELADA automáticamente.

Para pagar o confirmar, responde: *"ya pagué"*"""
        
        return mensaje
    
    def _ya_enviado_recordatorio(self, entidad_id: str, tipo: str, 
                                 hoy: bool = False, dias: int = 0) -> bool:
        """Verifica si ya se envió un recordatorio"""
        try:
            # Buscar en colección de recordatorios
            recordatorios_ref = self.db.collection('recordatorios')\
                .where('entidad_id', '==', entidad_id)\
                .where('tipo', '==', tipo)\
                .order_by('fecha_envio', direction='DESCENDING')\
                .limit(1)\
                .stream()
            
            for rec_doc in recordatorios_ref:
                rec_data = rec_doc.to_dict()
                fecha_envio = rec_data.get('fecha_envio')
                
                if isinstance(fecha_envio, str):
                    fecha_envio_dt = datetime.fromisoformat(fecha_envio)
                else:
                    fecha_envio_dt = fecha_envio
                
                if fecha_envio_dt.tzinfo is None:
                    fecha_envio_dt = self.mexico_tz.localize(fecha_envio_dt)
                
                now = datetime.now(self.mexico_tz)
                
                if hoy:
                    # Verificar si es hoy
                    return fecha_envio_dt.date() == now.date()
                elif dias > 0:
                    # Verificar si fue en los últimos N días
                    return (now - fecha_envio_dt).days < dias
                else:
                    # Ya existe recordatorio
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error verificando recordatorio: {e}")
            return False
    
    def _registrar_recordatorio_enviado(self, entidad_id: str, tipo: str):
        """Registra que se envió un recordatorio"""
        try:
            self.db.collection('recordatorios').add({
                'entidad_id': entidad_id,
                'tipo': tipo,
                'fecha_envio': datetime.now(self.mexico_tz),
                'creado': datetime.now(self.mexico_tz)
            })
        except Exception as e:
            print(f"Error registrando recordatorio: {e}")
    
    def _auto_cancel_cita_sin_pago(self, cita_id: str, cita_data: Dict):
        """Cancela automáticamente una cita sin pago"""
        try:
            # Actualizar estado
            self.db.collection('citas').document(cita_id).update({
                'estado': 'cancelada',
                'motivo_cancelacion': 'Pago no confirmado a tiempo',
                'cancelado_automaticamente': True,
                'fecha_cancelacion': datetime.now(self.mexico_tz),
                'actualizado': datetime.now(self.mexico_tz)
            })
            
            # Notificar al paciente
            paciente_id = cita_data.get('pacienteId') or cita_data.get('paciente_id')
            if paciente_id:
                paciente = self.paciente_repo.buscar_por_id(paciente_id)
                if paciente and paciente.telefono:
                    mensaje = f"""*Cita Cancelada*

Tu cita del {cita_data.get('fecha', 'N/A')} a las {cita_data.get('horaInicio', 'N/A')} fue cancelada por falta de confirmación de pago.

Si deseas agendar nuevamente, escribe *"agendar cita"*.

Disculpa las molestias."""
                    
                    result = self.whatsapp.send_text_message(
                        to_number=paciente.telefono,
                        message=mensaje
                    )
            
            
            
        except Exception as e:
            print(f"Error auto-cancelando cita: {e}")
    
    def process_message_retries(self):
        """
        Procesa los reintentos pendientes de mensajes fallidos
        J.RF10, J.RNF15: Reenvío automático
        """
        try:
            from services.retry_service import retry_service
            
            processed = retry_service.process_pending_retries()
            # Procesados: {processed} mensajes
        except Exception as e:
            import traceback
            traceback.print_exc()

# Instancia global del scheduler
reminder_scheduler = ReminderScheduler()


def start_reminder_system():
    """Función para iniciar el sistema de recordatorios"""
    reminder_scheduler.start()
    return reminder_scheduler


def stop_reminder_system():
    """Función para detener el sistema de recordatorios"""
    reminder_scheduler.stop()
