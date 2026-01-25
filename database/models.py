from database.database import FirebaseConfig
from datetime import datetime
from typing import List, Optional, Dict
from utils.phone_utils import normalize_phone_for_database

class Paciente:
    def __init__(self, uid=None, nombre=None, apellidos=None, telefono=None, 
                 email=None, nombreCompleto=None, preferences=None):
        self.uid = uid
        self.nombre = nombre
        self.apellidos = apellidos
        self.telefono = telefono
        self.email = email
        self.nombreCompleto = nombreCompleto
        self.preferences = preferences or {}
    
    @classmethod
    def from_dict(cls, uid: str, data: dict):
        return cls(
            uid=uid,
            nombre=data.get('nombre'),
            apellidos=data.get('apellidos'),
            telefono=data.get('telefono'),
            email=data.get('email'),
            nombreCompleto=data.get('nombreCompleto'),
            preferences=data.get('preferences', {})
        )


class Cita:
    def __init__(self, id=None, consultorioId=None, consultorioName=None,
                 dentistaId=None, dentistaName=None, fecha=None, 
                 horaInicio=None, horaFin=None, estado=None, 
                 motivo=None, servicioName=None, montoPago=None,
                 estadoPago=None, nombre_cliente=None, usuario_whatsapp=None):
        self.id = id
        self.consultorioId = consultorioId
        self.consultorioName = consultorioName
        self.dentistaId = dentistaId
        self.dentistaName = dentistaName
        self.fecha = fecha 
        self.horaInicio = horaInicio
        self.horaFin = horaFin
        self.estado = estado
        self.motivo = motivo
        self.servicioName = servicioName
        self.montoPago = montoPago
        self.estadoPago = estadoPago
        # Campos adicionales para compatibilidad
        self.nombre_cliente = nombre_cliente
        self.usuario_whatsapp = usuario_whatsapp
        # Para compatibilidad con código existente
        self.hora = horaInicio
        self.descripcion = motivo
    
    @classmethod
    def from_dict(cls, doc_id: str, data: dict):
        # Convertir fecha timestamp a string para compatibilidad
        fecha = data.get('fecha')
        if fecha and hasattr(fecha, 'strftime'):
            fecha_str = fecha.strftime('%Y-%m-%d')
        elif fecha:
            fecha_str = fecha
        else:
            fecha_str = None
        
        return cls(
            id=doc_id,
            consultorioId=data.get('consultorioID') or data.get('consultorioId'),
            consultorioName=data.get('consultorioName'),
            dentistaId=data.get('dentistaId'),
            dentistaName=data.get('dentistaName'),
            fecha=fecha_str,
            horaInicio=data.get('horaInicio'),
            horaFin=data.get('horaFin'),
            estado=data.get('estado'),
            motivo=data.get('motivo'),
            servicioName=data.get('servicioName'),
            montoPago=data.get('montoPago'),
            estadoPago=data.get('estadoPago'),
            nombre_cliente=data.get('pacienteName'),
            usuario_whatsapp=data.get('usuario_whatsapp')
        )
    
    def fecha_formateada(self) -> str:
        if self.fecha:
            fecha_dt = self.fecha.strftime('%d/%m/%Y')
            return fecha_dt
        return "Fecha no disponible"


class PacienteRepository:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.collection = self.db.collection('pacientes')
    
    def buscar_por_telefono(self, telefono: str) -> Optional[Paciente]:
        try:
            # Normalizar el número de teléfono para que coincida con el formato en Firestore
            # (quitar prefijo "whatsapp:" y el "1" extra si existe)
            telefono_normalizado = normalize_phone_for_database(telefono)
            print(f"Buscando paciente con teléfono normalizado: {telefono_normalizado} (original: {telefono})")
            
            query = self.collection.where('telefono', '==', telefono_normalizado).limit(1)
            docs = query.stream()

            for doc in docs:
                paciente = Paciente.from_dict(doc.id, doc.to_dict())
                print(f"Paciente encontrado: {paciente.nombreCompleto}")
                return paciente
            
            print(f"No existe paciente con teléfono: {telefono_normalizado}")
            return None
            
        except Exception as e:
            print(f"Error buscando paciente: {e}")
            return None
    
    def obtener_por_uid(self, uid: str) -> Optional[Paciente]:
        try:
            doc = self.collection.document(uid).get()
            
            if doc.exists:
                return Paciente.from_dict(doc.id, doc.to_dict())
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo paciente {uid}: {e}")
            return None
    
    def buscar_por_id(self, paciente_id: str) -> Optional[Paciente]:
        """Alias para obtener_por_uid para compatibilidad con código existente"""
        return self.obtener_por_uid(paciente_id)


