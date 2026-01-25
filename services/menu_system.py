"""
SISTEMA DE MENÚS ESTRUCTURADO
Sistema completo de menús para todas las funcionalidades del bot
Sin IA/ML, solo menús fijos y opciones estructuradas
"""

from services.actions_service import ActionsService
from services.citas_service import CitasService
from services.firebase_functions_service import FirebaseFunctionsService
from database.database import FirebaseConfig
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
        self.db = FirebaseConfig.get_db()  # Acceso directo a Firestore
    
    def get_main_menu(self, language: str = 'es') -> str:
        """Menú principal"""
        if language == 'en':
            return """*Densora - Main Menu*

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
        
        return """*Densora - Menú Principal*

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
        
        # Si está verificando OTP, tratar el mensaje como código OTP
        if current_step == 'verificando_otp':
            # Verificar si es un código OTP (6 dígitos)
            if message_clean.isdigit() and len(message_clean) == 6:
                return self._verify_otp_and_confirm(session_id, context, user_id, phone, message_clean)
            else:
                return {
                    'response': 'Por favor ingresa el código OTP de 6 dígitos que recibiste por WhatsApp.\n\nSi no lo recibiste, escribe "reenviar" para solicitar uno nuevo.',
                    'action': None,
                    'next_step': current_step,
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
                    'response': '¡Gracias por usar Densora!\n\nEscribe "menu" cuando quieras volver.',
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
        
        # Seleccionando consultorio (NUEVO PASO)
        elif current_step == 'seleccionando_consultorio':
            consultorios = context.get('consultorios_disponibles', [])
            if button_num == 9 or button_num == 0:
                # Volver al menú principal
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif consultorios and 0 <= button_num - 1 < len(consultorios):
                consultorio_seleccionado = consultorios[button_num - 1]
                context['consultorio_id'] = consultorio_seleccionado['id']
                context['consultorio_name'] = consultorio_seleccionado['nombre']
                context['step'] = 'seleccionando_dentista'
                # Mostrar dentistas de este consultorio
                return self._show_available_dentists(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Selecciona un número del 1 al {len(consultorios)} o *0* para cancelar.' if consultorios else 'No hay consultorios disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando dentista (NUEVO PASO)
        elif current_step == 'seleccionando_dentista':
            dentistas = context.get('dentistas_disponibles', [])
            if button_num == 9:
                # Volver a selección de consultorio
                return self._handle_schedule_appointment(session_id, context, user_id, phone)
            elif button_num == 0:
                # Cancelar y volver al menú principal
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif dentistas and 0 <= button_num - 1 < len(dentistas):
                dentista_seleccionado = dentistas[button_num - 1]
                context['dentista_id'] = dentista_seleccionado['id']
                context['dentista_name'] = dentista_seleccionado['nombre']
                context['step'] = 'seleccionando_servicio'
                # Mostrar servicios para este dentista/consultorio
                return self._show_available_services(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Selecciona un número del 1 al {len(dentistas)}, *9* para volver o *0* para cancelar.' if dentistas else 'No hay dentistas disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando servicio/tratamiento para agendar
        elif current_step == 'seleccionando_servicio':
            tratamientos = context.get('tratamientos_disponibles', [])
            if button_num == 9:
                # Volver a selección de dentista
                return self._show_available_dentists(context, user_id, phone)
            elif button_num == 0:
                # Cancelar y volver al menú principal
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif tratamientos and 0 <= button_num - 1 < len(tratamientos):
                tratamiento_seleccionado = tratamientos[button_num - 1]
                context['tratamiento_seleccionado'] = tratamiento_seleccionado
                context['step'] = 'seleccionando_fecha_agendar'
                # Obtener fechas disponibles
                return self._show_available_dates_for_appointment(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Selecciona un número del 1 al {len(tratamientos)}, *9* para volver o *0* para cancelar.' if tratamientos else 'No hay tratamientos disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando fecha para agendar
        elif current_step == 'seleccionando_fecha_agendar':
            fechas = context.get('fechas_disponibles', [])
            if button_num == 9:
                # Volver a selección de servicio
                return self._show_available_services(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif fechas and 0 <= button_num - 1 < len(fechas):
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
                    'response': f'Opción inválida. Selecciona un número del 1 al {len(fechas)}, *9* para volver o *0* para cancelar.' if fechas else 'No hay fechas disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando hora para agendar
        elif current_step == 'seleccionando_hora_agendar':
            horarios = context.get('horarios_disponibles', [])
            if button_num == 9:
                # Volver a selección de fecha
                return self._show_available_dates_for_appointment(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif horarios and 0 <= button_num - 1 < len(horarios):
                slot_seleccionado = horarios[button_num - 1]
                # Extraer horaInicio del slot (puede ser dict o string)
                if isinstance(slot_seleccionado, dict):
                    hora_seleccionada = slot_seleccionado.get('horaInicio', slot_seleccionado.get('inicio', ''))
                else:
                    hora_seleccionada = str(slot_seleccionado)
                context['hora_seleccionada'] = hora_seleccionada
                context['step'] = 'seleccionando_metodo_pago'
                return self._show_payment_methods(context)
            else:
                return {
                    'response': f'Opción inválida. Selecciona un número del 1 al {len(horarios)}, *9* para volver o *0* para cancelar.' if horarios else 'No hay horarios disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando método de pago
        elif current_step == 'seleccionando_metodo_pago':
            metodos_pago = [
                {'id': 'efectivo', 'nombre': 'Efectivo', 'descripcion': 'Pago al momento de la cita'},
                {'id': 'stripe', 'nombre': 'Tarjeta (Stripe)', 'descripcion': 'Pago con tarjeta de crédito/débito'}
            ]
            if button_num == 9:
                # Volver a selección de hora
                fecha = context.get('fecha_seleccionada')
                return self._show_available_times(context, user_id, phone, fecha)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif 0 <= button_num - 1 < len(metodos_pago):
                metodo_pago = metodos_pago[button_num - 1]
                context['metodo_pago'] = metodo_pago
                context['step'] = 'seleccionando_historial_medico'
                return self._show_medical_history_options(context)
            else:
                return {
                    'response': f'Opción inválida. Selecciona 1, 2, *9* para volver o *0* para cancelar.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando opción de historial médico (RF7)
        elif current_step == 'seleccionando_historial_medico':
            opciones_historial = [
                {'id': 'no_compartir', 'nivel': 0, 'nombre': 'No compartir', 'descripcion': 'El dentista solo verá información básica'},
                {'id': 'compartir_basico', 'nivel': 1, 'nombre': 'Compartir básico', 'descripcion': 'Nombre, edad y alergias'},
                {'id': 'compartir_completo', 'nivel': 3, 'nombre': 'Compartir completo', 'descripcion': 'Todo el historial médico'}
            ]
            if 0 <= button_num - 1 < len(opciones_historial):
                opcion_historial = opciones_historial[button_num - 1]
                context['historial_medico'] = opcion_historial
                context['sharedMedicalHistory'] = opcion_historial['nivel'] > 0
                context['medicalHistoryAccessLevel'] = opcion_historial['nivel']
                context['step'] = 'mostrando_resumen'
                return self._show_appointment_summary(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(opciones_historial)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando resumen
        elif current_step == 'mostrando_resumen':
            if button_num == 1:  # Confirmar
                # Para WhatsApp no necesitamos OTP - el usuario ya está verificado por su teléfono
                # Confirmar directamente la cita
                return self._confirm_appointment(session_id, context, user_id, phone)
            elif button_num == 2:  # Cancelar
                context['step'] = 'menu_principal'
                return {
                    'response': 'Agendamiento cancelado.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Por favor selecciona:\n*1.* Confirmar cita\n*2.* Cancelar',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Verificando OTP
        elif current_step == 'verificando_otp':
            # El OTP se maneja como texto, no como número de botón
            # Este caso no debería llegar aquí, pero lo dejamos por seguridad
            return {
                'response': 'Por favor ingresa el código OTP que recibiste por WhatsApp.',
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
                context['cita_reagendar'] = cita_seleccionada  # Guardar toda la info de la cita
                context['step'] = 'seleccionando_fecha_reagendar'
                return self._show_available_dates_for_reschedule(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(citas)}.' if citas else 'No hay citas disponibles.',
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
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(fechas)}.' if fechas else 'No hay fechas disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando hora para reagendar
        elif current_step == 'seleccionando_hora_reagendar':
            horarios = context.get('horarios_disponibles', [])
            if horarios and 0 <= button_num - 1 < len(horarios):
                slot_seleccionado = horarios[button_num - 1]
                # Extraer horaInicio del slot (puede ser dict o string)
                if isinstance(slot_seleccionado, dict):
                    hora_seleccionada = slot_seleccionado.get('horaInicio', slot_seleccionado.get('inicio', ''))
                else:
                    hora_seleccionada = str(slot_seleccionado)
                context['hora_seleccionada'] = hora_seleccionada
                context['step'] = 'confirmando_reagendamiento'
                # Mostrar resumen de reagendamiento para confirmar
                return self._show_reschedule_summary(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(horarios)}.' if horarios else 'No hay horarios disponibles.',
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
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(citas)}.' if citas else 'No hay citas disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando reagendamiento - Handler para confirmar/cancelar reagendamiento
        elif current_step == 'confirmando_reagendamiento':
            if button_num == 1:  # Confirmar
                return self._execute_reschedule(session_id, context, user_id, phone)
            elif button_num == 2:  # Cancelar
                context['step'] = 'menu_principal'
                return {
                    'response': 'Reagendamiento cancelado. Tu cita se mantiene en la fecha original.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Por favor selecciona:\n*1.* Sí, confirmar reagendamiento\n*2.* No, cancelar',
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
        
        # Menú de Historial Médico (Opción 5)
        elif current_step == 'menu_historial_medico':
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif button_num == 1:
                # Ver información médica
                return self._show_medical_info(context, user_id, phone)
            elif button_num == 2:
                # Ver alergias y medicamentos
                return self._show_allergies_medications(context, user_id, phone)
            elif button_num == 3:
                # Ver completitud
                return self._show_medical_completeness(context, user_id, phone)
            else:
                return {
                    'response': 'Opción inválida. Selecciona 1, 2, 3 o 0 para volver.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Menú de Reseñas (Opción 6)
        elif current_step == 'menu_resenas':
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif button_num == 1:
                # Ver mis reseñas
                return self._show_user_reviews(context, user_id, phone)
            elif button_num == 2:
                # Calificar cita pendiente
                return self._show_pending_reviews_to_rate(context, user_id, phone)
            elif button_num == 3:
                # Información sobre reseñas
                return self._show_reviews_info(context)
            else:
                return {
                    'response': 'Opción inválida. Selecciona 1, 2, 3 o 0 para volver.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando cita para calificar
        elif current_step == 'seleccionando_cita_calificar':
            citas = context.get('citas_pendientes_resena', [])
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif citas and 0 <= button_num - 1 < len(citas):
                cita_seleccionada = citas[button_num - 1]
                context['cita_a_calificar'] = cita_seleccionada
                context['step'] = 'ingresando_calificacion'
                return {
                    'response': f'*Calificar cita del {cita_seleccionada.get("fecha", "")}*\n\nDentista: {cita_seleccionada.get("dentista", "")}\n\n¿Qué calificación le das? (1-5 estrellas)\n\n*1.* ⭐ (Muy malo)\n*2.* ⭐⭐ (Malo)\n*3.* ⭐⭐⭐ (Regular)\n*4.* ⭐⭐⭐⭐ (Bueno)\n*5.* ⭐⭐⭐⭐⭐ (Excelente)\n\nEscribe el número de estrellas.',
                    'action': None,
                    'next_step': 'ingresando_calificacion',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f'Opción inválida. Selecciona un número del 1 al {len(citas)} o 0 para volver.' if citas else 'No hay citas disponibles.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Ingresando calificación
        elif current_step == 'ingresando_calificacion':
            if 1 <= button_num <= 5:
                context['calificacion_seleccionada'] = button_num
                context['step'] = 'confirmando_resena'
                cita = context.get('cita_a_calificar', {})
                return {
                    'response': f'*Confirmar Reseña*\n\nDentista: {cita.get("dentista", "")}\nFecha: {cita.get("fecha", "")}\nCalificación: {"⭐" * button_num}\n\n¿Deseas publicarla como anónimo?\n*1.* Sí, publicar anónimo\n*2.* No, publicar con mi nombre\n*0.* Cancelar',
                    'action': None,
                    'next_step': 'confirmando_resena',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Por favor selecciona una calificación del 1 al 5.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando reseña
        elif current_step == 'confirmando_resena':
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': 'Reseña cancelada.\n\n' + self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif button_num in [1, 2]:
                anonimo = button_num == 1
                return self._submit_review(session_id, context, user_id, phone, anonimo)
            else:
                return {
                    'response': 'Por favor selecciona 1, 2 o 0.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Menú de Ayuda (Opción 7) - Completo con todas las opciones
        elif current_step == 'menu_ayuda':
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif button_num == 1:
                # FAQ
                return self._show_faq(context)
            elif button_num == 2:
                # Cómo usar el chatbot
                return self._show_chatbot_guide(context)
            else:
                return {
                    'response': 'Opción inválida. Selecciona 1, 2 o 0 para volver.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Submenús de Ayuda - Permiten volver al menú de ayuda con opción 9
        elif current_step in ['submenu_faq', 'submenu_guia']:
            if button_num == 9:
                # Volver al menú de ayuda
                return self._handle_help(context)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Opción inválida. Escribe *9* para volver a Ayuda o *0* para el menú principal.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Submenús de Historial Médico - Permiten volver al menú de historial con opción 9
        elif current_step in ['submenu_info_medica', 'submenu_alergias', 'submenu_completitud']:
            if button_num == 9:
                # Volver al menú de historial médico
                return self._handle_medical_history(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Opción inválida. Escribe *9* para volver a Historial Médico o *0* para el menú principal.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Submenús de Reseñas - Permiten volver al menú de reseñas con opción 9
        elif current_step in ['submenu_mis_resenas', 'submenu_info_resenas']:
            if button_num == 9:
                # Volver al menú de reseñas
                return self._handle_reviews(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': 'Opción inválida. Escribe *9* para volver a Reseñas o *0* para el menú principal.',
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
        """Opción 1: Agendar cita - Flujo completo desde selección de consultorio"""
        print(f"[MENU_SYSTEM] _handle_schedule_appointment - user_id={user_id}, phone={phone}")
        
        context['step'] = 'seleccionando_consultorio'
        
        try:
            # Get all active consultorios - user must choose
            consultorios = self.actions_service.get_consultorios_info(limit=10)
            
            if not consultorios:
                return {
                    'response': 'No hay consultorios disponibles en este momento.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            context['consultorios_disponibles'] = consultorios
            
            # Format consultorios list - format direccion properly
            consultorios_texto = ''
            for i, c in enumerate(consultorios):
                direccion = c.get('direccion', '')
                # Format direccion if it's a dict
                if isinstance(direccion, dict):
                    calle = direccion.get('calle', '')
                    numero = direccion.get('numero', '')
                    colonia = direccion.get('colonia', '')
                    ciudad = direccion.get('ciudad', '')
                    direccion_str = f"{calle} #{numero}, {colonia}, {ciudad}"
                else:
                    direccion_str = str(direccion) if direccion else ''
                consultorios_texto += f'*{i+1}.* {c["nombre"]}\n   {direccion_str}\n'
            
            return {
                'response': f'*Agendar Nueva Cita*\n\n*Paso 1/6: Selecciona un consultorio:*\n\n{consultorios_texto}\n*0.* Cancelar\n\nEscribe el *número* del consultorio.',
                'action': 'show_consultorios',
                'next_step': 'seleccionando_consultorio',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error en _handle_schedule_appointment: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al cargar consultorios. Intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_dentists(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Shows available dentists for the selected consultorio"""
        try:
            consultorio_id = context.get('consultorio_id')
            
            if not consultorio_id:
                return {
                    'response': 'Error: No se seleccionó consultorio.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Get dentists from this consultorio
            dentistas_ref = self.db.collection('consultorio').document(consultorio_id).collection('dentistas')
            dentistas_query = dentistas_ref.where('activo', '==', True).limit(10)
            dentistas_docs = list(dentistas_query.stream())
            
            if not dentistas_docs:
                return {
                    'response': 'No hay dentistas disponibles en este consultorio.\n\nEscribe "menu" para seleccionar otro consultorio.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            dentistas = []
            for doc in dentistas_docs:
                data = doc.to_dict()
                dentistas.append({
                    'id': data.get('dentistaId', doc.id),
                    'nombre': data.get('nombreCompleto', 'Dentista'),
                    'especialidad': data.get('especialidad', 'General')
                })
            
            context['dentistas_disponibles'] = dentistas
            
            dentistas_texto = '\n'.join([
                f'*{i+1}.* {d["nombre"]}\n   Especialidad: {d.get("especialidad", "General")}'
                for i, d in enumerate(dentistas)
            ])
            
            return {
                'response': f'*Paso 2/6: Selecciona un dentista:*\n\nConsultorio: {context.get("consultorio_name", "")}\n\n{dentistas_texto}\n\n*9.* Volver al paso anterior\n*0.* Cancelar\n\nEscribe el *número* del dentista.',
                'action': 'show_dentistas',
                'next_step': 'seleccionando_dentista',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error getting dentists: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al cargar dentistas.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_services(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Shows available services/treatments for the selected dentist/consultorio"""
        try:
            dentista_id = context.get('dentista_id')
            consultorio_id = context.get('consultorio_id')
            
            tratamientos = self.actions_service.get_treatments_for_dentist(dentista_id, consultorio_id)
            context['tratamientos_disponibles'] = tratamientos
            
            if not tratamientos:
                return {
                    'response': 'No hay servicios disponibles para este dentista.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            servicios_texto = '\n'.join([
                f'*{i+1}.* {t["nombre"]}\n   ${t["precio"]:,.0f} MXN | {t["duracion"]} min\n   {t.get("descripcion", "")}'
                for i, t in enumerate(tratamientos[:10])
            ])
            
            return {
                'response': f'*Paso 3/6: Selecciona el servicio:*\n\nDentista: {context.get("dentista_name", "")}\nConsultorio: {context.get("consultorio_name", "")}\n\n{servicios_texto}\n\n*9.* Volver al paso anterior\n*0.* Cancelar\n\nEscribe el *número* del servicio.',
                'action': 'show_services',
                'next_step': 'seleccionando_servicio',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error getting services: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al cargar servicios.\n\nEscribe "menu" para volver.',
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
                'response': f'*Tus Próximas Citas:*\n\n{citas_texto}\n\nEscribe "menu" para volver al menú principal.',
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
                'response': f'*Reagendar Cita*\n\nSelecciona la cita que deseas reagendar:\n\n{citas_texto}\n\nEscribe el *número* de la cita.',
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
                'response': f'*Cancelar Cita*\n\nSelecciona la cita que deseas cancelar:\n\n{citas_texto}\n\nEscribe el *número* de la cita.',
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
        """Opcion 5: Historial medico - J.RF7 Enhanced con submenu"""
        context['step'] = 'menu_historial_medico'
        
        # Obtener datos del historial médico
        historial_result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
        
        status_text = ""
        if historial_result.get('success'):
            data = historial_result.get('data', {})
            completitud = data.get('completitud', 0)
            if completitud >= 80:
                status_text = f"*Estado:* Completado ({completitud}%)\n"
            elif completitud >= 40:
                status_text = f"*Estado:* Parcialmente completado ({completitud}%)\n"
            else:
                status_text = f"*Estado:* Pendiente de completar ({completitud}%)\n"
        
        response = f"""*Historial Medico*

{status_text}
¿Qué deseas consultar?

*1.* Ver mi información médica
*2.* Ver alergias y medicamentos
*3.* Ver porcentaje de completitud
*0.* Volver al menú principal

Escribe el *número* de la opción."""

        return {
            'response': response,
            'action': 'show_medical_history_menu',
            'next_step': 'menu_historial_medico',
            'mode': 'menu'
        }
    
    def _handle_reviews(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opcion 6: Resenas y calificaciones - J.RF9 Enhanced con submenu"""
        context['step'] = 'menu_resenas'
        
        # Obtener reseñas pendientes
        pending_count = 0
        try:
            pending_reviews = self.firebase_service.get_pending_reviews(user_id=user_id, phone=phone)
            pending_count = len(pending_reviews)
            context['citas_pendientes_resena'] = pending_reviews
        except Exception as e:
            print(f"Error checking pending reviews: {e}")
        
        pending_text = ""
        if pending_count > 0:
            pending_text = f"\n*Tienes {pending_count} cita(s) pendiente(s) de calificar*\n"
        
        response = f"""*Resenas y Calificaciones*
{pending_text}
¿Qué deseas hacer?

*1.* Ver mis reseñas escritas
*2.* Calificar una cita pendiente
*3.* ¿Cómo funcionan las reseñas?
*0.* Volver al menú principal

Escribe el *número* de la opción."""

        return {
            'response': response,
            'action': 'show_reviews_menu',
            'next_step': 'menu_resenas',
            'mode': 'menu'
        }
    
    def _handle_help(self, context: Dict) -> Dict:
        """Opción 7: Ayuda y Soporte con submenu completo"""
        context['step'] = 'menu_ayuda'
        
        response = """*Ayuda y Soporte*

¿En qué podemos ayudarte?

*1.* Preguntas frecuentes (FAQ)
*2.* Cómo usar el chatbot
*0.* Volver al menú principal

Escribe el *número* de la opción."""

        return {
            'response': response,
            'action': 'show_help_menu',
            'next_step': 'menu_ayuda',
            'mode': 'menu'
        }
    
    def _show_available_dates_for_appointment(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra fechas disponibles para agendar usando dentista_id y consultorio_id del contexto"""
        try:
            dentista_id = context.get('dentista_id')
            consultorio_id = context.get('consultorio_id')
            
            print(f"[MENU_SYSTEM] _show_available_dates_for_appointment - dentista_id={dentista_id}, consultorio_id={consultorio_id}")
            
            if not dentista_id or not consultorio_id:
                return {
                    'response': 'Error: No se encontró información del consultorio.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Obtener fechas disponibles directamente usando el repositorio con los IDs del contexto
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            from datetime import datetime
            
            fecha_base = datetime.now()
            fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
            
            print(f"[MENU_SYSTEM] Obteniendo fechas para dentista {dentista_id}, consultorio {consultorio_id}")
            fechas = cita_repo.obtener_fechas_disponibles(
                dentista_id,
                consultorio_id,
                fecha_timestamp,
                cantidad=5
            )
            
            print(f"[MENU_SYSTEM] Fechas obtenidas: {len(fechas) if fechas else 0}")
            context['fechas_disponibles'] = fechas or []
            
            if not fechas or len(fechas) == 0:
                return {
                    'response': 'Lo siento, no hay fechas disponibles en este momento.\n\nPor favor, contacta directamente con el consultorio o intenta más tarde.\n\nEscribe "menu" para volver.',
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
                'response': f'*Paso 4/6: Selecciona una fecha disponible:*\n\n{fechas_texto}\n\n*9.* Volver al paso anterior\n*0.* Cancelar\n\nEscribe el *número* de la fecha.',
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
    
    def _show_payment_methods(self, context: Dict) -> Dict:
        """Muestra métodos de pago disponibles"""
        metodos_texto = """*Paso 6/6: Selecciona el método de pago:*

*1.* Efectivo
   Pago al momento de la cita

*2.* Tarjeta (Stripe)
   Pago con tarjeta de crédito/débito

*9.* Volver al paso anterior
*0.* Cancelar

Escribe el *número* del método de pago."""
        
        return {
            'response': metodos_texto,
            'action': 'show_payment_methods',
            'next_step': 'seleccionando_metodo_pago',
            'mode': 'menu'
        }
    
    def _show_medical_history_options(self, context: Dict) -> Dict:
        """Muestra opciones para compartir historial médico (RF7)"""
        opciones_texto = """*Compartir Historial Médico*

¿Deseas compartir tu historial médico con el dentista?

*1.* No compartir
   El dentista solo verá información básica

*2.* Compartir básico (Nivel 1)
   Nombre, edad y alergias

*3.* Compartir completo (Nivel 3)
   Todo tu historial médico incluyendo documentos

*Nota:* Puedes cambiar esta configuración después desde tu perfil.

Escribe el *número* de la opción que prefieres."""
        
        return {
            'response': opciones_texto,
            'action': 'show_medical_history_options',
            'next_step': 'seleccionando_historial_medico',
            'mode': 'menu'
        }
    
    def _show_appointment_summary(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra resumen completo de la cita antes de confirmar (RF6)"""
        tratamiento = context.get('tratamiento_seleccionado', {})
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        metodo_pago = context.get('metodo_pago', {})
        historial_medico = context.get('historial_medico', {})
        dentista_name = context.get('dentista_name', 'Dentista')
        consultorio_name = context.get('consultorio_name', 'Consultorio')
        
        # Formatear fecha
        if hasattr(fecha, 'strftime'):
            fecha_str = fecha.strftime('%d/%m/%Y')
        else:
            fecha_str = str(fecha)
        
        # Formatear hora
        hora_str = hora if isinstance(hora, str) else str(hora)
        
        # Calcular total
        precio = tratamiento.get('precio', 0)
        duracion = tratamiento.get('duracion', 60)
        
        # Formatear opción de historial médico
        historial_texto = historial_medico.get('nombre', 'No compartir')
        if historial_medico.get('nivel', 0) > 0:
            historial_texto += f" (Nivel {historial_medico.get('nivel', 0)})"
        
        resumen = f"""*Resumen de tu Cita*

*Dentista:* {dentista_name}
*Consultorio:* {consultorio_name}
*Fecha:* {fecha_str}
*Hora:* {hora_str}
*Servicio:* {tratamiento.get('nombre', 'Consulta')}
*Duración:* {duracion} minutos
*Precio:* ${precio:,.0f} MXN
*Método de Pago:* {metodo_pago.get('nombre', 'Efectivo')}
*Historial Médico:* {historial_texto}

*Política de Cancelación:*
Puedes cancelar o reagendar tu cita con al menos 24 horas de anticipación sin penalización.

¿Confirmas esta cita?

*1.* Sí, confirmar cita
*2.* Cancelar"""
        
        return {
            'response': resumen,
            'action': 'show_summary',
            'next_step': 'mostrando_resumen',
            'mode': 'menu'
        }
    
    def _request_otp_for_appointment(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Solicita OTP para verificar agendamiento (RF8)"""
        try:
            # TODO: Implementar envío de OTP por WhatsApp usando el servicio de OTP
            # Por ahora, simular que se envió
            # En producción, esto debe llamar al servicio de OTP que envía por WhatsApp
            
            # Guardar que se solicitó OTP
            context['otp_requested'] = True
            context['otp_attempts'] = 0
            
            return {
                'response': '*Verificación Requerida*\n\nSe ha enviado un código de verificación a tu WhatsApp.\n\nPor favor, ingresa el código de 6 dígitos que recibiste.\n\nEscribe el código para continuar.',
                'action': 'request_otp',
                'next_step': 'verificando_otp',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error solicitando OTP: {e}")
            return {
                'response': 'Error al enviar código de verificación. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _grant_medical_history_access(self, paciente_id: str, dentista_id: str, nivel: int):
        """Otorga acceso al historial médico según el nivel seleccionado (RF7, RNF2)"""
        try:
            from datetime import datetime
            
            # Verificar si ya existe un acceso
            accesos_ref = self.db.collection('historial_medico_accesos')
            query = accesos_ref.where('pacienteId', '==', paciente_id)\
                              .where('dentistaId', '==', dentista_id)\
                              .where('activo', '==', True)\
                              .limit(1)
            
            docs = list(query.stream())
            
            acceso_data = {
                'pacienteId': paciente_id,
                'dentistaId': dentista_id,
                'nivel': nivel,
                'activo': True,
                'otorgadoEn': datetime.now(),  # datetime directly
                'otorgadoPor': 'paciente',
                'motivo': 'Otorgado durante agendamiento de cita',
                'updatedAt': datetime.now()
            }
            
            if docs:
                # Actualizar acceso existente
                docs[0].reference.update(acceso_data)
                print(f"Acceso al historial médico actualizado: Nivel {nivel}")
            else:
                # Crear nuevo acceso
                accesos_ref.add(acceso_data)
                print(f"Acceso al historial médico otorgado: Nivel {nivel}")
                
        except Exception as e:
            print(f"Error otorgando acceso al historial médico: {e}")
            import traceback
            traceback.print_exc()
            # No lanzar excepción, solo loggear
    
    def _verify_otp_and_confirm(self, session_id: str, context: Dict, user_id: str, phone: str, otp_code: str) -> Dict:
        """Verifica OTP y confirma la cita (RF8)"""
        try:
            # TODO: Implementar verificación real de OTP contra Firestore
            # Por ahora, aceptar cualquier código de 6 dígitos para desarrollo
            # En producción, esto debe verificar contra la subcolección otp_codes del paciente
            
            # Incrementar intentos
            context['otp_attempts'] = context.get('otp_attempts', 0) + 1
            
            # Por ahora, aceptar el código (en producción verificar contra Firestore)
            # if not self._validate_otp(user_id, phone, otp_code):
            #     if context['otp_attempts'] >= 3:
            #         context['step'] = 'menu_principal'
            #         return {
            #             'response': 'Código OTP incorrecto. Se agotaron los intentos.\n\nEscribe "menu" para volver.',
            #             'action': None,
            #             'next_step': 'menu_principal',
            #             'mode': 'menu'
            #         }
            #     return {
            #         'response': f'Código OTP incorrecto. Intento {context["otp_attempts"]}/3.\n\nPor favor, ingresa el código correcto.',
            #         'action': None,
            #         'next_step': 'verificando_otp',
            #         'mode': 'menu'
            #     }
            
            # OTP verificado, confirmar cita
            context['otp_verified'] = True
            return self._confirm_appointment(session_id, context, user_id, phone)
            
        except Exception as e:
            print(f"Error verificando OTP: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al verificar código. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_times(self, context: Dict, user_id: str, phone: str, fecha) -> Dict:
        """Muestra horarios disponibles para una fecha - Usa la misma lógica que la web"""
        try:
            # Convertir fecha a datetime si es necesario
            if isinstance(fecha, str):
                from datetime import datetime
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            elif hasattr(fecha, 'date'):
                fecha_dt = fecha
            else:
                from datetime import datetime
                fecha_dt = datetime.now()
            
            # Obtener dentista_id y consultorio_id del contexto
            dentista_id = context.get('dentista_id')
            consultorio_id = context.get('consultorio_id')
            
            if not dentista_id or not consultorio_id:
                return {
                    'response': 'Error: No se encontró información del consultorio.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Usar el método de CitaRepository que tiene la misma lógica que la web
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            
            # Crear datetime con timezone para pasar a obtener_horarios_disponibles
            # La función solo necesita un objeto con .timestamp() method
            from datetime import datetime, timezone
            fecha_midnight = datetime(fecha_dt.year, fecha_dt.month, fecha_dt.day, 12, 0, 0, tzinfo=timezone.utc)
            
            print(f"[MENU_SYSTEM] Getting horarios for dentista={dentista_id}, consultorio={consultorio_id}, fecha={fecha_midnight}")
            
            horarios_slots = cita_repo.obtener_horarios_disponibles(
                dentista_id,
                consultorio_id,
                fecha_midnight  # datetime tiene .timestamp() method
            )
            
            print(f"[MENU_SYSTEM] Horarios slots received: {len(horarios_slots) if horarios_slots else 0}")
            
            # Convertir slots a formato de texto para mostrar
            if not horarios_slots or len(horarios_slots) == 0:
                return {
                    'response': 'No hay horarios disponibles para esta fecha.\n\nEscribe "menu" para seleccionar otra fecha.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Guardar horarios en el contexto (como objetos con horaInicio)
            context['horarios_disponibles'] = horarios_slots
            
            # Formatear horarios para mostrar
            horarios_texto = '\n'.join([
                f'*{i+1}.* {slot.get("horaInicio", slot.get("inicio", ""))}' 
                for i, slot in enumerate(horarios_slots)
            ])
            
            return {
                'response': f'*Paso 5/6: Selecciona un horario:*\n\n{horarios_texto}\n\n*9.* Volver al paso anterior\n*0.* Cancelar\n\nEscribe el *numero* del horario.',
                'action': 'show_times',
                'next_step': context['step'],
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error obteniendo horarios: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al obtener horarios. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_dates_for_reschedule(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra fechas disponibles para reagendar - Usa dentista/consultorio de la cita original"""
        try:
            # Obtener info de la cita que se quiere reagendar
            cita_reagendar = context.get('cita_reagendar', {})
            dentista_id = cita_reagendar.get('dentistaId')
            consultorio_id = cita_reagendar.get('consultorioId')
            
            print(f"[_show_available_dates_for_reschedule] cita_reagendar={cita_reagendar}")
            print(f"[_show_available_dates_for_reschedule] dentista_id={dentista_id}, consultorio_id={consultorio_id}")
            
            from database.models import CitaRepository
            from datetime import datetime
            cita_repo = CitaRepository()
            fechas = []
            
            # Si tenemos dentista y consultorio, obtener fechas directamente
            if dentista_id and consultorio_id:
                context['dentista_id'] = dentista_id
                context['consultorio_id'] = consultorio_id
                
                fecha_base = datetime.now()
                fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
                
                fechas = cita_repo.obtener_fechas_disponibles(
                    dentista_id,
                    consultorio_id,
                    fecha_timestamp,
                    cantidad=5
                ) or []
            
            # Si no hay fechas o no tenemos dentista/consultorio, buscar en el primer consultorio disponible
            if not fechas:
                print(f"[_show_available_dates_for_reschedule] Buscando fechas alternativas...")
                try:
                    # Buscar el primer consultorio con disponibilidad
                    consultorios = list(self.db.collection('consultorios').limit(3).stream())
                    
                    for cons_doc in consultorios:
                        cons_data = cons_doc.to_dict()
                        cons_id = cons_doc.id
                        
                        # Buscar dentistas de este consultorio
                        dentistas = list(self.db.collection('dentistas').where('consultorioId', '==', cons_id).limit(2).stream())
                        
                        for dent_doc in dentistas:
                            dent_id = dent_doc.id
                            
                            fecha_base = datetime.now()
                            fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
                            
                            fechas_temp = cita_repo.obtener_fechas_disponibles(
                                dent_id,
                                cons_id,
                                fecha_timestamp,
                                cantidad=5
                            ) or []
                            
                            if fechas_temp:
                                fechas = fechas_temp
                                context['dentista_id'] = dent_id
                                context['consultorio_id'] = cons_id
                                print(f"[_show_available_dates_for_reschedule] Encontradas {len(fechas)} fechas en consultorio {cons_id}, dentista {dent_id}")
                                break
                        
                        if fechas:
                            break
                            
                except Exception as inner_e:
                    print(f"[_show_available_dates_for_reschedule] Error en fallback: {inner_e}")
            
            context['fechas_disponibles'] = fechas
            
            if not fechas:
                return {
                    'response': 'Lo siento, no hay fechas disponibles para reagendar en este momento.\n\nEscribe "menu" para volver al menú principal.',
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
                'response': f'*Selecciona Nueva Fecha*\n\nFechas disponibles:\n\n{fechas_texto}\n\nEscribe el *número* de la fecha que deseas.',
                'action': 'show_dates',
                'next_step': 'seleccionando_fecha_reagendar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo fechas para reagendar: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al obtener fechas disponibles. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _confirm_appointment(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Confirma el agendamiento con todos los datos (RF6, RF10)"""
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        tratamiento = context.get('tratamiento_seleccionado', {})
        metodo_pago = context.get('metodo_pago', {})
        dentista_id = context.get('dentista_id')
        consultorio_id = context.get('consultorio_id')
        
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
            
            # Preparar datos completos de la cita según requerimientos
            historial_medico = context.get('historial_medico', {})
            appointment_data = {
                'fecha': fecha_dt.strftime('%Y-%m-%d'),
                'hora': hora,
                'motivo': tratamiento.get('nombre', 'Consulta general'),
                'tratamientoId': tratamiento.get('id'),
                'tratamientoNombre': tratamiento.get('nombre'),
                'tratamientoPrecio': tratamiento.get('precio', 0),
                'duracion': tratamiento.get('duracion', 60),
                'dentistaId': dentista_id,
                'consultorioId': consultorio_id,
                'paymentMethod': metodo_pago.get('id', 'efectivo'),
                'paymentStatus': 'pending',
                'estado': 'programada',
                # RF7: Historial médico compartido
                'sharedMedicalHistory': historial_medico.get('nivel', 0) > 0,
                'medicalHistoryAccessLevel': historial_medico.get('nivel', 0),
                'historialCompartido': historial_medico.get('nivel', 0) > 0
            }
            
            # Crear cita usando el servicio que usa la misma estructura que la web
            result = self.firebase_service.create_appointment(user_id, appointment_data)
            
            if result.get('success'):
                context['step'] = 'menu_principal'
                fecha_str = fecha_dt.strftime('%d/%m/%Y') if hasattr(fecha_dt, 'strftime') else str(fecha_dt)
                
                # Registrar acceso al historial médico si se compartió (RF7, RNF2)
                historial_medico = context.get('historial_medico', {})
                nivel_acceso = historial_medico.get('nivel', 0)
                if nivel_acceso > 0 and dentista_id:
                    try:
                        self._grant_medical_history_access(user_id, dentista_id, nivel_acceso)
                    except Exception as e:
                        print(f"Error registrando acceso al historial médico: {e}")
                        # No fallar la creación de la cita si esto falla
                
                # Mensaje de confirmación completo (RF6, RF9)
                historial_texto = historial_medico.get('nombre', 'No compartido')
                if nivel_acceso > 0:
                    historial_texto += f" (Nivel {nivel_acceso})"
                
                mensaje = f"""*Cita Agendada Exitosamente*

*Fecha:* {fecha_str}
*Hora:* {hora}
*Dentista:* {context.get('dentista_name', 'Dentista')}
*Consultorio:* {context.get('consultorio_name', 'Consultorio')}
*Servicio:* {tratamiento.get('nombre', 'Consulta')}
*Precio:* ${tratamiento.get('precio', 0):,.0f} MXN
*Metodo de Pago:* {metodo_pago.get('nombre', 'Efectivo')}
*Historial Medico:* {historial_texto}

Recibiras un recordatorio 24h antes de tu cita.

Puedes completar o actualizar tu historial medico desde tu perfil en la app.

Escribe "menu" para volver al menu principal."""
                
                return {
                    'response': mensaje,
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
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al confirmar la cita. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_reschedule_summary(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra resumen del reagendamiento para confirmar (similar a _show_appointment_summary)"""
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        cita_original = context.get('cita_reagendar', {})
        
        # Formatear fecha
        if hasattr(fecha, 'strftime'):
            fecha_str = fecha.strftime('%d/%m/%Y')
        else:
            fecha_str = str(fecha)
        
        # Formatear hora
        hora_str = hora if isinstance(hora, str) else str(hora)
        
        # Info de la cita original
        fecha_original = cita_original.get('fecha', 'N/A')
        hora_original = cita_original.get('hora', cita_original.get('horaInicio', 'N/A'))
        dentista = cita_original.get('dentista', cita_original.get('dentistaName', 'Dentista'))
        
        resumen = f"""*Confirmar Reagendamiento*

*Dentista:* {dentista}

*Fecha original:* {fecha_original} {hora_original}
*Nueva fecha:* {fecha_str}
*Nueva hora:* {hora_str}

¿Confirmas este reagendamiento?

*1.* Sí, confirmar reagendamiento
*2.* No, cancelar"""
        
        return {
            'response': resumen,
            'action': 'show_reschedule_summary',
            'next_step': 'confirmando_reagendamiento',
            'mode': 'menu'
        }
    
    def _execute_reschedule(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Ejecuta el reagendamiento después de confirmación - Usa la misma estructura que la web"""
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
                    'response': f'*Cita Reagendada Exitosamente*\n\nNueva Fecha: {fecha_str}\nNueva Hora: {hora}\n\nRecibirás un recordatorio 24h antes.\n\nEscribe "menu" para volver al menú principal.',
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
            'response': f'*Confirmar Cancelación*\n\n¿Estás seguro de que deseas cancelar esta cita?\n\nFecha: {cita.get("fecha", "N/A")}\nHora: {cita.get("hora", "N/A")}\nDentista: {cita.get("dentista", "Dr. García")}\n\n*1.* Sí, cancelar cita\n*2.* No, mantener cita',
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
                    'response': '*Cita Cancelada Exitosamente*\n\nTu cita ha sido cancelada. Recibirás una confirmación por WhatsApp.\n\nEscribe "menu" para volver al menú principal.',
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

    # ============================================================
    # HELPER METHODS FOR MEDICAL HISTORY SUBMENU (Option 5)
    # ============================================================
    
    def _show_medical_info(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra información médica general del paciente"""
        try:
            print(f"[_show_medical_info] user_id={user_id}, phone={phone}")
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            
            if not result.get('success'):
                print(f"[_show_medical_info] Error: {result.get('error')}")
                return {
                    'response': 'No se pudo obtener tu información médica.\n\n*9.* Volver a Historial Médico\n*0.* Volver al menú principal',
                    'action': None,
                    'next_step': 'submenu_info_medica',
                    'mode': 'menu'
                }
            
            data = result.get('data', {})
            nombre = data.get('nombre', 'No registrado')
            edad = data.get('edad', 'No especificada')
            telefono = data.get('telefono', 'No registrado')
            email = data.get('email', 'No registrado')
            completitud = data.get('completitud', 0)
            
            response = f"""*Tu Informacion Medica*

*Nombre:* {nombre}
*Edad:* {edad}
*Teléfono:* {telefono}
*Email:* {email}
*Completitud:* {completitud}%

Para actualizar o completar tu historial medico, visita tu perfil en la app o web de Densora.

*9.* Volver a Historial Médico
*0.* Volver al menú principal"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_info_medica',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando info médica: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al obtener información.\n\n*9.* Volver a Historial Médico\n*0.* Volver al menú principal',
                'action': None,
                'next_step': 'submenu_info_medica',
                'mode': 'menu'
            }
    
    def _show_allergies_medications(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra alergias y medicamentos del paciente"""
        try:
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            
            if not result.get('success'):
                return {
                    'response': 'No se pudo obtener tu información.\n\n*9.* Volver a Historial Médico\n*0.* Volver al menú principal',
                    'action': None,
                    'next_step': 'submenu_alergias',
                    'mode': 'menu'
                }
            
            data = result.get('data', {})
            alergias = data.get('alergias', [])
            medicamentos = data.get('medicamentos', [])
            
            alergias_texto = ', '.join(alergias) if alergias else 'Ninguna registrada'
            medicamentos_texto = ', '.join(medicamentos) if medicamentos else 'Ninguno registrado'
            
            response = f"""*Alergias y Medicamentos*

*Alergias:*
{alergias_texto}

*Medicamentos actuales:*
{medicamentos_texto}

Es importante mantener esta informacion actualizada para una atencion segura.

*9.* Volver a Historial Médico
*0.* Volver al menú principal"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_alergias',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando alergias: {e}")
            return {
                'response': 'Error al obtener información.\n\n*9.* Volver a Historial Médico\n*0.* Volver al menú principal',
                'action': None,
                'next_step': 'submenu_alergias',
                'mode': 'menu'
            }
    
    def _show_medical_completeness(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra porcentaje de completitud del historial médico"""
        try:
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            
            if not result.get('success'):
                return {
                    'response': 'No se pudo obtener tu información.\n\n*9.* Volver a Historial Médico\n*0.* Volver al menú principal',
                    'action': None,
                    'next_step': 'submenu_completitud',
                    'mode': 'menu'
                }
            
            data = result.get('data', {})
            completitud = data.get('completitud', 0)
            
            # Barra de progreso visual
            filled = int(completitud / 10)
            empty = 10 - filled
            barra = '█' * filled + '░' * empty
            
            if completitud >= 80:
                estado = "Excelente"
                mensaje = "Tu historial esta muy completo. Gracias!"
            elif completitud >= 40:
                estado = "Parcial"
                mensaje = "Te recomendamos completar los campos faltantes."
            else:
                estado = "Incompleto"
                mensaje = "Por favor, completa tu historial para mejor atencion."
            
            response = f"""*Completitud del Historial*

{barra} *{completitud}%*

*Estado:* {estado}

{mensaje}

Puedes completar tu historial desde tu perfil en la app.

*9.* Volver a Historial Médico
*0.* Volver al menú principal"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_completitud',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando completitud: {e}")
            return {
                'response': 'Error al obtener información.\n\n*9.* Volver a Historial Médico\n*0.* Volver al menú principal',
                'action': None,
                'next_step': 'submenu_completitud',
                'mode': 'menu'
            }

    # ============================================================
    # HELPER METHODS FOR REVIEWS SUBMENU (Option 6)
    # ============================================================
    
    def _show_user_reviews(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra las reseñas escritas por el usuario"""
        try:
            reviews = self.firebase_service.get_user_reviews(user_id=user_id, phone=phone)
            
            if not reviews:
                return {
                    'response': '*Mis Resenas*\n\nNo has escrito ninguna resena todavia.\n\nDespues de cada cita, podras calificar tu experiencia.\n\n*9.* Volver a Reseñas\n*0.* Volver al menú principal',
                    'action': None,
                    'next_step': 'submenu_mis_resenas',
                    'mode': 'menu'
                }
            
            reviews_texto = '\n'.join([
                f"- {r.get('dentista', 'Dentista')} - {r.get('calificacion', 0)}/5 ({r.get('fecha', '')})"
                for r in reviews[:5]
            ])
            
            response = f"""*Mis Resenas*

{reviews_texto}

Total: {len(reviews)} resena(s)

*9.* Volver a Reseñas
*0.* Volver al menú principal"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_mis_resenas',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando reseñas: {e}")
            return {
                'response': 'Error al obtener reseñas.\n\n*9.* Volver a Reseñas\n*0.* Volver al menú principal',
                'action': None,
                'next_step': 'submenu_mis_resenas',
                'mode': 'menu'
            }
    
    def _show_pending_reviews_to_rate(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra citas pendientes de calificar"""
        try:
            pending = self.firebase_service.get_pending_reviews(user_id=user_id, phone=phone)
            context['citas_pendientes_resena'] = pending
            
            if not pending:
                return {
                    'response': '*Calificar Cita*\n\nNo tienes citas pendientes de calificar.\n\nCuando completes una cita, podras dejar tu resena aqui.\n\n*9.* Volver a Reseñas\n*0.* Volver al menú principal',
                    'action': None,
                    'next_step': 'submenu_mis_resenas',
                    'mode': 'menu'
                }
            
            context['step'] = 'seleccionando_cita_calificar'
            
            citas_texto = '\n'.join([
                f"*{i+1}.* {c.get('fecha', '')} - {c.get('dentista', 'Dentista')}"
                for i, c in enumerate(pending[:5])
            ])
            
            response = f"""*Calificar Cita*

Selecciona la cita que deseas calificar:

{citas_texto}

*0.* Volver

Escribe el *numero* de la cita."""

            return {
                'response': response,
                'action': 'show_pending_reviews',
                'next_step': 'seleccionando_cita_calificar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando citas pendientes: {e}")
            return {
                'response': 'Error al obtener citas. Escribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_reviews_info(self, context: Dict) -> Dict:
        """Muestra información sobre cómo funcionan las reseñas"""
        response = """*Como funcionan las resenas?*

- Despues de cada cita completada, puedes calificar
- Califica de 1 a 5 estrellas
- Puedes escribir un comentario opcional (max. 500 caracteres)
- Puedes publicar como anonimo si prefieres
- Puedes editar tu resena dentro de las primeras 24 horas
- El dentista puede responder a tu resena

Tus opiniones ayudan a otros pacientes y mejoran el servicio.

*9.* Volver a Reseñas
*0.* Volver al menú principal"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_info_resenas',
            'mode': 'menu'
        }
    
    def _submit_review(self, session_id: str, context: Dict, user_id: str, phone: str, anonimo: bool) -> Dict:
        """Envía la reseña a la base de datos"""
        try:
            cita = context.get('cita_a_calificar', {})
            calificacion = context.get('calificacion_seleccionada', 0)
            
            if not cita or not calificacion:
                return {
                    'response': 'Error: datos incompletos. Escribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            result = self.firebase_service.submit_review(
                user_id=user_id,
                dentista_id=cita.get('dentistaId'),
                cita_id=cita.get('id'),
                calificacion=calificacion,
                comentario='',  # Comentario vacío por ahora (simplificado para chat)
                anonimo=anonimo
            )
            
            if result.get('success'):
                context['step'] = 'menu_principal'
                return {
                    'response': f'*Gracias por tu resena!*\n\nTu calificacion de {calificacion}/5 ha sido registrada{" de forma anonima" if anonimo else ""}.\n\n{self.get_main_menu()}',
                    'action': 'review_submitted',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f'Error al enviar reseña: {result.get("error", "Error desconocido")}\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error enviando reseña: {e}")
            return {
                'response': 'Error al enviar reseña. Escribe "menu" para volver.',
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }

    # ============================================================
    # HELPER METHODS FOR HELP SUBMENU (Option 7)
    # ============================================================
    
    def _show_faq(self, context: Dict) -> Dict:
        """Muestra preguntas frecuentes"""
        response = """*Preguntas Frecuentes*

*Como agendo una cita?*
Escribe "1" en el menu principal y sigue los pasos.

*Puedo cancelar mi cita?*
Si, puedes cancelar hasta 24h antes sin penalizacion.

*Como pago mi cita?*
Aceptamos efectivo, tarjeta y transferencia.

*Puedo reagendar?*
Si, selecciona "3" en el menu principal.

*Mis datos estan seguros?*
Si, cumplimos con estandares de privacidad medica.

*9.* Volver a Ayuda y Soporte
*0.* Volver al menu principal"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_faq',
            'mode': 'menu'
        }
    
    def _show_chatbot_guide(self, context: Dict) -> Dict:
        """Muestra guía de uso del chatbot"""
        response = """*Como usar el Chatbot*

*Navegar:* Usa numeros para seleccionar opciones

*Volver atras:* Escribe "9" para volver al menu anterior

*Agendar cita:* Escribe "1"
*Ver mis citas:* Escribe "2"
*Reagendar:* Escribe "3"
*Cancelar:* Escribe "4"
*Historial medico:* Escribe "5"
*Resenas:* Escribe "6"
*Ayuda:* Escribe "7"

*9.* Volver a Ayuda y Soporte
*0.* Volver al menu principal"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_guia',
            'mode': 'menu'
        }
    
    def _show_support_contact(self, context: Dict) -> Dict:
        """Muestra información de contacto de soporte"""
        response = """*📞 Contactar Soporte*

*Email:* soporte@densora.com

*WhatsApp:* +52 55 1234 5678

*Tiempo de respuesta:* 24-48 horas

Para urgencias médicas, contacta directamente a tu consultorio o servicios de emergencia.

*9.* Volver a Ayuda y Soporte
*0.* Volver al menú principal"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_contacto',
            'mode': 'menu'
        }
    
    def _show_support_hours(self, context: Dict) -> Dict:
        """Muestra horarios de atención"""
        response = """*🕐 Horarios de Atención*

*Chatbot:* Disponible 24/7

*Soporte humano:*
Lunes a Viernes: 9:00 AM - 6:00 PM
Sábados: 9:00 AM - 2:00 PM
Domingos: Cerrado

*Nota:* Los horarios de los consultorios pueden variar.

Escribe *"menu"* para volver al menú principal."""

        return {
            'response': response,
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }

