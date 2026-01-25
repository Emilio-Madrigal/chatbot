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
from services.actions_service import ActionsService
from services.citas_service import CitasService
from services.firebase_functions_service import FirebaseFunctionsService
from services.language_service import language_service
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
        menu_title = language_service.t('main_menu_title', language)
        prompt = language_service.t('main_menu_prompt', language)
        
        return f"""{menu_title}

{prompt}

*1.* {language_service.t('menu_opt_schedule', language)}
*2.* {language_service.t('menu_opt_view', language)}
*3.* {language_service.t('menu_opt_reschedule', language)}
*4.* {language_service.t('menu_opt_cancel', language)}
*5.* {language_service.t('menu_opt_history', language)}
*6.* {language_service.t('menu_opt_reviews', language)}
*7.* {language_service.t('menu_opt_help', language)}
*0.* {language_service.t('menu_opt_exit', language)}

{language_service.t('type_number', language)}"""
    
    def process_message(self, session_id: str, message: str, 
                       context: Dict, user_id: str = None, 
                       phone: str = None) -> Dict:
        """
        Procesa mensajes en modo menú
        Solo acepta números y comandos predefinidos
        """
        message_clean = message.strip().lower()
        current_step = context.get('step', 'menu_principal')
        # Obtener idioma del contexto
        language = context.get('language', 'es')
        
        print(f"[MENU_SYSTEM] process_message - session_id={session_id}, message='{message}', current_step={current_step}, user_id={user_id}, phone={phone}, lang={language}")
        
        # Si es "menu" o "menú", volver al menú principal
        if message_clean in ['menu', 'menú', 'inicio', 'start', '0']:
            context['step'] = 'menu_principal'
            return {
                'response': self.get_main_menu(language),
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
                    'response': language_service.t('otp_instruction', language, fallback='Por favor ingresa el código OTP de 6 dígitos.'),
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
            'response': f"{language_service.t('agent_fallback', language)}\n\n{self.get_main_menu(language)}",
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
                # Historial Médico
                return self._handle_medical_history(context, user_id, phone)
            elif button_num == 6:
                # Reseñas
                return self._handle_reviews(context, user_id, phone)
            elif button_num == 7:
                # Ayuda
                return self._handle_help(context)
            elif button_num == 0:
                language = context.get('language', 'es')
                return {
                    'response': language_service.t('goodbye', language),
                    'action': 'exit',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                language = context.get('language', 'es')
                return {
                    'response': f"{language_service.t('error_invalid_option', language)}\n\n{self.get_main_menu(language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        
        # Seleccionando consultorio
        elif current_step == 'seleccionando_consultorio':
            language = context.get('language', 'es')
            consultorios = context.get('consultorios_disponibles', [])
            if button_num == 9 or button_num == 0:
                # Volver al menú principal
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando dentista
        elif current_step == 'seleccionando_dentista':
            language = context.get('language', 'es')
            dentistas = context.get('dentistas_disponibles', [])
            if button_num == 9:
                # Volver a selección de consultorio
                return self._handle_schedule_appointment(session_id, context, user_id, phone)
            elif button_num == 0:
                # Cancelar y volver al menú principal
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando servicio/tratamiento para agendar
        elif current_step == 'seleccionando_servicio':
            language = context.get('language', 'es')
            tratamientos = context.get('tratamientos_disponibles', [])
            if button_num == 9:
                # Volver a selección de dentista
                return self._show_available_dentists(context, user_id, phone)
            elif button_num == 0:
                # Cancelar y volver al menú principal
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando fecha para agendar
        elif current_step == 'seleccionando_fecha_agendar':
            language = context.get('language', 'es')
            fechas = context.get('fechas_disponibles', [])
            if button_num == 9:
                # Volver a selección de servicio
                return self._show_available_services(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando hora para agendar
        elif current_step == 'seleccionando_hora_agendar':
            language = context.get('language', 'es')
            horarios = context.get('horarios_disponibles', [])
            if button_num == 9:
                # Volver a selección de fecha
                return self._show_available_dates_for_appointment(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando método de pago
        elif current_step == 'seleccionando_metodo_pago':
            language = context.get('language', 'es')
            metodos_pago = [
                {'id': 'efectivo', 'nombre': language_service.t('payment_cash', language), 'descripcion': language_service.t('payment_cash_desc', language)},
                {'id': 'stripe', 'nombre': language_service.t('payment_card', language), 'descripcion': language_service.t('payment_card_desc', language)}
            ]
            if button_num == 9:
                # Volver a selección de hora
                fecha = context.get('fecha_seleccionada')
                return self._show_available_times(context, user_id, phone, fecha)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando opción de historial médico (RF7)
        elif current_step == 'seleccionando_historial_medico':
            language = context.get('language', 'es')
            opciones_historial = [
                {'id': 'no_compartir', 'nivel': 0, 'nombre': language_service.t('privacy_level_0', language), 'descripcion': language_service.t('privacy_level_0_desc', language)},
                {'id': 'compartir_basico', 'nivel': 1, 'nombre': language_service.t('privacy_level_1', language), 'descripcion': language_service.t('privacy_level_1_desc', language)},
                {'id': 'compartir_completo', 'nivel': 3, 'nombre': language_service.t('privacy_level_3', language), 'descripcion': language_service.t('privacy_level_3_desc', language)}
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando resumen
        elif current_step == 'mostrando_resumen':
            language = context.get('language', 'es')
            if button_num == 1:  # Confirmar
                return self._confirm_appointment(session_id, context, user_id, phone)
            elif button_num == 2:  # Cancelar
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
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
            language = context.get('language', 'es')
            citas = context.get('citas_disponibles', [])
            if citas and 0 <= button_num - 1 < len(citas):
                cita_seleccionada = citas[button_num - 1]
                context['cita_id_reagendar'] = cita_seleccionada['id']
                context['cita_reagendar'] = cita_seleccionada  # Guardar toda la info de la cita
                context['step'] = 'seleccionando_fecha_reagendar'
                return self._show_available_dates_for_reschedule(context, user_id, phone)
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando fecha para reagendar
        elif current_step == 'seleccionando_fecha_reagendar':
            language = context.get('language', 'es')
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando hora para reagendar
        elif current_step == 'seleccionando_hora_reagendar':
            language = context.get('language', 'es')
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando cita para cancelar
        elif current_step == 'seleccionando_cita_cancelar':
            language = context.get('language', 'es')
            citas = context.get('citas_disponibles', [])
            if citas and 0 <= button_num - 1 < len(citas):
                cita_seleccionada = citas[button_num - 1]
                context['cita_id_cancelar'] = cita_seleccionada['id']
                context['step'] = 'confirmando_cancelacion'
                return self._confirm_cancellation(session_id, context, user_id, phone, cita_seleccionada)
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando reagendamiento - Handler para confirmar/cancelar reagendamiento
        elif current_step == 'confirmando_reagendamiento':
            language = context.get('language', 'es')
            if button_num == 1:  # Confirmar
                return self._execute_reschedule(session_id, context, user_id, phone)
            elif button_num == 2:  # Cancelar
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('reschedule_cancel', language)}\n\n{self.get_main_menu(language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('reschedule_confirm_title', language)}\n\n*1.* {language_service.t('btn_confirm_reschedule', language)}\n*2.* {language_service.t('cancel', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando cancelación
        elif current_step == 'confirmando_cancelacion':
            language = context.get('language', 'es')
            if button_num == 1:  # Sí, confirmar
                return self._execute_cancellation(session_id, context, user_id, phone)
            elif button_num == 2:  # No, cancelar
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('cancel_aborted', language)}\n\n{self.get_main_menu(language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('cancel_confirm_title', language)}\n\n*1.* {language_service.t('btn_confirm_cancel', language)}\n*2.* {language_service.t('btn_keep_appointment', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Menú de Historial Médico (Opción 5)
        elif current_step == 'menu_historial_medico':
            language = context.get('language', 'es')
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif button_num == 1:
                # Datos Personales
                return self._show_personal_data(context, user_id, phone)
            elif button_num == 2:
                # Información Médica (Alergias, etc)
                return self._show_medical_details(context, user_id, phone)
            elif button_num == 3:
                # Historia Dental
                return self._show_dental_history(context, user_id, phone)
            elif button_num == 4:
                # Ver completitud
                return self._show_medical_completeness(context, user_id, phone)
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Menú de Reseñas (Opción 6)
        elif current_step == 'menu_resenas':
            language = context.get('language', 'es')
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
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
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando cita para calificar
        elif current_step == 'seleccionando_cita_calificar':
            language = context.get('language', 'es')
            citas = context.get('citas_pendientes_resena', [])
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif citas and 0 <= button_num - 1 < len(citas):
                cita_seleccionada = citas[button_num - 1]
                context['cita_a_calificar'] = cita_seleccionada
                context['step'] = 'ingresando_calificacion'
                
                rate_title = language_service.t('rate_title', language)
                rate_prompt = language_service.t('rate_prompt', language)
                r1 = language_service.t('rate_1', language)
                r2 = language_service.t('rate_2', language)
                r3 = language_service.t('rate_3', language)
                r4 = language_service.t('rate_4', language)
                r5 = language_service.t('rate_5', language)
                type_text = language_service.t('type_number', language)
                
                return {
                    'response': f'*{rate_title}: {cita_seleccionada.get("fecha", "")}*\n\n{language_service.t("label_dentist", language)}: {cita_seleccionada.get("dentista", "")}\n\n{rate_prompt}\n\n*1.* {r1}\n*2.* {r2}\n*3.* {r3}\n*4.* {r4}\n*5.* {r5}\n\n{type_text}',
                    'action': None,
                    'next_step': 'ingresando_calificacion',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)} {language_service.t('type_number', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Ingresando calificación
        elif current_step == 'ingresando_calificacion':
            language = context.get('language', 'es')
            if 1 <= button_num <= 5:
                context['calificacion_seleccionada'] = button_num
                context['step'] = 'confirmando_resena'
                cita = context.get('cita_a_calificar', {})
                
                confirm_title = language_service.t('confirm_review_title', language)
                label_dentist = language_service.t('label_dentist', language)
                label_date = language_service.t('label_date', language)
                label_rating = language_service.t('label_rating', language)
                rating_stars = "⭐" * button_num
                prompt = language_service.t('review_anon_prompt', language)
                btn_yes = language_service.t('btn_anon_yes', language)
                btn_no = language_service.t('btn_anon_no', language)
                cancel = language_service.t('cancel', language)
                
                return {
                    'response': f'{confirm_title}\n\n{label_dentist}: {cita.get("dentista", "")}\n{label_date}: {cita.get("fecha", "")}\n{label_rating}: {rating_stars}\n\n{prompt}\n*1.* {btn_yes}\n*2.* {btn_no}\n*0.* {cancel}',
                    'action': None,
                    'next_step': 'confirmando_resena',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Confirmando reseña
        elif current_step == 'confirmando_resena':
            language = context.get('language', 'es')
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': f"{language_service.t('consultorio_cancel', language)}\n\n{self.get_main_menu(language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            elif button_num in [1, 2]:
                anonimo = button_num == 1
                return self._submit_review(session_id, context, user_id, phone, anonimo)
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Menú de Ayuda (Opción 7) - Completo con todas las opciones
        elif current_step == 'menu_ayuda':
            language = context.get('language', 'es')
            if button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
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
                    'response': f"{language_service.t('error_invalid_option', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Submenús de Ayuda - Permiten volver al menú de ayuda con opción 9
        elif current_step in ['submenu_faq', 'submenu_guia']:
            language = context.get('language', 'es')
            if button_num == 9:
                # Volver al menú de ayuda
                return self._handle_help(context)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Submenús de Historial Médico - Permiten volver al menú de historial con opción 9
        elif current_step in ['submenu_info_medica', 'submenu_alergias', 'submenu_completitud']:
            language = context.get('language', 'es')
            if button_num == 9:
                # Volver al menú de historial médico
                return self._handle_medical_history(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Submenús de Reseñas - Permiten volver al menú de reseñas con opción 9
        elif current_step in ['submenu_mis_resenas', 'submenu_info_resenas']:
            language = context.get('language', 'es')
            if button_num == 9:
                # Volver al menú de reseñas
                return self._handle_reviews(context, user_id, phone)
            elif button_num == 0:
                context['step'] = 'menu_principal'
                return {
                    'response': self.get_main_menu(language),
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"{language_service.t('error_invalid_option', language)}",
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Si no coincide con ningún paso, volver al menú
        context['step'] = 'menu_principal'
        language = context.get('language', 'es')
        return {
            'response': f"{language_service.t('agent_fallback', language)}\n\n{self.get_main_menu(language)}",
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_schedule_appointment(self, session_id: str, context: Dict,
                                    user_id: str, phone: str) -> Dict:
        """Opción 1: Agendar cita - Flujo completo desde selección de consultorio"""
        print(f"[MENU_SYSTEM] _handle_schedule_appointment - user_id={user_id}, phone={phone}")
        
        language = context.get('language', 'es')
        context['step'] = 'seleccionando_consultorio'
        
        try:
            # Get all active consultorios - user must choose
            consultorios = self.actions_service.get_consultorios_info(limit=10)
            
            if not consultorios:
                return {
                    'response': f"{language_service.t('no_consultorios', language)}\n\n{language_service.t('type_menu', language)}",
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
            
            step_text = language_service.t('step_consultorio', language)
            cancel_text = language_service.t('cancel', language)
            type_text = language_service.t('type_number', language)
            title = language_service.t('schedule_title', language)
            
            return {
                'response': f'{title}\n\n{step_text}\n\n{consultorios_texto}\n*0.* {cancel_text}\n\n{type_text}',
                'action': 'show_consultorios',
                'next_step': 'seleccionando_consultorio',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error en _handle_schedule_appointment: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_dentists(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Shows available dentists for the selected consultorio"""
        language = context.get('language', 'es')
        try:
            consultorio_id = context.get('consultorio_id')
            
            if not consultorio_id:
                return {
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
                    'response': f"{language_service.t('no_dentists', language)}\n\n{language_service.t('type_menu', language)}",
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
                f'*{i+1}.* {d["nombre"]}\n   {d.get("especialidad", "General")}'
                for i, d in enumerate(dentistas)
            ])
            
            step_text = language_service.t('step_dentist', language)
            consultorio_text = language_service.t('dentist_consultorio', language, consultorio=context.get("consultorio_name", ""))
            back_text = language_service.t('back', language)
            cancel_text = language_service.t('cancel', language)
            type_text = language_service.t('type_number', language)
            
            return {
                'response': f'{step_text}\n\n{consultorio_text}\n\n{dentistas_texto}\n\n*9.* {back_text}\n*0.* {cancel_text}\n\n{type_text}',
                'action': 'show_dentistas',
                'next_step': 'seleccionando_dentista',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error getting dentists: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_available_services(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Shows available services/treatments for the selected dentist/consultorio"""
        language = context.get('language', 'es')
        try:
            dentista_id = context.get('dentista_id')
            consultorio_id = context.get('consultorio_id')
            
            tratamientos = self.actions_service.get_treatments_for_dentist(dentista_id, consultorio_id)
            context['tratamientos_disponibles'] = tratamientos
            
            if not tratamientos:
                return {
                    'response': f"{language_service.t('no_services', language)}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            min_text = language_service.t('label_min', language)
            servicios_texto = '\n'.join([
                f'*{i+1}.* {t["nombre"]}\n   ${t["precio"]:,.0f} MXN | {t["duracion"]} {min_text} \n   {t.get("descripcion", "")}'
                for i, t in enumerate(tratamientos[:10])
            ])
            
            step_text = language_service.t('step_service', language)
            header_text = f"{language_service.t('label_dentist', language)}: {context.get('dentista_name', '')}\n{language_service.t('label_consultorio', language)}: {context.get('consultorio_name', '')}"
            back_text = language_service.t('back', language)
            cancel_text = language_service.t('cancel', language)
            type_text = language_service.t('type_number', language)
            
            return {
                'response': f'{step_text}\n\n{header_text}\n\n{servicios_texto}\n\n*9.* {back_text}\n*0.* {cancel_text}\n\n{type_text}',
                'action': 'show_services',
                'next_step': 'seleccionando_servicio',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error getting services: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_view_appointments(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opción 2: Ver citas - Usa la misma estructura que la web"""
        language = context.get('language', 'es')
        try:
            # Usar el servicio que accede a la misma estructura que la web
            citas = self.firebase_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            
            if not citas:
                return {
                    'response': f"{language_service.t('no_appointments', language)}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            citas_texto = '\n'.join([
                f'*{i+1}.* {cita.get("fecha", "N/A")} {cita.get("hora", "N/A")} - {cita.get("dentista", "Dr. García")}'
                for i, cita in enumerate(citas[:5])
            ])
            
            return {
                'response': f'*{language_service.t("your_appointments", language)}:*\n\n{citas_texto}\n\n{language_service.t("type_menu", language)}',
                'action': 'show_appointments',
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo citas: {e}")
            return {
                'response': f"{language_service.t('error_fetching_appointments', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_reschedule_appointment(self, session_id: str, context: Dict,
                                      user_id: str, phone: str) -> Dict:
        """Opción 3: Reagendar cita - Usa la misma estructura que la web"""
        language = context.get('language', 'es')
        context['step'] = 'seleccionando_cita_reagendar'
        
        try:
            # Usar el servicio que accede a la misma estructura que la web
            citas = self.firebase_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            context['citas_disponibles'] = citas
            
            if not citas:
                return {
                    'response': f"{language_service.t('no_appointments_reschedule', language)}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            citas_texto = '\n'.join([
                f'*{i+1}.* {cita.get("fecha", "N/A")} {cita.get("hora", "N/A")} - {cita.get("dentista", "Dr. García")}'
                for i, cita in enumerate(citas[:5])
            ])
            
            return {
                'response': f'*{language_service.t("reschedule_title", language)}*\n\n{language_service.t("reschedule_prompt", language)}\n\n{citas_texto}\n\n{language_service.t("type_number", language)}',
                'action': 'show_appointments_to_reschedule',
                'next_step': 'seleccionando_cita_reagendar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo citas para reagendar: {e}")
            return {
                'response': f"{language_service.t('error_fetching_appointments', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_cancel_appointment(self, session_id: str, context: Dict,
                                  user_id: str, phone: str) -> Dict:
        """Opción 4: Cancelar cita - Usa la misma estructura que la web"""
        language = context.get('language', 'es')
        context['step'] = 'seleccionando_cita_cancelar'
        
        try:
            # Usar el servicio que accede a la misma estructura que la web
            citas = self.firebase_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            context['citas_disponibles'] = citas
            
            if not citas:
                return {
                    'response': f"{language_service.t('no_appointments_cancel', language)}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            citas_texto = '\n'.join([
                f'*{i+1}.* {cita.get("fecha", "N/A")} {cita.get("hora", "N/A")} - {cita.get("dentista", "Dr. García")}'
                for i, cita in enumerate(citas[:5])
            ])
            
            return {
                'response': f'*{language_service.t("cancel_title", language)}*\n\n{language_service.t("cancel_prompt", language)}\n\n{citas_texto}\n\n{language_service.t("type_number", language)}',
                'action': 'show_appointments_to_cancel',
                'next_step': 'seleccionando_cita_cancelar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo citas para cancelar: {e}")
            return {
                'response': f"{language_service.t('error_fetching_appointments', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _handle_medical_history(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opcion 5: Historial medico - Enhanced con pestañas (Tabs)"""
        language = context.get('language', 'es')
        context['step'] = 'menu_historial_medico'
        
        # Obtener datos del historial médico
        historial_result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
        
        status_text = ""
        if historial_result.get('success'):
            data = historial_result.get('data', {})
            # Robust get for completeness
            completitud = self._get_field_robust(data, ['completeness', 'completitud'], 0)
            
            try:
                completitud = int(float(completitud))
            except:
                completitud = 0
            
            status_label = language_service.t('status', language)
            
            if completitud >= 80:
                status_text = f"*{status_label}:* {language_service.t('status_completed', language)} ({completitud}%)\n"
            elif completitud >= 40:
                status_text = f"*{status_label}:* {language_service.t('status_partial', language)} ({completitud}%)\n"
            else:
                status_text = f"*{status_label}:* {language_service.t('status_pending', language)} ({completitud}%)\n"
        
        mh_title = language_service.t('medical_history_title', language)
        what_to_do = language_service.t('what_to_do', language)
        
        # Textos para opciones (simulando pestañas)
        opt_personal = language_service.t('tab_personal', language)
        opt_medical = language_service.t('tab_medical', language)
        opt_dental = language_service.t('tab_dental', language)
        opt_completeness = language_service.t('mh_opt_completeness', language)
        opt0 = language_service.t('menu_opt_exit', language)
        
        type_num = language_service.t('type_number', language)
        
        response = f"""*{mh_title}*

{status_text}
{what_to_do}

*1.* {opt_personal}
*2.* {opt_medical}
*3.* {opt_dental}
*4.* {opt_completeness}
*0.* {opt0}

{type_num}"""

        return {
            'response': response,
            'action': 'show_medical_history_menu',
            'next_step': 'menu_historial_medico',
            'mode': 'menu'
        }
    
    def _handle_reviews(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opcion 6: Resenas y calificaciones - J.RF9 Enhanced con submenu"""
        language = context.get('language', 'es')
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
            pending_text = f"\n*{language_service.t('pending_reviews_msg', language, count=pending_count)}*\n"
        
        title = language_service.t('reviews_title', language)
        what_to_do = language_service.t('what_to_do', language)
        opt1 = language_service.t('reviews_opt_my_reviews', language)
        opt2 = language_service.t('reviews_opt_rate', language)
        opt3 = language_service.t('reviews_opt_info', language)
        opt0 = language_service.t('menu_opt_exit', language)
        type_num = language_service.t('type_number', language)
        
        response = f"""*{title}*
{pending_text}
{what_to_do}

*1.* {opt1}
*2.* {opt2}
*3.* {opt3}
*0.* {opt0}

{type_num}"""

        return {
            'response': response,
            'action': 'show_reviews_menu',
            'next_step': 'menu_resenas',
            'mode': 'menu'
        }
    
    def _handle_help(self, context: Dict) -> Dict:
        """Opción 7: Ayuda y Soporte con submenu completo"""
        language = context.get('language', 'es')
        context['step'] = 'menu_ayuda'
        
        title = language_service.t('help_title', language)
        prompt = language_service.t('help_prompt', language)
        opt1 = language_service.t('help_opt_faq', language)
        opt2 = language_service.t('help_opt_guide', language)
        opt0 = language_service.t('menu_opt_exit', language)
        type_num = language_service.t('type_number', language)
        
        response = f"""*{title}*

{prompt}

*1.* {opt1}
*2.* {opt2}
*0.* {opt0}

{type_num}"""

        return {
            'response': response,
            'action': 'show_help_menu',
            'next_step': 'menu_ayuda',
            'mode': 'menu'
        }
    
    def _show_available_dates_for_appointment(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra fechas disponibles para agendar usando dentista_id y consultorio_id del contexto"""
        language = context.get('language', 'es')
        try:
            dentista_id = context.get('dentista_id')
            consultorio_id = context.get('consultorio_id')
            
            print(f"[MENU_SYSTEM] _show_available_dates_for_appointment - dentista_id={dentista_id}, consultorio_id={consultorio_id}")
            
            if not dentista_id or not consultorio_id:
                return {
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
                    'response': f"{language_service.t('no_dates', language)}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Formatear fechas
            fechas_texto = '\n'.join([
                f'*{i+1}.* {fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else str(fecha)}' 
                for i, fecha in enumerate(fechas)
            ])
            
            step_text = language_service.t('step_date', language)
            back_text = language_service.t('back', language)
            cancel_text = language_service.t('cancel', language)
            type_text = language_service.t('type_number', language)
            
            return {
                'response': f'{step_text}\n\n{fechas_texto}\n\n*9.* {back_text}\n*0.* {cancel_text}\n\n{type_text}',
                'action': 'show_dates',
                'next_step': 'seleccionando_fecha_agendar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error obteniendo fechas: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_payment_methods(self, context: Dict) -> Dict:
        """Muestra métodos de pago disponibles"""
        language = context.get('language', 'es')
        
        step_text = language_service.t('step_payment', language)
        cash_text = language_service.t('payment_cash', language)
        cash_desc = language_service.t('payment_cash_desc', language)
        card_text = language_service.t('payment_card', language)
        card_desc = language_service.t('payment_card_desc', language)
        back_text = language_service.t('back', language)
        cancel_text = language_service.t('cancel', language)
        type_text = language_service.t('type_number', language)
        
        metodos_texto = f"""{step_text}

*1.* {cash_text}
   {cash_desc}

*2.* {card_text}
   {card_desc}

*9.* {back_text}
*0.* {cancel_text}

{type_text}"""
        
        return {
            'response': metodos_texto,
            'action': 'show_payment_methods',
            'next_step': 'seleccionando_metodo_pago',
            'mode': 'menu'
        }
    
    def _show_medical_history_options(self, context: Dict) -> Dict:
        """Muestra opciones para compartir historial médico (RF7)"""
        language = context.get('language', 'es')
        
        title = language_service.t('step_medical_privacy', language)
        prompt = language_service.t('medical_privacy_prompt', language)
        
        l0 = language_service.t('privacy_level_0', language)
        l0_d = language_service.t('privacy_level_0_desc', language)
        
        l1 = language_service.t('privacy_level_1', language)
        l1_d = language_service.t('privacy_level_1_desc', language)
        
        l3 = language_service.t('privacy_level_3', language)
        l3_d = language_service.t('privacy_level_3_desc', language)
        
        note = language_service.t('privacy_note', language)
        type_text = language_service.t('type_number', language)
        
        opciones_texto = f"""{title}

{prompt}

*1.* {l0}
   {l0_d}

*2.* {l1}
   {l1_d}

*3.* {l3}
   {l3_d}

{note}

{type_text}"""
        
        return {
            'response': opciones_texto,
            'action': 'show_medical_history_options',
            'next_step': 'seleccionando_historial_medico',
            'mode': 'menu'
        }
    
    def _show_appointment_summary(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra resumen completo de la cita antes de confirmar (RF6)"""
        language = context.get('language', 'es')
        
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
        historial_texto = historial_medico.get('nombre', '')
        if not historial_texto:
            # Fallbacks locales si no hay nombre en el objeto (ej. si viene de una versión anterior)
            lvl = historial_medico.get('nivel', 0)
            if lvl == 0: historial_texto = language_service.t('privacy_level_0', language)
            elif lvl == 1: historial_texto = language_service.t('privacy_level_1', language)
            else: historial_texto = language_service.t('privacy_level_3', language)
            
        if historial_medico.get('nivel', 0) > 0:
            historial_texto += f" (Nivel {historial_medico.get('nivel', 0)})"
        
        resumen = f"""{language_service.t('summary_title', language)}

*{language_service.t('label_dentist', language)}:* {dentista_name}
*{language_service.t('label_consultorio', language)}:* {consultorio_name}
*{language_service.t('label_date', language)}:* {fecha_str}
*{language_service.t('label_time', language)}:* {hora_str}
*{language_service.t('label_service', language)}:* {tratamiento.get('nombre', 'Consulta')}
*{language_service.t('label_duration', language)}:* {duracion} {language_service.t('label_min', language)}
*{language_service.t('label_price', language)}:* ${precio:,.0f} MXN
*{language_service.t('label_payment', language)}:* {metodo_pago.get('nombre', 'Efectivo')}
*{language_service.t('label_history_access', language)}:* {historial_texto}

{language_service.t('cancellation_policy', language)}

{language_service.t('confirm_prompt', language)}

*1.* {language_service.t('btn_confirm', language)}
*2.* {language_service.t('btn_cancel', language)}"""
        
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
        language = context.get('language', 'es')
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
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
                    'response': f"{language_service.t('no_times', language)}\n\n{language_service.t('type_menu', language)}",
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
            
            step_text = language_service.t('step_time', language)
            back_text = language_service.t('back', language)
            cancel_text = language_service.t('cancel', language)
            type_text = language_service.t('type_number', language)
            
            return {
                'response': f'{step_text}\n\n{horarios_texto}\n\n*9.* {back_text}\n*0.* {cancel_text}\n\n{type_text}',
                'action': 'show_times',
                'next_step': context['step'],
                'mode': 'menu'
            }
        except Exception as e:
            print(f"[MENU_SYSTEM] Error obteniendo horarios: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
        language = context.get('language', 'es')
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        tratamiento = context.get('tratamiento_seleccionado', {})
        metodo_pago = context.get('metodo_pago', {})
        dentista_id = context.get('dentista_id')
        consultorio_id = context.get('consultorio_id')
        
        try:
            if not user_id:
                return {
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
                historial_texto = historial_medico.get('nombre', language_service.t('privacy_level_0', language))
                if nivel_acceso > 0:
                    historial_texto += f" (Nivel {nivel_acceso})"
                
                mensaje = f"""{language_service.t('appointment_confirmed_title', language)}

*{language_service.t('label_date', language)}:* {fecha_str}
*{language_service.t('label_time', language)}:* {hora}
*{language_service.t('label_dentist', language)}:* {context.get('dentista_name', 'Dentista')}
*{language_service.t('label_consultorio', language)}:* {context.get('consultorio_name', 'Consultorio')}
*{language_service.t('label_service', language)}:* {tratamiento.get('nombre', 'Consulta')}
*{language_service.t('label_price', language)}:* ${tratamiento.get('precio', 0):,.0f} MXN
*{language_service.t('label_payment', language)}:* {metodo_pago.get('nombre', 'Efectivo')}
*{language_service.t('label_history_access', language)}:* {historial_texto}

{language_service.t('reminder_note', language)}

{language_service.t('history_update_note', language)}

{language_service.t('type_menu', language)}"""
                
                return {
                    'response': mensaje,
                    'action': 'appointment_created',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                return {
                    'response': f'Error: {error_msg}\n\n{language_service.t("type_menu", language)}',
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
        language = context.get('language', 'es')
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
        
        resumen = f"""*{language_service.t('reschedule_confirm_title', language)}*

*{language_service.t('label_dentist', language)}:* {dentista}

*{language_service.t('label_original_date', language)}:* {fecha_original} {hora_original}
*{language_service.t('label_new_date', language)}:* {fecha_str}
*{language_service.t('label_new_time', language)}:* {hora_str}

{language_service.t('reschedule_confirm_prompt', language)}

*1.* {language_service.t('btn_confirm_reschedule', language)}
*2.* {language_service.t('cancel', language)}"""
        
        return {
            'response': resumen,
            'action': 'show_reschedule_summary',
            'next_step': 'confirmando_reagendamiento',
            'mode': 'menu'
        }
    
    def _execute_reschedule(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Ejecuta el reagendamiento después de confirmación - Usa la misma estructura que la web"""
        language = context.get('language', 'es')
        cita_id = context.get('cita_id_reagendar')
        fecha = context.get('fecha_seleccionada')
        hora = context.get('hora_seleccionada')
        
        try:
            if not user_id:
                return {
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
                    'response': f'*{language_service.t("reschedule_success", language)}*\n\n{language_service.t("label_new_date", language)}: {fecha_str}\n{language_service.t("label_new_time", language)}: {hora}\n\n{language_service.t("reminder_note", language)}\n\n{language_service.t("type_menu", language)}',
                    'action': 'appointment_rescheduled',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                return {
                    'response': f'Error: {error_msg}\n\n{language_service.t("type_menu", language)}',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error confirmando reagendamiento: {e}")
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _confirm_cancellation(self, session_id: str, context: Dict, user_id: str, 
                            phone: str, cita: Dict) -> Dict:
        """Muestra confirmación de cancelación"""
        language = context.get('language', 'es')
        return {
            'response': f'*{language_service.t("cancel_confirm_title", language)}*\n\n{language_service.t("cancel_confirm_prompt", language)}\n\n{language_service.t("label_date", language)}: {cita.get("fecha", "N/A")}\n{language_service.t("label_time", language)}: {cita.get("hora", "N/A")}\n{language_service.t("label_dentist", language)}: {cita.get("dentista", "")}\n\n*1.* {language_service.t("btn_confirm_cancel", language)}\n*2.* {language_service.t("btn_keep_appointment", language)}',
            'action': None,
            'next_step': 'confirmando_cancelacion',
            'mode': 'menu'
        }
    
    def _execute_cancellation(self, session_id: str, context: Dict, user_id: str, phone: str) -> Dict:
        """Ejecuta la cancelación - Usa la misma estructura que la web"""
        language = context.get('language', 'es')
        cita_id = context.get('cita_id_cancelar')
        
        try:
            if not user_id:
                return {
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            
            # Cancelar usando el servicio que usa la misma estructura que la web
            result = self.firebase_service.cancel_appointment(user_id, cita_id)
            
            if result.get('success'):
                context['step'] = 'menu_principal'
                return {
                    'response': f'*{language_service.t("cancel_success_title", language)}*\n\n{language_service.t("cancel_success_msg", language)}\n\n{language_service.t("type_menu", language)}',
                    'action': 'appointment_cancelled',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                return {
                    'response': f'Error: {error_msg}\n\n{language_service.t("type_menu", language)}',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error ejecutando cancelación: {e}")
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }

    # ============================================================
    # HELPER METHODS FOR MEDICAL HISTORY SUBMENU (Option 5)
    # ============================================================
    
    def _get_field_robust(self, data: Dict, keys: list, default=None):
        """Helper to try multiple keys"""
        for k in keys:
            if k in data and data[k]:
                return data[k]
        return default

    def _show_personal_data(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra datos personales (Tab 1)"""
        language = context.get('language', 'es')
        try:
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            
            back_mh = language_service.t('back_to_mh', language)
            
            if not result.get('success'):
                return self._error_response(language, back_mh)
            
            data = result.get('data', {})
            
            # Extract fields robustly
            nombre = self._get_field_robust(data, ['nombreCompleto', 'nombre', 'Nombre'], language_service.t('none_registered', language))
            edad = self._get_field_robust(data, ['edad', 'Edad'], language_service.t('last_visit_not_specified', language))
            telefono = self._get_field_robust(data, ['telefono', 'Telefono', 'celular'], language_service.t('none_registered', language))
            genero = self._get_field_robust(data, ['genero', 'sexo', 'Genero'], language_service.t('gender_not_specified', language))
            direccion = self._get_field_robust(data, ['direccion', 'domicilio', 'Direccion'], language_service.t('address_not_registered', language))
            if isinstance(direccion, dict): # If it's an object, format it
                direccion = f"{direccion.get('calle','')} {direccion.get('numero','')} {direccion.get('colonia','')}".strip()
            if not direccion:
                direccion = language_service.t('address_not_registered', language)
            
            title = language_service.t('tab_personal', language, fallback="Datos Personales")
            lbl_name = language_service.t('label_name', language)
            lbl_age = language_service.t('label_age', language)
            lbl_phone = language_service.t('label_phone', language)
            lbl_gender = language_service.t('label_gender', language)
            lbl_address = language_service.t('label_address', language)
            
            response = f"""*{title}*

*{lbl_name}:* {nombre}
*{lbl_age}:* {edad}
*{lbl_phone}:* {telefono}
*{lbl_gender}:* {genero}
*{lbl_address}:* {direccion}

{language_service.t('info_update_note', language)}

*9.* {back_mh}
*0.* {language_service.t('menu_opt_exit', language)}"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_info_medica',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando datos personales: {e}")
            return self._error_response(language, "Volver")

    def _show_medical_details(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra información médica detallada: Alergias, Enfermedades, Medicamentos (Tab 2)"""
        language = context.get('language', 'es')
        try:
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            back_mh = language_service.t('back_to_mh', language)
            
            if not result.get('success'):
                return self._error_response(language, back_mh)
            
            data = result.get('data', {})
            
            # Robust extraction - include medicamentosActuales (how web saves it)
            alergias = self._get_field_robust(data, ['alergias', 'allergies', 'Alergias'], [])
            enfermedades = self._get_field_robust(data, ['enfermedadesCronicas', 'condicionesMedicas', 'chronicDiseases', 'Enfermedades'], [])
            medicamentos = self._get_field_robust(data, ['medicamentosActuales', 'medicamentos', 'medications', 'Medicamentos', 'medicacionActual'], [])
            
            # Get translation for none registered
            none_txt = language_service.t('none_registered', language)
            
            # Format lists
            def format_list(l):
                if isinstance(l, list): return ', '.join(str(item) for item in l) if l else none_txt
                return str(l) if l else none_txt
                
            alergias_txt = format_list(alergias)
            enfermedades_txt = format_list(enfermedades)
            medicamentos_txt = format_list(medicamentos)
            
            title = language_service.t('tab_medical', language, fallback="Información Médica")
            lbl_allergies = language_service.t('label_allergies', language)
            lbl_chronic = language_service.t('label_chronic_diseases', language)
            lbl_meds = language_service.t('label_medications', language)
            
            response = f"""*{title}*

*{lbl_allergies}:*
{alergias_txt}

*{lbl_chronic}:*
{enfermedades_txt}

*{lbl_meds}:*
{medicamentos_txt}

{language_service.t('update_info_note', language)}

*9.* {back_mh}
*0.* {language_service.t('menu_opt_exit', language)}"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_alergias',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando detalles médicos: {e}")
            return self._error_response(language, "Volver")

    def _show_dental_history(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra historia dental (Tab 3)"""
        language = context.get('language', 'es')
        try:
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            back_mh = language_service.t('back_to_mh', language)
            
            if not result.get('success'):
                return self._error_response(language, back_mh)
            
            data = result.get('data', {})
            
            # Extract dental fields with translations for defaults
            motivo = self._get_field_robust(data, ['motivoConsulta', 'reasonForVisit'], language_service.t('reason_not_specified', language))
            ultima_visita = self._get_field_robust(data, ['ultimaVisitaDentista', 'lastDentalVisit'], language_service.t('last_visit_not_specified', language))
            dolor = self._get_field_robust(data, ['dolorBoca', 'dentalPain'], 'No')
            sangrado = self._get_field_robust(data, ['sangradoEncias', 'gumBleeding'], 'No')
            
            title = language_service.t('tab_dental', language, fallback="Historia Dental")
            lbl_reason = language_service.t('label_main_reason', language)
            lbl_last_visit = language_service.t('label_last_visit', language)
            lbl_pain = language_service.t('label_frequent_pain', language)
            lbl_bleeding = language_service.t('label_gum_bleeding', language)
            
            response = f"""*{title}*

*{lbl_reason}:* {motivo}
*{lbl_last_visit}:* {ultima_visita}
*{lbl_pain}* {dolor}
*{lbl_bleeding}* {sangrado}

*9.* {back_mh}
*0.* {language_service.t('menu_opt_exit', language)}"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_info_medica', # Reutilizamos paso
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando historia dental: {e}")
            return self._error_response(language, "Volver")

    def _show_medical_completeness(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra porcentaje de completitud (Tab 4)"""
        language = context.get('language', 'es')
        try:
            result = self.firebase_service.get_medical_history(user_id=user_id, phone=phone)
            back_mh = language_service.t('back_to_mh', language)
            
            if not result.get('success'):
                return self._error_response(language, back_mh)
            
            data = result.get('data', {})
            # Robust extraction of completeness
            completitud = self._get_field_robust(data, ['completeness', 'completitud'], 0)
            
            try:
                completitud = int(float(completitud))
            except:
                completitud = 0
            
            # Barra de progreso visual
            filled = int(completitud / 10)
            empty = 10 - filled
            barra = '█' * filled + '░' * empty
            
            if completitud >= 80:
                estado = language_service.t('status_excellent', language)
                mensaje = language_service.t('completeness_msg_high', language)
            elif completitud >= 40:
                estado = language_service.t('status_partial', language)
                mensaje = language_service.t('completeness_msg_med', language)
            else:
                estado = language_service.t('status_incomplete', language)
                mensaje = language_service.t('completeness_msg_low', language)
            
            response = f"""*{language_service.t('completeness_title', language)}*

{barra} *{completitud}%*

*{language_service.t('status', language)}:* {estado}

{mensaje}

{language_service.t('completeness_note', language)}

*9.* {back_mh}
*0.* {language_service.t('menu_opt_exit', language)}"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_completitud',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando completitud: {e}")
            return self._error_response(language, "Volver")

    def _error_response(self, language, back_text):
        return {
            'response': f"{language_service.t('error_fetch_info', language)}\n\n*9.* {back_text}\n*0.* {language_service.t('menu_opt_exit', language)}",
            'action': None,
            'next_step': 'menu_historial_medico',
            'mode': 'menu'
        }

    # ============================================================
    # HELPER METHODS FOR REVIEWS SUBMENU (Option 6)
    # ============================================================
    
    def _show_user_reviews(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra las reseñas escritas por el usuario"""
        language = context.get('language', 'es')
        try:
            reviews = self.firebase_service.get_user_reviews(user_id=user_id, phone=phone)
            
            back_rev = language_service.t('back_to_reviews', language)
            back_main = language_service.t('menu_opt_exit', language)
            
            if not reviews:
                return {
                    'response': f"*{language_service.t('reviews_opt_my_reviews', language)}*\n\n{language_service.t('no_reviews_yet', language)}\n\n*9.* {back_rev}\n*0.* {back_main}",
                    'action': None,
                    'next_step': 'submenu_mis_resenas',
                    'mode': 'menu'
                }
            
            reviews_texto = '\n'.join([
                f"- {r.get('dentista', 'Dentista')} - {r.get('calificacion', 0)}/5 ({r.get('fecha', '')})"
                for r in reviews[:5]
            ])
            
            response = f"""*My Reviews*

{reviews_texto}

Total: {len(reviews)}

*9.* {back_rev}
*0.* {back_main}"""

            return {
                'response': response,
                'action': None,
                'next_step': 'submenu_mis_resenas',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando reseñas: {e}")
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n*9.* {language_service.t('back_to_reviews', language)}\n*0.* {language_service.t('menu_opt_exit', language)}",
                'action': None,
                'next_step': 'submenu_mis_resenas',
                'mode': 'menu'
            }
    
    def _show_pending_reviews_to_rate(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra citas pendientes de calificar"""
        language = context.get('language', 'es')
        try:
            pending = self.firebase_service.get_pending_reviews(user_id=user_id, phone=phone)
            context['citas_pendientes_resena'] = pending
            
            back_rev = language_service.t('back_to_reviews', language)
            back_main = language_service.t('menu_opt_exit', language)
            
            if not pending:
                return {
                    'response': f"*{language_service.t('reviews_opt_rate', language)}*\n\n{language_service.t('no_pending_reviews', language)}\n\n*9.* {back_rev}\n*0.* {back_main}",
                    'action': None,
                    'next_step': 'submenu_mis_resenas',
                    'mode': 'menu'
                }
            
            context['step'] = 'seleccionando_cita_calificar'
            
            citas_texto = '\n'.join([
                f"*{i+1}.* {c.get('fecha', '')} - {c.get('dentista', 'Dentista')}"
                for i, c in enumerate(pending[:5])
            ])
            
            response = f"""*{language_service.t('reviews_opt_rate', language)}*

{language_service.t('select_review_prompt', language)}

{citas_texto}

*0.* {language_service.t('back', language)}

{language_service.t('type_number', language)}"""

            return {
                'response': response,
                'action': 'show_pending_reviews',
                'next_step': 'seleccionando_cita_calificar',
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error mostrando citas pendientes: {e}")
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
    
    def _show_reviews_info(self, context: Dict) -> Dict:
        """Muestra información sobre cómo funcionan las reseñas"""
        language = context.get('language', 'es')
        
        back_rev = language_service.t('back_to_reviews', language)
        back_main = language_service.t('menu_opt_exit', language)
        
        response = f"""*{language_service.t('reviews_info_title', language)}*

{language_service.t('reviews_info_content', language)}

*9.* {back_rev}
*0.* {back_main}"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_info_resenas',
            'mode': 'menu'
        }
    
    def _submit_review(self, session_id: str, context: Dict, user_id: str, phone: str, anonimo: bool) -> Dict:
        """Envía la reseña a la base de datos"""
        language = context.get('language', 'es')
        try:
            cita = context.get('cita_a_calificar', {})
            calificacion = context.get('calificacion_seleccionada', 0)
            
            if not cita or not calificacion:
                return {
                    'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
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
                msg = language_service.t('review_thanks_anon', language) if anonimo else language_service.t('review_thanks', language)
                return {
                    'response': f'*{msg}*\n\n{language_service.t("review_rating_saved", language, rating=calificacion)}\n\n{self.get_main_menu(language)}',
                    'action': 'review_submitted',
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
            else:
                return {
                    'response': f"Error: {result.get('error', 'Error desconocido')}\n\n{language_service.t('type_menu', language)}",
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
        except Exception as e:
            print(f"Error enviando reseña: {e}")
            return {
                'response': f"{language_service.t('error_generic', language)}\n\n{language_service.t('type_menu', language)}",
                'action': None,
                'next_step': 'menu_principal',
                'mode': 'menu'
            }

    # ============================================================
    # HELPER METHODS FOR HELP SUBMENU (Option 7)
    # ============================================================
    
    def _show_faq(self, context: Dict) -> Dict:
        """Muestra preguntas frecuentes"""
        language = context.get('language', 'es')
        back_help = language_service.t('back_to_help', language)
        back_main = language_service.t('menu_opt_exit', language)
        
        response = f"""*{language_service.t('faq_title', language)}*

*{language_service.t('faq_q1', language)}*
{language_service.t('faq_a1', language)}

*{language_service.t('faq_q2', language)}*
{language_service.t('faq_a2', language)}

*{language_service.t('faq_q3', language)}*
{language_service.t('faq_a3', language)}

*{language_service.t('faq_q4', language)}*
{language_service.t('faq_a4', language)}

*{language_service.t('faq_q5', language)}*
{language_service.t('faq_a5', language)}

*9.* {back_help}
*0.* {back_main}"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_faq',
            'mode': 'menu'
        }
    
    def _show_chatbot_guide(self, context: Dict) -> Dict:
        """Muestra guía de uso del chatbot"""
        language = context.get('language', 'es')
        back_help = language_service.t('back_to_help', language)
        back_main = language_service.t('menu_opt_exit', language)
        
        response = f"""*{language_service.t('guide_title', language)}*

{language_service.t('guide_intro', language)}

{language_service.t('guide_nav', language)}

{language_service.t('guide_back', language)}

{language_service.t('guide_options', language)}

*9.* {back_help}
*0.* {back_main}"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_guia',
            'mode': 'menu'
        }
    
    def _show_support_contact(self, context: Dict) -> Dict:
        """Muestra información de contacto de soporte"""
        language = context.get('language', 'es')
        back_help = language_service.t('back_to_help', language)
        back_main = language_service.t('menu_opt_exit', language)
        
        response = f"""*{language_service.t('support_contact_title', language)}*

{language_service.t('support_email', language)}: soporte@densora.com

{language_service.t('support_whatsapp', language)}: +52 55 1234 5678

{language_service.t('support_time', language)}

{language_service.t('support_emergency', language)}

*9.* {back_help}
*0.* {back_main}"""

        return {
            'response': response,
            'action': None,
            'next_step': 'submenu_contacto',
            'mode': 'menu'
        }
    
    def _show_support_hours(self, context: Dict) -> Dict:
        """Muestra horarios de atención"""
        language = context.get('language', 'es')
        
        response = f"""*{language_service.t('support_hours_title', language)}*

{language_service.t('support_hours_content', language)}

{language_service.t('type_menu', language)}"""

        return {
            'response': response,
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }

