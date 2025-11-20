"""
🎯 SERVICIO DE GESTIÓN DE PAGOS Y CONFIRMACIONES
Maneja pagos, confirmaciones, verificaciones y tiempos de expiración
"""

from database.models import CitaRepository, PacienteRepository
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

class PaymentService:
    """
    Servicio completo para gestión de pagos del chatbot
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.cita_repo = CitaRepository()
        self.paciente_repo = PacienteRepository()
        self.mexico_tz = pytz.timezone('America/Mexico_City')
    
    def get_payment_methods(self) -> Dict:
        """Obtiene información sobre métodos de pago disponibles"""
        return {
            'efectivo': {
                'nombre': 'Efectivo',
                'descripcion': 'Pago en efectivo al momento de la cita',
                'requiere_confirmacion_previa': False,
                'tiempo_pago': 'Al momento de la cita'
            },
            'transferencia': {
                'nombre': 'Transferencia Bancaria',
                'descripcion': 'Transferencia o depósito bancario',
                'requiere_confirmacion_previa': True,
                'tiempo_limite': 24,  # horas antes de la cita
                'instrucciones': 'Debes transferir al menos 24 horas antes de tu cita y enviar comprobante'
            },
            'stripe': {
                'nombre': 'Tarjeta (Stripe)',
                'descripcion': 'Pago en línea con tarjeta de crédito/débito',
                'requiere_confirmacion_previa': True,
                'tiempo_limite': 2,  # horas antes de la cita
                'instrucciones': 'Puedes pagar en línea hasta 2 horas antes de tu cita'
            }
        }
    
    def calcular_tiempo_restante_pago(self, cita: Dict, metodo_pago: str) -> Dict:
        """
        Calcula cuánto tiempo queda para realizar el pago
        
        Returns:
            Dict con:
            - tiene_tiempo: bool - Si aún hay tiempo para pagar
            - horas_restantes: int - Horas que quedan
            - minutos_restantes: int - Minutos que quedan
            - mensaje: str - Mensaje descriptivo
            - fecha_limite: str - Fecha límite ISO
        """
        try:
            metodos = self.get_payment_methods()
            info_metodo = metodos.get(metodo_pago.lower(), {})
            
            # Si es efectivo, no hay límite de tiempo
            if metodo_pago.lower() == 'efectivo':
                return {
                    'tiene_tiempo': True,
                    'horas_restantes': 999,
                    'minutos_restantes': 59,
                    'mensaje': 'Pagas en efectivo al momento de la cita. No hay límite de tiempo.',
                    'fecha_limite': None
                }
            
            # Obtener fecha/hora de la cita
            fecha_cita_str = cita.get('fecha') or cita.get('fechaCita')
            hora_cita_str = cita.get('hora') or cita.get('horaInicio')
            
            if not fecha_cita_str or not hora_cita_str:
                return {
                    'tiene_tiempo': False,
                    'error': 'No se pudo determinar fecha/hora de la cita',
                    'mensaje': 'Error: fecha de cita no disponible'
                }
            
            # Parsear fecha y hora
            fecha_cita = datetime.strptime(fecha_cita_str, '%Y-%m-%d')
            # Parsear hora (formato puede ser HH:MM o HH:MM:SS)
            if ':' in hora_cita_str:
                partes_hora = hora_cita_str.split(':')
                hora = int(partes_hora[0])
                minuto = int(partes_hora[1])
            else:
                hora = int(hora_cita_str)
                minuto = 0
            
            # Combinar fecha y hora
            fecha_hora_cita = datetime(
                fecha_cita.year, fecha_cita.month, fecha_cita.day,
                hora, minuto
            )
            fecha_hora_cita = self.mexico_tz.localize(fecha_hora_cita)
            
            # Obtener tiempo límite según método de pago
            tiempo_limite_horas = info_metodo.get('tiempo_limite', 24)
            fecha_limite = fecha_hora_cita - timedelta(hours=tiempo_limite_horas)
            
            # Calcular tiempo restante
            ahora = datetime.now(self.mexico_tz)
            tiempo_restante = fecha_limite - ahora
            
            if tiempo_restante.total_seconds() <= 0:
                return {
                    'tiene_tiempo': False,
                    'horas_restantes': 0,
                    'minutos_restantes': 0,
                    'mensaje': f'⚠️ El tiempo para pagar ha expirado. Debías pagar al menos {tiempo_limite_horas} horas antes de la cita.',
                    'fecha_limite': fecha_limite.isoformat()
                }
            
            horas_restantes = int(tiempo_restante.total_seconds() // 3600)
            minutos_restantes = int((tiempo_restante.total_seconds() % 3600) // 60)
            
            # Generar mensaje descriptivo
            if horas_restantes > 48:
                dias = horas_restantes // 24
                mensaje = f'Tienes {dias} días para realizar el pago.'
            elif horas_restantes > 24:
                mensaje = f'Tienes {horas_restantes} horas ({horas_restantes // 24} día y {horas_restantes % 24} horas) para pagar.'
            elif horas_restantes > 1:
                mensaje = f'Tienes {horas_restantes} horas y {minutos_restantes} minutos para realizar el pago.'
            elif horas_restantes == 1:
                mensaje = f'¡URGENTE! Tienes 1 hora y {minutos_restantes} minutos para pagar.'
            else:
                mensaje = f'⚠️ ¡MUY URGENTE! Solo tienes {minutos_restantes} minutos para realizar el pago.'
            
            return {
                'tiene_tiempo': True,
                'horas_restantes': horas_restantes,
                'minutos_restantes': minutos_restantes,
                'mensaje': mensaje,
                'fecha_limite': fecha_limite.isoformat(),
                'fecha_cita': fecha_hora_cita.isoformat()
            }
            
        except Exception as e:
            print(f"Error calculando tiempo restante: {e}")
            import traceback
            traceback.print_exc()
            return {
                'tiene_tiempo': False,
                'error': str(e),
                'mensaje': 'Error calculando tiempo restante'
            }
    
    def confirmar_pago(self, cita_id: str, metodo_confirmacion: str = 'chatbot',
                       comprobante_url: str = None, notas: str = None) -> Dict:
        """
        Confirma el pago de una cita
        
        Args:
            cita_id: ID de la cita
            metodo_confirmacion: 'chatbot', 'web', 'manual'
            comprobante_url: URL del comprobante (opcional)
            notas: Notas adicionales (opcional)
        
        Returns:
            Dict con resultado de la confirmación
        """
        try:
            # Obtener cita
            cita = self.cita_repo.obtener_por_id(cita_id)
            if not cita:
                return {
                    'success': False,
                    'error': 'Cita no encontrada',
                    'mensaje': 'No se encontró la cita especificada.'
                }
            
            # Verificar que el pago esté pendiente
            estado_pago = cita.paymentStatus or cita.estado_pago or 'pending'
            if estado_pago == 'pagado' or estado_pago == 'paid':
                return {
                    'success': False,
                    'error': 'Pago ya confirmado',
                    'mensaje': 'El pago de esta cita ya fue confirmado previamente.'
                }
            
            # Actualizar estado de pago
            ahora = datetime.now(self.mexico_tz)
            datos_actualizacion = {
                'paymentStatus': 'pending_verification',  # Pendiente de verificación
                'estado_pago': 'pendiente_verificacion',
                'fecha_confirmacion_usuario': ahora.isoformat(),
                'metodo_confirmacion': metodo_confirmacion,
                'actualizado': ahora
            }
            
            if comprobante_url:
                datos_actualizacion['comprobante_url'] = comprobante_url
            if notas:
                datos_actualizacion['notas_pago'] = notas
            
            # Actualizar en Firestore
            cita_ref = self.db.collection('citas').document(cita_id)
            cita_ref.update(datos_actualizacion)
            
            # TODO: Enviar notificación al dentista/admin para verificar pago
            
            return {
                'success': True,
                'mensaje': '✅ Confirmación recibida. Tu pago está siendo verificado y te notificaremos pronto.',
                'estado': 'pending_verification',
                'cita_id': cita_id
            }
            
        except Exception as e:
            print(f"Error confirmando pago: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'mensaje': 'Ocurrió un error al confirmar el pago. Por favor intenta nuevamente.'
            }
    
    def verificar_pago(self, cita_id: str, verificado_por: str, aprobado: bool = True,
                      motivo_rechazo: str = None) -> Dict:
        """
        Verifica un pago (solo para admin/dentista)
        
        Args:
            cita_id: ID de la cita
            verificado_por: UID del verificador (dentista/admin)
            aprobado: Si el pago fue aprobado o rechazado
            motivo_rechazo: Motivo si fue rechazado
        """
        try:
            ahora = datetime.now(self.mexico_tz)
            estado_nuevo = 'paid' if aprobado else 'rejected'
            
            datos_actualizacion = {
                'paymentStatus': estado_nuevo,
                'estado_pago': 'pagado' if aprobado else 'rechazado',
                'fecha_verificacion': ahora.isoformat(),
                'verificado_por': verificado_por,
                'actualizado': ahora
            }
            
            if not aprobado and motivo_rechazo:
                datos_actualizacion['motivo_rechazo_pago'] = motivo_rechazo
            
            # Actualizar en Firestore
            cita_ref = self.db.collection('citas').document(cita_id)
            cita_ref.update(datos_actualizacion)
            
            # TODO: Enviar notificación al paciente
            
            return {
                'success': True,
                'aprobado': aprobado,
                'mensaje': 'Pago verificado exitosamente'
            }
            
        except Exception as e:
            print(f"Error verificando pago: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_citas_con_pago_pendiente(self, paciente_id: str = None, 
                                     telefono: str = None) -> List[Dict]:
        """Obtiene citas con pago pendiente de un paciente"""
        try:
            # Obtener paciente
            paciente = None
            if paciente_id:
                paciente = self.paciente_repo.buscar_por_id(paciente_id)
            elif telefono:
                paciente = self.paciente_repo.buscar_por_telefono(telefono)
            
            if not paciente:
                return []
            
            # Obtener todas las citas del paciente
            citas = self.cita_repo.obtener_citas_paciente(paciente.uid)
            
            # Filtrar citas con pago pendiente
            citas_pendientes = []
            for cita in citas:
                estado_pago = cita.paymentStatus or cita.estado_pago or 'pending'
                metodo_pago = cita.metodoPago or cita.metodo_pago or 'efectivo'
                
                # Solo incluir si requiere pago previo y está pendiente
                if estado_pago.lower() in ['pending', 'pendiente', 'pending_verification', 'pendiente_verificacion']:
                    if metodo_pago.lower() != 'efectivo':
                        # Convertir a dict
                        cita_dict = {
                            'id': cita.id,
                            'fecha': cita.fecha.strftime('%Y-%m-%d') if hasattr(cita.fecha, 'strftime') else str(cita.fecha),
                            'hora': cita.horaInicio or cita.hora,
                            'dentista': cita.dentistaName or 'N/A',
                            'consultorio': cita.consultorioName or 'N/A',
                            'motivo': cita.motivo or 'Consulta',
                            'precio': cita.precio or 0,
                            'metodo_pago': metodo_pago,
                            'estado_pago': estado_pago,
                            'nombre_cliente': cita.nombre_cliente or ''
                        }
                        citas_pendientes.append(cita_dict)
            
            return citas_pendientes
            
        except Exception as e:
            print(f"Error obteniendo citas con pago pendiente: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def generar_link_pago_stripe(self, cita_id: str) -> Optional[str]:
        """
        Genera un link de pago de Stripe para una cita
        
        Returns:
            URL del link de pago o None si falla
        """
        try:
            # TODO: Implementar integración con Stripe Payment Links
            # Por ahora retornar placeholder
            return f"https://densora.com/pagar/{cita_id}"
        except Exception as e:
            print(f"Error generando link de pago: {e}")
            return None
    
    def get_instrucciones_pago(self, metodo_pago: str, cita: Dict = None) -> str:
        """
        Genera instrucciones detalladas de pago según el método
        """
        metodos = self.get_payment_methods()
        info = metodos.get(metodo_pago.lower(), {})
        
        if metodo_pago.lower() == 'efectivo':
            return """💵 *PAGO EN EFECTIVO*

