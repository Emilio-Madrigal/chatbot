from database.firebase_config import FirebaseConfig
from datetime import datetime
from typing import List, Optional, Dict

class Paciente:
    def __init__(self, uid=None, nombre=None, apellidos=None, telefono=None, 
                 email=None, nombreCompleto=None):
        self.uid = uid
        self.nombre = nombre
        self.apellidos = apellidos
        self.telefono = telefono
        self.email = email
        self.nombreCompleto = nombreCompleto
    
    @classmethod
    def from_dict(cls, uid: str, data: dict):
        return cls(
            uid=uid,
            nombre=data.get('nombre'),
            apellidos=data.get('apellidos'),
            telefono=data.get('telefono'),
            email=data.get('email'),
            nombreCompleto=data.get('nombreCompleto')
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
            query = self.collection.where('telefono', '==', telefono).limit(1)
            docs = query.stream()

            for doc in docs:
                paciente = Paciente.from_dict(doc.id, doc.to_dict())
                print(f"Paciente encontrado: {paciente.nombreCompleto}")
                return paciente
            
            print(f"No existe paciente con teléfono: {telefono}")
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


class CitaRepository:
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        self.paciente_repo = PacienteRepository()
    
    def obtener_paciente_por_telefono(self, telefono: str):
        """Obtiene el paciente por su número de teléfono"""
        return self.paciente_repo.buscar_por_telefono(telefono)
    
    def obtener_ultimo_consultorio_paciente(self, paciente_uid: str) -> Optional[Dict]:
        """Obtiene el último consultorio usado por el paciente basado en su última cita"""
        try:
            citas_ref = self.db.collection('pacientes')\
                              .document(paciente_uid)\
                              .collection('citas')
            # Ordenar por fecha descendente y tomar la primera
            query = citas_ref.order_by('fecha', direction='DESCENDING')\
                            .order_by('createdAt', direction='DESCENDING')\
                            .limit(1)
            
            for doc in query.stream():
                cita_data = doc.to_dict()
                return {
                    'consultorioId': cita_data.get('consultorioID'),
                    'consultorioName': cita_data.get('consultorioName'),
                    'dentistaId': cita_data.get('dentistaId'),
                    'dentistaName': cita_data.get('dentistaName')
                }
            
            return None
        except Exception as e:
            print(f"Error obteniendo último consultorio: {e}")
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
    
    def crear_cita(self, usuario_whatsapp: str, datos_cita: dict) -> Optional[str]:
        """Crea una nueva cita para el usuario"""
        try:
            from google.cloud.firestore import SERVER_TIMESTAMP
            from datetime import datetime
            
            # Buscar paciente por teléfono
            paciente = self.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            if not paciente:
                print(f"No se encontró paciente con teléfono: {usuario_whatsapp}")
                return None
            
            # Obtener último consultorio usado
            ultimo_consultorio = self.obtener_ultimo_consultorio_paciente(paciente.uid)
            if not ultimo_consultorio:
                print(f"No se encontró consultorio previo para el paciente")
                return None
            
            # Convertir fecha string a timestamp
            fecha_str = datos_cita.get('fecha')
            hora_inicio = datos_cita.get('hora')
            
            # Calcular hora fin (asumiendo 30 minutos por defecto)
            from datetime import timedelta
            hora_obj = datetime.strptime(hora_inicio, '%H:%M')
            hora_fin_obj = (hora_obj + timedelta(minutes=30)).time()
            hora_fin = hora_fin_obj.strftime('%H:%M')
            
            # Convertir fecha a timestamp
            fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
            fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
            
            # Crear documento de cita en subcolección del paciente
            cita_data = {
                'consultorioID': ultimo_consultorio['consultorioId'],
                'consultorioName': ultimo_consultorio['consultorioName'],
                'dentistaId': ultimo_consultorio['dentistaId'],
                'dentistaName': ultimo_consultorio['dentistaName'],
                'fecha': fecha_timestamp,
                'horaInicio': hora_inicio,
                'horaFin': hora_fin,
                'estado': 'confirmado',
                'motivo': datos_cita.get('descripcion', ''),
                'pacienteId': paciente.uid,
                'pacienteName': datos_cita.get('nombre_cliente', paciente.nombreCompleto),
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
            
            # También crear en colección global de citas
            cita_global_data = {
                **cita_data,
                'uid': paciente.uid
            }
            self.db.collection('citas').document(cita_id).set(cita_global_data)
            
            print(f"Cita creada: {cita_id}")
            return cita_id
            
        except Exception as e:
            print(f"Error creando cita: {e}")
            return None
    
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
            hora_obj = datetime.strptime(nueva_hora, '%H:%M')
            hora_fin_obj = (hora_obj + timedelta(minutes=30)).time()
            hora_fin = hora_fin_obj.strftime('%H:%M')
            
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
            
            # Actualizar en colección global
            self.db.collection('citas')\
                  .document(cita_id)\
                  .update({
                      'fecha': fecha_timestamp,
                      'horaInicio': nueva_hora,
                      'horaFin': hora_fin,
                      'estado': 'confirmado',
                      'updatedAt': SERVER_TIMESTAMP
                  })
            
            print(f"Cita {cita_id} actualizada")
            return True
            
        except Exception as e:
            print(f"Error actualizando cita: {e}")
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
            global_query = self.db.collection('citas')\
                                 .where('pacienteId', '==', paciente_uid)\
                                 .where('uid', '==', paciente_uid)\
                                 .limit(1)
            
            for doc in global_query.stream():
                self.db.collection('citas').document(doc.id).update({
                    'estado': 'cancelada',
                    'updatedAt': SERVER_TIMESTAMP
                })
                print(f"Cita actualizada en colección global")
            
            return True
            
        except Exception as e:
            print(f"Error cancelando cita: {e}")
            return False
    
    def obtener_horarios_disponibles(self, dentista_id: str, consultorio_id: str, fecha_timestamp) -> List[Dict]:
        try:
            from datetime import datetime, timedelta

            fecha_dt = datetime.fromtimestamp(fecha_timestamp.timestamp())
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dia_nombre = dias_semana[fecha_dt.weekday()]
            
            print(f"Buscando horarios para {dia_nombre}")
            horarios_ref = self.db.collection('consultorios')\
                                 .document(consultorio_id)\
                                 .collection('horarios')\
                                 .where('dia', '==', dia_nombre)\
                                 .where('activo', '==', True)\
                                 .limit(1)
            
            horarios_doc = None
            for doc in horarios_ref.stream():
                horarios_doc = doc.to_dict()
                break
            
            if not horarios_doc or 'horarios' not in horarios_doc:
                print(f"No hay horarios configurados para {dia_nombre}")
                return []
            hora_inicio_consultorio = horarios_doc['horarios']['inicio']  # "09:00"
            hora_fin_consultorio = horarios_doc['horarios']['fin']  # "18:00"
            
            print(f"Horario consultorio: {hora_inicio_consultorio} - {hora_fin_consultorio}")
            citas_existentes = self.db.collection('citas')\
                                     .where('dentistaId', '==', dentista_id)\
                                     .where('fecha', '==', fecha_timestamp)\
                                     .where('estado', 'in', ['confirmado', 'en proceso'])\
                                     .stream()
            horas_ocupadas = []
            for doc in citas_existentes:
                cita_data = doc.to_dict()
                horas_ocupadas.append({
                    'inicio': cita_data['horaInicio'],
                    'fin': cita_data['horaFin']
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

                dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                dia_nombre = dias_semana[fecha_actual.weekday()]

                horarios_ref = self.db.collection('consultorios')\
                                     .document(consultorio_id)\
                                     .collection('horarios')\
                                     .where('dia', '==', dia_nombre)\
                                     .where('activo', '==', True)\
                                     .limit(1)
                
                tiene_horario = False
                for doc in horarios_ref.stream():
                    tiene_horario = True
                    break
                
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

            global_query = self.db.collection('citas')\
                                 .where('pacienteId', '==', paciente_uid)\
                                 .limit(10)
            
            cita_encontrada = False
            for doc in global_query.stream():
                doc_data = doc.to_dict()
                self.db.collection('citas').document(doc.id).update({
                    'fecha': nueva_fecha,
                    'horaInicio': nueva_hora_inicio,
                    'horaFin': nueva_hora_fin,
                    'estado': 'confirmado',
                    'updatedAt': SERVER_TIMESTAMP
                })
                cita_encontrada = True
                print(f"Cita actualizada en colección global: {doc.id}")
                break 
            
            return True
            
        except Exception as e:
            print(f"Error reagendando cita: {e}")
            return False