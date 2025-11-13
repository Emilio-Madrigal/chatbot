"""
🎯 SERVICIO DE ACCIONES DEL CHATBOT
Integra con Firestore para realizar todas las acciones del sistema
"""

from database.models import CitaRepository, PacienteRepository
from database.database import FirebaseConfig
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re

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
                    'email': paciente.email
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
    
    def create_appointment(self, user_id: str = None, phone: str = None,
                          fecha: str = None, hora: str = None,
                          nombre_cliente: str = None, motivo: str = None) -> Dict:
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
            
            # Preparar datos de la cita
            datos_cita = {
                'fecha': fecha,
                'hora': hora,
                'nombre_cliente': nombre_cliente or paciente.nombreCompleto or 'Paciente',
                'descripcion': motivo or 'Consulta general'
            }
            
            # Crear cita
            usuario_whatsapp = phone or paciente.telefono
            cita_id = self.cita_repo.crear_cita(usuario_whatsapp, datos_cita, paciente_id=paciente.uid)
            
            if cita_id:
                return {
                    'success': True,
                    'cita_id': cita_id,
                    'message': 'Cita agendada exitosamente'
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