No necesitas hacer nada ahora. Pagarás el monto exacto al momento de tu cita.

ℹ️ Recuerda llevar efectivo suficiente el día de tu cita."""
        
        elif metodo_pago.lower() == 'transferencia':
            # TODO: Obtener datos bancarios del consultorio
            return """🏦 *PAGO POR TRANSFERENCIA*

1️⃣ Realiza la transferencia a:
   • Banco: BBVA
   • CLABE: 012180001234567890
   • Titular: Consultorio Dental

2️⃣ Envía tu comprobante respondiendo a este mensaje

3️⃣ Debes pagar al menos 24 horas antes de tu cita

⚠️ Tu cita se confirmará una vez que verifiquemos el pago."""
        
        elif metodo_pago.lower() == 'stripe':
            link = self.generar_link_pago_stripe(cita.get('id')) if cita else None
            mensaje = """💳 *PAGO CON TARJETA (STRIPE)*

1️⃣ Haz clic en el siguiente link para pagar en línea de forma segura:

"""
            if link:
                mensaje += f"{link}\n\n"
            
            mensaje += """2️⃣ Tu pago se procesará inmediatamente
3️⃣ Recibirás confirmación por correo y WhatsApp

✅ Pago 100% seguro con encriptación SSL"""
            
            return mensaje
        
        else:
            return "Método de pago no reconocido. Por favor contacta con soporte."
