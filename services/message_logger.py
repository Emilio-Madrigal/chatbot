# SISTEMA DE LOGGING DE MENSAJES DEL BOT
# J.RF13, J.RNF4: Registro completo de mensajes enviados por el bot

from database.database import FirebaseConfig
from datetime import datetime
from typing import Dict, Optional
from google.cloud.firestore import SERVER_TIMESTAMP

class MessageLogger:
    """
    Registra todos los mensajes enviados por el bot en Firestore
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('whatsapp_messages')
    
    def log_message(self, 
                   paciente_id: str,
                   dentista_id: Optional[str],
                   event_type: str,
                   message_content: str,
                   delivery_status: str = 'sent',
                   message_id: Optional[str] = None,
                   error: Optional[str] = None) -> str:
        """
        Registra un mensaje enviado por el bot
        
        Args:
            paciente_id: UID del paciente
            dentista_id: UID del dentista (si aplica)
            event_type: Tipo de evento (appointment_created, reminder_24h, etc.)
            message_content: Contenido del mensaje
            delivery_status: Estado de entrega (sent, delivered, read, failed)
            message_id: ID del mensaje de Twilio (si aplica)
            error: Mensaje de error (si falló)
        
        Returns:
            ID del documento creado
        """
        try:
            log_data = {
                'pacienteId': paciente_id,
                'dentistaId': dentista_id,
                'eventType': event_type,
                'messageContent': message_content[:500],  # Limitar tamaño
                'deliveryStatus': delivery_status,
                'messageId': message_id,
                'error': error,
                'timestamp': SERVER_TIMESTAMP,
                'createdAt': datetime.now().isoformat()
            }
            
            doc_ref = self.collection.add(log_data)
            return doc_ref[1].id
            
        except Exception as e:
            print(f"Error registrando mensaje: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_message_stats(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        Obtiene estadísticas de mensajes en un rango de fechas
        J.RNF11: Métricas del bot
        """
        try:
            messages_ref = self.collection\
                .where('timestamp', '>=', start_date)\
                .where('timestamp', '<=', end_date)
            
            total = 0
            by_status = {}
            by_type = {}
            errors = 0
            
            for doc in messages_ref.stream():
                total += 1
                data = doc.to_dict()
                
                status = data.get('deliveryStatus', 'unknown')
                by_status[status] = by_status.get(status, 0) + 1
                
                event_type = data.get('eventType', 'unknown')
                by_type[event_type] = by_type.get(event_type, 0) + 1
                
                if data.get('error'):
                    errors += 1
            
            return {
                'totalMessages': total,
                'byStatus': by_status,
                'byType': by_type,
                'errors': errors,
                'errorRate': (errors / total * 100) if total > 0 else 0
            }
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {
                'totalMessages': 0,
                'byStatus': {},
                'byType': {},
                'errors': 0,
                'errorRate': 0
            }

# Instancia global
message_logger = MessageLogger()

