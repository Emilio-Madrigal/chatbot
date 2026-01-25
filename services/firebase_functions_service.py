"""
🔗 SERVICIO DE INTEGRACIÓN CON CLOUD FUNCTIONS DE FIREBASE
Integra el chatbot con las mismas funciones que usa la web
"""

import requests
import os
from typing import Dict, List, Optional
from datetime import datetime
from database.database import FirebaseConfig
from utils.phone_utils import normalize_phone_for_database

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
                # Buscar paciente por teléfono (normalizar primero)
                phone_normalizado = normalize_phone_for_database(phone)
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone_normalizado).limit(1)
                docs = query.stream()
                for doc in docs:
                    paciente_id = doc.id
                    break
            
            if not paciente_id:
                print(f"[get_user_appointments] No se encontró paciente - user_id={user_id}, phone={phone}")
                return []
            
            print(f"[get_user_appointments] Buscando citas para paciente_id={paciente_id}")
            
            # Obtener citas desde la subcolección (misma estructura que la web)
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            
            # Obtener fecha actual para filtrar citas futuras
            from datetime import datetime
            ahora = datetime.now()
            
            # Obtener todas las citas y filtrar en Python (más robusto que filtros compuestos)
            all_docs = list(citas_ref.stream())
            print(f"[get_user_appointments] Total documentos en subcolección: {len(all_docs)}")
            
            citas = []
            for doc in all_docs:
                data = doc.to_dict()
                estado_cita = data.get('estado', data.get('status', ''))
                
                # Excluir citas canceladas y completadas si estamos buscando próximas
                if status == 'confirmado' and estado_cita in ['cancelada', 'cancelled']:
                    continue
                
                # Si buscamos específicamente completadas, solo mostrar esas
                if status == 'completado' and estado_cita not in ['completado', 'completada', 'completed']:
                    continue
                
                # Convertir fechaHora
                fecha_str = ''
                hora_str = ''
                fecha_dt = None
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
                
                # Para citas próximas, solo mostrar las que son futuras (o del día de hoy)
                if status == 'confirmado' and fecha_dt:
                    # Citas de hoy o futuras
                    if fecha_dt.date() < ahora.date():
                        continue
                
                # Fix: Fetch proper dentist name if missing or generic
                dentista_name = data.get('dentistaName', data.get('dentista', 'Dentista'))
                dentista_id = data.get('dentistaId')
                
                # If name is generic/missing but we have ID, try to fetch looking up in cache or DB
                if (not dentista_name or dentista_name in ['Dentista', 'Dr. Dentista Prueba', 'Unknown']) and dentista_id:
                    try:
                        # Simple lookup - in production optimize with cache
                        dentista_doc = self.db.collection('dentistas').document(dentista_id).get()
                        if dentista_doc.exists:
                            d_data = dentista_doc.to_dict()
                            # Try to construct full name
                            nombre = d_data.get('nombre', '')
                            apellido = d_data.get('apellido', '')
                            titulo = d_data.get('titulo', 'Dr.')
                            if nombre or apellido:
                                dentista_name = f"{titulo} {nombre} {apellido}".strip()
                    except Exception as e:
                        print(f"[get_user_appointments] Error fetching dentist name: {e}")

                citas.append({
                    'id': doc.id,
                    'fecha': fecha_str,
                    'hora': hora_str,
                    'dentista': dentista_name,
                    'dentistaId': dentista_id,
                    'consultorio': data.get('consultorioName', data.get('consultorio', 'Consultorio')),
                    'consultorioId': data.get('consultorioId'),
                    'estado': estado_cita or 'programada',
                    'motivo': data.get('motivo', data.get('Motivo', 'Consulta')),
                    'tratamiento': data.get('tratamientoNombre', data.get('tratamiento', 'N/A')),
                    'fechaHora': data.get('fechaHora')
                })
            
            # Ordenar por fecha
            citas.sort(key=lambda x: x.get('fechaHora') or datetime.max)
            
            print(f"[get_user_appointments] Citas encontradas después de filtrar: {len(citas)}")
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
                phone_normalizado = normalize_phone_for_database(phone)
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone_normalizado).limit(1)
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
                phone_normalizado = normalize_phone_for_database(phone)
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone_normalizado).limit(1)
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
            
            # Firebase Admin SDK accepts datetime objects directly
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            query = citas_ref.where('fechaHora', '>=', inicio_dia).where('fechaHora', '<=', fin_dia)
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
                'fechaHora': fecha_hora,  # datetime object - Firebase accepts it directly
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
                'createdAt': datetime.now(),  # datetime directly
                'updatedAt': datetime.now()
            }
            
            # Crear en subcolección (misma estructura que la web)
            citas_ref = self.db.collection('pacientes').document(user_id).collection('citas')
            doc_ref = citas_ref.add(cita_data)
            cita_id = doc_ref[1].id
            
            # También crear en colección principal para compatibilidad
            try:
                citas_principal_ref = self.db.collection('citas')
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
            
            # Actualizar cita - Firebase Admin SDK accepts datetime directly
            cita_ref.update({
                'fechaHora': nueva_fecha_hora,
                'appointmentDate': nueva_fecha.strftime('%Y-%m-%d'),
                'appointmentTime': nueva_hora,
                'updatedAt': datetime.now()
            })
            
            # También actualizar en colección principal si existe
            try:
                citas_principal_ref = self.db.collection('citas')
                query = citas_principal_ref.where('pacienteCitaId', '==', cita_id).limit(1)
                docs = list(query.stream())
                if docs:
                    docs[0].reference.update({
                        'fechaHora': nueva_fecha_hora,
                        'appointmentDate': nueva_fecha.strftime('%Y-%m-%d'),
                        'appointmentTime': nueva_hora,
                        'updatedAt': datetime.now()
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
            
            # Actualizar estado a cancelada - Firebase Admin SDK accepts datetime directly
            cita_ref.update({
                'estado': 'cancelada',
                'status': 'cancelada',
                'cancelacion': {
                    'motivo': 'Cancelado por el paciente',
                    'canceladoPor': 'paciente',
                    'fecha': datetime.now()
                },
                'updatedAt': datetime.now()
            })
            
            # También actualizar en colección principal si existe
            try:
                citas_principal_ref = self.db.collection('citas')
                query = citas_principal_ref.where('pacienteCitaId', '==', cita_id).limit(1)
                docs = list(query.stream())
                if docs:
                    docs[0].reference.update({
                        'estado': 'cancelada',
                        'status': 'cancelada',
                        'cancelacion': {
                            'motivo': 'Cancelado por el paciente',
                            'canceladoPor': 'paciente',
                            'fecha': datetime.now()
                        },
                        'updatedAt': datetime.now()
                    })
            except Exception as e:
                print(f"Error actualizando cita en colección principal (continuando): {e}")
            
            return {'success': True, 'message': 'Cita cancelada exitosamente'}
            
        except Exception as e:
            print(f"Error cancelando cita: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def get_medical_history(self, user_id: str = None, phone: str = None) -> Dict:
        """
        Obtiene el historial médico del paciente para mostrar en el chat
        Lee desde historialMedico/current subcollection (igual que la web)
        y desencripta los datos si están encriptados
        """
        try:
            # Obtener paciente
            paciente_id = None
            if user_id:
                paciente_id = user_id
            elif phone:
                phone_normalizado = normalize_phone_for_database(phone)
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone_normalizado).limit(1)
                docs = list(query.stream())
                if docs:
                    paciente_id = docs[0].id
            
            if not paciente_id:
                print(f"[get_medical_history] No se encontró paciente_id")
                return {'success': False, 'error': 'Paciente no encontrado'}
            
            print(f"[get_medical_history] Buscando paciente con id={paciente_id}")
            
            # Obtener documento del paciente
            paciente_ref = self.db.collection('pacientes').document(paciente_id)
            paciente_doc = paciente_ref.get()
            
            if not paciente_doc.exists:
                print(f"[get_medical_history] Paciente no existe en BD")
                return {'success': False, 'error': 'Paciente no encontrado'}
            
            paciente_data = paciente_doc.to_dict()
            print(f"[get_medical_history] Datos del paciente: {list(paciente_data.keys())}")
            
            # 1. PRIMARIO: Obtener historial médico desde subcollection historialMedico
            #    La web guarda con addDoc() y IDs automáticos, marcando isActive=True
            historial_data = {}
            historial_completado = False
            try:
                # PRIMERO: buscar documento activo (así lo guarda la web con addDoc)
                historial_query = paciente_ref.collection('historialMedico').where('isActive', '==', True).limit(1)
                historial_docs = list(historial_query.stream())
                
                if historial_docs:
                    historial_data = historial_docs[0].to_dict()
                    historial_completado = True
                    print(f"[get_medical_history] Historial ACTIVO encontrado (ID={historial_docs[0].id})")
                    print(f"[get_medical_history] Campos: {list(historial_data.keys())}")
                    print(f"[get_medical_history] _encrypted={historial_data.get('_encrypted')}")
                else:
                    # Fallback: buscar documento 'current' (estructura legacy)
                    historial_current_ref = paciente_ref.collection('historialMedico').document('current')
                    historial_current_doc = historial_current_ref.get()
                    
                    if historial_current_doc.exists:
                        historial_data = historial_current_doc.to_dict()
                        historial_completado = True
                        print(f"[get_medical_history] Historial encontrado en 'current': {list(historial_data.keys())}")
                    else:
                        # Último intento: obtener cualquier documento de la colección
                        any_docs = list(paciente_ref.collection('historialMedico').limit(1).stream())
                        if any_docs:
                            historial_data = any_docs[0].to_dict()
                            historial_completado = True
                            print(f"[get_medical_history] Historial encontrado (cualquier doc): {list(historial_data.keys())}")
                        else:
                            print(f"[get_medical_history] No se encontró ningún historial médico")
            except Exception as e:
                print(f"[get_medical_history] Error accediendo historialMedico subcollection: {e}")
                import traceback
                traceback.print_exc()
            
            # 2. DESENCRIPTAR si los datos están encriptados
            #    NOTA: Corregido bug de precedencia de operadores
            if historial_data and (historial_data.get('_encrypted') or historial_data.get('encryptionEnabled')):
                try:
                    from utils.encryption import decrypt_medical_history
                    print(f"[get_medical_history] Desencriptando historial médico...")
                    print(f"[get_medical_history] Datos antes de desencriptar: alergias={type(historial_data.get('alergias'))}")
                    historial_data = decrypt_medical_history(historial_data, paciente_id)
                    print(f"[get_medical_history] Historial desencriptado exitosamente")
                    print(f"[get_medical_history] Datos después: alergias={historial_data.get('alergias')}")
                except ImportError as ie:
                    print(f"[get_medical_history] Módulo de encryption no disponible: {ie}")
                except Exception as e:
                    print(f"[get_medical_history] Error desencriptando: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 3. Construir nombre completo de diferentes formas posibles
            nombre = (
                historial_data.get('nombre') or
                historial_data.get('nombreCompleto') or
                paciente_data.get('nombreCompleto') or 
                f"{paciente_data.get('nombres', paciente_data.get('nombre', ''))} {paciente_data.get('apellidos', paciente_data.get('apellido', ''))}".strip() or
                'No registrado'
            )
            
            # Combinar apellido si existe
            apellido = historial_data.get('apellido') or paciente_data.get('apellidos', paciente_data.get('apellido', ''))
            if apellido and not nombre.endswith(apellido):
                nombre_completo = f"{nombre} {apellido}".strip()
            else:
                nombre_completo = nombre
            
            # 4. Extraer datos médicos - priorizar historialMedico sobre paciente_data
            # Alergias
            alergias = (
                historial_data.get('alergias') or 
                paciente_data.get('alergias') or 
                []
            )
            if isinstance(alergias, str):
                alergias = [alergias] if alergias.strip() else []
            
            # Medicamentos (la web usa 'medicamentosActuales')
            medicamentos = (
                historial_data.get('medicamentosActuales') or
                historial_data.get('medicacionActual') or
                historial_data.get('medicamentos') or
                paciente_data.get('medicamentos') or
                []
            )
            if isinstance(medicamentos, str):
                medicamentos = [medicamentos] if medicamentos.strip() else []
            
            # Enfermedades crónicas (la web usa 'condicionesMedicas' y 'enfermedadesGeneticas')
            enfermedades = (
                historial_data.get('condicionesMedicas') or
                historial_data.get('enfermedadesCronicas') or
                historial_data.get('enfermedadesGeneticas') or
                paciente_data.get('enfermedadesCronicas') or
                []
            )
            if isinstance(enfermedades, str):
                enfermedades = [enfermedades] if enfermedades.strip() else []
            
            # 5. Calcular completitud usando mismos campos que la web
            #    Campos de la web: nombre, apellido, edad, sexo, telefono, contactoEmergencia, direccion,
            #                      alergias, medicamentosActuales, condicionesMedicas, grupoSanguineo, etc.
            campos_evaluados = [
                historial_data.get('nombre') or paciente_data.get('nombre') or paciente_data.get('nombres'),
                historial_data.get('apellido') or paciente_data.get('apellidos') or paciente_data.get('apellido'),
                historial_data.get('edad') or paciente_data.get('edad'),
                historial_data.get('sexo') or paciente_data.get('sexo'),
                historial_data.get('telefono') or paciente_data.get('telefono'),
                historial_data.get('contactoEmergencia') or paciente_data.get('contactoEmergencia'),
                historial_data.get('direccion') or paciente_data.get('direccion'),
                alergias,
                medicamentos,
                enfermedades,
                historial_data.get('grupoSanguineo') or paciente_data.get('grupoSanguineo'),
                historial_data.get('ultimaCita') or paciente_data.get('ultimaCita'),
                historial_data.get('observacionesClinicas'),
                historial_data.get('diagnosticosPrevios'),
            ]
            
            campos_completados = sum(1 for c in campos_evaluados if c)
            completitud = int((campos_completados / len(campos_evaluados)) * 100)
            
            # Si hay valor de completeness guardado en el historial, usarlo
            if historial_data.get('completeness'):
                try:
                    completitud = int(float(historial_data.get('completeness')))
                except:
                    pass
            
            # 6. Extraer más campos para historia dental
            motivo_consulta = historial_data.get('motivoConsulta') or historial_data.get('observacionesClinicas') or ''
            ultima_visita = historial_data.get('ultimaCita') or historial_data.get('ultimaVisitaDentista') or ''
            dolor_boca = historial_data.get('dolorBoca') or historial_data.get('dolor') or ''
            sangrado_encias = historial_data.get('sangradoEncias') or historial_data.get('sangrado') or ''
            
            return {
                'success': True,
                'data': {
                    'nombre': nombre_completo,
                    'edad': historial_data.get('edad') or paciente_data.get('edad') or paciente_data.get('fechaNacimiento') or 'No especificada',
                    'telefono': historial_data.get('telefono') or paciente_data.get('telefono') or 'No registrado',
                    'email': paciente_data.get('email') or 'No registrado',
                    'sexo': historial_data.get('sexo') or paciente_data.get('sexo') or '',
                    'direccion': historial_data.get('direccion') or paciente_data.get('direccion') or '',
                    'alergias': alergias,
                    'medicamentos': medicamentos,
                    'medicamentosActuales': medicamentos,  # Alias para compatibilidad
                    'enfermedadesCronicas': enfermedades,
                    'condicionesMedicas': enfermedades,  # Alias para compatibilidad
                    'grupoSanguineo': historial_data.get('grupoSanguineo') or paciente_data.get('grupoSanguineo') or '',
                    'antecedentesMedicos': historial_data.get('antecedentesMedicos') or paciente_data.get('antecedentesMedicos') or '',
                    'contactoEmergencia': historial_data.get('contactoEmergencia') or paciente_data.get('contactoEmergencia') or {},
                    # Campos de historia dental
                    'motivoConsulta': motivo_consulta,
                    'ultimaVisitaDentista': ultima_visita,
                    'dolorBoca': dolor_boca,
                    'sangradoEncias': sangrado_encias,
                    'observacionesClinicas': historial_data.get('observacionesClinicas') or '',
                    'diagnosticosPrevios': historial_data.get('diagnosticosPrevios') or '',
                    # Metadata
                    'historialCompletado': historial_completado,
                    'completeness': completitud,
                    'completitud': completitud,  # Alias
                    'historialExtra': historial_data
                }
            }
            
        except Exception as e:
            print(f"Error obteniendo historial médico: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    def get_pending_reviews(self, user_id: str = None, phone: str = None) -> List[Dict]:
        """
        Obtiene las citas completadas pendientes de reseña
        """
        try:
            # Obtener paciente
            paciente_id = None
            if user_id:
                paciente_id = user_id
            elif phone:
                phone_normalizado = normalize_phone_for_database(phone)
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone_normalizado).limit(1)
                docs = list(query.stream())
                if docs:
                    paciente_id = docs[0].id
            
            if not paciente_id:
                print(f"[get_pending_reviews] No se encontró paciente_id")
                return []
            
            print(f"[get_pending_reviews] Buscando citas para paciente_id={paciente_id}")
            
            # Obtener citas - buscar TODAS y filtrar en Python para manejar variantes
            citas_ref = self.db.collection('pacientes').document(paciente_id).collection('citas')
            # Obtener todas las citas ordenadas por fecha (no filtrar por estado en query)
            query = citas_ref.order_by('fechaHora', direction='DESCENDING').limit(20)
            
            citas_completadas = []
            estados_completados = ['completado', 'completada', 'completed', 'finalizada', 'finalizado']
            
            for doc in query.stream():
                data = doc.to_dict()
                cita_id = doc.id
                estado = data.get('estado', data.get('status', '')).lower().strip()
                
                print(f"[get_pending_reviews] Cita {cita_id} - estado: '{estado}'")
                
                # Verificar si el estado es alguna variante de completado
                if estado not in estados_completados:
                    continue
                
                # Verificar si ya tiene reseña
                tiene_resena = False
                try:
                    dentista_id = data.get('dentistaId')
                    if dentista_id:
                        resenas_ref = self.db.collection('dentistas').document(dentista_id).collection('resenas')
                        resena_query = resenas_ref.where('citaId', '==', cita_id).limit(1)
                        tiene_resena = len(list(resena_query.stream())) > 0
                except:
                    pass
                
                if not tiene_resena:
                    # Formatear fecha
                    fecha_str = ''
                    if data.get('fechaHora'):
                        fecha_obj = data['fechaHora']
                        if hasattr(fecha_obj, 'to_datetime'):
                            fecha_dt = fecha_obj.to_datetime()
                        elif hasattr(fecha_obj, 'timestamp'):
                            fecha_dt = datetime.fromtimestamp(fecha_obj.timestamp())
                        else:
                            fecha_dt = fecha_obj
                        fecha_str = fecha_dt.strftime('%d/%m/%Y')
                    
                    citas_completadas.append({
                        'id': cita_id,
                        'fecha': fecha_str,
                        'dentista': data.get('dentistaName', 'Dentista'),
                        'dentistaId': data.get('dentistaId'),
                        'consultorio': data.get('consultorioName', 'Consultorio'),
                        'tratamiento': data.get('tratamientoNombre', 'Consulta')
                    })
            
            print(f"[get_pending_reviews] Citas completadas sin reseña: {len(citas_completadas)}")
            return citas_completadas
            
        except Exception as e:
            print(f"Error obteniendo citas pendientes de reseña: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_user_reviews(self, user_id: str = None, phone: str = None) -> List[Dict]:
        """
        Obtiene las reseñas escritas por el usuario
        Version optimizada con mejor manejo de errores
        """
        try:
            # Obtener paciente
            paciente_id = None
            if user_id:
                paciente_id = user_id
            elif phone:
                phone_normalizado = normalize_phone_for_database(phone)
                pacientes_ref = self.db.collection('pacientes')
                query = pacientes_ref.where('telefono', '==', phone_normalizado).limit(1)
                docs = list(query.stream())
                if docs:
                    paciente_id = docs[0].id
            
            if not paciente_id:
                print(f"[get_user_reviews] No se encontro paciente_id")
                return []
            
            print(f"[get_user_reviews] Buscando resenas para paciente_id={paciente_id}")
            reviews = []
            
            # Buscar en dentistas - limitar a 20 para evitar timeout
            dentistas_ref = self.db.collection('dentistas')
            dentistas_docs = list(dentistas_ref.limit(20).stream())
            
            for dentista_doc in dentistas_docs:
                try:
                    resenas_ref = dentista_doc.reference.collection('resenas')
                    
                    # Buscar por pacienteId
                    query1 = resenas_ref.where('pacienteId', '==', paciente_id).limit(3)
                    for resena_doc in query1.stream():
                        data = resena_doc.to_dict()
                        dentista_data = dentista_doc.to_dict()
                        
                        fecha_str = ''
                        if data.get('created_at'):
                            try:
                                fecha_obj = data['created_at']
                                if hasattr(fecha_obj, 'strftime'):
                                    fecha_str = fecha_obj.strftime('%d/%m/%Y')
                                elif hasattr(fecha_obj, 'to_datetime'):
                                    fecha_str = fecha_obj.to_datetime().strftime('%d/%m/%Y')
                            except:
                                fecha_str = ''
                        
                        reviews.append({
                            'id': resena_doc.id,
                            'dentista': dentista_data.get('Nombre', dentista_data.get('nombre', 'Dentista')),
                            'calificacion': data.get('calificacion', 0),
                            'comentario': data.get('comentario', ''),
                            'fecha': fecha_str,
                            'anonimo': data.get('anonimo', False)
                        })
                    
                    # Tambien buscar por userId si es diferente
                    query2 = resenas_ref.where('userId', '==', paciente_id).limit(3)
                    for resena_doc in query2.stream():
                        # Evitar duplicados
                        if resena_doc.id not in [r['id'] for r in reviews]:
                            data = resena_doc.to_dict()
                            dentista_data = dentista_doc.to_dict()
                            
                            fecha_str = ''
                            if data.get('created_at'):
                                try:
                                    fecha_obj = data['created_at']
                                    if hasattr(fecha_obj, 'strftime'):
                                        fecha_str = fecha_obj.strftime('%d/%m/%Y')
                                    elif hasattr(fecha_obj, 'to_datetime'):
                                        fecha_str = fecha_obj.to_datetime().strftime('%d/%m/%Y')
                                except:
                                    fecha_str = ''
                            
                            reviews.append({
                                'id': resena_doc.id,
                                'dentista': dentista_data.get('Nombre', dentista_data.get('nombre', 'Dentista')),
                                'calificacion': data.get('calificacion', 0),
                                'comentario': data.get('comentario', ''),
                                'fecha': fecha_str,
                                'anonimo': data.get('anonimo', False)
                            })
                            
                except Exception as inner_e:
                    print(f"[get_user_reviews] Error en dentista {dentista_doc.id}: {inner_e}")
                    continue
            
            print(f"[get_user_reviews] Encontradas {len(reviews)} resenas")
            return reviews[:10]  # Maximo 10 resenas
            
        except Exception as e:
            print(f"Error obteniendo resenas del usuario: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def submit_review(self, user_id: str, dentista_id: str, cita_id: str,
                     calificacion: int, comentario: str = '', anonimo: bool = False) -> Dict:
        """
        Envía una reseña para un dentista
        Usa la misma estructura que la web
        """
        try:
            if not user_id or not dentista_id:
                return {'success': False, 'error': 'Faltan datos requeridos'}
            
            if calificacion < 1 or calificacion > 5:
                return {'success': False, 'error': 'La calificación debe ser entre 1 y 5'}
            
            # Obtener datos del paciente
            paciente_doc = self.db.collection('pacientes').document(user_id).get()
            paciente_data = paciente_doc.to_dict() if paciente_doc.exists else {}
            
            # Crear reseña
            resena_data = {
                'pacienteId': user_id,
                'userId': user_id,
                'citaId': cita_id,
                'calificacion': calificacion,
                'comentario': comentario[:500] if comentario else '',
                'anonimo': anonimo,
                'created_at': datetime.now(),
                'editada': False,
                'nombrePaciente': '' if anonimo else paciente_data.get('nombreCompleto', 
                    f"{paciente_data.get('nombre', '')} {paciente_data.get('apellidos', '')}".strip())
            }
            
            # Guardar en subcolección del dentista
            resenas_ref = self.db.collection('dentistas').document(dentista_id).collection('resenas')
            doc_ref = resenas_ref.add(resena_data)
            
            return {
                'success': True,
                'resenaId': doc_ref[1].id,
                'message': 'Reseña enviada exitosamente'
            }
            
        except Exception as e:
            print(f"Error enviando reseña: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

