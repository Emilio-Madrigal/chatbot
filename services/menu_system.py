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
        
        # Seleccionando servicio/tratamiento para agendar
        elif current_step == 'seleccionando_servicio':
            tratamientos = context.get('tratamientos_disponibles', [])
            if tratamientos and 0 <= button_num - 1 < len(tratamientos):
                tratamiento_seleccionado = tratamientos[button_num - 1]
                context['tratamiento_seleccionado'] = tratamiento_seleccionado
                context['step'] = 'seleccionando_fecha_agendar'
                # Obtener fechas disponibles
                return self._show_available_dates_for_appointment(context, user_id, phone)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(tratamientos)}.',
                    'action': None,
                    'next_step': current_step,
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
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(horarios)}.',
                    'action': None,
                    'next_step': current_step,
                    'mode': 'menu'
                }
        
        # Seleccionando método de pago
        elif current_step == 'seleccionando_metodo_pago':
            metodos_pago = [
                {'id': 'efectivo', 'nombre': 'Efectivo', 'descripcion': 'Pago al momento de la cita'},
                {'id': 'transferencia', 'nombre': 'Transferencia Bancaria', 'descripcion': 'Pago por transferencia (2 horas para confirmar)'},
                {'id': 'stripe', 'nombre': 'Tarjeta (Stripe)', 'descripcion': 'Pago con tarjeta de crédito/débito'}
            ]
            if 0 <= button_num - 1 < len(metodos_pago):
                metodo_pago = metodos_pago[button_num - 1]
                context['metodo_pago'] = metodo_pago
                context['step'] = 'seleccionando_historial_medico'
                return self._show_medical_history_options(context)
            else:
                return {
                    'response': f'Opción inválida. Por favor selecciona un número del 1 al {len(metodos_pago)}.',
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
                context['step'] = 'solicitando_otp'
                return self._request_otp_for_appointment(session_id, context, user_id, phone)
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
                    'response': 'Por favor selecciona:\n*1.* Confirmar y continuar\n*2.* Cancelar',
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
                slot_seleccionado = horarios[button_num - 1]
                # Extraer horaInicio del slot (puede ser dict o string)
                if isinstance(slot_seleccionado, dict):
                    hora_seleccionada = slot_seleccionado.get('horaInicio', slot_seleccionado.get('inicio', ''))
                else:
                    hora_seleccionada = str(slot_seleccionado)
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
        """Opción 1: Agendar cita - Flujo completo según requerimientos"""
        print(f"[MENU_SYSTEM] _handle_schedule_appointment - user_id={user_id}, phone={phone}")
        
        try:
            # Obtener último consultorio/dentista usado del paciente
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            paciente = None
            
            if user_id:
                paciente = cita_repo.obtener_paciente_por_id(user_id)
            elif phone:
                paciente = cita_repo.obtener_paciente_por_telefono(phone)
            
            ultimo_consultorio = None
            if paciente:
                ultimo_consultorio = cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
            
            # Si hay último consultorio, usarlo directamente y mostrar servicios
            if ultimo_consultorio:
                context['dentista_id'] = ultimo_consultorio.get('dentistaId')
                context['consultorio_id'] = ultimo_consultorio.get('consultorioId')
                context['dentista_name'] = ultimo_consultorio.get('dentistaName', 'Dentista')
                context['consultorio_name'] = ultimo_consultorio.get('consultorioName', 'Consultorio')
                context['step'] = 'seleccionando_servicio'
                
                # Obtener servicios/tratamientos disponibles
                tratamientos = self.actions_service.get_treatments_for_dentist(
                    context['dentista_id'],
                    context['consultorio_id']
                )
                context['tratamientos_disponibles'] = tratamientos
                
                if not tratamientos:
                    return {
                        'response': 'Lo siento, no hay servicios disponibles en este momento.\n\nEscribe "menu" para volver.',
                        'action': None,
                        'next_step': 'menu_principal',
                        'mode': 'menu'
                    }
                
                # Formatear servicios
                servicios_texto = '\n'.join([
                    f'*{i+1}.* {t["nombre"]}\n   ${t["precio"]:,.0f} MXN\n   {t["duracion"]} min\n   {t.get("descripcion", "")}'
                    for i, t in enumerate(tratamientos[:10])
                ])
                
                return {
                    'response': f'*Agendar Nueva Cita*\n\nDentista: {context["dentista_name"]}\nConsultorio: {context["consultorio_name"]}\n\n*Selecciona el motivo de consulta:*\n\n{servicios_texto}\n\nEscribe el *número* del servicio que deseas.',
                    'action': 'show_services',
                    'next_step': 'seleccionando_servicio',
                    'mode': 'menu'
                }
            else:
                # No hay último consultorio, mostrar opción de usar consultorio por defecto
                # Por ahora, buscar un consultorio activo
                consultorios = self.actions_service.get_consultorios_info(limit=1)
                if consultorios:
                    consultorio = consultorios[0]
                    # Buscar dentista del consultorio
                    dentistas_ref = self.db.collection('consultorio').document(consultorio['id']).collection('dentistas')
                    dentistas_query = dentistas_ref.where('activo', '==', True).limit(1)
                    dentistas_docs = list(dentistas_query.stream())
                    
                    if dentistas_docs:
                        dentista_data = dentistas_docs[0].to_dict()
                        context['dentista_id'] = dentista_data.get('dentistaId')
                        context['consultorio_id'] = consultorio['id']
                        context['dentista_name'] = dentista_data.get('nombreCompleto', 'Dentista')
                        context['consultorio_name'] = consultorio.get('nombre', 'Consultorio')
                        context['step'] = 'seleccionando_servicio'
                        
                        # Obtener servicios
                        tratamientos = self.actions_service.get_treatments_for_dentist(
                            context['dentista_id'],
                            context['consultorio_id']
                        )
                        context['tratamientos_disponibles'] = tratamientos
                        
                        if not tratamientos:
                            return {
                                'response': 'Lo siento, no hay servicios disponibles.\n\nEscribe "menu" para volver.',
                                'action': None,
                                'next_step': 'menu_principal',
                                'mode': 'menu'
                            }
                        
                        servicios_texto = '\n'.join([
                            f'*{i+1}.* {t["nombre"]}\n   ${t["precio"]:,.0f} MXN\n   {t["duracion"]} min\n   {t.get("descripcion", "")}'
                            for i, t in enumerate(tratamientos[:10])
                        ])
                        
                        return {
                            'response': f'*Agendar Nueva Cita*\n\nDentista: {context["dentista_name"]}\nConsultorio: {context["consultorio_name"]}\n\n*Selecciona el motivo de consulta:*\n\n{servicios_texto}\n\nEscribe el *número* del servicio que deseas.',
                            'action': 'show_services',
                            'next_step': 'seleccionando_servicio',
                            'mode': 'menu'
                        }
                
                return {
                    'response': 'Lo siento, no hay consultorios disponibles en este momento.\n\nPor favor, contacta directamente con el consultorio.\n\nEscribe "menu" para volver.',
                    'action': None,
                    'next_step': 'menu_principal',
                    'mode': 'menu'
                }
                
        except Exception as e:
            print(f"[MENU_SYSTEM] Error en _handle_schedule_appointment: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': 'Error al iniciar el agendamiento. Por favor intenta más tarde.\n\nEscribe "menu" para volver.',
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
        """Opción 5: Historial médico"""
        web_url = 'http://localhost:4321'  # TODO: obtener de config
        return {
            'response': f'*Historial Médico*\n\nPara acceder a tu historial médico, visita:\n\n{web_url}/historialMedico\n\nEscribe "menu" para volver al menú principal.',
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_reviews(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Opción 6: Reseñas y calificaciones"""
        web_url = 'http://localhost:4321'  # TODO: obtener de config
        return {
            'response': f'*Reseñas y Calificaciones*\n\nPara dejar una reseña o ver tus calificaciones, visita:\n\n{web_url}/mis-resenas\n\nEscribe "menu" para volver al menú principal.',
            'action': None,
            'next_step': 'menu_principal',
            'mode': 'menu'
        }
    
    def _handle_help(self, context: Dict) -> Dict:
        """Opción 7: Ayuda y soporte"""
        return {
            'response': f'*Ayuda y Soporte*\n\n{self.get_main_menu()}\n\n*Contacto:*\nsoporte@densora.com\n+52 55 1234 5678\n\n*Horario:*\nLun-Vie: 9:00 AM - 6:00 PM\nSáb: 9:00 AM - 2:00 PM',
            'action': None,
            'next_step': 'menu_principal',
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
                'response': f'*Selecciona una fecha disponible:*\n\n{fechas_texto}\n\nEscribe el *número* de la fecha que deseas.',
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
        metodos_texto = """*Selecciona el método de pago:*

*1.* Efectivo
   Pago al momento de la cita

*2.* Transferencia Bancaria
   Pago por transferencia (2 horas para confirmar con comprobante)

*3.* Tarjeta (Stripe)
   Pago con tarjeta de crédito/débito (pago inmediato)

Escribe el *número* del método de pago que deseas."""
        
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
            from google.cloud.firestore import Timestamp
            
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
                'otorgadoEn': Timestamp.now(),
                'otorgadoPor': 'paciente',
                'motivo': 'Otorgado durante agendamiento de cita',
                'updatedAt': Timestamp.now()
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
            # Convertir fecha string a datetime si es necesario
            if isinstance(fecha, str):
                fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
            else:
                fecha_dt = fecha
            
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
            
            # Convertir fecha a timestamp para el método
            from datetime import datetime
            fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
            from google.cloud.firestore import Timestamp
            fecha_timestamp_firestore = Timestamp.from_datetime(fecha_timestamp)
            
            horarios_slots = cita_repo.obtener_horarios_disponibles(
                dentista_id,
                consultorio_id,
                fecha_timestamp_firestore
            )
            
            # Convertir slots a formato de texto para mostrar
            if not horarios_slots or len(horarios_slots) == 0:
                return {
                    'response': 'Lo siento, no hay horarios disponibles para esta fecha.\n\nEscribe "menu" para volver al menú principal.',
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
                'response': f'*Selecciona un Horario*\n\nHorarios disponibles:\n\n{horarios_texto}\n\nEscribe el *número* del horario que deseas.',
                'action': 'show_times',
                'next_step': context['step'],
                'mode': 'menu'
            }
        except Exception as e:
            print(f"Error obteniendo horarios: {e}")
            import traceback
            traceback.print_exc()
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
                'response': f'*Selecciona Nueva Fecha*\n\nFechas disponibles:\n\n{fechas_texto}\n\nEscribe el *número* de la fecha que deseas.',
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
*Método de Pago:* {metodo_pago.get('nombre', 'Efectivo')}
*Historial Médico:* {historial_texto}

Recibirás un recordatorio 24h antes de tu cita.

Para completar o actualizar tu historial médico, visita:
http://localhost:4321/historialMedico

Escribe "menu" para volver al menú principal."""
                
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

