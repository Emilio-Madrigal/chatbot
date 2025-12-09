"""
SISTEMA DE AUTORIZACIÓN DE HISTORIAL MÉDICO
J.RF11: Solicitud de autorización de acceso al historial médico
"""

from services.whatsapp_service import WhatsAppService
from services.message_logger import message_logger
from services.token_service import token_service
from database.models import PacienteRepository
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz

class MedicalHistoryAuthService:
    """
    Servicio para solicitar autorización de acceso al historial médico
    """
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        self.paciente_repo = PacienteRepository()
        self.db = FirebaseConfig.get_db()
        self.timezone = pytz.timezone('America/Mexico_City')
    
    async def request_medical_history_access(self, paciente_id: str, dentista_id: str,
                                           dentista_name: str, consultorio_name: str,
                                           cita_id: Optional[str] = None) -> Dict:
        """
        J.RF11: Solicita autorización de acceso al historial médico
        
        Envía un mensaje al paciente con enlaces para aprobar o rechazar
        """
        try:
            paciente = self.paciente_repo.buscar_por_id(paciente_id)
            if not paciente or not paciente.telefono:
                return {
                    'success': False,
                    'error': 'Paciente no encontrado o sin teléfono'
                }
            
            # Generar tokens para aprobar y rechazar
            approve_token = token_service.generate_token({
                'action': 'approve_medical_history',
                'pacienteId': paciente_id,
                'dentistaId': dentista_id,
                'citaId': cita_id
            })
            
            reject_token = token_service.generate_token({
                'action': 'reject_medical_history',
                'pacienteId': paciente_id,
                'dentistaId': dentista_id,
                'citaId': cita_id
            })
            
            approve_link = f"https://www.densora.com/authorize-history?token={approve_token}" if approve_token else None
            reject_link = f"https://www.densora.com/reject-history?token={reject_token}" if reject_token else None
            
            mensaje = f"""*SOLICITUD DE ACCESO AL HISTORIAL MÉDICO*

Hola {paciente.nombre or 'Paciente'},

El Dr(a). {dentista_name} del consultorio {consultorio_name} solicita acceso a tu historial médico para brindarte una mejor atención."""
            
            if cita_id:
                mensaje += f"\n\nEsta solicitud está relacionada con tu cita programada."
            
            mensaje += f"""

*¿Deseas autorizar el acceso?*

*Aprobar:* {approve_link if approve_link else 'Contacta con el consultorio'}
*Rechazar:* {reject_link if reject_link else 'Contacta con el consultorio'}

*Nota:* Puedes revocar este acceso en cualquier momento desde tu perfil.

¡Gracias!"""
            
            result = self.whatsapp.send_text_message(paciente.telefono, mensaje)
            
            if result:
                # Guardar solicitud en Firestore
                self.db.collection('pacientes')\
                    .document(paciente_id)\
                    .collection('historial_authorizations')\
                    .add({
                        'dentistaId': dentista_id,
                        'dentistaName': dentista_name,
                        'consultorioName': consultorio_name,
                        'citaId': cita_id,
                        'status': 'pending',
                        'requestedAt': datetime.now(self.timezone),
                        'expiresAt': datetime.now(self.timezone) + timedelta(days=7),  # Expira en 7 días
                        'approveToken': approve_token,
                        'rejectToken': reject_token
                    })
                
                # Registrar en logs
                message_logger.log_message(
                    paciente_id=paciente_id,
                    dentista_id=dentista_id,
                    event_type='medical_history_access_request',
                    message_content=mensaje,
                    delivery_status='sent',
                    message_id=result.get('sid')
                )
            
            return {
                'success': result is not None,
                'message_id': result.get('sid') if result else None
            }
            
        except Exception as e:
            print(f"Error solicitando autorización de historial: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_authorization_response(self, token: str, action: str) -> Dict:
        """
        Procesa la respuesta del paciente (aprobar o rechazar)
        """
        try:
            # Validar token
            token_data = token_service.validate_token(token)
            if not token_data:
                return {
                    'success': False,
                    'error': 'Token inválido o expirado'
                }
            
            paciente_id = token_data.get('pacienteId')
            dentista_id = token_data.get('dentistaId')
            cita_id = token_data.get('citaId')
            
            # Buscar solicitud pendiente
            auth_ref = self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('historial_authorizations')\
                .where('dentistaId', '==', dentista_id)\
                .where('status', '==', 'pending')\
                .order_by('requestedAt', direction='DESCENDING')\
                .limit(1)
            
            auth_doc = None
            for doc in auth_ref.stream():
                auth_doc = doc
                break
            
            if not auth_doc:
                return {
                    'success': False,
                    'error': 'Solicitud no encontrada o ya procesada'
                }
            
            # Actualizar estado
            new_status = 'approved' if action == 'approve' else 'rejected'
            self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('historial_authorizations')\
                .document(auth_doc.id)\
                .update({
                    'status': new_status,
                    'respondedAt': datetime.now(self.timezone),
                    'response': action
                })
            
            # Si se aprobó, crear registro de acceso
            if action == 'approve':
                self.db.collection('dentistas')\
                    .document(dentista_id)\
                    .collection('authorized_patients')\
                    .document(paciente_id)\
                    .set({
                        'authorizedAt': datetime.now(self.timezone),
                        'authorizedFor': cita_id or 'general',
                        'status': 'active'
                    })
            
            return {
                'success': True,
                'status': new_status
            }
            
        except Exception as e:
            print(f"Error procesando autorización: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Instancia global
medical_history_auth_service = MedicalHistoryAuthService()

