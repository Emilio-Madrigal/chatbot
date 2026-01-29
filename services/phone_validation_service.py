"""
RNF16: Sistema de validación y bloqueo de números telefónicos
Bloquea números reportados como inválidos tras 3 fallos consecutivos de entrega
"""

from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from google.cloud.firestore import SERVER_TIMESTAMP
import re

class PhoneValidationService:
    """
    RNF16: Servicio para validar y bloquear números de teléfono inválidos
    Bloquea números tras 3 fallos consecutivos de entrega en eventos distintos
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('phone_validation')
        self.max_consecutive_failures = 3
        self.block_duration_days = 30  # Bloqueo por 30 días
    
    def is_valid_phone_format(self, phone: str) -> bool:
        """
        Valida que el número de teléfono tenga un formato válido
        """
        if not phone:
            return False
        
        # Limpiar número
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Debe tener al menos 10 dígitos (sin código de país) o 12+ con código
        if phone_clean.startswith('+'):
            digits = re.sub(r'[^\d]', '', phone_clean)
            return 12 <= len(digits) <= 15
        else:
            digits = re.sub(r'[^\d]', '', phone_clean)
            return len(digits) == 10
    
    def is_phone_blocked(self, phone: str) -> Tuple[bool, Optional[str]]:
        """
        RNF16: Verifica si un número está bloqueado
        
        Returns:
            Tuple[bool, Optional[str]]: (está_bloqueado, razón)
        """
        try:
            phone_normalized = self._normalize_phone(phone)
            
            doc_ref = self.collection.document(phone_normalized)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False, None
            
            data = doc.to_dict()
            
            # Verificar si está bloqueado
            if data.get('blocked', False):
                blocked_until = data.get('blockedUntil')
                
                # Si tiene fecha de expiración, verificar si ya pasó
                if blocked_until:
                    if hasattr(blocked_until, 'timestamp'):
                        blocked_until_dt = datetime.fromtimestamp(blocked_until.timestamp())
                    else:
                        blocked_until_dt = blocked_until
                    
                    if datetime.now() > blocked_until_dt:
                        # El bloqueo expiró, desbloquear
                        doc_ref.update({
                            'blocked': False,
                            'consecutiveFailures': 0,
                            'unblockedAt': SERVER_TIMESTAMP
                        })
                        return False, None
                
                return True, data.get('blockReason', 'Número bloqueado por fallos de entrega')
            
            return False, None
            
        except Exception as e:
            print(f"Error verificando bloqueo de teléfono: {e}")
            return False, None
    
    def record_delivery_failure(self, phone: str, event_type: str, error_message: str) -> Dict:
        """
        RNF16: Registra un fallo de entrega de mensaje
        Si alcanza 3 fallos consecutivos en eventos distintos, bloquea el número
        
        Args:
            phone: Número de teléfono
            event_type: Tipo de evento (appointment_created, reminder, etc.)
            error_message: Mensaje de error de Twilio
            
        Returns:
            Dict con información del estado del número
        """
        try:
            phone_normalized = self._normalize_phone(phone)
            
            doc_ref = self.collection.document(phone_normalized)
            doc = doc_ref.get()
            
            now = datetime.now()
            
            if doc.exists:
                data = doc.to_dict()
                consecutive_failures = data.get('consecutiveFailures', 0)
                failure_events = data.get('failureEvents', [])
                
                # Verificar si es un evento distinto
                last_event_types = [f.get('eventType') for f in failure_events[-3:]] if failure_events else []
                
                # Agregar nuevo fallo
                failure_events.append({
                    'eventType': event_type,
                    'errorMessage': error_message,
                    'timestamp': now.isoformat()
                })
                
                # Solo incrementar si es un evento distinto al último
                if not last_event_types or event_type != last_event_types[-1]:
                    consecutive_failures += 1
                
                # Verificar si debe bloquearse
                should_block = consecutive_failures >= self.max_consecutive_failures
                
                update_data = {
                    'consecutiveFailures': consecutive_failures,
                    'failureEvents': failure_events[-10:],  # Mantener últimos 10
                    'lastFailure': SERVER_TIMESTAMP,
                    'lastEventType': event_type,
                    'lastError': error_message
                }
                
                if should_block and not data.get('blocked', False):
                    # RNF16: Bloquear número
                    update_data['blocked'] = True
                    update_data['blockedAt'] = SERVER_TIMESTAMP
                    update_data['blockedUntil'] = now + timedelta(days=self.block_duration_days)
                    update_data['blockReason'] = f'Bloqueado automáticamente tras {consecutive_failures} fallos consecutivos de entrega'
                    
                    print(f"RNF16: Número {phone_normalized} bloqueado tras {consecutive_failures} fallos consecutivos")
                
                doc_ref.update(update_data)
                
                return {
                    'phone': phone_normalized,
                    'consecutiveFailures': consecutive_failures,
                    'blocked': should_block,
                    'blockReason': update_data.get('blockReason')
                }
            else:
                # Primer fallo registrado
                doc_ref.set({
                    'phone': phone_normalized,
                    'consecutiveFailures': 1,
                    'failureEvents': [{
                        'eventType': event_type,
                        'errorMessage': error_message,
                        'timestamp': now.isoformat()
                    }],
                    'lastFailure': SERVER_TIMESTAMP,
                    'lastEventType': event_type,
                    'lastError': error_message,
                    'blocked': False,
                    'createdAt': SERVER_TIMESTAMP
                })
                
                return {
                    'phone': phone_normalized,
                    'consecutiveFailures': 1,
                    'blocked': False
                }
                
        except Exception as e:
            print(f"Error registrando fallo de entrega: {e}")
            return {'error': str(e)}
    
    def record_delivery_success(self, phone: str) -> None:
        """
        Registra una entrega exitosa, reseteando el contador de fallos
        """
        try:
            phone_normalized = self._normalize_phone(phone)
            
            doc_ref = self.collection.document(phone_normalized)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.update({
                    'consecutiveFailures': 0,
                    'lastSuccess': SERVER_TIMESTAMP
                })
                
        except Exception as e:
            print(f"Error registrando éxito de entrega: {e}")
    
    def unblock_phone(self, phone: str, admin_id: str, reason: str = "") -> bool:
        """
        Desbloquea manualmente un número de teléfono
        """
        try:
            phone_normalized = self._normalize_phone(phone)
            
            doc_ref = self.collection.document(phone_normalized)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            doc_ref.update({
                'blocked': False,
                'consecutiveFailures': 0,
                'unblockedAt': SERVER_TIMESTAMP,
                'unblockedBy': admin_id,
                'unblockReason': reason
            })
            
            print(f"RNF16: Número {phone_normalized} desbloqueado manualmente por {admin_id}")
            return True
            
        except Exception as e:
            print(f"Error desbloqueando teléfono: {e}")
            return False
    
    def get_blocked_phones(self, limit: int = 100) -> list:
        """
        Obtiene lista de números bloqueados
        """
        try:
            blocked_docs = self.collection\
                .where('blocked', '==', True)\
                .limit(limit)\
                .stream()
            
            blocked_phones = []
            for doc in blocked_docs:
                data = doc.to_dict()
                blocked_phones.append({
                    'phone': data.get('phone'),
                    'blockedAt': data.get('blockedAt'),
                    'blockReason': data.get('blockReason'),
                    'consecutiveFailures': data.get('consecutiveFailures')
                })
            
            return blocked_phones
            
        except Exception as e:
            print(f"Error obteniendo teléfonos bloqueados: {e}")
            return []
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normaliza el número de teléfono para usarlo como ID de documento
        """
        # Remover prefijo whatsapp: si existe
        if phone.startswith('whatsapp:'):
            phone = phone.replace('whatsapp:', '')
        
        # Remover caracteres no numéricos excepto +
        return ''.join(c for c in phone if c.isdigit() or c == '+')


# Instancia global
phone_validation_service = PhoneValidationService()
