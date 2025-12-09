"""
# SISTEMA DE CONFIGURACIÓN DE NOTIFICACIONES
J.RF8: Configuración de notificaciones desde app
J.RNF7: Desactivación de notificaciones WhatsApp
"""

from database.database import FirebaseConfig
from datetime import datetime
from typing import Dict, Optional, List

class NotificationConfigService:
    """
    Servicio para gestionar la configuración de notificaciones
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
    
    def get_notification_settings(self, dentista_id: str) -> Dict:
        """
        Obtiene la configuración de notificaciones de un dentista
        """
        try:
            doc = self.db.collection('dentistas')\
                .document(dentista_id)\
                .collection('config')\
                .document('notifications')\
                .get()
            
            if doc.exists:
                return doc.to_dict()
            
            # Configuración por defecto (todas activas)
            default_config = {
                'reminders': True,
                'changes': True,
                'requests': True,
                'reviews': True,
                'whatsapp_enabled': True,
                'email_enabled': True,
                'push_enabled': True,
                'updatedAt': datetime.now().isoformat()
            }
            
            # Guardar configuración por defecto
            self.db.collection('dentistas')\
                .document(dentista_id)\
                .collection('config')\
                .document('notifications')\
                .set(default_config)
            
            return default_config
            
        except Exception as e:
            print(f"Error obteniendo configuración de notificaciones: {e}")
            # Retornar configuración por defecto
            return {
                'reminders': True,
                'changes': True,
                'requests': True,
                'reviews': True,
                'whatsapp_enabled': True,
                'email_enabled': True,
                'push_enabled': True
            }
    
    def update_notification_settings(self, dentista_id: str, settings: Dict) -> bool:
        """
        Actualiza la configuración de notificaciones de un dentista
        J.RF8: Permitir activar/desactivar tipos de notificaciones
        """
        try:
            current_settings = self.get_notification_settings(dentista_id)
            current_settings.update(settings)
            current_settings['updatedAt'] = datetime.now().isoformat()
            
            self.db.collection('dentistas')\
                .document(dentista_id)\
                .collection('config')\
                .document('notifications')\
                .set(current_settings)
            
            return True
            
        except Exception as e:
            print(f"Error actualizando configuración de notificaciones: {e}")
            return False
    
    def get_patient_notification_settings(self, paciente_id: str) -> Dict:
        """
        Obtiene la configuración de notificaciones de un paciente
        J.RNF7: Desactivación de notificaciones WhatsApp
        """
        try:
            doc = self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('config')\
                .document('notifications')\
                .get()
            
            if doc.exists:
                return doc.to_dict()
            
            # Configuración por defecto
            default_config = {
                'whatsapp_enabled': True,
                'email_enabled': True,
                'push_enabled': True,
                'reminders_enabled': True,
                'reviews_enabled': True,
                'updates_enabled': True,
                'updatedAt': datetime.now().isoformat()
            }
            
            # Guardar configuración por defecto
            self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('config')\
                .document('notifications')\
                .set(default_config)
            
            return default_config
            
        except Exception as e:
            print(f"Error obteniendo configuración de notificaciones del paciente: {e}")
            return {
                'whatsapp_enabled': True,
                'email_enabled': True,
                'push_enabled': True,
                'reminders_enabled': True,
                'reviews_enabled': True,
                'updates_enabled': True
            }
    
    def update_patient_notification_settings(self, paciente_id: str, settings: Dict) -> bool:
        """
        Actualiza la configuración de notificaciones de un paciente
        J.RNF7: Desactivación de notificaciones WhatsApp
        """
        try:
            current_settings = self.get_patient_notification_settings(paciente_id)
            current_settings.update(settings)
            current_settings['updatedAt'] = datetime.now().isoformat()
            
            self.db.collection('pacientes')\
                .document(paciente_id)\
                .collection('config')\
                .document('notifications')\
                .set(current_settings)
            
            return True
            
        except Exception as e:
            print(f"Error actualizando configuración de notificaciones del paciente: {e}")
            return False
    
    def should_send_notification(self, dentista_id: Optional[str], paciente_id: Optional[str],
                                notification_type: str) -> bool:
        """
        Verifica si se debe enviar una notificación según la configuración
        
        Args:
            dentista_id: ID del dentista (opcional)
            paciente_id: ID del paciente (opcional)
            notification_type: Tipo de notificación ('reminder', 'change', 'request', 'review')
        """
        try:
            # Verificar configuración del paciente primero
            if paciente_id:
                patient_settings = self.get_patient_notification_settings(paciente_id)
                if not patient_settings.get('whatsapp_enabled', True):
                    return False
                
                # Verificar tipo específico
                if notification_type == 'reminder' and not patient_settings.get('reminders_enabled', True):
                    return False
                if notification_type == 'review' and not patient_settings.get('reviews_enabled', True):
                    return False
                if notification_type == 'change' and not patient_settings.get('updates_enabled', True):
                    return False
            
            # Verificar configuración del dentista
            if dentista_id:
                dentist_settings = self.get_notification_settings(dentista_id)
                if not dentist_settings.get('whatsapp_enabled', True):
                    return False
                
                # Verificar tipo específico
                type_mapping = {
                    'reminder': 'reminders',
                    'change': 'changes',
                    'request': 'requests',
                    'review': 'reviews'
                }
                
                setting_key = type_mapping.get(notification_type)
                if setting_key and not dentist_settings.get(setting_key, True):
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error verificando configuración de notificaciones: {e}")
            # Por defecto, permitir notificaciones
            return True

# Instancia global
notification_config_service = NotificationConfigService()

