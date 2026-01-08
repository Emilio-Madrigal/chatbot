from apscheduler.schedulers.background import BackgroundScheduler
from database.models import CitaRepository, PacienteRepository
from services.whatsapp_service import WhatsAppService
from datetime import datetime, timedelta
import pytz
from config import Config

class NotificacionesService:
    def __init__(self):
        self.cita_repo = CitaRepository()
        self.paciente_repo = PacienteRepository()
        self.whatsapp = WhatsAppService()
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(Config.TIMEZONE)
        self._setup_scheduled_jobs()

    def _setup_scheduled_jobs(self):
        self.scheduler.add_job(
            func=self.check_upcoming_appointments,
            trigger='interval',
            hours=1,
            id='check_appointments',
            name='Revisar citas proximas'
        )
        self.scheduler.add_job(
                        func=self.send_daily_reminders,
            trigger="cron",
            hour=9,
            minute=0,
            timezone=self.timezone,
            id='daily_reminders',
            name='Recordatorios diarios'
        )
        # J.RF14: Resumen semanal paciente (cada lunes a las 10:00)
        self.scheduler.add_job(
            func=self.send_weekly_summaries,
            trigger="cron",
            day_of_week='mon',
            hour=10,
            minute=0,
            timezone=self.timezone,
            id='weekly_summaries',
            name='Resúmenes semanales pacientes'
        )
        print("trabajos programados y configurados")
    def start_scheduler(self):
        if not self.scheduler.running:
            self.scheduler.start()
            print("init del servicio")
    def stop_scheduler(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("altooo, yo ya estuve en estos juegos ")
    def check_upcoming_appointments(self):
        try:
            tomorrow=datetime.now()+timedelta(days=1)
            fecha_limite=tomorrow.strftime('%Y-%m-%d')
            citas_proximas=self.cita_repo.obtener_citas_proximas(fecha_limite)
            for cita in citas_proximas:
                self._process_appointment_reminder(cita)
                print(f"\Procesadas {len(citas_proximas)} citas próximas")
        except Exception as e:
            print(f"error revisando citas proximas: {e}")
    def _process_appointment_reminder(self, cita):
        try:
            now=datetime.now()
            fecha_cita=datetime.strptime(cita.fecha,'%Y-%m-%d')
            tiempo_hasta_cita = fecha_cita - now.replace(hour=0, minute=0, second=0, microsecond=0)
            dias_hasta_cita = tiempo_hasta_cita.days

            if dias_hasta_cita==1:
                self.send_24_hour_reminder(cita)
            elif dias_hasta_cita==0:
                self._check_same_day_reminder(cita)
        except Exception as e:
            print(f"error procesando recordatorio de cita {cita.id}: {e}")
    def _check_same_day_reminder(self, cita):
        try:
            now=datetime.now()
            hora_cita=datetime.strptime(cita.hora,'%H:%M').time()
            fecha_hora_cita=datetime.combine(datetime.now().date(),hora_cita)

            minutos_hasta_cita=(fecha_hora_cita-now).total_seconds()/60
            if 110<=minutos_hasta_cita<=130:
                self.send_2_hour_reminder(cita)
        except Exception as e:
            print(f"error en el recordatorio del mismo dia: {e}")

    def send_24_hour_reminder(self, cita):
        try:
            fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
            
            mensaje = f"""*RECORDATORIO DE CITA*

            *Paciente:* {cita.nombre_cliente}
            *Mañana:* {fecha_formatted}
            *Hora:* {cita.hora}
            *Motivo:* {cita.descripcion}

            No olvides confirmar tu asistencia.
            Responde *CONFIRMO* si asistirás o *CANCELAR* si necesitas cancelar.

            ¡Te esperamos!"""
            
            result = self.whatsapp.send_text_message(cita.usuario_whatsapp, mensaje)
            
            if result:
                print(f"se envio el reminder de 24 horas {cita.id}")
            else:
                print(f"error enviando el reminder de 24 horas {cita.id}")
                
        except Exception as e:
            print(f"error canijo en el reminder de 24 horas: {e}")
    def send_2_hour_reminder(self, cita):
        try:
            mensaje = f"""*RECORDATORIO URGENTE*

            *{cita.nombre_cliente}*
            Tu cita es en *2 horas* ({cita.hora})

            *¿Ya estás preparado/a?*
            Recuerda considerar el tiempo de traslado.

            ¡Nos vemos pronto!"""
            
            result = self.whatsapp.send_text_message(cita.usuario_whatsapp, mensaje)
            
            if result:
                print(f"se envio el reminder de 2 horas {cita.id}")
            else:
                print(f"error enviando el reminder de 2 horas {cita.id}")
            
        except Exception as e:
            print(f"error canijo en el reminder de 2 horas{e}")
    def send_daily_reminders(self):
        try:
            today=datetime.now().strftime('%Y-%m-%d')
            citas_hoy=self.cita_repo.obtener_citas_proximas(today)
            citas_hoy=[c for c in citas_hoy if c.fecha==today]

            usuarios_con_citas={}
            for cita in citas_hoy:
                if cita.usuario_whatsapp not in usuarios_con_citas:
                    usuarios_con_citas[cita.usuario_whatsapp]=[]
                usuarios_con_citas[cita.usuario_whatsapp].append(cita)
            for usuario, citas in usuarios_con_citas.items():
                self._send_daily_summary(usuario,citas)
            print(f"recordatorios diarios enviados a {len(usuarios_con_citas)} usuarios")

        except Exception as e:
            print(f"error enviando recordatoriso diaros: {e}")
    def _send_daily_summary(self,usuario_whatsapp,citas_hoy):
        try:
            if len(citas_hoy) == 1:
                cita = citas_hoy[0]
                mensaje = f"""*BUENOS DÍAS*

                Tienes *1 cita* programada para hoy:

                *{cita.nombre_cliente}*
                *{cita.hora}*
                {cita.descripcion}

                ¡Que tengas un excelente día!"""
            
            else:
                mensaje = "*BUENOS DÍAS*\n\nTienes *{} citas* programadas para hoy:\n\n".format(len(citas_hoy))
                
                for i, cita in enumerate(citas_hoy, 1):
                    mensaje += f"{i}. *{cita.nombre_cliente}* - {cita.hora}\n"
                
                mensaje += "\n¡Que tengas un día productivo!"""
            
            self.whatsapp.send_text_message(usuario_whatsapp, mensaje)
            print(f"resumen diario enviado a {usuario_whatsapp}")
        except Exception as e:
            print(f"error enviado resumen diario a {usuario_whatsapp}: {e}")

    def send_custom_reminder(self,cita_id:str,mensaje_personalizado:str=None):
        try:
            cita=self.cita_repo.obtener_cita(cita_id)
            if not cita:
                print(f"cita {cita_id} no encontrada")
                return False
            if mensaje_personalizado:
                mensaje=mensaje_personalizado
            else:
                fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
                mensaje = f"""*RECORDATORIO ESPECIAL*

                {cita.nombre_cliente}
                {fecha_formatted} - {cita.hora}
                {cita.descripcion}

                Este es un recordatorio especial sobre tu cita próxima."""
            result=self.whatsapp.send_text_message(cita.usuario_whatsapp,mensaje)
            return result is not None
        except Exception as e:
            print(f"error enviando recordatorio personalizado: {e}")
            return False

    # J.RF14: Enviar resumen semanal a pacientes
    def send_weekly_summaries(self):
        try:
            from database.models import PacienteRepository
            from google.cloud.firestore import SERVER_TIMESTAMP
            
            paciente_repo = PacienteRepository()
            db = self.cita_repo.db
            
            # Obtener todos los pacientes activos
            pacientes_ref = db.collection('pacientes')
            pacientes = []
            for doc in pacientes_ref.stream():
                paciente_data = doc.to_dict()
                telefono = paciente_data.get('telefono')
                if telefono:
                    pacientes.append({
                        'uid': doc.id,
                        'telefono': telefono,
                        'nombre': paciente_data.get('nombre', ''),
                        'apellidos': paciente_data.get('apellidos', ''),
                        'nombreCompleto': paciente_data.get('nombreCompleto', ''),
                        'lastLogin': paciente_data.get('lastLogin'),
                    })
            
            print(f"J.RF14: Enviando resúmenes semanales a {len(pacientes)} pacientes")
            
            # Calcular fechas para la semana
            now = datetime.now()
            semana_siguiente = now + timedelta(days=7)
            
            for paciente in pacientes:
                try:
                    self._send_weekly_summary_to_patient(paciente, now, semana_siguiente)
                except Exception as e:
                    print(f"Error enviando resumen semanal a {paciente.get('telefono')}: {e}")
            
            print(f"J.RF14: Resúmenes semanales enviados")
            
        except Exception as e:
            print(f"Error en send_weekly_summaries: {e}")
            import traceback
            traceback.print_exc()

    # J.RF14: Enviar resumen semanal a un paciente específico
    def _send_weekly_summary_to_patient(self, paciente: dict, now: datetime, semana_siguiente: datetime):
        try:
            paciente_uid = paciente['uid']
            telefono = paciente['telefono']
            nombre = paciente.get('nombreCompleto') or f"{paciente.get('nombre', '')} {paciente.get('apellidos', '')}".strip()
            
            # Obtener citas próximas (próximos 7 días)
            citas_proximas = self.cita_repo.obtener_citas_paciente(paciente_uid)
            citas_semana = [
                c for c in citas_proximas 
                if c.fecha and c.estado in ['confirmada', 'programada']
            ]
            
            # Filtrar citas de la próxima semana
            citas_semana = [
                c for c in citas_semana
                if c.fecha and now.strftime('%Y-%m-%d') <= c.fecha <= semana_siguiente.strftime('%Y-%m-%d')
            ]
            
            # Obtener citas completadas sin historial médico (últimos 30 días)
            db = self.cita_repo.db
            citas_completadas = db.collection('pacientes').document(paciente_uid).collection('citas')\
                .where('estado', '==', 'completada')\
                .where('fecha', '>=', now - timedelta(days=30))\
                .stream()
            
            citas_sin_historial = []
            for cita_doc in citas_completadas:
                cita_data = cita_doc.to_dict()
                # Verificar si tiene historial médico asociado
                historial_ref = db.collection('pacientes').document(paciente_uid).collection('historialMedico')\
                    .where('citaId', '==', cita_doc.id).limit(1).get()
                if not list(historial_ref):
                    citas_sin_historial.append(cita_data)
            
            # Obtener citas completadas sin reseña (últimos 30 días)
            citas_sin_resena = []
            for cita_doc in db.collection('pacientes').document(paciente_uid).collection('citas')\
                .where('estado', '==', 'completada')\
                .where('fecha', '>=', now - timedelta(days=30))\
                .stream():
                cita_data = cita_doc.to_dict()
                # Verificar si tiene reseña
                reseñas_ref = db.collection('resenas')\
                    .where('pacienteId', '==', paciente_uid)\
                    .where('citaId', '==', cita_doc.id).limit(1).get()
                if not list(reseñas_ref):
                    citas_sin_resena.append(cita_data)
            
            # Verificar última vez que inició sesión
            last_login = paciente.get('lastLogin')
            necesita_actualizar_datos = False
            if last_login:
                if hasattr(last_login, 'timestamp'):
                    last_login_date = last_login.timestamp().to_datetime()
                elif hasattr(last_login, 'to_datetime'):
                    last_login_date = last_login.to_datetime()
                else:
                    last_login_date = None
                
                if last_login_date:
                    dias_sin_login = (now - last_login_date.replace(tzinfo=None)).days
                    if dias_sin_login > 30:
                        necesita_actualizar_datos = True
            else:
                # Si nunca ha iniciado sesión, también recordarle
                necesita_actualizar_datos = True
            
            # Construir mensaje de resumen semanal
            mensaje = f"""*RESUMEN SEMANAL - Densora*

Hola {nombre}!

"""
            
            # Próximas citas
            if citas_semana:
                mensaje += f"""*Tus próximas citas esta semana:*

"""
                for i, cita in enumerate(citas_semana[:5], 1):  # Máximo 5 citas
                    fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y') if isinstance(cita.fecha, str) else cita.fecha.strftime('%d/%m/%Y')
                    mensaje += f"{i}. {fecha_formatted} - {cita.horaInicio or cita.hora}\n"
                    mensaje += f"   {cita.dentistaName or 'Dentista'}\n"
                    mensaje += f"   {cita.motivo or cita.descripcion or 'Consulta'}\n\n"
            else:
                mensaje += """*Próximas citas:* No tienes citas programadas esta semana.

"""
            
            # Historial pendiente
            if citas_sin_historial:
                mensaje += f"""*Historial médico pendiente:*
Tienes {len(citas_sin_historial)} cita(s) completada(s) sin historial médico actualizado.
Visita tu perfil para actualizar tu historial.

"""
            
            # Reseñas pendientes
            if citas_sin_resena:
                mensaje += f"""*Reseñas pendientes:*
Tienes {len(citas_sin_resena)} cita(s) completada(s) sin reseña.
Escribe "calificar" para dejar tu opinión.

"""
            
            # Recordatorio de actualización de datos
            if necesita_actualizar_datos:
                mensaje += """*Actualiza tus datos:*
Hace más de 30 días que no inicias sesión.
Visita nuestra web para mantener tu información actualizada.

"""
            
            mensaje += f"""*Visita nuestra web:* http://localhost:4321

¡Que tengas una excelente semana!"""
            
            # Enviar mensaje
            self.whatsapp.send_text_message(telefono, mensaje)
            print(f"J.RF14: Resumen semanal enviado a {telefono}")
            
        except Exception as e:
            print(f"Error enviando resumen semanal a paciente {paciente.get('telefono')}: {e}")
            import traceback
            traceback.print_exc()

notidicaciones_service=NotificacionesService()