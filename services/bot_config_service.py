"""
# SISTEMA DE CONFIGURACIÓN DEL BOT
J.RF16: Interfaz de configuración del bot
J.RNF18: Configuración de firma del bot
"""

from database.database import FirebaseConfig
from datetime import datetime
from typing import Dict, Optional

class BotConfigService:
    """
    Servicio para gestionar la configuración del bot
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('bot_config')
    
    def get_bot_config(self) -> Dict:
        """
        Obtiene la configuración actual del bot
        """
        try:
            doc = self.collection.document('main').get()
            
            if doc.exists:
                return doc.to_dict()
            
            # Configuración por defecto
            default_config = {
                'bot_name': 'Densorita',
                'bot_signature': 'Densora - Tu salud dental, nuestra prioridad',
                'welcome_message': '¡Hola! Soy Densorita, tu asistente virtual de Densora. ¿En qué puedo ayudarte?',
                'help_message': 'Puedo ayudarte con:\n1. Agendar citas\n2. Ver tus citas\n3. Reagendar o cancelar\n4. Información sobre servicios',
                'language': 'es',
                'updatedAt': datetime.now().isoformat(),
                'updatedBy': 'system'
            }
            
            # Guardar configuración por defecto
            self.collection.document('main').set(default_config)
            
            return default_config
            
        except Exception as e:
            print(f"Error obteniendo configuración del bot: {e}")
            return {
                'bot_name': 'Densorita',
                'bot_signature': 'Densora - Tu salud dental, nuestra prioridad',
                'welcome_message': '¡Hola! Soy Densorita, tu asistente virtual de Densora. ¿En qué puedo ayudarte?',
                'help_message': 'Puedo ayudarte con:\n1. Agendar citas\n2. Ver tus citas\n3. Reagendar o cancelar\n4. Información sobre servicios',
                'language': 'es'
            }
    
    def update_bot_config(self, admin_id: str, config_updates: Dict) -> bool:
        """
        Actualiza la configuración del bot
        J.RF16: Permitir actualizar textos del bot desde interfaz web
        J.RNF18: Configuración de firma del bot
        """
        try:
            current_config = self.get_bot_config()
            current_config.update(config_updates)
            current_config['updatedAt'] = datetime.now().isoformat()
            current_config['updatedBy'] = admin_id
            
            self.collection.document('main').set(current_config)
            
            return True
            
        except Exception as e:
            print(f"Error actualizando configuración del bot: {e}")
            return False
    
    def get_bot_signature(self) -> str:
        """
        J.RNF18: Obtiene la firma configurada del bot
        """
        config = self.get_bot_config()
        return config.get('bot_signature', 'Densora - Tu salud dental, nuestra prioridad')
    
    def get_bot_name(self) -> str:
        """
        Obtiene el nombre configurado del bot
        """
        config = self.get_bot_config()
        return config.get('bot_name', 'Densorita')
    
    def format_message_with_signature(self, message: str) -> str:
        """
        Formatea un mensaje agregando la firma del bot
        J.RNF18: Usar firma configurada
        """
        signature = self.get_bot_signature()
        return f"{message}\n\n— {signature}"

# Instancia global
bot_config_service = BotConfigService()

