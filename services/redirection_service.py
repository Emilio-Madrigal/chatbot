"""
🔄 SERVICIO DE REDIRECCIÓN DE CITAS
Sistema para manejar las respuestas del paciente cuando un dentista
cancela o reagenda una cita, ofreciendo alternativas.

RED.RF1-RF4: Redirección inteligente de citas
"""

import requests
from config import Config
from database.database import FirebaseConfig
from datetime import datetime, timedelta

class RedirectionService:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.functions_base_url = "https://us-central1-densora-4f01d.cloudfunctions.net"
    
    def check_pending_redirection(self, phone: str) -> dict:
        """
        Verifica si hay una solicitud de redirección pendiente para este teléfono.
        Retorna la información de la redirección si existe.
        """
        try:
            # Buscar redirección pendiente por teléfono
            redirections = self.db.collection('redirectionRequests')\
                .where('telefonoPaciente', '==', phone)\
                .where('estado', '==', 'pendiente')\
                .order_by('createdAt', direction='DESCENDING')\
                .limit(1)\
                .get()
            
            if not redirections:
                return None
            
            doc = redirections[0]
            data = doc.to_dict()
            
            # Verificar que no haya expirado
            expires_at = data.get('expiresAt')
            if expires_at:
                if isinstance(expires_at, datetime):
                    if expires_at < datetime.now():
                        return None
                else:
                    # Es un Timestamp de Firestore
                    if expires_at.to_datetime() < datetime.now():
                        return None
            
            return {
                'token': doc.id,
                'tipo_accion': data.get('tipoAccion'),
                'cita_id': data.get('citaId'),
                'alternativas': data.get('alternativas', []),
                'tratamiento': data.get('tratamiento'),
                'nueva_fecha_hora': data.get('nuevaFechaHora'),
                'dentista_original_id': data.get('dentistaIdOriginal')
            }
            
        except Exception as e:
            print(f"[Redirection] Error verificando redirección: {e}")
            return None
    
    def is_redirection_response(self, text: str) -> bool:
        """
        Verifica si el texto es una respuesta a una solicitud de redirección.
        """
        text_upper = text.upper().strip()
        
        keywords = ['ACEPTAR', 'CANCELAR', 'ALTERNATIVAS', 'OPCION']
        
        for keyword in keywords:
            if text_upper.startswith(keyword):
                return True
        
        return False
    
    def process_response(self, phone: str, text: str) -> dict:
        """
        Procesa la respuesta del paciente a una solicitud de redirección.
        
        Posibles respuestas:
        - ACEPTAR: Confirma la nueva fecha (solo para reagendación)
        - CANCELAR: Cancela la cita
        - ALTERNATIVAS: Muestra todas las alternativas disponibles
        - OPCION 1, OPCION 2, etc.: Selecciona una alternativa específica
        """
        try:
            # Verificar si hay redirección pendiente
            redirection = self.check_pending_redirection(phone)
            
            if not redirection:
                return {
                    'success': False,
                    'mensaje': 'No hay una solicitud de redirección activa. Escribe *menu* para ver las opciones disponibles.'
                }
            
            text_upper = text.upper().strip()
            token = redirection['token']
            
            # Procesar según el tipo de respuesta
            if text_upper == 'ACEPTAR':
                return self._handle_accept(redirection)
            
            elif text_upper == 'CANCELAR':
                return self._handle_cancel(redirection)
            
            elif text_upper == 'ALTERNATIVAS':
                return self._handle_show_alternatives(redirection)
            
            elif text_upper.startswith('OPCION '):
                option_num = text_upper.replace('OPCION ', '').strip()
                return self._handle_select_alternative(redirection, option_num)
            
            else:
                return {
                    'success': False,
                    'mensaje': '❓ No entendí tu respuesta. Por favor escribe:\n' +
                              '• *ACEPTAR* - Para confirmar la nueva fecha\n' +
                              '• *CANCELAR* - Para cancelar la cita\n' +
                              '• *ALTERNATIVAS* - Para ver otras opciones\n' +
                              '• *OPCION 1*, *OPCION 2*, etc. - Para agendar una alternativa'
                }
        
        except Exception as e:
            print(f"[Redirection] Error procesando respuesta: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'mensaje': 'Ocurrió un error procesando tu respuesta. Intenta nuevamente.'
            }
    
    def _handle_accept(self, redirection: dict) -> dict:
        """Maneja respuesta ACEPTAR (confirmar nueva fecha)"""
        try:
            if redirection['tipo_accion'] != 'reagendacion':
                return {
                    'success': False,
                    'mensaje': 'Esta opción solo está disponible para citas reagendadas.'
                }
            
            # Actualizar estado en Firestore
            self.db.collection('redirectionRequests').document(redirection['token']).update({
                'estado': 'aceptada',
                'respuesta': 'ACEPTAR',
                'respondidoAt': datetime.now()
            })
            
            return {
                'success': True,
                'accion': 'aceptar',
                'mensaje': '✅ ¡Perfecto! Tu cita ha sido confirmada en la nueva fecha.\n\nTe esperamos. Escribe *menu* para más opciones.'
            }
            
        except Exception as e:
            print(f"[Redirection] Error en aceptar: {e}")
            return {
                'success': False,
                'mensaje': 'Error confirmando la cita. Intenta nuevamente.'
            }
    
    def _handle_cancel(self, redirection: dict) -> dict:
        """Maneja respuesta CANCELAR"""
        try:
            cita_id = redirection['cita_id']
            
            # Cancelar la cita en Firestore
            self.db.collection('citas').document(cita_id).update({
                'estado': 'cancelada',
                'canceladoPor': 'paciente_post_reagendacion',
                'canceladoAt': datetime.now()
            })
            
            # Actualizar redirección
            self.db.collection('redirectionRequests').document(redirection['token']).update({
                'estado': 'cancelada',
                'respuesta': 'CANCELAR',
                'respondidoAt': datetime.now()
            })
            
            return {
                'success': True,
                'accion': 'cancelar',
                'mensaje': '❌ Tu cita ha sido cancelada.\n\nSi deseas agendar una nueva cita, escribe *ALTERNATIVAS* para ver opciones con otros dentistas o escribe *menu* para volver al menú principal.'
            }
            
        except Exception as e:
            print(f"[Redirection] Error en cancelar: {e}")
            return {
                'success': False,
                'mensaje': 'Error cancelando la cita. Intenta nuevamente.'
            }
    
    def _handle_show_alternatives(self, redirection: dict) -> dict:
        """Maneja respuesta ALTERNATIVAS (mostrar opciones)"""
        try:
            alternativas = redirection.get('alternativas', [])
            
            if not alternativas:
                return {
                    'success': True,
                    'accion': 'alternativas',
                    'mensaje': '😔 Lo sentimos, no encontramos alternativas disponibles en este momento.\n\nPuedes buscar manualmente en app.densora.com\n\nEscribe *menu* para volver al menú principal.'
                }
            
            mensaje = '🔍 *Alternativas disponibles:*\n\n'
            
            for i, alt in enumerate(alternativas[:5]):  # Mostrar máximo 5
                fecha_str = self._format_fecha(alt.get('fechaHora'))
                
                mensaje += f'*OPCION {i + 1}:*\n'
                mensaje += f'👨‍⚕️ Dr./Dra. {alt.get("dentistaNombre", "N/A")}\n'
                mensaje += f'📍 {alt.get("consultorioNombre", "Consultorio")}\n'
                
                if alt.get('consultorioDireccion'):
                    mensaje += f'   {alt.get("consultorioDireccion")}\n'
                
                mensaje += f'📅 {fecha_str}\n'
                
                if alt.get('precio'):
                    mensaje += f'💰 ${alt.get("precio")} MXN\n'
                
                if alt.get('dentistaRating'):
                    mensaje += f'⭐ {alt.get("dentistaRating"):.1f}/5\n'
                
                mensaje += '\n'
            
            if len(alternativas) > 5:
                mensaje += f'... y {len(alternativas) - 5} opciones más\n\n'
            
            mensaje += 'Escribe *OPCION 1*, *OPCION 2*, etc. para agendar.'
            
            return {
                'success': True,
                'accion': 'alternativas',
                'mensaje': mensaje,
                'alternativas': alternativas
            }
            
        except Exception as e:
            print(f"[Redirection] Error mostrando alternativas: {e}")
            return {
                'success': False,
                'mensaje': 'Error obteniendo alternativas. Intenta nuevamente.'
            }
    
    def _handle_select_alternative(self, redirection: dict, option_str: str) -> dict:
        """Maneja selección de una alternativa específica"""
        try:
            # Convertir a número
            try:
                option_num = int(option_str) - 1  # Ajustar a índice 0-based
            except ValueError:
                return {
                    'success': False,
                    'mensaje': f'❌ Opción no válida. Escribe OPCION seguido de un número (ej: OPCION 1)'
                }
            
            alternativas = redirection.get('alternativas', [])
            
            if option_num < 0 or option_num >= len(alternativas):
                return {
                    'success': False,
                    'mensaje': f'❌ Opción no válida. Escribe OPCION 1 hasta OPCION {len(alternativas)}'
                }
            
            alt = alternativas[option_num]
            
            # Crear nueva cita con la alternativa
            from google.cloud.firestore import SERVER_TIMESTAMP
            from datetime import datetime
            
            fecha_hora = alt.get('fechaHora')
            if isinstance(fecha_hora, str):
                fecha_hora = datetime.fromisoformat(fecha_hora.replace('Z', '+00:00'))
            
            nueva_cita = {
                'pacienteId': redirection.get('paciente_id'),
                'dentistaId': alt.get('dentistaId'),
                'consultorioId': alt.get('consultorioId'),
                'fechaHora': fecha_hora,
                'duracion': alt.get('duracion', 60),
                'tratamientoNombre': redirection.get('tratamiento'),
                'precio': alt.get('precio'),
                'estado': 'pendiente',
                'origen': 'redireccion_whatsapp',
                'citaOriginalId': redirection.get('cita_id'),
                'createdAt': SERVER_TIMESTAMP,
                'updatedAt': SERVER_TIMESTAMP
            }
            
            # Agregar a Firestore
            nueva_cita_ref = self.db.collection('citas').add(nueva_cita)
            nueva_cita_id = nueva_cita_ref[1].id
            
            # Actualizar redirección
            self.db.collection('redirectionRequests').document(redirection['token']).update({
                'estado': 'redirigida',
                'respuesta': f'OPCION {option_num + 1}',
                'nuevaCitaId': nueva_cita_id,
                'respondidoAt': datetime.now()
            })
            
            # Formatear mensaje de confirmación
            fecha_str = self._format_fecha(alt.get('fechaHora'))
            
            mensaje = f'✅ ¡Cita agendada exitosamente!\n\n'
            mensaje += f'👨‍⚕️ Dr./Dra. {alt.get("dentistaNombre")}\n'
            mensaje += f'📍 {alt.get("consultorioNombre")}\n'
            mensaje += f'📅 {fecha_str}\n'
            
            if alt.get('precio'):
                mensaje += f'💰 ${alt.get("precio")} MXN\n'
            
            mensaje += '\nTe enviaremos un recordatorio antes de tu cita. ¡Gracias por confiar en Densora!\n\nEscribe *menu* para más opciones.'
            
            return {
                'success': True,
                'accion': 'agendar_alternativa',
                'nuevaCitaId': nueva_cita_id,
                'mensaje': mensaje
            }
            
        except Exception as e:
            print(f"[Redirection] Error seleccionando alternativa: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'mensaje': 'Error agendando la cita. Intenta nuevamente.'
            }
    
    def _format_fecha(self, fecha) -> str:
        """Formatea una fecha para mostrar"""
        try:
            if isinstance(fecha, str):
                fecha = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
            
            dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
            meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            
            dia_semana = dias[fecha.weekday()]
            dia = fecha.day
            mes = meses[fecha.month - 1]
            hora = fecha.strftime('%H:%M')
            
            return f'{dia_semana} {dia} de {mes} a las {hora}'
            
        except Exception:
            return str(fecha) if fecha else 'N/A'


# Instancia global
redirection_service = RedirectionService()
