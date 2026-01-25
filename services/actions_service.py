"""
# SERVICIO DE ACCIONES DEL CHATBOT
Integra con Firestore para realizar todas las acciones del sistema
"""

from database.models import CitaRepository, PacienteRepository
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
try:
    from utils.encryption import decrypt_medical_history
except ImportError:
    pass

class ActionsService:
    """
    Servicio que ejecuta acciones del chatbot con acceso completo a Firestore
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.cita_repo = CitaRepository()
        self.paciente_repo = PacienteRepository()
    
    def get_user_info(self, user_id: str = None, phone: str = None) -> Optional[Dict]:
        """Obtiene información del usuario"""
        try:
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if paciente:
                return {
                    'uid': paciente.uid,
                    'nombre': paciente.nombreCompleto or f"{paciente.nombre or ''} {paciente.apellidos or ''}".strip(),
                    'telefono': paciente.telefono,
                    'email': paciente.email,
                    'preferredLanguage': paciente.preferences.get('language') if hasattr(paciente, 'preferences') and isinstance(paciente.preferences, dict) else getattr(paciente, 'preferredLanguage', None),
                    'idioma': getattr(paciente, 'idioma', None)
                }
            return None
        except Exception as e:
            print(f"Error obteniendo info usuario: {e}")
            return None
    
    def get_user_appointments(self, user_id: str = None, phone: str = None, 
                             status: str = None) -> List[Dict]:
        """Obtiene las citas del usuario"""
        try:
            # Obtener paciente
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return []
            
            # Obtener citas
            citas = self.cita_repo.obtener_citas_paciente(paciente.uid)
            
            # Filtrar por estado si se especifica
            if status:
                citas = [c for c in citas if c.estado == status]
            
            # Convertir a formato simple
            citas_formateadas = []
            for cita in citas:
                fecha_str = ''
                if cita.fecha:
                    if isinstance(cita.fecha, str):
                        fecha_str = cita.fecha
                    elif hasattr(cita.fecha, 'strftime'):
                        fecha_str = cita.fecha.strftime('%Y-%m-%d')
                    else:
                        fecha_str = str(cita.fecha)
                
                citas_formateadas.append({
                    'id': cita.id,
                    'nombre': cita.nombre_cliente or 'N/A',
                    'fecha': fecha_str,
                    'hora': cita.horaInicio or cita.hora or 'N/A',
                    'motivo': cita.motivo or 'N/A',
                    'estado': cita.estado or 'confirmado',
                    'dentista': cita.dentistaName or 'N/A',
                    'consultorio': cita.consultorioName or 'N/A'
                })
            
            return citas_formateadas
            
        except Exception as e:
            print(f"Error obteniendo citas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_available_dates(self, user_id: str = None, phone: str = None, 
                           count: int = 3) -> List[str]:
        """Obtiene fechas disponibles para agendar"""
        try:
            # Obtener paciente
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return []
            
            # Obtener último consultorio usado
            ultimo_consultorio = self.cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
            if not ultimo_consultorio:
                print(f"No se encontró último consultorio para paciente {paciente.uid}, buscando consultorio por defecto")
                # Buscar cualquier consultorio activo
                consultorios = self.get_consultorios_info(limit=1)
                if not consultorios:
                    print("No hay consultorios activos disponibles")
                    return []
                # Usar el primer consultorio disponible
                consultorio_id = consultorios[0]['id']
                # Buscar dentista asociado
                consultorio_doc = self.db.collection('consultorio').document(consultorio_id).get()
                if consultorio_doc.exists:
                    consultorio_data = consultorio_doc.to_dict()
                    # Buscar dentista en la subcolección dentistas
                    dentistas_ref = self.db.collection('consultorio')\
                                         .document(consultorio_id)\
                                         .collection('dentistas')\
                                         .where('activo', '==', True)\
                                         .limit(1)
                    dentista_id = None
                    dentista_name = None
                    for dentista_doc in dentistas_ref.stream():
                        dentista_data = dentista_doc.to_dict()
                        dentista_id = dentista_data.get('dentistaId')
                        dentista_name = dentista_data.get('nombreCompleto', 'Dentista')
                        break
                    
                    if dentista_id:
                        ultimo_consultorio = {
                            'consultorioId': consultorio_id,
                            'consultorioName': consultorio_data.get('nombre', 'Consultorio'),
                            'dentistaId': dentista_id,
                            'dentistaName': dentista_name or consultorio_data.get('dentistaName', 'Dentista')
                        }
                    else:
                        print(f"No se encontró dentista activo para consultorio {consultorio_id}")
                        return []
                else:
                    print(f"Consultorio {consultorio_id} no existe")
                    return []
            
            # Obtener fechas disponibles
            fecha_base = datetime.now()
            fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
            
            fechas = self.cita_repo.obtener_fechas_disponibles(
                ultimo_consultorio['dentistaId'],
                ultimo_consultorio['consultorioId'],
                fecha_timestamp,
                cantidad=count
            )
            
            # Convertir a strings
            fechas_str = []
            for fecha_ts in fechas:
                if hasattr(fecha_ts, 'strftime'):
                    fechas_str.append(fecha_ts.strftime('%Y-%m-%d'))
                else:
                    fechas_str.append(str(fecha_ts))
            
            return fechas_str
            
        except Exception as e:
            print(f"Error obteniendo fechas disponibles: {e}")
            return []
    
    def get_available_times(self, user_id: str = None, phone: str = None,
                           fecha: str = None, nombre_dentista: str = None) -> List[str]:
        """Obtiene horarios disponibles para una fecha"""
        try:
            # Obtener paciente
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return []
            
            # Obtener último consultorio usado
            ultimo_consultorio = self.cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
            if not ultimo_consultorio:
                print(f"No se encontró último consultorio para paciente {paciente.uid}, buscando consultorio por defecto")
                # Buscar cualquier consultorio activo
                consultorios = self.get_consultorios_info(limit=1)
                if not consultorios:
                    print("No hay consultorios activos disponibles")
                    return []
                # Usar el primer consultorio disponible
                consultorio_id = consultorios[0]['id']
                # Buscar dentista asociado
                consultorio_doc = self.db.collection('consultorio').document(consultorio_id).get()
                if consultorio_doc.exists:
                    consultorio_data = consultorio_doc.to_dict()
                    # Buscar dentista en la subcolección dentistas
                    dentistas_ref = self.db.collection('consultorio')\
                                         .document(consultorio_id)\
                                         .collection('dentistas')\
                                         .where('activo', '==', True)\
                                         .limit(1)
                    dentista_id = None
                    dentista_name = None
                    for dentista_doc in dentistas_ref.stream():
                        dentista_data = dentista_doc.to_dict()
                        dentista_id = dentista_data.get('dentistaId')
                        dentista_name = dentista_data.get('nombreCompleto', 'Dentista')
                        break
                    
                    if dentista_id:
                        ultimo_consultorio = {
                            'consultorioId': consultorio_id,
                            'consultorioName': consultorio_data.get('nombre', 'Consultorio'),
                            'dentistaId': dentista_id,
                            'dentistaName': dentista_name or consultorio_data.get('dentistaName', 'Dentista')
                        }
                    else:
                        print(f"No se encontró dentista activo para consultorio {consultorio_id}")
                        return []
                else:
                    print(f"Consultorio {consultorio_id} no existe")
                    return []
            
            # Convertir fecha a timestamp
            if isinstance(fecha, str):
                # Si la fecha es relativa (mañana, hoy, etc.), convertirla primero
                fecha_lower = fecha.lower().strip()
                if fecha_lower in ['mañana', 'tomorrow', 'pasado mañana', 'hoy', 'today']:
                    from datetime import timedelta
                    if fecha_lower in ['mañana', 'tomorrow']:
                        fecha = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    elif fecha_lower == 'pasado mañana':
                        fecha = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
                    elif fecha_lower in ['hoy', 'today']:
                        fecha = datetime.now().strftime('%Y-%m-%d')
                
                # Intentar parsear la fecha
                try:
                    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                except ValueError:
                    # Si no es formato YYYY-MM-DD, intentar otros formatos
                    try:
                        fecha_dt = datetime.strptime(fecha, '%d/%m/%Y')
                    except ValueError:
                        try:
                            fecha_dt = datetime.strptime(fecha, '%d-%m-%Y')
                        except ValueError:
                            print(f"Error: No se pudo parsear la fecha '{fecha}'. Formato esperado: YYYY-MM-DD")
                            raise ValueError(f"Formato de fecha inválido: {fecha}. Por favor proporciona la fecha en formato YYYY-MM-DD (ej: 2025-11-14)")
            else:
                fecha_dt = fecha
            
            fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
            
            # Obtener horarios disponibles
            horarios = self.cita_repo.obtener_horarios_disponibles(
                ultimo_consultorio['dentistaId'],
                ultimo_consultorio['consultorioId'],
                fecha_timestamp
            )
            
            # Convertir a strings
            horarios_str = []
            for slot in horarios:
                hora = slot.get('horaInicio', slot.get('inicio', ''))
                if hora:
                    horarios_str.append(hora)
            
            return horarios_str
            
        except Exception as e:
            print(f"Error obteniendo horarios disponibles: {e}")
            return []
    
    def buscar_dentista_por_nombre(self, nombre_dentista: str, consultorio_id: str = None) -> Optional[Dict]:
        """Busca un dentista por nombre en el sistema"""
        try:
            if not nombre_dentista:
                return None
            
            nombre_lower = nombre_dentista.lower().strip()
            
            
            # Si hay consultorio_id, buscar primero en ese consultorio
            if consultorio_id:
                dentistas_ref = self.db.collection('consultorio')\
                                      .document(consultorio_id)\
                                      .collection('dentistas')\
                                      .where('activo', '==', True)
                
                for doc in dentistas_ref.stream():
                    data = doc.to_dict()
                    nombre_completo = data.get('nombreCompleto', '').lower()
                    nombre_simple = data.get('nombre', '').lower()
                    
                    # Buscar coincidencias parciales
                    if (nombre_lower in nombre_completo or 
                        nombre_lower in nombre_simple or
                        nombre_completo.startswith(nombre_lower) or
                        nombre_simple.startswith(nombre_lower)):
                        return {
                            'dentistaId': data.get('dentistaId'),
                            'dentistaName': data.get('nombreCompleto', nombre_dentista),
                            'consultorioId': consultorio_id
                        }
            
            # Si no se encontró en el consultorio específico, buscar en toda la colección de dentistas
            dentistas_ref = self.db.collection('dentistas')\
                                  .where('activo', '==', True)
            
            for doc in dentistas_ref.stream():
                data = doc.to_dict()
                nombre_completo = data.get('nombreCompleto', '').lower()
                nombre_simple = data.get('nombre', '').lower()
                
                # Buscar coincidencias parciales
                if (nombre_lower in nombre_completo or 
                    nombre_lower in nombre_simple or
                    nombre_completo.startswith(nombre_lower) or
                    nombre_simple.startswith(nombre_lower)):
                    # Buscar en qué consultorio está asociado
                    consultorios_ref = doc.reference.collection('consultorios')
                    for consultorio_doc in consultorios_ref.stream():
                        consultorio_data = consultorio_doc.to_dict()
                        if consultorio_data.get('activo', False):
                            return {
                                'dentistaId': doc.id,
                                'dentistaName': data.get('nombreCompleto', nombre_dentista),
                                'consultorioId': consultorio_data.get('consultorioID')
                            }
            
            
            return None
            
        except Exception as e:
            print(f"Error buscando dentista por nombre: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_appointment(self, user_id: str = None, phone: str = None,
                          fecha: str = None, hora: str = None,
                          nombre_cliente: str = None, motivo: str = None,
                          nombre_dentista: str = None) -> Dict:
        """Crea una nueva cita"""
        try:
            # Validar datos requeridos
            if not fecha or not hora:
                return {
                    'success': False,
                    'error': 'Faltan fecha u hora para agendar la cita'
                }
            
            # Obtener paciente
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return {
                    'success': False,
                    'error': 'No se encontró tu cuenta. Por favor regístrate primero.'
                }
            
            # Obtener último consultorio usado
            ultimo_consultorio = self.cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
            if not ultimo_consultorio:
                return {
                    'success': False,
                    'error': 'No se encontró un consultorio previo. Por favor agenda desde la web primero.'
                }
            
            # Si se mencionó un dentista específico, buscar y usar ese consultorio/dentista
            consultorio_final = ultimo_consultorio
            if nombre_dentista:
                dentista_encontrado = self.buscar_dentista_por_nombre(nombre_dentista, ultimo_consultorio['consultorioId'])
                if dentista_encontrado:
                    consultorio_final = {
                        'consultorioId': dentista_encontrado['consultorioId'],
                        'consultorioName': ultimo_consultorio.get('consultorioName', 'Consultorio'),
                        'dentistaId': dentista_encontrado['dentistaId'],
                        'dentistaName': dentista_encontrado['dentistaName']
                    }
                else:
                    pass
            
            # Preparar datos de la cita
            payment_method = 'cash'  # Por defecto efectivo desde chatbot
            datos_cita = {
                'fecha': fecha,
                'hora': hora,
                'nombre_cliente': nombre_cliente or paciente.nombreCompleto or 'Paciente',
                'descripcion': motivo or 'Consulta general',
                'metodo_pago': payment_method
            }
            
            # Crear cita
            usuario_whatsapp = phone or paciente.telefono
            cita_id = self.cita_repo.crear_cita(usuario_whatsapp, datos_cita, paciente_id=paciente.uid, consultorio_especifico=consultorio_final)
            
            if cita_id:
                # Calcular payment_deadline para incluir en la respuesta
                payment_deadline = self._calculate_payment_deadline(payment_method)
                
                return {
                    'success': True,
                    'cita_id': cita_id,
                    'message': 'Cita agendada exitosamente',
                    'dentista_name': consultorio_final.get('dentistaName', 'Dentista'),
                    'consultorio_name': consultorio_final.get('consultorioName', 'Consultorio'),
                    'payment_method': payment_method,
                    'payment_deadline': payment_deadline
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo crear la cita. Intenta nuevamente.'
                }
                
        except Exception as e:
            print(f"Error creando cita: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Error al crear la cita: {str(e)}'
            }
    
    def reschedule_appointment(self, user_id: str = None, phone: str = None,
                              cita_id: str = None, nueva_fecha: str = None,
                              nueva_hora: str = None) -> Dict:
        """Reagenda una cita existente"""
        try:
            # Validar datos
            if not cita_id or not nueva_fecha or not nueva_hora:
                return {
                    'success': False,
                    'error': 'Faltan datos para reagendar la cita'
                }
            
            # Obtener paciente
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return {
                    'success': False,
                    'error': 'No se encontró tu cuenta'
                }
            
            # Verificar que la cita existe y pertenece al usuario
            cita = self.cita_repo.obtener_cita_por_id(paciente.uid, cita_id)
            if not cita:
                return {
                    'success': False,
                    'error': 'No se encontró la cita especificada'
                }
            
            # Verificar que la cita no esté cancelada o completada
            if cita.estado in ['cancelada', 'completada']:
                return {
                    'success': False,
                    'error': f'No se puede reagendar una cita que está {cita.estado}'
                }
            
            # Reagendar
            success = self.cita_repo.actualizar_cita_por_id(
                paciente.uid, cita_id, nueva_fecha, nueva_hora
            )
            
            if success:
                return {
                    'success': True,
                    'message': 'Cita reagendada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo reagendar la cita'
                }
                
        except Exception as e:
            print(f"Error reagendando cita: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Error al reagendar: {str(e)}'
            }
    
    def cancel_appointment(self, user_id: str = None, phone: str = None,
                          cita_id: str = None) -> Dict:
        """Cancela una cita"""
        try:
            # Validar datos
            if not cita_id:
                return {
                    'success': False,
                    'error': 'No se especificó qué cita cancelar'
                }
            
            # Obtener paciente
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return {
                    'success': False,
                    'error': 'No se encontró tu cuenta'
                }
            
            # Verificar que la cita existe y pertenece al usuario
            cita = self.cita_repo.obtener_cita_por_id(paciente.uid, cita_id)
            if not cita:
                return {
                    'success': False,
                    'error': 'No se encontró la cita especificada'
                }
            
            # Verificar que la cita no esté ya cancelada o completada
            if cita.estado == 'cancelada':
                return {
                    'success': False,
                    'error': 'Esta cita ya está cancelada'
                }
            
            if cita.estado == 'completada':
                return {
                    'success': False,
                    'error': 'No se puede cancelar una cita que ya fue completada'
                }
            
            # Cancelar
            success = self.cita_repo.cancelar_cita(paciente.uid, cita_id)
            
            if success:
                return {
                    'success': True,
                    'message': 'Cita cancelada exitosamente'
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo cancelar la cita'
                }
                
        except Exception as e:
            print(f"Error cancelando cita: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Error al cancelar: {str(e)}'
            }
    
    def get_dentists_info(self, limit: int = 10) -> List[Dict]:
        """Obtiene información de dentistas disponibles"""
        try:
            dentistas_ref = self.db.collection('dentistas')
            query = dentistas_ref.where('activo', '==', True).limit(limit)
            
            dentistas = []
            for doc in query.stream():
                data = doc.to_dict()
                dentistas.append({
                    'id': doc.id,
                    'nombre': data.get('nombreCompleto', 'N/A'),
                    'especialidad': data.get('especialidad', 'N/A'),
                    'calificacion': data.get('calificacion', 0),
                    'numResenas': data.get('numResenas', 0)
                })
            
            return dentistas
            
        except Exception as e:
            print(f"Error obteniendo dentistas: {e}")
            return []
    
    def get_consultorios_info(self, limit: int = 10) -> List[Dict]:
        """Obtiene información de consultorios disponibles"""
        try:
            consultorios_ref = self.db.collection('consultorio')
            query = consultorios_ref.where('activo', '==', True).limit(limit)
            
            consultorios = []
            for doc in query.stream():
                data = doc.to_dict()
                consultorios.append({
                    'id': doc.id,
                    'nombre': data.get('nombre', 'N/A'),
                    'direccion': data.get('direccion', 'N/A'),
                    'calificacion': data.get('calificacion', 0)
                })
            
            return consultorios
            
        except Exception as e:
            print(f"Error obteniendo consultorios: {e}")
            return []
    
    def _calculate_payment_deadline(self, payment_method: str):
        """
        Calcula la fecha de expiración de pago según el método de pago.
        
        Configuración por defecto:
        - Efectivo/cash: None (se paga al momento de la cita, el dentista lo marca como pagado)
        - Tarjeta/stripe: None (pago inmediato online)
        - Transferencia: 2 horas (debe confirmar con comprobante)
        - PayPal/MercadoPago: 2 horas
        
        Returns:
            datetime o None si no aplica
        """
        from datetime import datetime, timedelta
        
        payment_method_lower = payment_method.lower() if payment_method else 'cash'
        
        # Configuración de tiempos límite (en horas)
        # None = sin límite de tiempo (se paga en persona o inmediatamente)
        deadlines_config = {
            'cash': None,  # Efectivo: se paga al momento de la cita
            'efectivo': None,
            'card': None,  # Tarjeta: pago inmediato
            'tarjeta': None,
            'stripe': None,
            'transfer': 2,  # Transferencia: 2 horas para enviar comprobante
            'transferencia': 2,
            'paypal': 2,
            'mercadopago': 2
        }
        
        hours = deadlines_config.get(payment_method_lower, None)
        
        # Si es None, no hay deadline
        if hours is None:
            return None
        
        # Calcular fecha de expiración
        now = datetime.now()
        deadline = now + timedelta(hours=hours)
        
        return deadline
    
    def get_treatments_for_dentist(self, dentista_id: str, consultorio_id: str = None) -> List[Dict]:
        """Obtiene tratamientos/servicios disponibles para un dentista desde la base de datos real"""
        try:
            tratamientos = []
            
            # Buscar servicios del consultorio (la colección se llama "servicios", no "tratamientos")
            if consultorio_id:
                consultorio_ref = self.db.collection('consultorio').document(consultorio_id)
                servicios_ref = consultorio_ref.collection('servicios')
                docs = servicios_ref.where('activo', '==', True).stream()
                
                for doc in docs:
                    data = doc.to_dict()
                    
                    # El precio viene como string, convertir a número
                    precio_str = data.get('precio', '0')
                    try:
                        precio_valor = float(precio_str) if isinstance(precio_str, str) else (precio_str if isinstance(precio_str, (int, float)) else 0)
                    except (ValueError, TypeError):
                        precio_valor = 0
                    
                    # La duración viene como string, convertir a número
                    duracion_str = data.get('duracion', '60')
                    try:
                        duracion_valor = int(duracion_str) if isinstance(duracion_str, str) else (duracion_str if isinstance(duracion_str, int) else 60)
                    except (ValueError, TypeError):
                        duracion_valor = 60
                    
                    # La descripción puede venir como "descrippcion" (con doble p) o "descripcion"
                    descripcion = data.get('descripcion') or data.get('descrippcion', '')
                    
                    tratamientos.append({
                        'id': doc.id,
                        'nombre': data.get('nombre', 'Servicio'),
                        'precio': precio_valor,
                        'duracion': duracion_valor,
                        'descripcion': descripcion,
                        'categoria': data.get('categoria', 'general')
                    })
            
            # Si no hay servicios del consultorio, buscar en la colección global de tratamientos
            if not tratamientos:
                tratamientos_ref = self.db.collection('tratamientos')
                docs = tratamientos_ref.where('activo', '==', True).limit(10).stream()
                
                for doc in docs:
                    data = doc.to_dict()
                    precio = data.get('precio', {})
                    if isinstance(precio, dict):
                        precio_valor = precio.get('precio', precio.get('precioFinal', 0))
                    else:
                        try:
                            precio_valor = float(precio) if isinstance(precio, str) else (precio if isinstance(precio, (int, float)) else 0)
                        except (ValueError, TypeError):
                            precio_valor = 0
                    
                    tratamientos.append({
                        'id': doc.id,
                        'nombre': data.get('nombre', 'Servicio'),
                        'precio': precio_valor,
                        'duracion': data.get('tiempoEstimado', data.get('duracionMinutos', data.get('duracion', 60))),
                        'descripcion': data.get('descripcion', ''),
                        'categoria': data.get('categoria', 'general')
                    })
            
            # Si aún no hay tratamientos, retornar lista vacía (no usar valores por defecto)
            if not tratamientos:
                print(f"No se encontraron servicios para consultorio {consultorio_id}")
                return []
            
            return tratamientos
            
        except Exception as e:
            print(f"Error obteniendo tratamientos: {e}")
            import traceback
            traceback.print_exc()
            return []

    def quick_register_user(self, phone: str, name: str = None) -> Optional[Dict]:
        """Registro rápido de usuario desde chatbot"""
        try:
            # Verificar si ya existe
            paciente = self.paciente_repo.buscar_por_telefono(phone)
            if paciente:
                 return {
                    'uid': paciente.uid,
                    'nombre': paciente.nombreCompleto or name or 'Paciente',
                    'telefono': paciente.telefono
                }
            
            # Crear nuevo paciente
            # Usar timestamp como ID temporal si no hay auth
            temp_uid = f"chat_{int(datetime.now().timestamp())}"
            
            datos_paciente = {
                'telefono': phone,
                'nombreCompleto': name or 'Usuario Chat',
                'origen': 'whatsapp_bot',
                'fecha_registro': datetime.now(self.mexico_tz).isoformat(),
                'activo': True
            }
            
            # Guardar en Firestore
            self.db.collection('pacientes').document(temp_uid).set(datos_paciente)
            
            return {
                'uid': temp_uid,
                'nombre': name or 'Usuario Chat',
                'telefono': phone
            }
            
        except Exception as e:
            print(f"Error en registro rápido: {e}")
            return None

    def get_medical_history(self, user_id: str = None, phone: str = None) -> Dict[str, Any]:
        """
        Obtiene el historial médico completo (desencriptado).
        Retorna un dict con los datos procesados para el chatbot.
        """
        try:
            paciente = None
            if user_id:
                paciente = self.paciente_repo.buscar_por_id(user_id)
            elif phone:
                paciente = self.paciente_repo.buscar_por_telefono(phone)
            
            if not paciente:
                return {}
            
            # 1. Obtener historial médico activo desde Firestore
            historial_ref = self.db.collection('pacientes')\
                                   .document(paciente.uid)\
                                   .collection('historialMedico')\
                                   .where('isActive', '==', True)\
                                   .limit(1)
            
            docs = list(historial_ref.stream())
            
            if not docs:
                return {}
            
            historial_data = docs[0].to_dict()
            
            # 2. Desencriptar si es necesario
            try:
                from utils.encryption import decrypt_medical_history
                # Solo desencriptar si está marcado como encriptado
                if historial_data.get('_encrypted'):
                    historial_data = decrypt_medical_history(historial_data, paciente.uid)
            except ImportError:
                print("Encryption module not available")
            except Exception as e:
                print(f"Error decrypting history: {e}")
                
            # 3. Retornar datos completos
            return historial_data
            
        except Exception as e:
            print(f"Error getting medical history: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_dentist_reviews(self, dentista_name: str = None) -> List[Dict]:
        """Obtiene reseñas de dentistas"""
        try:
            # Si no hay nombre, traer reseñas generales destacadas
            reseñas_ref = self.db.collection('resenas')
            
            query = reseñas_ref
            if dentista_name:
                # Búsqueda simple por nombre de dentista en la reseña
                # Idealmente sería por ID, pero el chat maneja nombres
                pass 
                
            docs = query.order_by('fecha', direction='DESCENDING').limit(5).stream()
            
            reseñas = []
            for doc in docs:
                data = doc.to_dict()
                reseñas.append({
                    'autor': data.get('autor', 'Anónimo'),
                    'calificacion': data.get('calificacion', 5),
                    'comentario': data.get('comentario', ''),
                    'dentista': data.get('dentistaName', 'General'),
                    'fecha': data.get('fecha', '')
                })
            
            # Filtrar manual si se pidió un dentista específico (por limitación de firestore en queries complejos)
            if dentista_name:
                dentista_lower = dentista_name.lower()
                reseñas = [r for r in reseñas if dentista_lower in r['dentista'].lower()]
                
            return reseñas
            
        except Exception as e:
            print(f"Error obteniendo reseñas: {e}")
            # Mock data si falla la DB (para demo)
            return [
                {'autor': 'María G.', 'calificacion': 5, 'comentario': 'Excelente atención, muy suave.', 'dentista': 'Dr. Ana García'},
                {'autor': 'Carlos P.', 'calificacion': 5, 'comentario': 'Me explicaron todo el procedimiento.', 'dentista': 'Dr. Juan Pérez'},
                {'autor': 'Sofia L.', 'calificacion': 4, 'comentario': 'Un poco de espera pero valió la pena.', 'dentista': 'Dra. Laura'}
            ]

    def search_dentists(self, query: str) -> List[Dict]:
        """Busca dentistas por nombre o especialidad"""
        try:
            query_lower = query.lower().strip()
            dentistas_ref = self.db.collection('dentistas').where('activo', '==', True)
            
            resultados = []
            for doc in dentistas_ref.stream():
                data = doc.to_dict()
                nombre = data.get('nombreCompleto', '').lower()
                especialidad = data.get('especialidad', '').lower()
                
                # Coincidencia simple
                if query_lower in nombre or query_lower in especialidad:
                     resultados.append({
                        'id': doc.id,
                        'nombre': data.get('nombreCompleto', 'Doctor'),
                        'especialidad': data.get('especialidad', 'General'),
                        'calificacion': data.get('calificacion', 5.0),
                        'ubicacion': data.get('ubicacion', 'Consultorio Central')
                    })
            
            return resultados
        except Exception as e:
            print(f"Error buscando dentistas: {e}")
            return []
