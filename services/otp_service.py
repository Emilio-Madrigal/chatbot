"""
🔐 SISTEMA DE OTP POR WHATSAPP
J.RF4: Envío de código OTP de verificación durante registro, agendamiento y acciones sensibles
J.RNF10: Límite de reenvío de OTP (1 vez por día)
"""

from services.whatsapp_service import WhatsAppService
from services.message_logger import message_logger
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Optional, Dict
import random
import pytz

class OTPService:
    """
    Servicio para generar y enviar códigos OTP por WhatsApp
    """
    
    def __init__(self):
        self.whatsapp = WhatsAppService()
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('otp_codes')
        self.timezone = pytz.timezone('America/Mexico_City')
        self.otp_expiry_minutes = 15
        self.max_resends_per_day = 1  # J.RNF10: Máximo 1 reenvío por día
    
    def generate_otp(self, length: int = 6) -> str:
        """Genera un código OTP numérico"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    async def send_otp(self, paciente_id: str, telefono: str, 
                      action_type: str = 'verification',
                      nombre: str = 'Usuario') -> Dict:
        """
        Envía un código OTP por WhatsApp
        
        Args:
            paciente_id: ID del paciente
            telefono: Número de teléfono
            action_type: Tipo de acción ('registration', 'appointment', 'cancel', 'reschedule')
            nombre: Nombre del usuario
        
        Returns:
            Dict con success, otp_code, expires_at
        """
        try:
            # J.RNF10: Verificar límite de reenvíos por día
            today = datetime.now(self.timezone).date()
            resends_today = self._count_resends_today(paciente_id, action_type, today)
            
            if resends_today >= self.max_resends_per_day:
                return {
                    'success': False,
                    'error': 'Límite de reenvíos alcanzado. Solo puedes solicitar un OTP por día.',
                    'code': None
                }
            
            # Generar código OTP
            otp_code = self.generate_otp()
            expires_at = datetime.now(self.timezone) + timedelta(minutes=self.otp_expiry_minutes)
            
            # Guardar OTP en Firestore
            otp_doc = self.collection.add({
                'pacienteId': paciente_id,
                'telefono': telefono,
                'otpCode': otp_code,
                'actionType': action_type,
                'expiresAt': expires_at,
                'used': False,
                'createdAt': datetime.now(self.timezone),
                'resendCount': resends_today + 1
            })
            
            # Construir mensaje según tipo de acción
            mensaje = self._build_otp_message(otp_code, action_type, nombre, expires_at)
            
            # Enviar por WhatsApp
            result = self.whatsapp.send_text_message(telefono, mensaje)
            
            if result:
                # Registrar en logs
                message_logger.log_message(
                    paciente_id=paciente_id,
                    dentista_id=None,
                    event_type=f'otp_{action_type}',
                    message_content=mensaje,
                    delivery_status='sent',
                    message_id=result.get('sid')
                )
                
                return {
                    'success': True,
                    'otp_code': otp_code,
                    'expires_at': expires_at.isoformat(),
                    'message_id': result.get('sid')
                }
            else:
                return {
                    'success': False,
                    'error': 'Error enviando OTP por WhatsApp',
                    'code': None
                }
                
        except Exception as e:
            print(f"Error enviando OTP: {e}")
            return {
                'success': False,
                'error': str(e),
                'code': None
            }
    
    def _build_otp_message(self, otp_code: str, action_type: str, 
                          nombre: str, expires_at: datetime) -> str:
        """Construye el mensaje de OTP según el tipo de acción"""
        
        action_messages = {
            'registration': 'verificar tu registro',
            'appointment': 'confirmar tu cita',
            'cancel': 'cancelar tu cita',
            'reschedule': 'reagendar tu cita',
            'verification': 'verificar tu identidad'
        }
        
        action_text = action_messages.get(action_type, 'verificar tu acción')
        
        expires_formatted = expires_at.strftime('%H:%M')
        
        mensaje = f"""🔐 *CÓDIGO DE VERIFICACIÓN - Densora*

Hola {nombre},

Tu código de verificación para {action_text} es:

*{otp_code}*

⏰ Válido por 15 minutos (hasta las {expires_formatted})

⚠️ *IMPORTANTE:*
• No compartas este código con nadie
• El código expira en 15 minutos
• Si no lo solicitaste, ignora este mensaje

¡Gracias por usar Densora! 😊"""
        
        return mensaje
    
    def _count_resends_today(self, paciente_id: str, action_type: str, 
                            date: datetime.date) -> int:
        """Cuenta cuántos OTPs se han enviado hoy para este paciente y acción"""
        try:
            start_of_day = datetime.combine(date, datetime.min.time())
            start_of_day = self.timezone.localize(start_of_day)
            end_of_day = start_of_day + timedelta(days=1)
            
            query = self.collection\
                .where('pacienteId', '==', paciente_id)\
                .where('actionType', '==', action_type)\
                .where('createdAt', '>=', start_of_day)\
                .where('createdAt', '<', end_of_day)
            
            count = sum(1 for _ in query.stream())
            return count
            
        except Exception as e:
            print(f"Error contando reenvíos: {e}")
            return 0
    
    async def verify_otp(self, paciente_id: str, otp_code: str, 
                        action_type: str) -> Dict:
        """
        Verifica un código OTP
        
        Returns:
            Dict con success, valid, reason
        """
        try:
            # Buscar OTP válido
            query = self.collection\
                .where('pacienteId', '==', paciente_id)\
                .where('otpCode', '==', otp_code)\
                .where('actionType', '==', action_type)\
                .where('used', '==', False)\
                .order_by('createdAt', direction='DESCENDING')\
                .limit(1)
            
            otp_doc = None
            for doc in query.stream():
                otp_doc = doc
                break
            
            if not otp_doc:
                return {
                    'success': True,
                    'valid': False,
                    'reason': 'Código OTP no encontrado o ya usado'
                }
            
            otp_data = otp_doc.to_dict()
            expires_at = otp_data.get('expiresAt')
            
            # Verificar expiración
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            elif hasattr(expires_at, 'timestamp'):
                expires_at = expires_at.timestamp().to_datetime()
            
            if expires_at.tzinfo is None:
                expires_at = self.timezone.localize(expires_at)
            
            now = datetime.now(self.timezone)
            
            if now > expires_at:
                return {
                    'success': True,
                    'valid': False,
                    'reason': 'Código OTP expirado'
                }
            
            # Marcar como usado
            self.collection.document(otp_doc.id).update({
                'used': True,
                'usedAt': datetime.now(self.timezone)
            })
            
            return {
                'success': True,
                'valid': True,
                'reason': 'Código OTP válido'
            }
            
        except Exception as e:
            print(f"Error verificando OTP: {e}")
            return {
                'success': False,
                'valid': False,
                'reason': str(e)
            }

# Instancia global
otp_service = OTPService()

