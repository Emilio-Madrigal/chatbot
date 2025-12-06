"""
🚦 SISTEMA DE RATE LIMITING
J.RNF5: Límite de 3 mensajes por hora por paciente
"""

from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Optional, Dict

class RateLimiter:
    """
    Controla el límite de mensajes por hora para prevenir spam
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('whatsapp_rate_limits')
        self.max_messages_per_hour = 3
    
    def check_rate_limit(self, paciente_id: str) -> Dict:
        """
        Verifica si el paciente puede enviar más mensajes
        
        Returns:
            Dict con:
            - allowed: bool - Si puede enviar mensaje
            - messages_sent: int - Mensajes enviados en la última hora
            - reset_time: datetime - Cuándo se resetea el contador
            - message: str - Mensaje explicativo
        """
        try:
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            
            # Buscar registro del paciente
            doc_ref = self.collection.document(paciente_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                # Primera vez, permitir
                doc_ref.set({
                    'messages': [now.isoformat()],
                    'lastReset': now.isoformat(),
                    'createdAt': now.isoformat()
                })
                return {
                    'allowed': True,
                    'messages_sent': 1,
                    'reset_time': now + timedelta(hours=1),
                    'message': ''
                }
            
            data = doc.to_dict()
            messages = data.get('messages', [])
            
            # Filtrar mensajes de la última hora
            recent_messages = []
            for msg_time_str in messages:
                try:
                    msg_time = datetime.fromisoformat(msg_time_str)
                    if msg_time >= one_hour_ago:
                        recent_messages.append(msg_time)
                except:
                    continue
            
            # Ordenar por más reciente
            recent_messages.sort(reverse=True)
            
            # Verificar límite
            if len(recent_messages) >= self.max_messages_per_hour:
                # Calcular cuándo se resetea (hora del mensaje más antiguo + 1 hora)
                oldest_message = recent_messages[-1]
                reset_time = oldest_message + timedelta(hours=1)
                minutes_remaining = int((reset_time - now).total_seconds() / 60)
                
                return {
                    'allowed': False,
                    'messages_sent': len(recent_messages),
                    'reset_time': reset_time,
                    'message': f'Has alcanzado el límite de {self.max_messages_per_hour} mensajes por hora. Intenta de nuevo en {minutes_remaining} minutos.'
                }
            
            # Permitir y registrar mensaje
            recent_messages.append(now)
            # Mantener solo los de la última hora
            recent_messages = [m for m in recent_messages if m >= one_hour_ago]
            
            doc_ref.update({
                'messages': [m.isoformat() for m in recent_messages],
                'lastReset': now.isoformat()
            })
            
            return {
                'allowed': True,
                'messages_sent': len(recent_messages),
                'reset_time': now + timedelta(hours=1),
                'message': ''
            }
            
        except Exception as e:
            print(f"Error verificando rate limit: {e}")
            # En caso de error, permitir (fail open)
            return {
                'allowed': True,
                'messages_sent': 0,
                'reset_time': datetime.now() + timedelta(hours=1),
                'message': ''
            }
    
    def reset_rate_limit(self, paciente_id: str):
        """Resetea el contador de mensajes para un paciente (útil para testing)"""
        try:
            self.collection.document(paciente_id).delete()
        except Exception as e:
            print(f"Error reseteando rate limit: {e}")

# Instancia global
rate_limiter = RateLimiter()

