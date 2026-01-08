"""
🔐 SISTEMA DE TOKENS FIRMADOS PARA ENLACES
J.RNF17: Tokens firmados para enlaces con expiración 24h
"""

import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import base64

class TokenService:
    """
    Genera y valida tokens firmados para enlaces del bot
    """
    
    def __init__(self):
        import os
        self.secret_key = os.getenv('TOKEN_SECRET_KEY', 'densora-secret-key-change-in-production')
        self.token_expiry_hours = 24
    
    def generate_token(self, data: Dict) -> str:
        """
        Genera un token firmado para un enlace
        
        Args:
            data: Datos a incluir en el token (ej: {'action': 'cancel', 'citaId': '123'})
        
        Returns:
            Token firmado en formato base64
        """
        try:
            # Agregar expiración
            expires_at = datetime.now() + timedelta(hours=self.token_expiry_hours)
            token_data = {
                **data,
                'expiresAt': expires_at.isoformat(),
                'issuedAt': datetime.now().isoformat()
            }
            
            # Serializar datos
            payload = json.dumps(token_data, sort_keys=True)
            payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode()
            
            # Generar firma HMAC
            signature = hmac.new(
                self.secret_key.encode(),
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Combinar payload y firma
            token = f"{payload_b64}.{signature}"
            
            return token
            
        except Exception as e:
            print(f"Error generando token: {e}")
            return None
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Valida un token y retorna los datos si es válido
        
        Args:
            token: Token a validar
        
        Returns:
            Dict con los datos del token si es válido, None si es inválido o expirado
        """
        try:
            # Separar payload y firma
            parts = token.split('.')
            if len(parts) != 2:
                return None
            
            payload_b64, signature = parts
            
            # Verificar firma
            expected_signature = hmac.new(
                self.secret_key.encode(),
                payload_b64.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # Decodificar payload
            payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
            token_data = json.loads(payload)
            
            # Verificar expiración
            expires_at_str = token_data.get('expiresAt')
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    return None
            
            # Remover campos internos
            token_data.pop('expiresAt', None)
            token_data.pop('issuedAt', None)
            
            return token_data
            
        except Exception as e:
            print(f"Error validando token: {e}")
            return None
    
    def generate_cancel_link(self, cita_id: str, paciente_id: str) -> str:
        """
        Genera un enlace único para cancelar una cita
        J.RF2: Enlace único para cancelación
        """
        token = self.generate_token({
            'action': 'cancel_appointment',
            'citaId': cita_id,
            'pacienteId': paciente_id
        })
        
        if token:
            return f"http://localhost:4321/CancelarCita?citaId={cita_id}&pacienteId={paciente_id}"
        return None
    
    def generate_medical_history_link(self, paciente_id: str) -> str:
        """
        Genera un enlace único para acceder al historial médico
        J.RF7: Link de acceso rápido al historial médico
        """
        token = self.generate_token({
            'action': 'view_medical_history',
            'pacienteId': paciente_id
        })
        
        if token:
            return f"http://localhost:4321/historialMedico?token={token}"
        return None
    
    def generate_reschedule_link(self, cita_id: str, paciente_id: str) -> str:
        """
        Genera un enlace único para reagendar una cita
        """
        token = self.generate_token({
            'action': 'reschedule_appointment',
            'citaId': cita_id,
            'pacienteId': paciente_id
        })
        
        if token:
            return f"http://localhost:4321/Reagendar?citaId={cita_id}&pacienteId={paciente_id}"
        return None

# Instancia global
token_service = TokenService()

