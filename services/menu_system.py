"""
SISTEMA DE MENÚS ESTRUCTURADO
Sistema completo de menús para todas las funcionalidades del bot
Sin IA/ML, solo menús fijos y opciones estructuradas
"""

from services.actions_service import ActionsService
from services.citas_service import CitasService
from services.firebase_functions_service import FirebaseFunctionsService
from typing import Dict, Optional
from datetime import datetime, timedelta

class MenuSystem:
    """
    Sistema de menús estructurado para el bot
    Todas las funcionalidades se acceden mediante números y opciones fijas
    """
    
    def __init__(self):
        self.actions_service = ActionsService()
        self.citas_service = CitasService()
        self.firebase_service = FirebaseFunctionsService()  # Servicio que usa la misma estructura que la web
    
    def get_main_menu(self, language: str = 'es') -> str:
        """Menú principal"""
        if language == 'en':
            return """🦷 *Densora - Main Menu*

What would you like to do?

*1.* Schedule Appointment
*2.* View My Appointments
*3.* Reschedule Appointment
*4.* Cancel Appointment
*5.* Medical History
*6.* Reviews & Ratings
*7.* Help & Support
*0.* Exit

Type the *number* of the option you want."""
        
        return """🦷 *Densora - Menú Principal*

¿Qué te gustaría hacer?

*1.* Agendar Cita
*2.* Ver Mis Citas
*3.* Reagendar Cita
*4.* Cancelar Cita
*5.* Historial Médico
*6.* Reseñas y Calificaciones
*7.* Ayuda y Soporte
*0.* Salir

Escribe el *número* de la opción que deseas."""
    
    def process_message(self, session_id: str, message: str, 
                       context: Dict, user_id: str = None, 
                       phone: str = None) -> Dict:
        """
        Procesa mensajes en modo menú
        Solo acepta números y comandos predefinidos
        """
        message_clean = message.strip().lower()
        current_step = context.get('step', 'menu_principal')
        print(f"[MENU_SYSTEM] process_message - session_id={session_id}, message='{message}', current_step={current_step}, user_id={user_id}, phone={phone}")
        
        # Si es "menu" o "menú", volver al menú principal
        if message_clean in ['menu', 'menú', 'inicio', 'start', '0']:
            context['step'] = 'menu_principal'
            return {
                'response': self.get_main_menu(context.get('language', 'es')),
                'action': 'show_menu',
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
        
        # Si es un número, procesarlo según el paso actual
        if message_clean.isdigit():
            button_num = int(message_clean)
            print(f"[MENU_SYSTEM] Mensaje numérico detectado: {button_num}, step actual: {current_step}")
            result = self._handle_numeric_input(session_id, button_num, context, user_id, phone)
            print(f"[MENU_SYSTEM] Resultado de _handle_numeric_input: tiene response={bool(result.get('response'))}")
            return result
        
        # Si no es número ni comando reconocido, mostrar menú y pedir número
        print(f"[MENU_SYSTEM] Mensaje no reconocido, mostrando menú por defecto")
        return {
            'response': f"Por favor, usa números para navegar.\n\n{self.get_main_menu(context.get('language', 'es'))}",
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_numeric_input(self, session_id: str, button_num: int,
                             context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja entrada numérica según el paso actual"""
        current_step = context.get('step', 'menu_principal')
        print(f"[MENU_SYSTEM] Procesando entrada numérica: button_num={button_num}, current_step={current_step}")
        
        # Menú principal
        if current_step == 'menu_principal' or current_step == 'inicial':
            if button_num == 1:
                print(f"[MENU_SYSTEM] Opción 1 seleccionada - Agendar cita")
                result = self._handle_schedule_appointment(session_id, context, user_id, phone)
                print(f"[MENU_SYSTEM] Resultado de _handle_schedule_appointment: {result.get('response', '')[:100] if result.get('response') else 'SIN RESPUESTA'}")
                return result
            elif button_num == 2:
                return self._handle_view_appointments(context, user_id, phone)
            elif button_num == 3:
                return self._handle_reschedule_appointment(session_id, context, user_id, phone)
            elif button_num == 4:
                return self._handle_cancel_appointment(session_id, context, user_id, phone)
            elif button_num == 5:
                return self._handle_medical_history(context, user_id, phone)
            elif button_num == 6:
                return self._handle_reviews(context, user_id, phone)
            elif button_num == 7:
                return self._handle_help(context)
            elif button_num == 0:
                return {
                    'response': '¡Gracias por usar Densora! 👋\n\nEscribe "menu" cuando quieras volver.',
                    'action': 'exit',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 0 al 7.\n\n{self.get_main_menu()}',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        
        # Seleccionando fecha para agendar
        elif current_step == 'seleccionando_fecha_agendar':
            fechas = context.get('fechas_disponibles', [])
            if fechas and 0 <= button_num - 1 < len(fechas):
                fecha_seleccionada = fechas[button_num - 1]
                # Guardar como string para consistencia
                if hasattr(fecha_seleccionada, 'strftime'):
                    fecha_str = fecha_seleccionada.strftime('%Y-%m-%d')
                else:
                    fecha_str = str(fecha_seleccionada)
                context['fecha_seleccionada'] = fecha_seleccionada
                context['step'] = 'seleccionando_hora_agendar'
                return self._show_available_times(context, user_id, phone, fecha_seleccionada)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(fechas)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando hora para agendar
        elif current_step == 'seleccionando_hora_agendar':
            horarios = context.get('horarios_disponibles', [])
            if horarios and 0 <= button_num - 1 < len(horarios):
                hora_seleccionada = horarios[button_num - 1]
                context['hora_seleccionada'] = hora_seleccionada
                context['step'] = 'confirmando_agendamiento'
                return self._confirm_appointment(session_id, context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(horarios)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando cita para reagendar
        elif current_step == 'seleccionando_cita_reagendar':
            citas = context.get('citas_disponibles', [])
            if citas and 0 <= button_num - 1 < len(citas):
                cita_seleccionada = citas[button_num - 1]
                context['cita_id_reagendar'] = cita_seleccionada['id']
                context['step'] = 'seleccionando_fecha_reagendar'
                return self._show_available_dates_for_reschedule(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(citas)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando fecha para reagendar
        elif current_step == 'seleccionando_fecha_reagendar':
            fechas = context.get('fechas_disponibles', [])
            if fechas and 0 <= button_num - 1 < len(fechas):
                fecha_seleccionada = fechas[button_num - 1]
                # Guardar como string para consistencia
                if hasattr(fecha_seleccionada, 'strftime'):
                    fecha_str = fecha_seleccionada.strftime('%Y-%m-%d')
                else:
                    fecha_str = str(fecha_seleccionada)
                context['fecha_seleccionada'] = fecha_seleccionada
                context['step'] = 'seleccionando_hora_reagendar'
                return self._show_available_times(context, user_id, phone, fecha_seleccionada)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(fechas)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando hora para reagendar
        elif current_step == 'seleccionando_hora_reagendar':
            horarios = context.get('horarios_disponibles', [])
            if horarios and 0 <= button_num - 1 < len(horarios):
                hora_seleccionada = horarios[button_num - 1]
                context['hora_seleccionada'] = hora_seleccionada
                context['step'] = 'confirmando_reagendamiento'
                return self._confirm_reschedule(session_id, context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(horarios)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando cita para cancelar
        elif current_step == 'seleccionando_cita_cancelar':
            citas = context.get('citas_disponibles', [])
            if citas and 0 <= button_num - 1 < len(citas):
                cita_seleccionada = citas[button_num - 1]
                context['cita_id_cancelar'] = cita_seleccionada['id']
                context['step'] = 'confirmando_cancelacion'
                return self._confirm_cancellation(session_id, context, user_id, phone, cita_seleccionada)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(citas)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando cancelación
        elif current_step == 'confirmando_cancelacion':
            if button_num == 1:  # Sí, confirmar
                return self._execute_cancellation(session_id, context, user_id, phone)
            elif button_num == 2:  # No, cancelar
                context['step'] = 'menu_principal'
                return {
                    'response': 'Cancelación cancelada. Tu cita se mantiene programada.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Por favor selecciona:\n*1.* Sí, cancelar cita\n*2.* No, mantener cita',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Si no coincide con ningún paso, volver al menú
        context['step'] = 'menu_principal'
        return {
            'response': f'Opción no válida en este contexto.\n\n{self.get_main_menu()}',
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_schedule_appointment(self, session_id: str, context: Dict,
                                    user_id: str, phone: str) -> Dict:
        """Opción 1: Agendar cita - Usa la misma estructura que la web"""
        print(f"[MENU_SYSTEM] _handle_schedule_appointment - user_id={user_id}, phone={phone}")
        context['step'] = 'seleccionando_fecha_agendar'
        
        # Obtener fechas disponibles usando el servicio que accede a la misma estructura que la web
        try:
            print(f"[MENU_SYSTEM] Obteniendo fechas disponibles...")
            fechas = self.firebase_service.get_available_dates(user_id=user_id, phone=phone, count=5)
            print(f"[MENU_SYSTEM] Fechas obtenidas: {len(fechas) if fechas else 0}, tipo: {type(fechas)}")
            context['fechas_disponibles'] = fechas or []
            
            if not fechas or len(fechas) == 0:
                return {
                    'response': 'Lo siento, no hay fechas disponibles en este momento.\n\nPor favor, contacta directamente con el consultorio o intenta más tarde.\n\nEscribe "menu" para volver al menú principal.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Formatear fechas
            fechas_texto = '\n'.join([
                f'*{i+1}.* {fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else str(fecha)}' 
                for i, fecha in enumerate(fechas)
            ])
            
            return {
                'response': f'📅 *Agendar Nueva Cita*\n\nSelecciona una fecha disponible:\n\n{fechas_texto}\n\nEscribe el *número* de la fecha que deseas.',
                'action': 'show_dates',
                'next_step': 'seleccionando_fecha_agendar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error obteniendo fechas: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al obtener fechas disponibles. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_view_appointments(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opción 2: Ver citas - Usa la misma estructura que la web"""
        try:
            # Usar el servicio que accede a la misma estructura que la web
            citas = self.firebase_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            
            if not citas:
                return {
                    'response': 'No tienes citas programadas en este momento.\n\nEscribe "menu" para volver al menú principal.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            citas_texto = '\n'.join([
                f'*{i+1}.* {cita.get("fecha", "N/A")} {cita.get("hora", "N/A")} - {cita.get("dentista", "Dr. García")}'
                for i, cita in enumerate(citas[:5])
            ])
            
            return {
                'response': f'📋 *Tus Próximas Citas:*\n\n{citas_texto}\n\nEscribe "menu" para volver al menú principal.',
                'action': 'show_appointments',
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo citas: {e}")
            return {
                'response': 'Error al obtener tus citas. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_reschedule_appointment(self, session_id: str, context: Dict,
                                      user_id: str, phone: str) -> Dict:
        """Opción 3: Reagendar cita - Usa la misma estructura que la web"""
        context['step'] = 'seleccionando_cita_reagendar'
        
        try:
            # Usar el servicio que accede a la misma estructura que la web
            citas = self.firebase_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            context['citas_disponibles'] = citas
            
            if not citas:
                return {
                    'response': 'No tienes citas programadas para reagendar.\n\nEscribe "menu" para volver al menú principal.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            citas_texto = '\n'.join([
                f'*{i+1}.* {cita.get("fecha", "N/A")} {cita.get("hora", "N/A")} - {cita.get("dentista", "Dr. García")}'
                for i, cita in enumerate(citas[:5])
            ])
            
            return {
                'response': f'🔄 *Reagendar Cita*\n\nSelecciona la cita que deseas reagendar:\n\n{citas_texto}\n\nEscribe el *número* de la cita.',
                'action': 'show_appointments_to_reschedule',
                'next_step': 'seleccionando_cita_reagendar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo citas para reagendar: {e}")
            return {
                'response': 'Error al obtener tus citas. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_cancel_appointment(self, session_id: str, context: Dict,
                                  user_id: str, phone: str) -> Dict:
        """Opción 4: Cancelar cita - Usa la misma estructura que la web"""
        context['step'] = 'seleccionando_cita_cancelar'
        
        try:
            # Usar el servicio que accede a la misma estructura que la web
            citas = self.firebase_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            context['citas_disponibles'] = citas
            
            if not citas:
                return {
                    'response': 'No tienes citas programadas para cancelar.\n\nEscribe "menu" para volver al menú principal.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            citas_texto = '\n'.join([
                f'*{i+1}.* {cita.get("fecha", "N/A")} {cita.get("hora", "N/A")} - {cita.get("dentista", "Dr. García")}'
                for i, cita in enumerate(citas[:5])
            ])
            
            return {
                'response': f'❌ *Cancelar Cita*\n\nSelecciona la cita que deseas cancelar:\n\n{citas_texto}\n\nEscribe el *número* de la cita.',
                'action': 'show_appointments_to_cancel',
                'next_step': 'seleccionando_cita_cancelar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo citas para cancelar: {e}")
            return {
                'response': 'Error al obtener tus citas. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_medical_history(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opción 5: Historial médico"""
        web_url = 'https://www.densora.com'  # TODO: obtener de config
        return {
            'response': f'📋 *Historial Médico*\n\nPara acceder a tu historial médico, visita:\n\n🔗 {web_url}/historialMedico\n\nEscribe "menu" para volver al menú principal.',
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_reviews(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opción 6: Reseñas y calificaciones"""
        web_url = 'https://www.densora.com'  # TODO: obtener de config
        return {
            'response': f'⭐ *Reseñas y Calificaciones*\n\nPara dejar una reseña o ver tus calificaciones, visita:\n\n🔗 {web_url}/mis-resenas\n\nEscribe "menu" para volver al menú principal.',
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_help(self, context: Dict) -> Dict:
        """Opción 7: Ayuda y soporte"""
        return {
            'response': f'❓ *Ayuda y Soporte*\n\n{self.get_main_menu()}\n\n*Contacto:*\n📧 soporte@densora.com\n📱 +52 55 1234 5678\n\n*Horario:*\nLun-Vie: 9:00 AM - 6:00 PM\nSáb: 9:00 AM - 2:00 PM',
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _show_available_times(self, context: Dict, user_id: str, phone: str, fecha) -> Dict:
        """Muestra horarios disponibles para una fecha - Usa la misma estructura que la web"""
        try:
            # Convertir fecha string a datetime si es necesario
            if isinstance(fecha, str):
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            else:
                fecha_dt = fecha
            
            # Usar el servicio que accede a la misma estructura que la web
            horarios = self.firebase_service.get_available_times(user_id=user_id, phone=phone, fecha=fecha_dt)
            context['horarios_disponibles'] = horarios
            
            if not horarios:
                return {
                    'response': 'Lo siento, no hay horarios disponibles para esta fecha.\n\nEscribe "menu" para volver al menú principal.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            horarios_texto = '\n'.join([f'*{i+1}.* {hora}' for i, hora in enumerate(horarios)])
            
            return {
                'response': f'🕐 *Selecciona un Horario*\n\nHorarios disponibles:\n\n{horarios_texto}\n\nEscribe el *número* del horario que deseas.',
                'action': 'show_times',
                'next_step': context['step'],
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo horarios: {e}")
            return {
                'response': 'Error al obtener horarios disponibles. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_dates_for_reschedule(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra fechas disponibles para reagendar - Usa la misma estructura que la web"""
        try:
            # Usar el servicio que accede a la misma estructura que la web
            fechas = self.firebase_service.get_available_dates(user_id=user_id, phone=phone, count=5)
            context['fechas_disponibles'] = fechas
            
            if not fechas:
                return {
                    'response': 'Lo siento, no hay fechas disponibles para reagendar.\n\nEscribe "menu" para volver al menú principal.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Formatear fechas
            fechas_texto = '\n'.join([
                f'*{i+1}.* {fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else str(fecha)}' 
                for i, fecha in enumerate(fechas)
            ])
            
            return {
                'response': f'📅 *Selecciona Nueva Fecha*\n\nFechas disponibles:\n\n{fechas_texto}\n\nEscribe el *número* de la fecha que deseas.',
                'action': 'show_dates',
                'next_step': 'seleccionando_fecha_reagendar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo fechas: {e}")
            return {
                'response': 'Error al obtener fechas disponibles. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _confirm_appointment(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Confirma el agendamiento - Usa la misma estructura que la web"""
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        
        try:
            if not user_id:
                return {
                    'response': 'Error: No se encontró tu cuenta. Por favor regístrate primero.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Convertir fecha a datetime si es string
            if isinstance(fecha, str):
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            else:
                fecha_dt = fecha
            
            # Crear cita usando el servicio que usa la misma estructura que la web
            result = self.firebase_service.create_appointment(
                user_id,
                {
                    'fecha': fecha_dt.strftime('%Y-%m-%d'),
                    'hora': hora,
                    'motivo': 'Consulta general'
                }
            )
            
            if result.get('success'):
                context['step'] = 'menu_principal'
                fecha_str = fecha_dt.strftime('%d/%m/%Y') if hasattr(fecha_dt, 'strftime') else str(fecha_dt)
                return {
                    'response': f'✅ *Cita Agendada Exitosamente*\n\n📅 Fecha: {fecha_str}\n🕐 Hora: {hora}\n\nRecibirás un recordatorio 24h antes.\n\nEscribe "menu" para volver al menú principal.',
                    'action': 'appointment_created',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                return {
                    'response': f'Error al agendar la cita: {error_msg}\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error confirmando cita: {e}")
            return {
                'response': 'Error al confirmar la cita. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _confirm_reschedule(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Confirma el reagendamiento - Usa la misma estructura que la web"""
        cita_id = context.get('cita_id_reagendar')
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        
        try:
            if not user_id:
                return {
                    'response': 'Error: No se encontró tu cuenta.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Convertir fecha a datetime si es string
            if isinstance(fecha, str):
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            else:
                fecha_dt = fecha
            
            # Reagendar usando el servicio que usa la misma estructura que la web
            result = self.firebase_service.reschedule_appointment(
                user_id,
                cita_id,
                fecha_dt,
                hora
            )
            
            if result.get('success'):
                context['step'] = 'menu_principal'
                fecha_str = fecha_dt.strftime('%d/%m/%Y') if hasattr(fecha_dt, 'strftime') else str(fecha_dt)
                return {
                    'response': f'✅ *Cita Reagendada Exitosamente*\n\n📅 Nueva Fecha: {fecha_str}\n🕐 Nueva Hora: {hora}\n\nRecibirás un recordatorio 24h antes.\n\nEscribe "menu" para volver al menú principal.',
                    'action': 'appointment_rescheduled',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                return {
                    'response': f'Error al reagendar la cita: {error_msg}\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error confirmando reagendamiento: {e}")
            return {
                'response': 'Error al confirmar el reagendamiento. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _confirm_cancellation(self, session_id: str, context: Dict, user_id: str, 
                            phone: str, cita: Dict) -> Dict:
        """Muestra confirmación de cancelación"""
        return {
            'response': f'⚠️ *Confirmar Cancelación*\n\n¿Estás seguro de que deseas cancelar esta cita?\n\n📅 Fecha: {cita.get("fecha", "N/A")}\n🕐 Hora: {cita.get("hora", "N/A")}\n👨‍⚕️ Dentista: {cita.get("dentista", "Dr. García")}\n\n*1.* Sí, cancelar cita\n*2.* No, mantener cita',
            'action': None,
            'next_step': 'confirmando_cancelacion',
            'mode': 'menu'
        }
    
    def _execute_cancellation(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Ejecuta la cancelación - Usa la misma estructura que la web"""
        cita_id = context.get('cita_id_cancelar')
        
        try:
            if not user_id:
                return {
                    'response': 'Error: No se encontró tu cuenta.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Cancelar usando el servicio que usa la misma estructura que la web
            result = self.firebase_service.cancel_appointment(user_id, cita_id)
            
            if result.get('success'):
                context['step'] = 'menu_principal'
                return {
                    'response': '✅ *Cita Cancelada Exitosamente*\n\nTu cita ha sido cancelada. Recibirás una confirmación por WhatsApp.\n\nEscribe "menu" para volver al menú principal.',
                    'action': 'appointment_cancelled',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                return {
                    'response': f'Error al cancelar la cita: {error_msg}\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error ejecutando cancelación: {e}")
            return {
                'response': 'Error al cancelar la cita. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }

