"""
🔗 SERVICIO DE INTEGRACIÓN CON CLOUD FUNCTIONS DE FIREBASE
Integra el chatbot con las mismas funciones que usa la web
"""

import requests
import os
from typing import Dict, List, Optional
from datetime import datetime
from database.database import FirebaseConfig

class FirebaseFunctionsService:
    """
    Servicio para llamar a Cloud Functions de Firebase desde Python
    Usa HTTP requests con autenticación de Firebase
    """
    
    def __init__(self):
        self.db = FirebaseConfig.get_db()
        # URL base de las Cloud Functions (debe configurarse)
        self.functions_base_url = os.getenv('FIREBASE_FUNCTIONS_URL', 'https://us-central1-densora.cloudfunctions.net')
        # Para llamadas directas a Firestore, usamos Admin SDK
        self.use_direct_firestore = True  # Preferir acceso directo a Firestore
    
    def get_user_appointments(self, user_id: str = None, phone: str = None, 
                             status: str = 'confirmado') -> List[Dict]:
        """
        Obtiene las citas del usuario usando la misma estructura que la web
        Accede directamente a pacientes/{pacienteId}/citas
        """
        try:
            # Obtener paciente
            paciente_id = None
            if user_id:
                paciente_id = user_id
            elif phone:
                # Buscar paciente por teléfono
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone).limit(1)
                docs = query.stream()
                for doc in docs:
                    paciente_id = doc.id
                    break
            
            if not paciente_id:
                return []
            
            # Obtener citas desde la subcolección (misma estructura que la web)
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            
            # Filtrar por estado si se especifica
            if status:
                query = citas_ref.where('estado', 'in', ['programada', 'confirmada', status]).order_by('fechaHora', direction='ASCENDING')
            else:
                query = citas_ref.order_by('fechaHora', direction='ASCENDING')
            
            citas = []
            for doc in query.stream():
                data = doc.to_dict()
                
                # Convertir fechaHora
                fecha_str = ''
                hora_str = ''
                if data.get('fechaHora'):
                    fecha_obj = data['fechaHora']
                    if hasattr(fecha_obj, 'to_datetime'):
                        fecha_dt = fecha_obj.to_datetime()
                    elif hasattr(fecha_obj, 'timestamp'):
                        fecha_dt = datetime.fromtimestamp(fecha_obj.timestamp())
                    else:
                        fecha_dt = fecha_obj
                    
                    fecha_str = fecha_dt.strftime('%d/%m/%Y')
                    hora_str = fecha_dt.strftime('%H:%M')
                
                citas.append({
                    'id': doc.id,
                    'fecha': fecha_str,
                    'hora': hora_str,
                    'dentista': data.get('dentistaName', 'Dr. García'),
                    'consultorio': data.get('consultorioName', 'Consultorio'),
                    'estado': data.get('estado', 'confirmado'),
                    'motivo': data.get('motivo', data.get('Motivo', 'Consulta')),
                    'tratamiento': data.get('tratamientoNombre', 'N/A'),
                    'fechaHora': data.get('fechaHora')
                })
            
            return citas
            
        except Exception as e:
            print(f"Error obteniendo citas: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_available_dates(self, user_id: str = None, phone: str = None, 
                           count: int = 5) -> List[datetime]:
        """
        Obtiene fechas disponibles para agendar
        Usa la misma lógica que la web
        """
        try:
            # Obtener paciente
            paciente_id = None
            if user_id:
                paciente_id = user_id
            elif phone:
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone).limit(1)
                docs = query.stream()
                for doc in docs:
                    paciente_id = doc.id
                    break
            
            if not paciente_id:
                return []
            
            # Obtener último consultorio usado del paciente
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            query = citas_ref.order_by('fechaHora', direction='DESCENDING').limit(1)
            docs = list(query.stream())
            
            consultorio_id = None
            dentista_id = None
            
            if docs:
                ultima_cita = docs[0].to_dict()
                consultorio_id = ultima_cita.get('consultorioId')
                dentista_id = ultima_cita.get('dentistaId')
            
            # Si no hay consultorio previo, buscar uno activo
            if not consultorio_id:
                consultorios_ref = self.db.collection('consultorio')
                query = consultorios_ref.where('activo', '==', True).limit(1)
                docs = list(query.stream())
                if docs:
                    consultorio_id = docs[0].id
                    # Buscar dentista asociado
                    dentistas_ref = self.db.collection('consultorio').document(consultorio_id).collection('dentistas')
                    dentistas_query = dentistas_ref.where('activo', '==', True).limit(1)
                    dentistas_docs = list(dentistas_query.stream())
                    if dentistas_docs:
                        dentista_id = dentistas_docs[0].to_dict().get('dentistaId')
            
            if not consultorio_id or not dentista_id:
                return []
            
            # Obtener horarios del consultorio
            horarios_ref = self.db.collection('consultorio').document(consultorio_id).collection('horarios')
            horarios_docs = list(horarios_ref.stream())
            
            # Generar fechas disponibles (próximos N días laborables)
            from datetime import timedelta
            fechas_disponibles = []
            fecha_actual = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            dias_agregados = 0
            dias_contados = 0
            
            while dias_agregados < count and dias_contados < 30:  # Máximo 30 días
                fecha_candidata = fecha_actual + timedelta(days=dias_contados)
                dia_semana = fecha_candidata.strftime('%A').lower()
                
                # Verificar si hay horario para este día
                tiene_horario = False
                for horario_doc in horarios_docs:
                    horario_data = horario_doc.to_dict()
                    if horario_data.get('dia', '').lower() == dia_semana and horario_data.get('activo', False):
                        tiene_horario = True
                        break
                
                # Solo agregar días laborables (lunes a sábado) con horario
                if fecha_candidata.weekday() < 6 and tiene_horario:  # 0-5 = lunes a sábado
                    fechas_disponibles.append(fecha_candidata)
                    dias_agregados += 1
                
                dias_contados += 1
            
            return fechas_disponibles
            
        except Exception as e:
            print(f"Error obteniendo fechas disponibles: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_available_times(self, user_id: str = None, phone: str = None,
                           fecha: datetime = None) -> List[str]:
        """
        Obtiene horarios disponibles para una fecha
        Usa la misma lógica que la web
        """
        try:
            from datetime import timedelta
            
            if not fecha:
                return []
            
            # Obtener paciente
            paciente_id = None
            if user_id:
                paciente_id = user_id
            elif phone:
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone).limit(1)
                docs = query.stream()
                for doc in docs:
                    paciente_id = doc.id
                    break
            
            if not paciente_id:
                return []
            
            # Obtener último consultorio usado
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            query = citas_ref.order_by('fechaHora', direction='DESCENDING').limit(1)
            docs = list(query.stream())
            
            consultorio_id = None
            dentista_id = None
            
            if docs:
                ultima_cita = docs[0].to_dict()
                consultorio_id = ultima_cita.get('consultorioId')
                dentista_id = ultima_cita.get('dentistaId')
            
            if not consultorio_id:
                consultorios_ref = self.db.collection('consultorio')
                query = consultorios_ref.where('activo', '==', True).limit(1)
                docs = list(query.stream())
                if docs:
                    consultorio_id = docs[0].id
                    dentistas_ref = self.db.collection('consultorio').document(consultorio_id).collection('dentistas')
                    dentistas_query = dentistas_ref.where('activo', '==', True).limit(1)
                    dentistas_docs = list(dentistas_query.stream())
                    if dentistas_docs:
                        dentista_id = dentistas_docs[0].to_dict().get('dentistaId')
            
            if not consultorio_id:
                return []
            
            # Obtener horarios del día
            dia_semana = fecha.strftime('%A').lower()
            horarios_ref = self.db.collection('consultorio').document(consultorio_id).collection('horarios')
            query = horarios_ref.where('dia', '==', dia_semana).where('activo', '==', True).limit(1)
            horarios_docs = list(query.stream())
            
            if not horarios_docs:
                return []
            
            horario_data = horarios_docs[0].to_dict()
            horarios_array = horario_data.get('horarios', [])
            
            # Obtener citas existentes para ese día
            inicio_dia = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
            fin_dia = fecha.replace(hour=23, minute=59, second=59, microsecond=999)
            
            from google.cloud.firestore import Timestamp
            inicio_timestamp = Timestamp.from_datetime(inicio_dia)
            fin_timestamp = Timestamp.from_datetime(fin_dia)
            
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            query = citas_ref.where('fechaHora', '>=', inicio_timestamp).where('fechaHora', '<=', fin_timestamp)
            citas_docs = list(query.stream())
            
            citas_ocupadas = []
            for cita_doc in citas_docs:
                cita_data = cita_doc.to_dict()
                fecha_hora = cita_data.get('fechaHora')
                if fecha_hora:
                    if hasattr(fecha_hora, 'to_datetime'):
                        fecha_dt = fecha_hora.to_datetime()
                    else:
                        fecha_dt = fecha_hora
                    citas_ocupadas.append(fecha_dt.strftime('%H:%M'))
            
            # Generar slots disponibles
            horarios_disponibles = []
            for horario_slot in horarios_array:
                inicio_str = horario_slot.get('inicio', '')
                fin_str = horario_slot.get('fin', '')
                
                if inicio_str and fin_str:
                    # Parsear horas
                    inicio_h, inicio_m = map(int, inicio_str.split(':'))
                    fin_h, fin_m = map(int, fin_str.split(':'))
                    
                    # Generar slots cada 30 minutos
                    hora_actual = inicio_h
                    minuto_actual = inicio_m
                    
                    while hora_actual < fin_h or (hora_actual == fin_h and minuto_actual < fin_m):
                        slot_str = f"{hora_actual:02d}:{minuto_actual:02d}"
                        
                        # Verificar si está ocupado
                        if slot_str not in citas_ocupadas:
                            # Verificar que no sea en el pasado
                            slot_datetime = fecha.replace(hour=hora_actual, minute=minuto_actual)
                            if slot_datetime > datetime.now():
                                horarios_disponibles.append(slot_str)
                        
                        # Avanzar 30 minutos
                        minuto_actual += 30
                        if minuto_actual >= 60:
                            minuto_actual = 0
                            hora_actual += 1
            
            return horarios_disponibles[:10]  # Máximo 10 horarios
            
        except Exception as e:
            print(f"Error obteniendo horarios disponibles: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def create_appointment(self, user_id: str, appointment_data: Dict) -> Dict:
        """
        Crea una cita usando la misma estructura que la web
        Accede directamente a Firestore como lo hace la web
        """
        try:
            from google.cloud.firestore import Timestamp
            
            # Preparar fechaHora
            fecha_str = appointment_data.get('fecha')
            hora_str = appointment_data.get('hora')
            
            if not fecha_str or not hora_str:
                return {'success': False, 'error': 'Faltan fecha u hora'}
            
            # Parsear fecha y hora
            if isinstance(fecha_str, str):
                fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
            else:
                fecha_obj = fecha_str
            
            hora_parts = hora_str.split(':')
            fecha_hora = fecha_obj.replace(hour=int(hora_parts[0]), minute=int(hora_parts[1]))
            
            # Obtener último consultorio usado
            citas_ref = self.db.collection('pacientes').document(user_id).collection('citas')
            query = citas_ref.order_by('fechaHora', direction='DESCENDING').limit(1)
            docs = list(query.stream())
            
            consultorio_id = None
            dentista_id = None
            consultorio_name = None
            dentista_name = None
            
            if docs:
                ultima_cita = docs[0].to_dict()
                consultorio_id = ultima_cita.get('consultorioId')
                dentista_id = ultima_cita.get('dentistaId')
                consultorio_name = ultima_cita.get('consultorioName')
                dentista_name = ultima_cita.get('dentistaName')
            
            if not consultorio_id:
                # Buscar consultorio activo
                consultorios_ref = self.db.collection('consultorio')
                query = consultorios_ref.where('activo', '==', True).limit(1)
                docs = list(query.stream())
                if docs:
                    consultorio_doc = docs[0]
                    consultorio_id = consultorio_doc.id
                    consultorio_data = consultorio_doc.to_dict()
                    consultorio_name = consultorio_data.get('nombre', 'Consultorio')
                    
                    # Buscar dentista
                    dentistas_ref = self.db.collection('consultorio').document(consultorio_id).collection('dentistas')
                    dentistas_query = dentistas_ref.where('activo', '==', True).limit(1)
                    dentistas_docs = list(dentistas_query.stream())
                    if dentistas_docs:
                        dentista_data = dentistas_docs[0].to_dict()
                        dentista_id = dentista_data.get('dentistaId')
                        dentista_name = dentista_data.get('nombreCompleto', 'Dr. García')
            
            if not consultorio_id or not dentista_id:
                return {'success': False, 'error': 'No se encontró consultorio o dentista disponible'}
            
            # Obtener datos del paciente
            paciente_doc = self.db.collection('pacientes').document(user_id).get()
            paciente_data = paciente_doc.to_dict() if paciente_doc.exists else {}
            
            # Crear cita (misma estructura que la web)
            cita_data = {
                'pacienteId': user_id,
                'patientName': paciente_data.get('nombreCompleto', ''),
                'patientPhone': paciente_data.get('telefono', ''),
                'dentistaId': dentista_id,
                'dentistaName': dentista_name,
                'consultorioId': consultorio_id,
                'consultorioName': consultorio_name,
                'fechaHora': Timestamp.from_datetime(fecha_hora),
                'appointmentDate': fecha_str,
                'appointmentTime': hora_str,
                'Duracion': 60,
                'duracion': 60,
                'Motivo': appointment_data.get('motivo', 'Consulta general'),
                'motivo': appointment_data.get('motivo', 'Consulta general'),
                'estado': 'programada',
                'status': 'programada',
                'paymentMethod': 'cash',
                'paymentStatus': 'pending',
                'createdAt': Timestamp.from_datetime(datetime.now()),
                'updatedAt': Timestamp.from_datetime(datetime.now())
            }
            
            # Crear en subcolección (misma estructura que la web)
            citas_ref = self.db.collection('pacientes').document(user_id).collection('citas')
            doc_ref = citas_ref.add(cita_data)
            cita_id = doc_ref[1].id
            
            # También crear en colección principal para compatibilidad
            try:
                citas_principal_ref = self.db.collection('Citas')
                cita_principal_data = {
                    **cita_data,
                    'id': cita_id,
                    'pacienteCitaId': cita_id
                }
                citas_principal_ref.add(cita_principal_data)
            except Exception as e:
                print(f"Error creando cita en colección principal (continuando): {e}")
            
            return {
                'success': True,
                'citaId': cita_id,
                'message': 'Cita creada exitosamente'
            }
            
        except Exception as e:
            print(f"Error creando cita: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def reschedule_appointment(self, user_id: str, cita_id: str, 
                              nueva_fecha: datetime, nueva_hora: str) -> Dict:
        """
        Reagenda una cita usando la misma estructura que la web
        """
        try:
            from google.cloud.firestore import Timestamp
            
            # Obtener cita
            cita_ref = self.db.collection('pacientes').document(user_id).collection('citas').document(cita_id)
            cita_doc = cita_ref.get()
            
            if not cita_doc.exists:
                return {'success': False, 'error': 'Cita no encontrada'}
            
            cita_data = cita_doc.to_dict()
            
            # Verificar que no esté cancelada o completada
            if cita_data.get('estado') in ['cancelada', 'completada']:
                return {'success': False, 'error': f'No se puede reagendar una cita {cita_data.get("estado")}'}
            
            # Preparar nueva fechaHora
            hora_parts = nueva_hora.split(':')
            nueva_fecha_hora = nueva_fecha.replace(hour=int(hora_parts[0]), minute=int(hora_parts[1]))
            
            # Actualizar cita
            cita_ref.update({
                'fechaHora': Timestamp.from_datetime(nueva_fecha_hora),
                'appointmentDate': nueva_fecha.strftime('%Y-%m-%d'),
                'appointmentTime': nueva_hora,
                'updatedAt': Timestamp.from_datetime(datetime.now())
            })
            
            # También actualizar en colección principal si existe
            try:
                citas_principal_ref = self.db.collection('Citas')
                query = citas_principal_ref.where('pacienteCitaId', '==', cita_id).limit(1)
                docs = list(query.stream())
                if docs:
                    docs[0].reference.update({
                        'fechaHora': Timestamp.from_datetime(nueva_fecha_hora),
                        'appointmentDate': nueva_fecha.strftime('%Y-%m-%d'),
                        'appointmentTime': nueva_hora,
                        'updatedAt': Timestamp.from_datetime(datetime.now())
                    })
            except Exception as e:
                print(f"Error actualizando cita en colección principal (continuando): {e}")
            
            return {'success': True, 'message': 'Cita reagendada exitosamente'}
            
        except Exception as e:
            print(f"Error reagendando cita: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def cancel_appointment(self, user_id: str, cita_id: str) -> Dict:
        """
        Cancela una cita usando la misma estructura que la web
        """
        try:
            from google.cloud.firestore import Timestamp
            
            # Obtener cita
            cita_ref = self.db.collection('pacientes').document(user_id).collection('citas').document(cita_id)
            cita_doc = cita_ref.get()
            
            if not cita_doc.exists:
                return {'success': False, 'error': 'Cita no encontrada'}
            
            cita_data = cita_doc.to_dict()
            
            # Verificar que no esté ya cancelada o completada
            if cita_data.get('estado') == 'cancelada':
                return {'success': False, 'error': 'La cita ya está cancelada'}
            
            if cita_data.get('estado') == 'completada':
                return {'success': False, 'error': 'No se puede cancelar una cita completada'}
            
            # Actualizar estado a cancelada
            cita_ref.update({
                'estado': 'cancelada',
                'status': 'cancelada',
                'cancelacion': {
                    'motivo': 'Cancelado por el paciente',
                    'canceladoPor': 'paciente',
                    'fecha': Timestamp.from_datetime(datetime.now())
                },
                'updatedAt': Timestamp.from_datetime(datetime.now())
            })
            
            # También actualizar en colección principal si existe
            try:
                citas_principal_ref = self.db.collection('Citas')
                query = citas_principal_ref.where('pacienteCitaId', '==', cita_id).limit(1)
                docs = list(query.stream())
                if docs:
                    docs[0].reference.update({
                        'estado': 'cancelada',
                        'status': 'cancelada',
                        'cancelacion': {
                            'motivo': 'Cancelado por el paciente',
                            'canceladoPor': 'paciente',
                            'fecha': Timestamp.from_datetime(datetime.now())
                        },
                        'updatedAt': Timestamp.from_datetime(datetime.now())
                    })
            except Exception as e:
                print(f"Error actualizando cita en colección principal (continuando): {e}")
            
            return {'success': True, 'message': 'Cita cancelada exitosamente'}
            
        except Exception as e:
            print(f"Error cancelando cita: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

