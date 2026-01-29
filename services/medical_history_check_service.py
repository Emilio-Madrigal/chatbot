"""
RF4: Sistema de verificación de historial médico tras agendamiento
Verifica automáticamente el estado del historial médico y envía alertas al paciente
"""

from services.whatsapp_service import WhatsAppService
from services.message_logger import message_logger
from services.token_service import token_service
from services.language_service import language_service
from services.notification_config_service import notification_config_service
from database.models import PacienteRepository
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import pytz

class MedicalHistoryCheckService:
    """
    RF4: Servicio para verificar historial médico tras agendamiento
    y enviar alertas al paciente si está incompleto
    """
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        self.paciente_repo = PacienteRepository()
        self.db = FirebaseConfig.get_db()
        self.timezone = pytz.timezone('America/Mexico_City')
        
        # Campos requeridos del historial médico
        self.required_fields = [
            'alergias',
            'enfermedadesCronicas',
            'medicamentosActuales',
            'grupoSanguineo',
            'contactoEmergencia'
        ]
        
        # Campos opcionales pero recomendados
        self.recommended_fields = [
            'antecedentesQuirurgicos',
            'antecedentesFamiliares',
            'habitosNocivos',
            'ultimaVisitaDentista'
        ]
    
    async def check_medical_history_after_appointment(self, paciente_id: str, cita_id: str,
                                                      dentista_id: Optional[str] = None,
                                                      dentista_name: str = "",
                                                      fecha_cita: str = "") -> Dict:
        """
        RF4: Verifica el historial médico tras el agendamiento
        Si está incompleto, envía alerta al paciente
        
        Args:
            paciente_id: ID del paciente
            cita_id: ID de la cita agendada
            dentista_id: ID del dentista (opcional)
            dentista_name: Nombre del dentista
            fecha_cita: Fecha de la cita
            
        Returns:
            Dict con el resultado de la verificación
        """
        try:
            # Obtener datos del paciente
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return {
                    'success': False,
                    'error': 'Paciente no encontrado o sin teléfono'
                }
            
            # Verificar configuración de notificaciones
            if not notification_config_service.should_send_notification(
                dentista_id=dentista_id,
                paciente_id=paciente_id,
                notification_type='reminder'
            ):
                print(f"RF4: Notificación de historial médico deshabilitada para paciente {paciente_id}")
                return {
                    'success': True,
                    'notification_sent': False,
                    'reason': 'Notificaciones deshabilitadas'
                }
            
            # Obtener historial médico del paciente
            historial = await self._get_medical_history(paciente_id)
            
            # Verificar completitud
            check_result = self._check_completeness(historial)
            
            if check_result['is_complete']:
                # Historial completo, no enviar alerta
                return {
                    'success': True,
                    'notification_sent': False,
                    'historial_status': 'complete',
                    'completeness_percentage': 100
                }
            
            # RF4: Historial incompleto, enviar alerta al paciente
            notification_result = await self._send_incomplete_history_alert(
                paciente=paciente,
                paciente_id=paciente_id,
                cita_id=cita_id,
                dentista_name=dentista_name,
                fecha_cita=fecha_cita,
                missing_fields=check_result['missing_fields'],
                completeness_percentage=check_result['completeness_percentage']
            )
            
            # Registrar verificación en Firestore
            await self._log_history_check(
                paciente_id=paciente_id,
                cita_id=cita_id,
                check_result=check_result,
                notification_sent=notification_result.get('success', False)
            )
            
            return {
                'success': True,
                'notification_sent': notification_result.get('success', False),
                'historial_status': 'incomplete',
                'completeness_percentage': check_result['completeness_percentage'],
                'missing_fields': check_result['missing_fields']
            }
            
        except Exception as e:
            print(f"RF4: Error verificando historial médico: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_medical_history(self, paciente_id: str) -> Dict:
        """
        Obtiene el historial médico del paciente desde Firestore
        """
        try:
            # Buscar en la subcolección historialMedico del paciente
            historial_ref = self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('historialMedico')\
                .order_by('fechaActualizacion', direction='DESCENDING')\
                .limit(1)
            
            historial_docs = list(historial_ref.stream())
            
            if historial_docs:
                return historial_docs[0].to_dict()
            
            # Si no hay subcolección, buscar en el documento principal
            paciente_doc = self.db.collection('pacientes').document(paciente_id).get()
            if paciente_doc.exists:
                paciente_data = paciente_doc.to_dict()
                return paciente_data.get('historialMedico', {})
            
            return {}
            
        except Exception as e:
            print(f"Error obteniendo historial médico: {e}")
            return {}
    
    def _check_completeness(self, historial: Dict) -> Dict:
        """
        Verifica la completitud del historial médico
        
        Returns:
            Dict con:
            - is_complete: bool
            - completeness_percentage: int
            - missing_fields: list
            - missing_recommended: list
        """
        if not historial:
            return {
                'is_complete': False,
                'completeness_percentage': 0,
                'missing_fields': self.required_fields.copy(),
                'missing_recommended': self.recommended_fields.copy()
            }
        
        # Verificar campos requeridos
        missing_required = []
        for field in self.required_fields:
            value = historial.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                missing_required.append(field)
        
        # Verificar campos recomendados
        missing_recommended = []
        for field in self.recommended_fields:
            value = historial.get(field)
            if not value or (isinstance(value, str) and value.strip() == ''):
                missing_recommended.append(field)
        
        # Calcular porcentaje de completitud (solo campos requeridos)
        total_required = len(self.required_fields)
        completed_required = total_required - len(missing_required)
        completeness_percentage = int((completed_required / total_required) * 100) if total_required > 0 else 0
        
        return {
            'is_complete': len(missing_required) == 0,
            'completeness_percentage': completeness_percentage,
            'missing_fields': missing_required,
            'missing_recommended': missing_recommended
        }
    
    async def _send_incomplete_history_alert(self, paciente, paciente_id: str,
                                            cita_id: str, dentista_name: str,
                                            fecha_cita: str, missing_fields: List[str],
                                            completeness_percentage: int) -> Dict:
        """
        RF4: Envía alerta al paciente sobre historial médico incompleto
        """
        try:
            # Generar enlace para completar historial
            update_link = token_service.generate_token({
                'action': 'update_medical_history',
                'pacienteId': paciente_id,
                'citaId': cita_id
            })
            
            update_url = f"http://localhost:4321/completar-historial?token={update_link}" if update_link else "http://localhost:4321/perfil"
            
            # Obtener idioma del paciente
            language = language_service.get_patient_language(paciente_id)
            
            # Formatear fecha
            fecha_formatted = fecha_cita
            if fecha_cita and isinstance(fecha_cita, str):
                try:
                    fecha_obj = datetime.strptime(fecha_cita, '%Y-%m-%d')
                    fecha_formatted = fecha_obj.strftime('%d/%m/%Y')
                except:
                    pass
            
            # Traducir campos faltantes
            field_translations = {
                'es': {
                    'alergias': 'Alergias',
                    'enfermedadesCronicas': 'Enfermedades crónicas',
                    'medicamentosActuales': 'Medicamentos actuales',
                    'grupoSanguineo': 'Grupo sanguíneo',
                    'contactoEmergencia': 'Contacto de emergencia',
                    'antecedentesQuirurgicos': 'Antecedentes quirúrgicos',
                    'antecedentesFamiliares': 'Antecedentes familiares',
                    'habitosNocivos': 'Hábitos nocivos',
                    'ultimaVisitaDentista': 'Última visita al dentista'
                },
                'en': {
                    'alergias': 'Allergies',
                    'enfermedadesCronicas': 'Chronic diseases',
                    'medicamentosActuales': 'Current medications',
                    'grupoSanguineo': 'Blood type',
                    'contactoEmergencia': 'Emergency contact',
                    'antecedentesQuirurgicos': 'Surgical history',
                    'antecedentesFamiliares': 'Family history',
                    'habitosNocivos': 'Harmful habits',
                    'ultimaVisitaDentista': 'Last dentist visit'
                }
            }
            
            translations = field_translations.get(language, field_translations['es'])
            missing_translated = [translations.get(f, f) for f in missing_fields[:5]]  # Máximo 5 campos
            missing_list = '\n'.join([f"• {field}" for field in missing_translated])
            
            # Construir mensaje según idioma
            if language == 'en':
                mensaje = f"""📋 *COMPLETE YOUR MEDICAL HISTORY*

Hello {paciente.nombre or 'Patient'},

Your appointment has been scheduled for *{fecha_formatted}*{f' with Dr. {dentista_name}' if dentista_name else ''}.

To provide you with better care, we need you to complete your medical history.

*Current status:* {completeness_percentage}% complete

*Missing information:*
{missing_list}

Complete your history before your appointment to speed up your care at the clinic.

👉 *Complete now:* {update_url}

This information is confidential and will only be used for your medical care.

Thank you for your trust!"""
            else:
                mensaje = f"""📋 *COMPLETA TU HISTORIAL MÉDICO*

Hola {paciente.nombre or 'Paciente'},

Tu cita ha sido agendada para el *{fecha_formatted}*{f' con el Dr(a). {dentista_name}' if dentista_name else ''}.

Para brindarte una mejor atención, necesitamos que completes tu historial médico.

*Estado actual:* {completeness_percentage}% completo

*Información faltante:*
{missing_list}

Completa tu historial antes de tu cita para agilizar tu atención en el consultorio.

👉 *Completar ahora:* {update_url}

Esta información es confidencial y solo será utilizada para tu atención médica.

¡Gracias por tu confianza!"""
            
            # Enviar mensaje
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            # Registrar en logs
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='medical_history_incomplete_alert',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            if result:
                print(f"RF4: Alerta de historial médico incompleto enviada a {paciente.telefono}")
            
            return {
                'success': result is not None,
                'message_id': result.get('sid') if result else None
            }
            
        except Exception as e:
            print(f"RF4: Error enviando alerta de historial: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _log_history_check(self, paciente_id: str, cita_id: str,
                                 check_result: Dict, notification_sent: bool) -> None:
        """
        Registra la verificación del historial en Firestore
        """
        try:
            self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('historial_checks')\
                .add({
                    'citaId': cita_id,
                    'checkedAt': datetime.now(self.timezone),
                    'isComplete': check_result['is_complete'],
                    'completenessPercentage': check_result['completeness_percentage'],
                    'missingFields': check_result['missing_fields'],
                    'notificationSent': notification_sent
                })
        except Exception as e:
            print(f"Error registrando verificación de historial: {e}")
    
    async def send_history_reminder_before_appointment(self, cita_id: str, paciente_id: str,
                                                       hours_before: int = 24) -> Dict:
        """
        RF4: Envía recordatorio de completar historial antes de la cita
        Se puede llamar desde el scheduler de recordatorios
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return {'success': False, 'error': 'Paciente no encontrado'}
            
            # Verificar historial
            historial = await self._get_medical_history(paciente_id)
            check_result = self._check_completeness(historial)
            
            if check_result['is_complete']:
                return {
                    'success': True,
                    'notification_sent': False,
                    'reason': 'Historial ya completo'
                }
            
            # Obtener idioma
            language = language_service.get_patient_language(paciente_id)
            
            # Generar enlace
            update_link = token_service.generate_token({
                'action': 'update_medical_history',
                'pacienteId': paciente_id,
                'citaId': cita_id
            })
            update_url = f"http://localhost:4321/completar-historial?token={update_link}" if update_link else "http://localhost:4321/perfil"
            
            if language == 'en':
                mensaje = f"""⏰ *REMINDER: Complete your medical history*

Hello {paciente.nombre or 'Patient'},

Your appointment is in *{hours_before} hours* and your medical history is still incomplete ({check_result['completeness_percentage']}%).

Complete it now to speed up your care:
👉 {update_url}

See you soon!"""
            else:
                mensaje = f"""⏰ *RECORDATORIO: Completa tu historial médico*

Hola {paciente.nombre or 'Paciente'},

Tu cita es en *{hours_before} horas* y tu historial médico aún está incompleto ({check_result['completeness_percentage']}%).

Complétalo ahora para agilizar tu atención:
👉 {update_url}

¡Te esperamos!"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            message_logger.log_message(
                paciente_id=paciente_id,
                dentista_id=None,
                event_type='medical_history_reminder',
                message_content=mensaje,
                delivery_status='sent' if result else 'failed',
                message_id=result.get('sid') if result else None
            )
            
            return {
                'success': result is not None,
                'notification_sent': True
            }
            
        except Exception as e:
            print(f"Error enviando recordatorio de historial: {e}")
            return {'success': False, 'error': str(e)}


# Instancia global
medical_history_check_service = MedicalHistoryCheckService()
