from datetime import datetime, timedelta
import pytz
from config import Config

class DateUtils:
    @staticmethod
    def get_timezone():
        return pytz.timezone(Config.TIMEZONE)
    
    @staticmethod
    def get_current_datetime():
        tz = DateUtils.get_timezone()
        return datetime.now(tz)
    
    @staticmethod
    def format_date_for_display(date_string: str) -> str:
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        except ValueError:
            return date_string
    
    @staticmethod
    def format_date_for_database(date_string: str) -> str:
        try:
            date_obj = datetime.strptime(date_string, '%d/%m/%Y')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return date_string
    
    @staticmethod
    def is_valid_date(date_string: str, format: str = '%Y-%m-%d') -> bool:
        try:
            datetime.strptime(date_string, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_future_date(date_string: str) -> bool:
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d').date()
            today = DateUtils.get_current_datetime().date()
            return date_obj > today
        except ValueError:
            return False
    
    @staticmethod
    def is_business_day(date_string: str) -> bool:
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            return date_obj.weekday() < 5 
        except ValueError:
            return False
    
    @staticmethod
    def get_next_business_days(count: int = 7) -> list:
        business_days = []
        current_date = DateUtils.get_current_datetime().date()
        
        while len(business_days) < count:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Es día laborable
                business_days.append(current_date.strftime('%Y-%m-%d'))
        
        return business_days
    
    @staticmethod
    def is_valid_time(time_string: str) -> bool:
        try:
            datetime.strptime(time_string, '%H:%M')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_business_hours(time_string: str) -> bool:
        try:
            time_obj = datetime.strptime(time_string, '%H:%M').time()
            start_time = datetime.strptime('09:00', '%H:%M').time()
            end_time = datetime.strptime('18:00', '%H:%M').time()
            
            return start_time <= time_obj <= end_time
        except ValueError:
            return False
    
    @staticmethod
    def get_available_times() -> list:
        return [
            '09:00', '09:30', '10:00', '10:30',
            '11:00', '11:30', '12:00', '12:30',
            '14:00', '14:30', '15:00', '15:30',
            '16:00', '16:30', '17:00', '17:30'
        ]
    
    @staticmethod
    def time_until_appointment(fecha: str, hora: str) -> dict:
        try:
            fecha_hora_cita = datetime.strptime(f"{fecha} {hora}", '%Y-%m-%d %H:%M')
            ahora = DateUtils.get_current_datetime().replace(tzinfo=None)
            
            if fecha_hora_cita <= ahora:
                return {'past': True}
            
            diferencia = fecha_hora_cita - ahora
            dias = diferencia.days
            horas, remainder = divmod(diferencia.seconds, 3600)
            minutos, _ = divmod(remainder, 60)
            
            return {
                'past': False,
                'days': dias,
                'hours': horas,
                'minutes': minutos,
                'total_minutes': diferencia.total_seconds() / 60
            }
            
        except ValueError:
            return {'past': True}
    
    @staticmethod
    def get_week_day_name(date_string: str) -> str:
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            return days[date_obj.weekday()]
        except ValueError:
            return 'Desconocido'
    
    @staticmethod
    def get_month_name(date_string: str) -> str:
        try:
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            months = [
                'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
            ]
            return months[date_obj.month - 1]
        except ValueError:
            return 'Desconocido'
    
    @staticmethod
    def format_date_complete(date_string: str) -> str:
        try:
            day_name = DateUtils.get_week_day_name(date_string)
            date_obj = datetime.strptime(date_string, '%Y-%m-%d')
            month_name = DateUtils.get_month_name(date_string)
            
            return f"{day_name} {date_obj.day} de {month_name} de {date_obj.year}"
        except ValueError:
            return date_string
    
    @staticmethod
    def is_appointment_soon(fecha: str, hora: str, hours_threshold: int = 24) -> bool:
        time_info = DateUtils.time_until_appointment(fecha, hora)
        
        if time_info.get('past', False):
            return False
        
        total_hours = (time_info['days'] * 24) + time_info['hours']
        return total_hours <= hours_threshold