class CitaRepository:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.paciente_repo = PacienteRepository()
    
    def obtener_paciente_por_telefono(self, telefono: str):
        """Obtiene el paciente por su número de teléfono"""
        return self.paciente_repo.buscar_por_telefono(telefono)
    
    def obtener_paciente_por_id(self, paciente_id: str):
        """Obtiene el paciente por su ID (uid)"""
        return self.paciente_repo.buscar_por_id(paciente_id)
    
    def obtener_paciente(self, telefono: str = None, paciente_id: str = None):
        """Obtiene el paciente por teléfono o ID, priorizando ID si está disponible"""
        if paciente_id:
            paciente = self.obtener_paciente_por_id(paciente_id)
            if paciente:
                return paciente
        if telefono:
            return self.obtener_paciente_por_telefono(telefono)
        return None
    
    def obtener_ultimo_consultorio_paciente(self, paciente_uid: str) -> Optional[Dict]:
        """Obtiene el último consultorio usado por el paciente basado en su última cita"""
        try:
            # Primero intentar en subcolección de pacientes (no requiere índice compuesto)
            print(f"Buscando último consultorio para paciente: {paciente_uid}")
            print("Buscando en subcolección de pacientes primero...")
            citas_ref = self.db.collection('pacientes')\
                              .document(paciente_uid)\
                              .collection('citas')
            query = citas_ref.order_by('createdAt', direction='DESCENDING')\
                            .limit(1)
            
            for doc in query.stream():
                cita_data = doc.to_dict()
                consultorio_id = cita_data.get('consultorioID') or cita_data.get('consultorioId')
                dentista_id = cita_data.get('dentistaId')
                if consultorio_id and dentista_id:
                    print(f"Encontrado último consultorio en subcolección: {consultorio_id}")
                    
                    # Obtener nombre del consultorio desde la colección
                    consultorio_doc = self.db.collection('consultorio').document(consultorio_id).get()
                    consultorio_name = 'Consultorio'
                    if consultorio_doc.exists:
                        consultorio_data = consultorio_doc.to_dict()
                        consultorio_name = consultorio_data.get('nombre', cita_data.get('consultorioName', 'Consultorio'))
                    
                    # Obtener nombre del dentista desde la subcolección del consultorio
                    dentista_name = cita_data.get('dentistaName', 'Dentista')
                    try:
                        dentistas_ref = self.db.collection('consultorio')\
                                              .document(consultorio_id)\
                                              .collection('dentistas')\
                                              .where('dentistaId', '==', dentista_id)\
                                              .where('activo', '==', True)\
                                              .limit(1)
                        for dentista_doc in dentistas_ref.stream():
                            dentista_data = dentista_doc.to_dict()
                            dentista_name = dentista_data.get('nombreCompleto', dentista_name)
                            print(f"Nombre del dentista obtenido de subcolección: {dentista_name}")
                            break
                    except Exception as e:
                        print(f"Error obteniendo nombre del dentista: {e}")
                    
                    return {
                        'consultorioId': consultorio_id,
                        'consultorioName': consultorio_name,
                        'dentistaId': dentista_id,
                        'dentistaName': dentista_name
                    }
            
            # Si no hay citas previas, buscar cualquier consultorio activo
            print("No se encontraron citas previas, usando consultorio por defecto")
            return self._obtener_consultorio_por_defecto()
            
        except Exception as e:
            print(f"Error obteniendo último consultorio: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: buscar cualquier consultorio activo
            return self._obtener_consultorio_por_defecto()
    
    def _obtener_consultorio_por_defecto(self) -> Optional[Dict]:
        """Obtiene un consultorio activo por defecto si no hay historial"""
        try:
            print("Buscando consultorio por defecto...")
            consultorios_ref = self.db.collection('consultorio')
            query = consultorios_ref.where('activo', '==', True).limit(1)
            
            for doc in query.stream():
                consultorio_data = doc.to_dict()
                consultorio_id = doc.id
                consultorio_nombre = consultorio_data.get('nombre', 'Consultorio')
                print(f"Consultorio encontrado: {consultorio_id}, nombre: {consultorio_nombre}")
                
                # Buscar el dentista en la subcolección de dentistas
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
                    print(f"Dentista encontrado en subcolección: {dentista_id}, nombre: {dentista_name}")
                    break
                
                if dentista_id:
                    return {
                        'consultorioId': consultorio_id,
                        'consultorioName': consultorio_nombre,
                        'dentistaId': dentista_id,
                        'dentistaName': dentista_name or 'Dentista'
                    }
                else:
                    print(f"No se encontró dentista activo para el consultorio {consultorio_id}")
            
            print("No se encontró ningún consultorio activo")
            return None
        except Exception as e:
            print(f"Error obteniendo consultorio por defecto: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def obtener_citas_usuario(self, usuario_whatsapp: str) -> List[Cita]:
        """Obtiene las citas de un usuario por su número de WhatsApp"""
        try:
            # Buscar paciente por teléfono
            paciente = self.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            if not paciente:
                print(f"No se encontró paciente con teléfono: {usuario_whatsapp}")
                return []
            
            return self.obtener_citas_paciente(paciente.uid)
        except Exception as e:
            print(f"Error obteniendo citas usuario: {e}")
            return []
    
    def obtener_citas_paciente(self, paciente_uid: str) -> List[Cita]:
        try:
            citas_ref = self.db.collection('pacientes')\
                              .document(paciente_uid)\
                              .collection('citas')
            query = citas_ref.where('estado', '!=', 'cancelada')\
                            .order_by('estado')\
                            .order_by('fecha')
            citas = []
            for doc in query.stream():
                cita = Cita.from_dict(doc.id, doc.to_dict())
                citas.append(cita)
            
            print(f"Encontradas {len(citas)} citas para paciente {paciente_uid}")
            return citas
            
        except Exception as e:
            print(f"Error obteniendo citas: {e}")
            return []
    
    def obtener_citas_proximas(self, fecha_limite: str) -> List[Cita]:
        """
        Obtiene citas próximas hasta una fecha límite
        J.RF6: Recordatorios automáticos
        """
        try:
            from datetime import datetime
            citas = []
            
            # Buscar en colección global de citas
            citas_ref = self.db.collection('citas')\
                              .where('estado', 'in', ['confirmado', 'programada', 'confirmada'])\
                              .where('fecha', '<=', fecha_limite)\
                              .where('fecha', '>=', datetime.now().strftime('%Y-%m-%d'))
            
            for doc in citas_ref.stream():
                cita_data = doc.to_dict()
                # Convertir a objeto Cita
                cita = Cita.from_dict(doc.id, cita_data)
                citas.append(cita)
            
            print(f"Encontradas {len(citas)} citas próximas hasta {fecha_limite}")
            return citas
            
        except Exception as e:
            print(f"Error obteniendo citas próximas: {e}")
            return []
    
    def obtener_por_id(self, cita_id: str) -> Optional[Cita]:
        """
        Obtiene una cita por su ID desde la colección global
        """
        try:
            doc = self.db.collection('citas').document(cita_id).get()
            if doc.exists:
                return Cita.from_dict(doc.id, doc.to_dict())
            return None
        except Exception as e:
            print(f"Error obteniendo cita por ID {cita_id}: {e}")
            return None
    
    def obtener_cita_por_id(self, paciente_uid: str, cita_id: str) -> Optional[Cita]:
        try:
            doc = self.db.collection('pacientes')\
                        .document(paciente_uid)\
                        .collection('citas')\
                        .document(cita_id)\
                        .get()
            
            if doc.exists:
                return Cita.from_dict(doc.id, doc.to_dict())
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo cita {cita_id}: {e}")
            return None
    
    def obtener_cita(self, usuario_whatsapp: str, cita_id: str) -> Optional[Cita]:
        """Obtiene una cita específica por ID y usuario WhatsApp"""
        try:
            paciente = self.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            if not paciente:
                return None
            
            return self.obtener_cita_por_id(paciente.uid, cita_id)
        except Exception as e:
            print(f"Error obteniendo cita: {e}")
            return None
    
    def crear_cita(self, usuario_whatsapp: str, datos_cita: dict, paciente_id: str = None, consultorio_especifico: dict = None) -> Optional[str]:
        """Crea una nueva cita para el usuario. Puede usar paciente_id o buscar por teléfono"""
        try:
            from google.cloud.firestore import SERVER_TIMESTAMP
            from datetime import datetime
            
            # Buscar paciente por ID o teléfono
            if paciente_id:
                paciente = self.paciente_repo.buscar_por_id(paciente_id)
            else:
                paciente = self.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            
            if not paciente:
                print(f"No se encontró paciente con teléfono: {usuario_whatsapp} o ID: {paciente_id}")
                return None
            
            # Usar consultorio específico si se proporciona, sino obtener último consultorio usado
            if consultorio_especifico:
                ultimo_consultorio = consultorio_especifico
                print(f"Usando consultorio específico: {ultimo_consultorio.get('consultorioName')} - {ultimo_consultorio.get('dentistaName')}")
            else:
                ultimo_consultorio = self.obtener_ultimo_consultorio_paciente(paciente.uid)
                if not ultimo_consultorio:
                    print(f"No se encontró consultorio previo para el paciente")
                    return None
            
            # Convertir fecha string a timestamp
            fecha_str = datos_cita.get('fecha')
            hora_inicio = datos_cita.get('hora')
            
            # Calcular hora fin (asumiendo 30 minutos por defecto)
            from datetime import timedelta
            # Parsear hora y extraer solo el time object
            hora_dt = datetime.strptime(hora_inicio, '%H:%M')
            hora_obj = hora_dt.time()  # Extraer solo la hora (time object)
            hora_fin_dt = hora_dt + timedelta(minutes=30)
            hora_fin = hora_fin_dt.strftime('%H:%M')
            
            # Convertir fecha a timestamp
            fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
            fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
            
            # Crear documento de cita en subcolección del paciente
            # Preparar fechaHora completa
            fecha_hora_completa = datetime.combine(fecha_dt.date(), hora_obj)
            
            # Obtener datos adicionales del consultorio para compatibilidad con web
            consultorio_doc = self.db.collection('consultorio').document(ultimo_consultorio['consultorioId']).get()
            consultorio_address = {}
            consultorio_data_full = {}
            if consultorio_doc.exists:
                consultorio_data_full = consultorio_doc.to_dict()
                consultorio_address = consultorio_data_full.get('direccion', {})
            
            # Obtener datos del dentista para especialidad
            dentista_specialty = ''
            try:
                dentista_doc = self.db.collection('dentistas').document(ultimo_consultorio['dentistaId']).get()
                if dentista_doc.exists:
                    dentista_data = dentista_doc.to_dict()
                    dentista_specialty = dentista_data.get('especialidad', '')
            except:
                pass
            
            # Generar ID de confirmación único
            import uuid
            confirmation_id = str(uuid.uuid4())
            fecha_confirmacion_str = datetime.now().isoformat()
            
            # Calcular fecha de expiración de pago según método de pago
            payment_method = datos_cita.get('metodo_pago', 'cash')
            payment_deadline = self._calculate_payment_deadline(payment_method)
            
            # Preparar datos completos de la cita (iguales que la web)
            cita_data = {
                # Información del paciente
                'pacienteId': paciente.uid,
                'pacienteName': datos_cita.get('nombre_cliente', paciente.nombreCompleto),
                'patientName': datos_cita.get('nombre_cliente', paciente.nombreCompleto),
                'patientPhone': paciente.telefono or usuario_whatsapp,
                'patientEmail': paciente.email or '',
                'patientAge': '',  # No tenemos edad en el chatbot por ahora
                
                # Información del dentista
                'dentistaId': ultimo_consultorio['dentistaId'],
                'dentistaName': ultimo_consultorio['dentistaName'],
                'dentistaSpecialty': dentista_specialty,
                
                # Información del consultorio
                'consultorioID': ultimo_consultorio['consultorioId'],  # Formato legacy
                'consultorioId': ultimo_consultorio['consultorioId'],
                'consultorioName': ultimo_consultorio['consultorioName'],
                'consultorioAddress': consultorio_address,
                
                # Fecha y hora
                'fecha': fecha_timestamp,
                'fechaHora': fecha_hora_completa,
                'appointmentDate': fecha_hora_completa.strftime('%Y-%m-%d'),  # Solo fecha en formato string
                'appointmentTime': hora_inicio,
                'horaInicio': hora_inicio,
                'horaFin': hora_fin,
                
                # Duración
                'Duracion': 30,
                'duracion': 30,
                
                # Motivo (todos los formatos)
                'Motivo': datos_cita.get('descripcion', 'Consulta general'),
                'motivo': datos_cita.get('descripcion', 'Consulta general'),
                'appointmentReason': datos_cita.get('descripcion', 'Consulta general'),
                
                # Tratamiento (vacío por ahora, chatbot no selecciona tratamientos específicos)
                'tratamientoId': '',
                'tratamientoNombre': '',
                'tratamientoPrecio': 0,
                
                # Estado
                'estado': 'programada',  # Igual que la web después de verificar OTP
                'status': 'programada',
                
                # Método de pago
                'paymentMethod': payment_method,
                'paymentStatus': 'pending',
                'paymentDeadline': payment_deadline,  # Fecha de expiración de pago
                
                # Validaciones (simulamos las mismas que la web)
                'validacionesCompletadas': {
                    'otpVerified': True,  # Chatbot no usa OTP pero lo marcamos como verificado
                    'conflictsChecked': True,
                    'limitChecked': True,
                    'blockedDaysChecked': True,
                    'validatedAt': fecha_confirmacion_str
                },
                'otpVerified': True,
                'otpVerifiedAt': fecha_confirmacion_str,
                'confirmationId': confirmation_id,
                'fechaConfirmacion': fecha_confirmacion_str,
                
                # Historial médico compartido (null por ahora)
                'sharedMedicalHistory': None,
                
                # Timestamps
                'createdAt': SERVER_TIMESTAMP,
                'updatedAt': SERVER_TIMESTAMP
            }
            
            # Agregar a subcolección del paciente
            doc_ref = self.db.collection('pacientes')\
                            .document(paciente.uid)\
                            .collection('citas')\
                            .document()
            
            doc_ref.set(cita_data)
            cita_id = doc_ref.id
            
            # También crear en colección global de citas (citas minúscula, estándar)
            # Preparar datos completos como la web
            fecha_hora_completa = datetime.combine(fecha_dt.date(), hora_obj)
            
            cita_global_data = {
                'id': cita_id,
                'pacienteId': paciente.uid,
                'pacienteCitaId': cita_id,
                'patientName': datos_cita.get('nombre_cliente', paciente.nombreCompleto or 'Paciente'),
                'patientPhone': paciente.telefono or usuario_whatsapp,
                'patientEmail': paciente.email or '',
                'patientAge': '',  # Se puede agregar si está disponible
                'dentistaId': ultimo_consultorio['dentistaId'],
                'dentistaName': ultimo_consultorio['dentistaName'],
                'dentistaSpecialty': '',  # Se puede obtener del dentista
                'consultorioId': ultimo_consultorio['consultorioId'],
                'consultorioName': ultimo_consultorio['consultorioName'],
                'consultorioAddress': {},  # Se puede obtener del consultorio
                'fechaHora': fecha_hora_completa,  # Timestamp completo
                'appointmentDate': fecha_hora_completa.isoformat(),
                'appointmentTime': hora_inicio,
                'Duracion': 30,  # Por defecto 30 minutos
                'duracion': 30,
                'Motivo': datos_cita.get('descripcion', 'Consulta general'),
                'motivo': datos_cita.get('descripcion', 'Consulta general'),
                'appointmentReason': datos_cita.get('descripcion', 'Consulta general'),
                'tratamientoId': '',
                'tratamientoNombre': '',
                'tratamientoPrecio': 0,
                'estado': 'confirmado',
                'status': 'confirmado',
                'paymentMethod': payment_method,
                'paymentStatus': 'pending',
                'paymentDeadline': payment_deadline,  # Fecha de expiración de pago
                'validacionesCompletadas': {
                    'otpVerified': False,  # En chatbot no se requiere OTP
                    'conflictsChecked': True,
                    'limitChecked': True,
                    'blockedDaysChecked': True,
                    'validatedAt': datetime.now().isoformat()
                },
                'otpVerified': False,
                'otpVerifiedAt': None,
                'confirmationId': f"confirm_{ultimo_consultorio['dentistaId']}_{fecha_hora_completa.isoformat()}_{int(datetime.now().timestamp() * 1000)}",
                'fechaConfirmacion': datetime.now().isoformat(),
                'sharedMedicalHistory': None,
                'createdAt': SERVER_TIMESTAMP,
                'updatedAt': SERVER_TIMESTAMP
            }
            self.db.collection('citas').document(cita_id).set(cita_global_data)
            
            print(f"Cita creada: {cita_id}")
            return cita_id
            
        except Exception as e:
            print(f"Error creando cita: {e}")
            return None
    
    def actualizar_cita_por_id(self, paciente_id: str, cita_id: str, nueva_fecha: str, nueva_hora: str) -> bool:
        """Actualiza una cita por paciente_id y cita_id"""
        try:
            from datetime import datetime, timedelta
            
            # Convertir fecha string a timestamp
            fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d')
            fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
            
            # Calcular hora fin
            hora_dt = datetime.strptime(nueva_hora, '%H:%M')
            hora_obj = hora_dt.time()  # Extraer solo la hora (time object)
            hora_fin_dt = hora_dt + timedelta(minutes=30)
            hora_fin = hora_fin_dt.strftime('%H:%M')
            
            # Actualizar en subcolección del paciente
            cita_ref = self.db.collection('pacientes')\
                              .document(paciente_id)\
                              .collection('citas')\
                              .document(cita_id)
            
            cita_ref.update({
                'fecha': fecha_timestamp,
                'horaInicio': nueva_hora,
                'horaFin': hora_fin,
                'updatedAt': datetime.now()
            })
            
            # También actualizar en colección global (citas minúscula, estándar)
            nueva_fecha_hora_completa = datetime.combine(fecha_dt.date(), hora_obj)
            self.db.collection('citas').document(cita_id).update({
                'fecha': fecha_timestamp,
                'fechaHora': nueva_fecha_hora_completa,
                'appointmentDate': nueva_fecha_hora_completa.isoformat(),
                'appointmentTime': nueva_hora,
                'horaInicio': nueva_hora,
                'horaFin': hora_fin,
                'estado': 'confirmado',
                'status': 'confirmado',
                'updatedAt': datetime.now()
            })
            
            print(f"Cita {cita_id} actualizada")
            return True
        except Exception as e:
            print(f"Error actualizando cita: {e}")
            return False
    
    def actualizar_cita(self, usuario_whatsapp: str, cita_id: str, nueva_fecha: str, nueva_hora: str) -> bool:
        """Actualiza una cita existente"""
        try:
            from google.cloud.firestore import SERVER_TIMESTAMP
            from datetime import datetime
            
            paciente = self.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            if not paciente:
                return False
            
            # Convertir fecha y hora
            fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d')
            fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
            
            from datetime import timedelta
            hora_dt = datetime.strptime(nueva_hora, '%H:%M')
            hora_obj = hora_dt.time()  # Extraer solo la hora (time object)
            hora_fin_dt = hora_dt + timedelta(minutes=30)
            hora_fin = hora_fin_dt.strftime('%H:%M')
            
            # Actualizar en subcolección
            self.db.collection('pacientes')\
                  .document(paciente.uid)\
                  .collection('citas')\
                  .document(cita_id)\
                  .update({
                      'fecha': fecha_timestamp,
                      'horaInicio': nueva_hora,
                      'horaFin': hora_fin,
                      'estado': 'confirmado',
                      'updatedAt': SERVER_TIMESTAMP
                  })
            
            # Actualizar en colección global (citas minúscula, estándar)
            nueva_fecha_hora_completa = datetime.combine(fecha_dt.date(), hora_obj)
            self.db.collection('citas')\
                  .document(cita_id)\
                  .update({
                      'fecha': fecha_timestamp,
                      'fechaHora': nueva_fecha_hora_completa,
                      'appointmentDate': nueva_fecha_hora_completa.isoformat(),
                      'appointmentTime': nueva_hora,
                      'horaInicio': nueva_hora,
                      'horaFin': hora_fin,
                      'estado': 'confirmado',
                      'status': 'confirmado',
                      'updatedAt': SERVER_TIMESTAMP
                  })
            
            print(f"Cita {cita_id} actualizada")
            return True
            
        except Exception as e:
            print(f"Error actualizando cita: {e}")
            return False
    
    def eliminar_cita_por_id(self, paciente_id: str, cita_id: str) -> bool:
        """Elimina una cita por paciente_id y cita_id"""
        try:
            # Eliminar de subcolección del paciente
            cita_ref = self.db.collection('pacientes')\
                              .document(paciente_id)\
                              .collection('citas')\
                              .document(cita_id)
            cita_ref.delete()
            
            # También eliminar de colección global (citas minúscula, estándar)
            self.db.collection('citas').document(cita_id).delete()
            
            print(f"Cita {cita_id} eliminada")
            return True
        except Exception as e:
            print(f"Error eliminando cita: {e}")
            return False
    
    def eliminar_cita(self, usuario_whatsapp: str, cita_id: str) -> bool:
        """Elimina (cancela) una cita"""
        try:
            paciente = self.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            if not paciente:
                return False
            
            return self.cancelar_cita(paciente.uid, cita_id)
            
        except Exception as e:
            print(f"Error eliminando cita: {e}")
            return False
    
    def cancelar_cita(self, paciente_uid: str, cita_id: str) -> bool:
        try:
            from google.cloud.firestore import SERVER_TIMESTAMP
            
            self.db.collection('pacientes')\
                  .document(paciente_uid)\
                  .collection('citas')\
                  .document(cita_id)\
                  .update({
                      'estado': 'cancelada',
                      'updatedAt': SERVER_TIMESTAMP
                  })
            
            print(f"Cita {cita_id} cancelada en subcolección")
            # Actualizar en colección global (citas minúscula, estándar)
            # Buscar por pacienteId y cita_id
            cita_global_ref = self.db.collection('citas').document(cita_id)
            cita_global_doc = cita_global_ref.get()
            
            if cita_global_doc.exists:
                cita_global_ref.update({
                    'estado': 'cancelada',
                    'status': 'cancelada',
                    'updatedAt': SERVER_TIMESTAMP
                })
                print(f"Cita actualizada en colección global citas")
            else:
                # Fallback: buscar por pacienteId
                global_query = self.db.collection('citas')\
                                     .where('pacienteId', '==', paciente_uid)\
                                     .where('id', '==', cita_id)\
                                     .limit(1)
                
                for doc in global_query.stream():
                    self.db.collection('citas').document(doc.id).update({
                        'estado': 'cancelada',
                        'status': 'cancelada',
                        'updatedAt': SERVER_TIMESTAMP
                    })
                    print(f"Cita actualizada en colección global citas (fallback)")
            
            return True
            
        except Exception as e:
            print(f"Error cancelando cita: {e}")
            return False
    
    def obtener_horarios_disponibles(self, dentista_id: str, consultorio_id: str, fecha_timestamp) -> List[Dict]:
        try:
            from datetime import datetime, timedelta

            fecha_dt = datetime.fromtimestamp(fecha_timestamp.timestamp())
            # Usar minúsculas para coincidir con la estructura de la BD
            dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
            dia_nombre = dias_semana[fecha_dt.weekday()]
            
            print(f"Buscando horarios para {dia_nombre} (consultorio: {consultorio_id}, dentista: {dentista_id})")
            
            # Intentar buscar por ID del documento primero (más directo)
            horarios_doc_ref = self.db.collection('consultorio')\
                                     .document(consultorio_id)\
                                     .collection('horarios')\
                                     .document(dia_nombre)
            horarios_doc_snap = horarios_doc_ref.get()
            horarios_doc = None
            
            if horarios_doc_snap.exists:
                horarios_doc = horarios_doc_snap.to_dict()
                print(f"Horarios encontrados por ID del documento para {dia_nombre}")
            else:
                # Si no se encuentra por ID, intentar buscar por campo 'dia'
                print(f"No se encontró por ID, intentando por campo 'dia'...")
                horarios_ref = self.db.collection('consultorio')\
                                     .document(consultorio_id)\
                                     .collection('horarios')\
                                     .where('dia', '==', dia_nombre)\
                                     .where('activo', '==', True)\
                                     .limit(1)
                
                for doc in horarios_ref.stream():
                    horarios_doc = doc.to_dict()
                    print(f"Horarios encontrados por campo 'dia' para {dia_nombre}")
                    break
            
            if not horarios_doc:
                print(f"No se encontró documento de horarios para {dia_nombre}")
                # Intentar listar todos los documentos de horarios para debug
                try:
                    all_horarios = self.db.collection('consultorio')\
                                         .document(consultorio_id)\
                                         .collection('horarios')\
                                         .stream()
                    dias_disponibles = [doc.id for doc in all_horarios]
                    print(f"Días disponibles en horarios: {dias_disponibles}")
                except Exception as e:
                    print(f"Error listando horarios: {e}")
                return []
            
            if 'horarios' not in horarios_doc:
                print(f"Documento de horarios no tiene campo 'horarios': {list(horarios_doc.keys())}")
                return []
            
            # horarios es un array, tomar el primer elemento
            horarios_array = horarios_doc['horarios']
            if not horarios_array or len(horarios_array) == 0:
                print(f"Array de horarios vacío para {dia_nombre}")
                return []
            
            # Tomar el primer bloque de horarios (puede haber múltiples bloques)
            primer_horario = horarios_array[0]
            hora_inicio_consultorio = primer_horario.get('inicio', '09:00')  # "09:00"
            hora_fin_consultorio = primer_horario.get('fin', '18:00')  # "18:00"
            
            print(f"Horario consultorio: {hora_inicio_consultorio} - {hora_fin_consultorio}")
            
            # Convertir fecha_timestamp a formato compatible con Firestore
            # Las citas usan fechaHora como timestamp, pero también pueden usar fecha como string
            fecha_str = fecha_dt.strftime('%Y-%m-%d')
            
            # Buscar citas existentes - intentar múltiples formatos
            citas_existentes = []
            
            # Buscar citas existentes en TODAS las ubicaciones (como lo hace la web)
            # 1. Buscar en colección principal citas
            try:
                citas_por_timestamp = self.db.collection('citas')\
                                             .where('dentistaId', '==', dentista_id)\
                                             .where('estado', 'in', ['programada', 'confirmado', 'en proceso', 'pendiente'])\
                                             .stream()
                for doc in citas_por_timestamp:
                    cita_data = doc.to_dict()
                    # Verificar si la fecha coincide
                    fecha_hora = cita_data.get('fechaHora')
                    if fecha_hora:
                        # Convertir timestamp a datetime
                        if hasattr(fecha_hora, 'to_datetime'):
                            cita_datetime = fecha_hora.to_datetime()
                        elif hasattr(fecha_hora, 'date'):
                            # Es un Timestamp de Firestore
                            from google.cloud.firestore import Timestamp
                            if isinstance(fecha_hora, Timestamp):
                                cita_datetime = fecha_hora.to_datetime()
                            else:
                                continue
                        elif isinstance(fecha_hora, dict) and '_seconds' in fecha_hora:
                            cita_datetime = datetime.fromtimestamp(fecha_hora['_seconds'])
                        else:
                            continue
                        
                        if cita_datetime.date() == fecha_dt.date():
                            citas_existentes.append(cita_data)
            except Exception as e:
                print(f"Error buscando citas por timestamp en colección principal: {e}")
            
            # 2. Buscar también en subcolecciones de pacientes (estructura usada por la web)
            # Usar filtro por rango de fecha para ser más eficiente
            try:
                from google.cloud.firestore import Timestamp
                inicio_dia = datetime.combine(fecha_dt.date(), datetime.min.time())
                fin_dia = datetime.combine(fecha_dt.date(), datetime.max.time())
                inicio_timestamp = Timestamp.from_datetime(inicio_dia)
                fin_timestamp = Timestamp.from_datetime(fin_dia)
                
                pacientes_ref = self.db.collection('pacientes')
                pacientes_docs = pacientes_ref.stream()
                
                for paciente_doc in pacientes_docs:
                    paciente_id = paciente_doc.id
                    try:
                        citas_sub_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
                        # Filtrar por dentista, estado y rango de fecha
                        citas_sub_query = citas_sub_ref.where('dentistaId', '==', dentista_id)\
                                                       .where('fechaHora', '>=', inicio_timestamp)\
                                                       .where('fechaHora', '<=', fin_timestamp)\
                                                       .where('estado', 'in', ['programada', 'confirmado', 'en proceso', 'pendiente'])\
                                                       .stream()
                        
                        for cita_doc in citas_sub_query:
                            cita_data = cita_doc.to_dict()
                            fecha_hora = cita_data.get('fechaHora')
                            if fecha_hora:
                                # Convertir timestamp a datetime
                                if hasattr(fecha_hora, 'to_datetime'):
                                    cita_datetime = fecha_hora.to_datetime()
                                elif isinstance(fecha_hora, Timestamp):
                                    cita_datetime = fecha_hora.to_datetime()
                                elif isinstance(fecha_hora, dict) and '_seconds' in fecha_hora:
                                    cita_datetime = datetime.fromtimestamp(fecha_hora['_seconds'])
                                else:
                                    continue
                                
                                # Verificar que la fecha coincida (doble verificación)
                                if cita_datetime.date() == fecha_dt.date():
                                    # Evitar duplicados
                                    cita_id = cita_doc.id
                                    if not any(c.get('_id') == cita_id for c in citas_existentes):
                                        cita_data['_id'] = cita_id
                                        citas_existentes.append(cita_data)
                    except Exception as paciente_error:
                        # Continuar con el siguiente paciente si hay error
                        continue
            except Exception as e:
                print(f"Error buscando citas en subcolecciones: {e}")
                import traceback
                traceback.print_exc()
            
            # Extraer horas ocupadas de las citas encontradas
            horas_ocupadas = []
            for cita_data in citas_existentes:
                fecha_hora = cita_data.get('fechaHora')
                duracion = cita_data.get('duracion') or cita_data.get('Duracion') or 30  # Default 30 min
                
                if fecha_hora:
                    # Convertir timestamp a datetime para extraer hora
                    if hasattr(fecha_hora, 'to_datetime'):
                        cita_datetime = fecha_hora.to_datetime()
                    elif hasattr(fecha_hora, 'date'):
                        from google.cloud.firestore import Timestamp
                        if isinstance(fecha_hora, Timestamp):
                            cita_datetime = fecha_hora.to_datetime()
                        else:
                            continue
                    elif isinstance(fecha_hora, dict) and '_seconds' in fecha_hora:
                        cita_datetime = datetime.fromtimestamp(fecha_hora['_seconds'])
                    else:
                        # Intentar extraer de otros campos
                        hora_inicio = cita_data.get('horaInicio') or cita_data.get('appointmentTime') or cita_data.get('hora')
                        if hora_inicio and isinstance(hora_inicio, str) and ':' in hora_inicio:
                            try:
                                hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M')
                                hora_fin_dt = hora_inicio_dt + timedelta(minutes=duracion)
                                horas_ocupadas.append({
                                    'inicio': hora_inicio_dt.strftime('%H:%M'),
                                    'fin': hora_fin_dt.strftime('%H:%M')
                                })
                            except:
                                pass
                        continue
                    
                    # Extraer hora del timestamp
                    hora_inicio_str = cita_datetime.strftime('%H:%M')
                    hora_fin_dt = cita_datetime + timedelta(minutes=duracion)
                    hora_fin_str = hora_fin_dt.strftime('%H:%M')
                    
                    horas_ocupadas.append({
                        'inicio': hora_inicio_str,
                        'fin': hora_fin_str
                    })
            
            print(f"Horas ocupadas: {len(horas_ocupadas)}")
            slots_disponibles = []
            hora_actual = datetime.strptime(hora_inicio_consultorio, '%H:%M')
            hora_limite = datetime.strptime(hora_fin_consultorio, '%H:%M')
            
            while hora_actual < hora_limite:
                hora_fin_slot = hora_actual + timedelta(minutes=30)
                
                hora_inicio_str = hora_actual.strftime('%H:%M')
                hora_fin_str = hora_fin_slot.strftime('%H:%M')
                esta_ocupado = False
                for ocupada in horas_ocupadas:
                    if (hora_inicio_str < ocupada['fin'] and 
                        hora_fin_str > ocupada['inicio']):
                        esta_ocupado = True
                        break
                
                if not esta_ocupado:
                    slots_disponibles.append({
                        'horaInicio': hora_inicio_str,
                        'horaFin': hora_fin_str
                    })
                
                hora_actual = hora_fin_slot
            
            print(f"Slots disponibles: {len(slots_disponibles)}")
            return slots_disponibles
            
        except Exception as e:
            print(f"Error obteniendo horarios disponibles: {e}")
            return []
    
    def obtener_fechas_disponibles(self, dentista_id: str, consultorio_id: str,fecha_original_timestamp, cantidad: int = 3) -> List:
        try:
            from datetime import datetime, timedelta
            
            fecha_inicio = datetime.fromtimestamp(fecha_original_timestamp.timestamp())
            fechas_disponibles = []
            dias_revisados = 0
            max_dias = 30
            
            while len(fechas_disponibles) < cantidad and dias_revisados < max_dias:
                fecha_actual = fecha_inicio + timedelta(days=dias_revisados)
                dias_revisados += 1

                if fecha_actual.weekday() == 6:
                    continue

                # Usar minúsculas para coincidir con la estructura de la BD
                dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
                dia_nombre = dias_semana[fecha_actual.weekday()]

                # Intentar buscar por campo 'dia' primero
                horarios_ref = self.db.collection('consultorio')\
                                     .document(consultorio_id)\
                                     .collection('horarios')\
                                     .where('dia', '==', dia_nombre)\
                                     .where('activo', '==', True)\
                                     .limit(1)
                
                tiene_horario = False
                horarios_doc = None
                for doc in horarios_ref.stream():
                    horarios_doc = doc.to_dict()
                    if horarios_doc and 'horarios' in horarios_doc:
                        horarios_array = horarios_doc['horarios']
                        if horarios_array and len(horarios_array) > 0:
                            tiene_horario = True
                    break
                
                # Si no se encuentra por campo 'dia', intentar buscar por ID del documento
                if not tiene_horario:
                    horarios_doc_ref = self.db.collection('consultorio')\
                                             .document(consultorio_id)\
                                             .collection('horarios')\
                                             .document(dia_nombre)
                    horarios_doc_snap = horarios_doc_ref.get()
                    if horarios_doc_snap.exists:
                        horarios_doc = horarios_doc_snap.to_dict()
                        if horarios_doc and 'horarios' in horarios_doc:
                            horarios_array = horarios_doc['horarios']
                            if horarios_array and len(horarios_array) > 0:
                                tiene_horario = True
                
                if tiene_horario:

                    from google.cloud.firestore import SERVER_TIMESTAMP
                    fecha_timestamp = datetime.combine(fecha_actual.date(), datetime.min.time())
                    fechas_disponibles.append(fecha_timestamp)
            
            print(f"Encontradas {len(fechas_disponibles)} fechas disponibles")
            return fechas_disponibles
            
        except Exception as e:
            print(f"Error obteniendo fechas disponibles: {e}")
            return []
    
    def reagendar_cita(self, paciente_uid: str, cita_id: str,nueva_fecha, nueva_hora_inicio: str,nueva_hora_fin: str) -> bool:
        try:
            from google.cloud.firestore import SERVER_TIMESTAMP

            self.db.collection('pacientes')\
                  .document(paciente_uid)\
                  .collection('citas')\
                  .document(cita_id)\
                  .update({
                      'fecha': nueva_fecha,
                      'horaInicio': nueva_hora_inicio,
                      'horaFin': nueva_hora_fin,
                      'estado': 'confirmado',
                      'updatedAt': SERVER_TIMESTAMP
                  })
            
            print(f"Cita {cita_id} reagendada en subcolección")

            # Actualizar en colección global (citas minúscula, estándar)
            # Intentar actualizar directamente por ID
            cita_global_ref = self.db.collection('citas').document(cita_id)
            cita_global_doc = cita_global_ref.get()
            
            if cita_global_doc.exists:
                # Calcular fechaHora completa
                from datetime import datetime
                if isinstance(nueva_fecha, str):
                    fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d')
                else:
                    fecha_dt = nueva_fecha
                hora_dt = datetime.strptime(nueva_hora_inicio, '%H:%M')
                hora_obj = hora_dt.time()  # Extraer solo la hora (time object)
                nueva_fecha_hora_completa = datetime.combine(fecha_dt.date(), hora_obj)
                
                cita_global_ref.update({
                    'fecha': nueva_fecha,
                    'fechaHora': nueva_fecha_hora_completa,
                    'appointmentDate': nueva_fecha_hora_completa.isoformat(),
                    'appointmentTime': nueva_hora_inicio,
                    'horaInicio': nueva_hora_inicio,
                    'horaFin': nueva_hora_fin,
                    'estado': 'confirmado',
                    'status': 'confirmado',
                    'updatedAt': SERVER_TIMESTAMP
                })
                print(f"Cita actualizada en colección global citas: {cita_id}")
            else:
                # Fallback: buscar por pacienteId
                global_query = self.db.collection('citas')\
                                     .where('pacienteId', '==', paciente_uid)\
                                     .where('id', '==', cita_id)\
                                     .limit(1)
                
                for doc in global_query.stream():
                    from datetime import datetime
                    if isinstance(nueva_fecha, str):
                        fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d')
                    else:
                        fecha_dt = nueva_fecha
                    hora_dt = datetime.strptime(nueva_hora_inicio, '%H:%M')
                    hora_obj = hora_dt.time()  # Extraer solo la hora (time object)
                    nueva_fecha_hora_completa = datetime.combine(fecha_dt.date(), hora_obj)
                    
                    self.db.collection('citas').document(doc.id).update({
                        'fecha': nueva_fecha,
                        'fechaHora': nueva_fecha_hora_completa,
                        'appointmentDate': nueva_fecha_hora_completa.isoformat(),
                        'appointmentTime': nueva_hora_inicio,
                        'horaInicio': nueva_hora_inicio,
                        'horaFin': nueva_hora_fin,
                        'estado': 'confirmado',
                        'status': 'confirmado',
                        'updatedAt': SERVER_TIMESTAMP
                    })
                    print(f"Cita actualizada en colección global citas (fallback): {doc.id}")
                    break 
            
            return True
            
        except Exception as e:
            print(f"Error reagendando cita: {e}")
            return False
    
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