from apscheduler.schedulers.background import BackgroundScheduler
from database.models import cita
from services.whatsapp_service import WhatsAppService
from datetime import datetime, timedelta
import pytz
from config import Config
class NotificacionesService:
    def __init__(self):
        self.cita_repo = CitaRepository()
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
            
            mensaje = f"""🔔 *RECORDATORIO DE CITA*

            👤 *Paciente:* {cita.nombre_cliente}
            📅 *Mañana:* {fecha_formatted}
            ⏰ *Hora:* {cita.hora}
            📝 *Motivo:* {cita.descripcion}

            📍 No olvides confirmar tu asistencia.
            💬 Responde *CONFIRMO* si asistirás o *CANCELAR* si necesitas cancelar.

            ¡Te esperamos! 👩‍⚕️"""
            
            result = self.whatsapp.send_text_message(cita.usuario_whatsapp, mensaje)
            
            if result:
                print(f"se envio el reminder de 24 horas {cita.id}")
            else:
                print(f"error enviando el reminder de 24 horas {cita.id}")
                
        except Exception as e:
            print(f"error canijo en el reminder de 24 horas: {e}")
    def send_2_hour_reminder(self, cita):
        try:
            mensaje = f"""⏰ *RECORDATORIO URGENTE*

            👤 *{cita.nombre_cliente}*
            🕐 Tu cita es en *2 horas* ({cita.hora})

            📍 *¿Ya estás preparado/a?*
            🚗 Recuerda considerar el tiempo de traslado.

            ¡Nos vemos pronto! 👋"""
            
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
                mensaje = f"""🌅 *BUENOS DÍAS*

                📋 Tienes *1 cita* programada para hoy:

                👤 *{cita.nombre_cliente}*
                ⏰ *{cita.hora}*
                📝 {cita.descripcion}

                ¡Que tengas un excelente día! ☀️"""
            
            else:
                mensaje = "🌅 *BUENOS DÍAS*\n\n📋 Tienes *{} citas* programadas para hoy:\n\n".format(len(citas_hoy))
                
                for i, cita in enumerate(citas_hoy, 1):
                    mensaje += f"{i}. *{cita.nombre_cliente}* - {cita.hora}\n"
                
                mensaje += "\n¡Que tengas un día productivo! ✨"
            
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
                mensaje = f"""📢 *RECORDATORIO ESPECIAL*

                👤 {cita.nombre_cliente}
                📅 {fecha_formatted} - {cita.hora}
                📝 {cita.descripcion}

                Este es un recordatorio especial sobre tu cita próxima."""
            result=self.whatsapp.send_text_message(cita.usuario_whatsapp,mensaje)
            return result is not None
        except Exception as e:
            print(f"error enviando recordatorio personalizado: {e}")
            return False
notidicaciones_service=NotificacionesService()