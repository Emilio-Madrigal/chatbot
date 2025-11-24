"""
🔄 SISTEMA DE REENVÍO Y REINTENTOS
J.RF10: Reenvío automático de mensajes
J.RNF15: Estrategia de reintentos (2 intentos cada 30 min)
"""

from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, Optional
from google.cloud.firestore import SERVER_TIMESTAMP
from services.whatsapp_service import WhatsAppService
from services.message_logger import message_logger

class RetryService:
    """
    Maneja el reenvío automático de mensajes fallidos
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('whatsapp_retry_queue')
        self.whatsapp = WhatsAppService()
        self.max_retries = 2
        self.retry_interval_minutes = 30
    
    def schedule_retry(self, 
                      paciente_id: str,
                      dentista_id: Optional[str],
                      event_type: str,
                      message_content: str,
                      original_message_id: str,
                      error: str):
        """
        Programa un reintento para un mensaje fallido
        """
        try:
            # Verificar si ya hay reintentos programados
            existing_retries = self.collection\
                .where('pacienteId', '==', paciente_id)\
                .where('eventType', '==', event_type)\
                .where('status', '==', 'pending')\
                .stream()
            
            retry_count = sum(1 for _ in existing_retries)
            
            if retry_count >= self.max_retries:
                # Ya se intentó el máximo de veces
                self.collection.add({
                    'pacienteId': paciente_id,
                    'dentistaId': dentista_id,
                    'eventType': event_type,
                    'messageContent': message_content,
                    'originalMessageId': original_message_id,
                    'error': error,
                    'status': 'failed',
                    'retryCount': retry_count + 1,
                    'maxRetriesReached': True,
                    'createdAt': SERVER_TIMESTAMP,
                    'lastAttempt': datetime.now().isoformat()
                })
                return False
            
            # Programar reintento
            retry_time = datetime.now() + timedelta(minutes=self.retry_interval_minutes)
            
            self.collection.add({
                'pacienteId': paciente_id,
                'dentistaId': dentista_id,
                'eventType': event_type,
                'messageContent': message_content,
                'originalMessageId': original_message_id,
                'error': error,
                'status': 'pending',
                'retryCount': retry_count + 1,
                'scheduledFor': retry_time.isoformat(),
                'createdAt': SERVER_TIMESTAMP
            })
            
            return True
            
        except Exception as e:
            print(f"Error programando reintento: {e}")
            return False
    
    def process_pending_retries(self):
        """
        Procesa los reintentos pendientes que ya pasaron su tiempo programado
        """
        try:
            now = datetime.now()
            
            # Buscar reintentos pendientes que ya deben ejecutarse
            pending_retries = self.collection\
                .where('status', '==', 'pending')\
                .stream()
            
            processed = 0
            for retry_doc in pending_retries:
                retry_data = retry_doc.to_dict()
                scheduled_for_str = retry_data.get('scheduledFor')
                
                if not scheduled_for_str:
                    continue
                
                scheduled_for = datetime.fromisoformat(scheduled_for_str)
                
                if scheduled_for <= now:
                    # Intentar reenviar
                    success = self._retry_message(retry_doc.id, retry_data)
                    if success:
                        processed += 1
            
            if processed > 0:
                print(f"✅ Procesados {processed} reintentos pendientes")
            
            return processed
            
        except Exception as e:
            print(f"Error procesando reintentos: {e}")
            return 0
    
    def _retry_message(self, retry_id: str, retry_data: Dict) -> bool:
        """
        Intenta reenviar un mensaje
        """
        try:
            paciente_id = retry_data.get('pacienteId')
            message_content = retry_data.get('messageContent')
            
            # Obtener teléfono del paciente
            from database.models import PacienteRepository
            paciente_repo = PacienteRepository()
            paciente = paciente_repo.buscar_por_id(paciente_id)
            
            if not paciente or not paciente.telefono:
                # Marcar como fallido
                self.collection.document(retry_id).update({
                    'status': 'failed',
                    'error': 'Paciente no encontrado o sin teléfono',
                    'lastAttempt': datetime.now().isoformat()
                })
                return False
            
            # Intentar enviar
            result = self.whatsapp.send_text_message(
                to_number=paciente.telefono,
                message=message_content
            )
            
            if result and result.get('status') == 'sent':
                # Éxito
                self.collection.document(retry_id).update({
                    'status': 'sent',
                    'messageId': result.get('sid'),
                    'sentAt': datetime.now().isoformat(),
                    'lastAttempt': datetime.now().isoformat()
                })
                
                # Registrar en logs
                message_logger.log_message(
                    paciente_id=paciente_id,
                    dentista_id=retry_data.get('dentistaId'),
                    event_type=retry_data.get('eventType'),
                    message_content=message_content,
                    delivery_status='sent',
                    message_id=result.get('sid')
                )
                
                return True
            else:
                # Falló de nuevo, programar otro reintento si no se alcanzó el máximo
                retry_count = retry_data.get('retryCount', 0)
                if retry_count < self.max_retries:
                    # Programar otro reintento
                    new_retry_time = datetime.now() + timedelta(minutes=self.retry_interval_minutes)
                    self.collection.document(retry_id).update({
                        'status': 'pending',
                        'retryCount': retry_count + 1,
                        'scheduledFor': new_retry_time.isoformat(),
                        'lastAttempt': datetime.now().isoformat(),
                        'lastError': 'Reintento fallido'
                    })
                else:
                    # Máximo alcanzado
                    self.collection.document(retry_id).update({
                        'status': 'failed',
                        'maxRetriesReached': True,
                        'lastAttempt': datetime.now().isoformat(),
                        'lastError': 'Máximo de reintentos alcanzado'
                    })
                
                return False
                
        except Exception as e:
            print(f"Error en reintento de mensaje: {e}")
            self.collection.document(retry_id).update({
                'status': 'failed',
                'error': str(e),
                'lastAttempt': datetime.now().isoformat()
            })
            return False

# Instancia global
retry_service = RetryService()

