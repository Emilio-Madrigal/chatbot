"""
GESTOR DE CONVERSACIONES - SOLO MENÚS
Sistema de menús estructurado sin IA/ML
"""

from services.menu_system import MenuSystem
from services.ml_service import MLService
from services.actions_service import ActionsService
from services.payment_service import PaymentService
from typing import Dict, Optional
from datetime import datetime

class ConversationManager:
    """
    Gestiona el flujo de conversación del chatbot con contexto y memoria
    """
    
    def __init__(self):
        self.ml_service = MLService()
        self.actions_service = ActionsService()
        self.payment_service = PaymentService()
        self.menu_system = MenuSystem()
        self.conversations = {}  # Almacena el contexto de cada conversación
    
    def get_conversation_context(self, session_id: str) -> Dict:
        """Obtiene el contexto de una conversación"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'step': 'menu_principal',
                'user_data': {},
                'history': [],
                'language': 'es',  # Idioma por defecto
                'created_at': datetime.now()
            }
        return self.conversations[session_id]
    
    def update_conversation_context(self, session_id: str, updates: Dict):
        """Actualiza el contexto de una conversación"""
        context = self.get_conversation_context(session_id)
        context.update(updates)
        context['updated_at'] = datetime.now()
    
    def add_to_history(self, session_id: str, role: str, message: str):
        """Agrega un mensaje al historial de la conversación"""
        context = self.get_conversation_context(session_id)
        context['history'].append({
            'role': role,  # 'user' o 'assistant'
            'message': message,
            'timestamp': datetime.now()
        })
        # Mantener solo los últimos 10 mensajes
        if len(context['history']) > 10:
            context['history'] = context['history'][-10:]
    
    def process_message(self, session_id: str, message: str, 
                       user_id: str = None, phone: str = None,
                       user_name: str = None, mode: str = None) -> Dict:
        """
        Procesa mensajes usando SOLO el sistema de menús estructurado
        Ignora el parámetro mode - siempre usa menús
        Sin IA/ML, solo opciones numeradas y flujos fijos
        """
        # Obtener contexto
        context = self.get_conversation_context(session_id)
        print(f"[CONVERSATION_MANAGER] process_message - session_id={session_id}, message='{message}', context_step={context.get('step')}, user_id={user_id}, phone={phone}")
        
        # Actualizar datos del usuario si están disponibles
        if user_id or phone:
            from services.actions_service import ActionsService
            actions_service = ActionsService()
            user_data = actions_service.get_user_info(user_id=user_id, phone=phone)
            if user_data:
                context['user_data'] = user_data
            elif user_name:
                context['user_data'] = {'nombre': user_name}
        
        # Agregar mensaje al historial
        self.add_to_history(session_id, 'user', message)
        
        # SIEMPRE usar sistema de menús - ignorar cualquier referencia a modo agente
        result = self.menu_system.process_message(session_id, message, context, user_id, phone)
        
        # Actualizar contexto con el siguiente paso
        if result.get('next_step'):
            self.update_conversation_context(session_id, {'step': result['next_step']})
        
        # Agregar respuesta al historial
        if result.get('response'):
            self.add_to_history(session_id, 'assistant', result['response'])
        
        # Siempre retornar modo 'menu'
        result['mode'] = 'menu'
        
        return result
    
    def _process_menu_mode(self, session_id: str, message: str, context: Dict,
                          user_id: str, phone: str) -> Dict:
        """Procesa mensajes en modo menú (flujo guiado)"""
        message_clean = message.strip()
        current_step = context.get('step', 'inicial')
        
        # Manejar respuestas numéricas primero (1, 2, 3, etc.)
        if message_clean.isdigit():
            button_num = int(message_clean)
            response_data = self._handle_numeric_response(session_id, button_num, context, user_id, phone)
            if response_data:
                if response_data.get('response'):
                    self.add_to_history(session_id, 'assistant', response_data['response'])
                return response_data
        
        # Si no es número, usar ML para detectar intención
        intent_result = self.ml_service.classify_intent(message, context)
        intent = intent_result['intent']
        confidence = intent_result.get('confidence', 0.5)
        
        # Si detecta una intención clara de agendar/reagendar/cancelar/ver citas, procesarla
        # Aunque esté en modo menú, si el usuario habla naturalmente, ayudarlo
        if intent in ['agendar_cita', 'reagendar_cita', 'cancelar_cita', 'ver_citas'] and confidence > 0.6:
            print(f"Modo menú detectó intención clara: {intent} (confianza: {confidence})")
            entities = self.ml_service.extract_entities(message, intent, context)
            response_data = self._handle_intent(session_id, intent, entities, context)
            if response_data.get('response'):
                self.add_to_history(session_id, 'assistant', response_data['response'])
            return response_data
        
        # En modo menú, procesar intenciones básicas
        if intent in ['saludar', 'ayuda']:
            entities = self.ml_service.extract_entities(message, intent, context)
            response_data = self._handle_intent(session_id, intent, entities, context)
            if response_data.get('response'):
                self.add_to_history(session_id, 'assistant', response_data['response'])
            return response_data
        
        # Para otras intenciones, sugerir usar números
        return {
            'response': 'En modo menú, por favor usa números para navegar:\n\n1. Agendar una cita\n2. Ver tus citas\n3. Reagendar una cita\n4. Cancelar una cita\n5. Información\n\nO escribe "modo agente" para conversación natural.',
            'action': None,
            'next_step': current_step
        }
    
    def _process_agent_mode(self, session_id: str, message: str, context: Dict,
                           user_id: str, phone: str) -> Dict:
        """Procesa mensajes en modo agente (ML completo)"""
        # Clasificar intención usando ML completo
        intent_result = self.ml_service.classify_intent(message, context)
        intent = intent_result['intent']
        confidence = intent_result['confidence']
        
        # Extraer entidades con contexto mejorado
        entities = self.ml_service.extract_entities(message, intent, context)
        
        # Actualizar contexto
        context['intent'] = intent
        context['entities'].update(entities)
        
        # Obtener historial de conversación para contexto mejorado
        conversation_history = context.get('history', [])
        
        # Si la intención es clara y confiable, procesarla directamente
        if confidence > 0.7 and intent in ['agendar_cita', 'reagendar_cita', 'cancelar_cita', 'ver_citas']:
            response_data = self._handle_intent(session_id, intent, entities, context)
            # Mejorar respuesta con IA si es genérica
            if response_data.get('response') and len(response_data['response']) < 100:
                ai_response = self.ml_service.generate_response(
                    intent, entities, context, context.get('user_data'), conversation_history
                )
                if ai_response and len(ai_response) > len(response_data['response']):
                    response_data['response'] = ai_response
        else:
            # Generar respuesta usando ML mejorado con historial completo
            response = self.ml_service.generate_response(
                intent, entities, context, context.get('user_data'), conversation_history
            )
            
            # Si la intención es agendar/reagendar/cancelar pero no es clara, intentar procesarla
            if intent in ['agendar_cita', 'reagendar_cita', 'cancelar_cita']:
                response_data = self._handle_intent(session_id, intent, entities, context)
                # Mejorar respuesta con IA
                if response and len(response) > len(response_data.get('response', '')):
                    response_data['response'] = response
            else:
                # Para otras intenciones, usar respuesta generada por ML
                response_data = {
                    'response': response,
                    'action': None,
                    'next_step': context.get('step', 'inicial')
                }
        
        # Agregar respuesta al historial
        if response_data.get('response'):
            self.add_to_history(session_id, 'assistant', response_data['response'])
        
        return response_data
    
    def _handle_numeric_response(self, session_id: str, button_num: int, 
                                context: Dict, user_id: str, phone: str) -> Optional[Dict]:
        """Maneja respuestas numéricas según el contexto actual"""
        current_step = context.get('step', 'inicial')
        
        # Mapear según el contexto
        if current_step == 'menu_principal' or current_step == 'inicial' or current_step == 'ayuda':
            if button_num == 1:
                self.update_conversation_context(session_id, {'step': 'agendando'})
                return self._handle_schedule_appointment(session_id, {}, context, user_id, phone)
            elif button_num == 2:
                self.update_conversation_context(session_id, {'step': 'viendo_citas'})
                return self._handle_view_appointments(context, user_id, phone)
            elif button_num == 3:
                self.update_conversation_context(session_id, {'step': 'reagendando'})
                return self._handle_reschedule_appointment(session_id, {}, context, user_id, phone)
            elif button_num == 4:
                self.update_conversation_context(session_id, {'step': 'cancelando'})
                return self._handle_cancel_appointment(session_id, {}, context, user_id, phone)
            elif button_num == 5:
                self.update_conversation_context(session_id, {'step': 'menu_principal'})
                return self._handle_help(context, {})
            else:
                return {
                    'response': 'Opción inválida. Por favor selecciona un número del 1 al 5.',
                    'action': None,
                    'next_step': current_step
                }
        elif current_step == 'seleccionando_fecha' or current_step == 'reagendando_fecha' or current_step == 'agendando':
            # Obtener fechas disponibles del contexto o buscarlas
            fechas = context.get('entities', {}).get('fechas_disponibles', [])
            if not fechas:
                # Si no hay fechas en el contexto, buscarlas
                fechas = self.actions_service.get_available_dates(user_id=user_id, phone=phone, count=5)
            
            if fechas and 0 <= button_num - 1 < len(fechas):
                fecha = fechas[button_num - 1]
                entities = {'fecha': fecha, 'numero_cita': button_num}
                context['entities']['fechas_disponibles'] = fechas
                if current_step == 'reagendando_fecha':
                    return self._handle_reschedule_appointment(session_id, entities, context, user_id, phone)
                else:
                    return self._handle_select_date(session_id, entities, context, user_id, phone)
        elif current_step == 'selecionando_hora' or current_step == 'reagendando_hora':
            # Obtener horarios disponibles del contexto
            horarios = context.get('entities', {}).get('horarios_disponibles', [])
            if horarios and 0 <= button_num - 1 < len(horarios):
                hora = horarios[button_num - 1]
                entities = {'hora': hora, 'numero_cita': button_num}
                if current_step == 'reagendando_hora':
                    return self._handle_reschedule_appointment(session_id, entities, context, user_id, phone)
                else:
                    return self._handle_select_time(session_id, entities, context, user_id, phone)
        elif current_step == 'seleccionando_cita_reagendar' or current_step == 'reagendando':
            # Obtener citas del contexto o buscarlas
            citas = context.get('entities', {}).get('citas', [])
            if not citas:
                citas = self.actions_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
                context['entities']['citas'] = citas
            
            if citas and 0 <= button_num - 1 < len(citas):
                cita_id = citas[button_num - 1]['id']
                self.update_conversation_context(session_id, {
                    'step': 'reagendando_fecha',
                    'cita_id': cita_id
                })
                return self._handle_reschedule_appointment(session_id, {}, context, user_id, phone)
        elif current_step == 'seleccionando_cita_cancelar' or current_step == 'cancelando':
            # Obtener citas del contexto o buscarlas
            citas = context.get('entities', {}).get('citas', [])
            if not citas:
                citas = self.actions_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
                context['entities']['citas'] = citas
            
            if citas and 0 <= button_num - 1 < len(citas):
                cita_id = citas[button_num - 1]['id']
                self.update_conversation_context(session_id, {
                    'step': 'confirmando_cancelacion',
                    'cita_id': cita_id
                })
                return self._handle_cancel_appointment(session_id, {}, context, user_id, phone)
        
        return None
    
    def _handle_intent(self, session_id: str, intent: str, entities: Dict, 
                      context: Dict) -> Dict:
        """Maneja cada intención y genera la respuesta apropiada"""
        user_data = context.get('user_data', {})
        user_id = user_data.get('uid')
        phone = user_data.get('telefono')
        current_step = context.get('step', 'inicial')
        
        # Manejar según intención
        if intent == 'saludar':
            result = self._handle_greeting(context)
            self.update_conversation_context(session_id, {'step': 'menu_principal'})
            return result
        
        elif intent == 'ayuda' or intent == 'consultar_informacion':
            result = self._handle_help(context, entities)
            self.update_conversation_context(session_id, {'step': 'menu_principal'})
            return result
        
        # J.RF12: Procesamiento mejorado de palabras clave específicas
        elif intent == 'contacto' or 'contacto' in message_lower or 'contact' in message_lower:
            return {
                'response': 'Para contactarnos:\n\nTeléfono: [Número de contacto]\nEmail: contacto@densora.com\nWeb: www.densora.com\n\n¿Necesitas algo más?',
                'action': None,
                'next_step': 'inicial'
            }
        
        elif intent == 'agendar_cita':
            return self._handle_schedule_appointment(session_id, entities, context, user_id, phone)
        
        elif intent == 'reagendar_cita':
            return self._handle_reschedule_appointment(session_id, entities, context, user_id, phone)
        
        elif intent == 'cancelar_cita':
            return self._handle_cancel_appointment(session_id, entities, context, user_id, phone)
        
        elif intent == 'ver_citas':
            return self._handle_view_appointments(context, user_id, phone)
        
        elif intent == 'seleccionar_fecha':
            return self._handle_select_date(session_id, entities, context, user_id, phone)
        
        elif intent == 'seleccionar_hora':
            return self._handle_select_time(session_id, entities, context, user_id, phone)
        
        elif intent == 'confirmar_pago':
            return self._handle_confirm_payment(session_id, entities, context, user_id, phone)
        
        elif intent == 'consultar_tiempo_pago':
            return self._handle_check_payment_time(context, user_id, phone)
        
        elif intent == 'consultar_servicios':
            return self._handle_services_info(context)
        
        elif intent == 'ver_historial':
            return self._handle_appointment_history(context, user_id, phone)
        
        elif intent == 'contacto':
            return {
                'response': 'Para contactarnos:\n\nTeléfono: [Número de contacto]\nEmail: contacto@densora.com\nWeb: www.densora.com\nUbicación: [Dirección]\n\n¿Necesitas algo más?',
                'action': None,
                'next_step': 'inicial'
            }
        
        elif intent == 'confirmar_pago':
            return self._handle_confirm_payment(context, user_id, phone)
        
        elif intent == 'consultar_tiempo_pago':
            return self._handle_check_payment_time(context, user_id, phone)
        
        elif intent == 'informacion_servicios':
            return self._handle_services_info(context, entities)
        
        elif intent == 'despedirse':
            return {
                'response': '¡Hasta luego! Que tengas un excelente día.',
                'action': None,
                'next_step': 'inicial'
            }
        
        else:
            # Intención no reconocida
            return {
                'response': self.ml_service.generate_response('otro', entities, context, user_data),
                'action': None,
                'next_step': current_step
            }
    
    def _handle_greeting(self, context: Dict) -> Dict:
        """Maneja saludos"""
        # Necesitamos el session_id para actualizar el contexto
        # Lo pasamos desde _handle_intent
        user_data = context.get('user_data', {})
        nombre = user_data.get('nombre', '')
        saludo = f"Hola {nombre}, " if nombre else "Hola, "
        current_mode = context.get('mode', 'menu')
        
        if current_mode == 'menu':
            response = f"""{saludo}Puedo ayudarte con:

1. Agendar una cita
2. Ver tus citas
3. Reagendar una cita
4. Cancelar una cita
5. Información sobre nuestros servicios

¿Qué te gustaría hacer?

Escribe "modo agente" para conversación natural."""
        else:
            response = f"""{saludo}¡Bienvenido a Densora!

Soy Densorita, tu asistente virtual. Puedo ayudarte a:
• Agendar citas
• Ver tus citas programadas
• Reagendar o cancelar citas
• Responder preguntas sobre nuestros servicios

¿En qué puedo ayudarte hoy?"""
        
        return {
            'response': response,
            'action': None,
            'next_step': 'menu_principal' if current_mode == 'menu' else 'inicial'
        }
    
    def _handle_help(self, context: Dict, entities: Dict) -> Dict:
        """Maneja solicitudes de ayuda"""
        question = entities.get('motivo', '')
        if question:
            # Intentar responder la pregunta específica
            answer = self.ml_service.answer_question(question)
            response = answer
        else:
            user_data = context.get('user_data', {})
            nombre = user_data.get('nombre', '')
            saludo = f"Hola {nombre}, " if nombre else "Hola, "
            response = f"""{saludo}Puedo ayudarte con:

1. Agendar una cita
2. Ver tus citas
3. Reagendar una cita
4. Cancelar una cita
5. Información sobre nuestros servicios

¿Qué te gustaría hacer?"""
        
        return {
            'response': response,
            'action': None,
            'next_step': 'menu_principal'
        }
    
    def _handle_schedule_appointment(self, session_id: str, entities: Dict, 
                                   context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja el agendamiento de citas - MODO INTELIGENTE"""
        current_step = context.get('step', 'inicial')
        current_mode = context.get('mode', 'menu')
        
        # Validar y convertir fecha si es relativa
        fecha = entities.get('fecha') or context.get('entities', {}).get('fecha') or context.get('fecha_seleccionada')
        hora = entities.get('hora') or context.get('hora_seleccionada')
        nombre = entities.get('nombre_cliente') or context.get('nombre_cliente') or context.get('user_data', {}).get('nombre', 'Paciente')
        motivo = entities.get('motivo') or context.get('motivo', 'Consulta general')
        
        if fecha:
            from datetime import datetime, timedelta
            if isinstance(fecha, str):
                fecha_lower = fecha.lower().strip()
                # Si es fecha relativa, convertirla
                if fecha_lower in ['mañana', 'tomorrow']:
                    fecha = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    print(f"Fecha relativa convertida: 'mañana' -> {fecha}")
                elif fecha_lower in ['pasado mañana', 'day after tomorrow']:
                    fecha = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
                    print(f"Fecha relativa convertida: 'pasado mañana' -> {fecha}")
                elif fecha_lower in ['hoy', 'today']:
                    fecha = datetime.now().strftime('%Y-%m-%d')
                    print(f"Fecha relativa convertida: 'hoy' -> {fecha}")
                
                # Validar formato
                try:
                    datetime.strptime(fecha, '%Y-%m-%d')
                except ValueError:
                    # Si no es formato válido, pedir fecha específica
                    return {
                        'response': "No pude entender la fecha que mencionaste. Por favor, proporciona la fecha en formato día/mes/año (ej: 14/11/2025) o di 'mañana', 'hoy', etc.",
                        'action': None,
                        'next_step': 'seleccionando_fecha'
                    }
        
        # ========== CASO 1: TENEMOS FECHA Y HORA ==========
        # Si el usuario dio fecha Y hora desde el principio, CREAR LA CITA DIRECTAMENTE
        if fecha and hora:
            print(f"CASO COMPLETO: Tenemos fecha ({fecha}) y hora ({hora}), creando cita directamente...")
            
            # Validar que la hora esté disponible
            horarios_disponibles = self.actions_service.get_available_times(
                user_id=user_id,
                phone=phone,
                fecha=fecha,
                nombre_dentista=entities.get('nombre_dentista')
            )
            
            if not horarios_disponibles:
                return {
                    'response': f"Lo siento, no hay horarios disponibles para el {fecha}.\n\n¿Te gustaría elegir otra fecha?",
                    'action': None,
                    'next_step': 'seleccionando_fecha'
                }
            
            # Verificar que la hora solicitada esté disponible
            if hora not in horarios_disponibles:
                horarios_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(horarios_disponibles[:5])])
                return {
                    'response': f"La hora {hora} no está disponible para el {fecha}.\n\nHorarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres?",
                    'action': None,
                    'next_step': 'selecionando_hora',
                    'entities': {'fecha': fecha, 'horarios_disponibles': horarios_disponibles}
                }
            
            # ¡CREAR LA CITA DIRECTAMENTE!
            result = self.actions_service.create_appointment(
                user_id=user_id,
                phone=phone,
                fecha=fecha,
                hora=hora,
                nombre_cliente=nombre,
                motivo=motivo,
                nombre_dentista=entities.get('nombre_dentista')  # Pasar nombre del dentista si se mencionó
            )
            
            if result.get('success'):
                # Obtener nombre del dentista usado (del resultado, no de entities)
                dentista_usado = result.get('dentista_name', entities.get('nombre_dentista', 'tu dentista'))
                consultorio_usado = result.get('consultorio_name', 'Consultorio')
                self.update_conversation_context(session_id, {'step': 'inicial', 'mode': current_mode})
                
                # Agregar información de pago si aplica
                payment_info = ""
                payment_deadline = result.get('payment_deadline')
                payment_method = result.get('payment_method', 'cash')
                
                # Solo mostrar advertencia si hay deadline (transferencias, paypal, etc)
                if payment_deadline and payment_method.lower() in ['transfer', 'transferencia', 'paypal', 'mercadopago']:
                    # Calcular horas restantes
                    from datetime import datetime
                    if isinstance(payment_deadline, str):
                        deadline_dt = datetime.fromisoformat(payment_deadline)
                    else:
                        deadline_dt = payment_deadline
                    hours_remaining = int((deadline_dt - datetime.now()).total_seconds() / 3600)
                    payment_info = f"\n\nIMPORTANTE: Esta cita requiere confirmación de pago por {payment_method} dentro de las próximas {hours_remaining} horas. De lo contrario, será cancelada automáticamente."
                elif payment_method.lower() in ['cash', 'efectivo']:
                    payment_info = f"\n\nMétodo de pago: Efectivo (se paga al momento de la cita)"
                
                response_text = f"¡Perfecto! Tu cita ha sido agendada exitosamente.\n\nFecha: {fecha}\nHora: {hora}\nDentista: {dentista_usado}\nConsultorio: {consultorio_usado}\nPaciente: {nombre}\nMotivo: {motivo}{payment_info}\n\nTe enviaremos un recordatorio antes de tu cita. ¡Gracias por usar Densora!"
                print(f"Cita creada exitosamente, retornando respuesta: {response_text[:100]}...")
                return {
                    'response': response_text,
                    'action': 'appointment_created',
                    'next_step': 'inicial'
                }
            else:
                error_msg = result.get('error', 'Error desconocido')
                print(f"Error creando cita: {error_msg}")
                return {
                    'response': f"Lo siento, no pude agendar tu cita: {error_msg}\n\nPor favor intenta nuevamente.",
                    'action': None,
                    'next_step': 'inicial'
                }
        
        # ========== CASO 2: SOLO TENEMOS FECHA ==========
        # Si tenemos fecha pero no hora, mostrar horarios disponibles
        if fecha and not hora:
            print(f"CASO PARCIAL: Tenemos fecha ({fecha}) pero no hora, mostrando horarios...")
            
            self.update_conversation_context(session_id, {
                'step': 'selecionando_hora',
                'fecha_seleccionada': fecha,
                'motivo': motivo,
                'nombre_cliente': nombre
            })
            
            # Obtener horarios disponibles
            horarios = self.actions_service.get_available_times(
                user_id=user_id,
                phone=phone,
                fecha=fecha,
                nombre_dentista=entities.get('nombre_dentista')
            )
            
            if horarios:
                horarios_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(horarios[:5])])
                self.update_conversation_context(session_id, {
                    'entities': {'fecha': fecha, 'horarios_disponibles': horarios}
                })
                return {
                    'response': f"Fecha seleccionada: {fecha}\n\nHorarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres? (Escribe el número o la hora)",
                    'action': None,
                    'next_step': 'selecionando_hora',
                    'entities': {'fecha': fecha, 'horarios_disponibles': horarios}
                }
            else:
                return {
                    'response': f"Lo siento, no hay horarios disponibles para el {fecha}.\n\n¿Te gustaría elegir otra fecha?",
                    'action': None,
                    'next_step': 'seleccionando_fecha'
                }
        
        # Si no tenemos fecha, pedir fecha
        fechas = self.actions_service.get_available_dates(user_id=user_id, phone=phone, count=5)
        if fechas:
            from datetime import datetime, timedelta
            # Formatear fechas para mostrar
            fechas_formateadas = []
            for fecha_str in fechas:
                try:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
                    fecha_display = fecha_obj.strftime('%d/%m/%Y')
                    fechas_formateadas.append(fecha_display)
                except:
                    fechas_formateadas.append(fecha_str)
            
            fechas_text = "\n".join([f"{i+1}. {f}" for i, f in enumerate(fechas_formateadas)])
            self.update_conversation_context(session_id, {
                'step': 'seleccionando_fecha',
                'entities': {'fechas_disponibles': fechas}
            })
            return {
                'response': f"¡Perfecto! Te ayudo a agendar tu cita.\n\nFechas disponibles:\n{fechas_text}\n\n¿Qué fecha prefieres? (Escribe el número o la fecha)",
                'action': None,
                'next_step': 'seleccionando_fecha',
                'entities': {'fechas_disponibles': fechas}
            }
        else:
            return {
                'response': "Lo siento, no hay fechas disponibles en este momento.\n\nEsto puede deberse a que:\n• No tienes un consultorio asociado\n• No hay horarios configurados\n\nPor favor contacta directamente con el consultorio o intenta más tarde.\n\nEscribe *menu* para ver otras opciones.",
                'action': None,
                'next_step': 'menu_principal'
            }
    
    def _handle_reschedule_appointment(self, session_id: str, entities: Dict,
                                     context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja el reagendamiento de citas"""
        current_step = context.get('step', 'inicial')
        
        # Si ya tenemos nueva fecha y hora, reagendar
        if current_step == 'reagendando_hora' and entities.get('hora'):
            cita_id = context.get('cita_id')
            nueva_fecha = context.get('nueva_fecha')
            nueva_hora = entities.get('hora')
            
            if cita_id and nueva_fecha and nueva_hora:
                result = self.actions_service.reschedule_appointment(
                    user_id=user_id,
                    phone=phone,
                    cita_id=cita_id,
                    nueva_fecha=nueva_fecha,
                    nueva_hora=nueva_hora
                )
                
                if result['success']:
                    self.update_conversation_context(session_id, {'step': 'inicial'})
                    return {
                        'response': f"¡Perfecto! Tu cita ha sido reagendada exitosamente.\n\nNueva fecha: {nueva_fecha}\nNueva hora: {nueva_hora}\n\nTe enviaremos un recordatorio antes de tu cita.",
                        'action': 'appointment_rescheduled',
                        'next_step': 'inicial'
                    }
                else:
                    return {
                        'response': f"No pude reagendar tu cita: {result.get('error', 'Error desconocido')}",
                        'action': None,
                        'next_step': current_step
                    }
        
        # Si tenemos nueva fecha pero no hora, pedir hora
        if current_step == 'reagendando_fecha' or entities.get('fecha'):
            nueva_fecha = entities.get('fecha')
            cita_id = context.get('cita_id')
            
            if nueva_fecha and cita_id:
                self.update_conversation_context(session_id, {
                    'step': 'reagendando_hora',
                    'nueva_fecha': nueva_fecha
                })
                
                horarios = self.actions_service.get_available_times(
                    user_id=user_id,
                    phone=phone,
                    fecha=nueva_fecha
                )
                
                if horarios:
                    horarios_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(horarios[:5])])
                    return {
                        'response': f"Nueva fecha seleccionada: {nueva_fecha}\n\nHorarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres?",
                        'action': None,
                        'next_step': 'reagendando_hora',
                        'entities': {'fecha': nueva_fecha, 'horarios_disponibles': horarios}
                    }
        
        # Si no tenemos cita seleccionada, mostrar citas
        citas = self.actions_service.get_user_appointments(
            user_id=user_id,
            phone=phone,
            status='confirmado'
        )
        
        if not citas:
            return {
                'response': "No tienes citas programadas para reagendar.\n\nEscribe *menu* para ver las opciones disponibles.",
                'action': None,
                'next_step': 'menu_principal'
            }
        
        # Si hay número de cita en entidades, usarlo
        if entities.get('numero_cita'):
            cita_num = entities['numero_cita'] - 1
            if 0 <= cita_num < len(citas):
                cita_id = citas[cita_num]['id']
                self.update_conversation_context(session_id, {
                    'step': 'reagendando_fecha',
                    'cita_id': cita_id
                })
                
                fechas = self.actions_service.get_available_dates(user_id=user_id, phone=phone, count=5)
                if fechas:
                    fechas_text = "\n".join([f"{i+1}. {f}" for i, f in enumerate(fechas)])
                    return {
                        'response': f"Reagendando cita de {citas[cita_num]['fecha']} {citas[cita_num]['hora']}\n\nFechas disponibles:\n{fechas_text}\n\n¿Qué fecha prefieres?",
                        'action': None,
                        'next_step': 'reagendando_fecha',
                        'entities': {'fechas_disponibles': fechas}
                    }
        
        # Mostrar lista de citas
        citas_text = "\n".join([
            f"{i+1}. {c['fecha']} {c['hora']} - {c['nombre']}"
            for i, c in enumerate(citas)
        ])
        
        return {
            'response': f"Reagendar Cita\n\nTus citas programadas:\n{citas_text}\n\n¿Cuál cita quieres reagendar? (Escribe el número)",
            'action': None,
            'next_step': 'seleccionando_cita_reagendar',
            'entities': {'citas': citas}
        }
    
    def _handle_cancel_appointment(self, session_id: str, entities: Dict,
                                   context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja la cancelación de citas"""
        current_step = context.get('step', 'inicial')
        
        # Si estamos confirmando cancelación
        if current_step == 'confirmando_cancelacion':
            cita_id = context.get('cita_id')
            if cita_id:
                result = self.actions_service.cancel_appointment(
                    user_id=user_id,
                    phone=phone,
                    cita_id=cita_id
                )
                
                if result['success']:
                    self.update_conversation_context(session_id, {'step': 'inicial'})
                    return {
                        'response': "Tu cita ha sido cancelada exitosamente.\n\nSi necesitas agendar una nueva cita, escribe *menu*.",
                        'action': 'appointment_cancelled',
                        'next_step': 'inicial'
                    }
                else:
                    return {
                        'response': f"No pude cancelar tu cita: {result.get('error', 'Error desconocido')}",
                        'action': None,
                        'next_step': current_step
                    }
        
        # Si hay número de cita en entidades, usarlo
        if entities.get('numero_cita'):
            citas = self.actions_service.get_user_appointments(
                user_id=user_id,
                phone=phone,
                status='confirmado'
            )
            
            cita_num = entities['numero_cita'] - 1
            if 0 <= cita_num < len(citas):
                cita_id = citas[cita_num]['id']
                self.update_conversation_context(session_id, {
                    'step': 'confirmando_cancelacion',
                    'cita_id': cita_id
                })
                
                return {
                    'response': f"¿Estás seguro de que quieres cancelar esta cita?\n\n{citas[cita_num]['fecha']} {citas[cita_num]['hora']}\n{citas[cita_num]['nombre']}\n\nResponde *SI* para confirmar o *NO* para mantenerla.",
                    'action': None,
                    'next_step': 'confirmando_cancelacion'
                }
        
        # Mostrar lista de citas
        citas = self.actions_service.get_user_appointments(
            user_id=user_id,
            phone=phone,
            status='confirmado'
        )
        
        if not citas:
            return {
                'response': "No tienes citas programadas para cancelar.\n\nEscribe *menu* para ver las opciones disponibles.",
                'action': None,
                'next_step': 'menu_principal'
            }
        
        citas_text = "\n".join([
            f"{i+1}. {c['fecha']} {c['hora']} - {c['nombre']}"
            for i, c in enumerate(citas)
        ])
        
        return {
            'response': f"Cancelar Cita\n\nTus citas programadas:\n{citas_text}\n\n¿Cuál cita quieres cancelar? (Escribe el número)",
            'action': None,
            'next_step': 'seleccionando_cita_cancelar',
            'entities': {'citas': citas}
        }
    
    def _handle_view_appointments(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja la visualización de citas"""
        citas = self.actions_service.get_user_appointments(
            user_id=user_id,
            phone=phone
        )
        
        if not citas:
            return {
                'response': "No tienes citas programadas actualmente.\n\nEscribe *1* o *agendar cita* para agendar una nueva.",
                'action': None,
                'next_step': 'menu_principal'
            }
        
        # Formatear fechas para mostrar
        citas_text = []
        for i, c in enumerate(citas, 1):
            fecha_display = c['fecha']
            try:
                from datetime import datetime
                fecha_obj = datetime.strptime(c['fecha'], '%Y-%m-%d')
                fecha_display = fecha_obj.strftime('%d/%m/%Y')
            except:
                pass
            
            citas_text.append(f"{i}. {fecha_display} {c['hora']}\n   {c['nombre']}\n   {c['consultorio']}\n   {c['motivo']}\n   Estado: {c['estado']}")
        
        return {
            'response': f"Tus Citas Programadas:\n\n" + "\n\n".join(citas_text) + "\n\n¿Necesitas hacer algún cambio? Escribe *3* para reagendar o *4* para cancelar.",
            'action': None,
            'next_step': 'menu_principal'
        }
    
    def _handle_select_date(self, session_id: str, entities: Dict, context: Dict,
                           user_id: str, phone: str) -> Dict:
        """Maneja la selección de fecha"""
        fecha = entities.get('fecha')
        if not fecha:
            # Intentar extraer de número si hay fechas disponibles
            fechas = context.get('entities', {}).get('fechas_disponibles', [])
            if fechas and entities.get('numero_cita'):
                fecha_num = entities['numero_cita'] - 1
                if 0 <= fecha_num < len(fechas):
                    fecha = fechas[fecha_num]
        
        if fecha:
            self.update_conversation_context(session_id, {
                'step': 'selecionando_hora',
                'fecha_seleccionada': fecha
            })
            
            horarios = self.actions_service.get_available_times(
                user_id=user_id,
                phone=phone,
                fecha=fecha
            )
            
            if horarios:
                horarios_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(horarios[:5])])
                return {
                    'response': f"Fecha seleccionada: {fecha}\n\nHorarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres?",
                    'action': None,
                    'next_step': 'selecionando_hora',
                    'entities': {'fecha': fecha, 'horarios_disponibles': horarios}
                }
        
        return {
            'response': "Por favor selecciona una fecha válida.",
            'action': None,
            'next_step': 'seleccionando_fecha'
        }
    
    def _handle_select_time(self, session_id: str, entities: Dict, context: Dict,
                           user_id: str, phone: str) -> Dict:
        """Maneja la selección de hora"""
        hora = entities.get('hora')
        if not hora:
            # Intentar extraer de número si hay horarios disponibles
            horarios = context.get('entities', {}).get('horarios_disponibles', [])
            if horarios and entities.get('numero_cita'):
                hora_num = entities['numero_cita'] - 1
                if 0 <= hora_num < len(horarios):
                    hora = horarios[hora_num]
        
        fecha = context.get('fecha_seleccionada')
        if not fecha:
            # Intentar obtener de entidades
            fecha = entities.get('fecha')
        
        user_data = context.get('user_data', {})
        nombre = user_data.get('nombre', 'Paciente') if user_data else 'Paciente'
        motivo = context.get('motivo', 'Consulta general')
        
        if hora and fecha:
            # Crear cita
            result = self.actions_service.create_appointment(
                user_id=user_id,
                phone=phone,
                fecha=fecha,
                hora=hora,
                nombre_cliente=nombre,
                motivo=motivo
            )
            
            if result['success']:
                self.update_conversation_context(session_id, {'step': 'inicial'})
                # Formatear fecha para mostrar
                try:
                    from datetime import datetime
                    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
                    fecha_display = fecha_obj.strftime('%d/%m/%Y')
                except:
                    fecha_display = fecha
                
                return {
                    'response': f"¡Perfecto! Tu cita ha sido agendada exitosamente.\n\nFecha: {fecha_display}\nHora: {hora}\nPaciente: {nombre}\n\nTe enviaremos un recordatorio antes de tu cita.",
                    'action': 'appointment_created',
                    'next_step': 'inicial'
                }
            else:
                return {
                    'response': f"No pude agendar tu cita: {result.get('error', 'Error desconocido')}\n\nPor favor intenta nuevamente.",
                    'action': None,
                    'next_step': 'selecionando_hora'
                }
        
        return {
            'response': "Por favor selecciona una hora válida.",
            'action': None,
            'next_step': 'selecionando_hora'
        }
    
    def _handle_confirm_payment(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja confirmación de pago por parte del paciente - MEJORADO"""
        try:
            # Obtener citas con pago pendiente usando el PaymentService
            citas_pendientes = self.payment_service.get_citas_con_pago_pendiente(
                paciente_id=user_id,
                telefono=phone
            )
            
            if not citas_pendientes:
                return {
                    'response': "No tienes citas con pago pendiente.\n\nTodas tus citas están al día. ¿Hay algo más en lo que pueda ayudarte?",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Si solo hay una cita pendiente, procesarla directamente
            if len(citas_pendientes) == 1:
                cita = citas_pendientes[0]
                cita_id = cita.get('id')
                metodo_pago = cita.get('metodo_pago', 'transferencia')
                
                # Confirmar pago
                resultado = self.payment_service.confirmar_pago(
                    cita_id=cita_id,
                    metodo_confirmacion='chatbot'
                )
                
                if resultado.get('success'):
                    response = f"""¡Excelente! He registrado tu confirmación de pago.

Cita: {cita.get('fecha', 'N/A')} a las {cita.get('hora', 'N/A')}
Dentista: {cita.get('dentista', 'N/A')}
Método: {metodo_pago.title()}
Estado: Pendiente de verificación

Tu confirmación fue recibida. El consultorio verificará tu pago y te notificaremos cuando esté aprobado.

¿Necesitas ayuda con algo más?"""
                else:
                    response = f"{resultado.get('mensaje', 'Error al confirmar pago')}\n\nPor favor contacta al consultorio directamente."
                
                return {
                    'response': response,
                    'action': 'payment_confirmed' if resultado.get('success') else None,
                    'next_step': 'inicial'
                }
            
            # Si hay múltiples citas, pedir que especifique cuál
            citas_text = "\n".join([
                f"{i+1}. {c.get('fecha', 'N/A')} - {c.get('hora', 'N/A')}\n   Dentista: {c.get('dentista', 'N/A')}\n   ${c.get('precio', 0):.2f} ({c.get('metodo_pago', 'N/A').title()})"
                for i, c in enumerate(citas_pendientes)
            ])
            
            return {
                'response': f"Tienes {len(citas_pendientes)} citas con pago pendiente:\n\n{citas_text}\n\n¿Para cuál cita quieres confirmar el pago? (Escribe el número)",
                'action': None,
                'next_step': 'confirmando_pago'
            }
            
        except Exception as e:
            print(f"Error en _handle_confirm_payment: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': "Hubo un error al procesar tu confirmación. Por favor contacta directamente con el consultorio.",
                'action': None,
                'next_step': 'inicial'
            }
    
    def _handle_check_payment_time(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja consulta de tiempo restante para pagar - MEJORADO"""
        try:
            # Obtener citas con pago pendiente usando PaymentService
            citas_pendientes = self.payment_service.get_citas_con_pago_pendiente(
                paciente_id=user_id,
                telefono=phone
            )
            
            if not citas_pendientes:
                return {
                    'response': "No tienes citas con pago pendiente.\n\nTodas tus citas están al día.",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Calcular tiempo restante para cada cita
            response_text = "*Tiempo restante para pagar tus citas:*\n\n"
            
            for i, cita in enumerate(citas_pendientes, 1):
                fecha = cita.get('fecha', 'N/A')
                hora = cita.get('hora', 'N/A')
                metodo_pago = cita.get('metodo_pago', 'transferencia')
                
                # Calcular tiempo restante
                tiempo_info = self.payment_service.calcular_tiempo_restante_pago(
                    cita=cita,
                    metodo_pago=metodo_pago
                )
                
                mensaje_tiempo = tiempo_info.get('mensaje', 'Tiempo no disponible')
                tiene_tiempo = tiempo_info.get('tiene_tiempo', True)
                
                # Indicador de urgencia
                if not tiene_tiempo:
                    indicador = "[URGENTE]"
                elif tiempo_info.get('horas_restantes', 999) <= 2:
                    indicador = "[MUY PRONTO]"
                elif tiempo_info.get('horas_restantes', 999) <= 12:
                    indicador = "[PRONTO]"
                else:
                    indicador = "[OK]"
                
                response_text += f"{indicador} *Cita {i}:*\n"
                response_text += f"   Fecha: {fecha} a las {hora}\n"
                response_text += f"   Método: {metodo_pago.title()}\n"
                response_text += f"   {mensaje_tiempo}\n\n"
            
            response_text += "\n*Tip:* Escribe *'ya pagué'* cuando hayas completado el pago."
            
            # Mostrar instrucciones de pago si hay citas urgentes
            urgentes = [c for c in citas_pendientes if self.payment_service.calcular_tiempo_restante_pago(c, c.get('metodo_pago', 'transferencia')).get('horas_restantes', 999) <= 12]
            
            if urgentes:
                response_text += "\n\n*¡Tienes pagos urgentes!* Escribe *'cómo pagar'* para ver las instrucciones."
            
            return {
                'response': response_text,
                'action': None,
                'next_step': 'inicial'
            }
            
        except Exception as e:
            print(f"Error en _handle_check_payment_time: {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': "Hubo un error al consultar el tiempo restante. Por favor intenta nuevamente.",
                'action': None,
                'next_step': 'inicial'
            }
    
    def _handle_services_info(self, context: Dict, entities: Dict = None) -> Dict:
        """Maneja consulta de información de servicios"""
        servicios = """Servicios Dentales Disponibles:

Servicios Generales:
• Consulta general y diagnóstico
• Limpieza dental (profilaxis)
• Blanqueamiento dental
• Resinas (empastes estéticos)
• Extracciones simples y complejas

Especialidades:
• Ortodoncia (brackets y alineadores)
• Endodoncia (tratamiento de conductos)
• Prótesis dentales
• Periodoncia (encías)
• Odontopediatría (niños)
• Implantes dentales

Tratamientos Estéticos:
• Carillas dentales
• Diseño de sonrisa
• Contorneado estético

Precios:
Los precios varían según el tratamiento. Para obtener un presupuesto exacto, agenda una consulta de evaluación.

¿Te gustaría agendar una cita para alguno de estos servicios?"""
        
        return {
            'response': servicios,
            'action': None,
            'next_step': 'inicial'
        }
    
    def _handle_appointment_history(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja consulta de historial de citas"""
        try:
            # Obtener todas las citas del usuario (incluyendo completadas y canceladas)
            citas = self.actions_service.get_user_appointments(
                user_id=user_id,
                phone=phone,
                status=None  # Obtener todas, sin filtro de estado
            )
            
            if not citas:
                return {
                    'response': "No tienes historial de citas aún.\n\n¿Te gustaría agendar tu primera cita? Escribe *'agendar cita'* para comenzar.",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Separar por estado
            proximas = []
            pasadas = []
            canceladas = []
            
            from datetime import datetime
            now = datetime.now()
            
            for cita in citas:
                estado = cita.get('estado', '').lower()
                fecha_str = cita.get('fecha', '')
                
                try:
                    fecha_cita = datetime.strptime(fecha_str, '%Y-%m-%d')
                    es_futura = fecha_cita >= now
                except:
                    es_futura = True
                
                if estado == 'cancelada':
                    canceladas.append(cita)
                elif es_futura and estado in ['confirmado', 'programada', 'pendiente']:
                    proximas.append(cita)
                else:
                    pasadas.append(cita)
            
            response_text = "Tu Historial de Citas:\n\n"
            
            # Citas próximas
            if proximas:
                response_text += "Próximas Citas:\n"
                for i, cita in enumerate(proximas[:3], 1):
                    fecha = cita.get('fecha', 'N/A')
                    hora = cita.get('hora', 'N/A')
                    dentista = cita.get('dentista', 'N/A')
                    motivo = cita.get('descripcion', cita.get('motivo', 'Consulta'))
                    response_text += f"{i}. {fecha} - {hora}\n   {dentista}\n   {motivo}\n\n"
            
            # Citas pasadas
            if pasadas:
                response_text += "\nCitas Anteriores:\n"
                for i, cita in enumerate(pasadas[:3], 1):
                    fecha = cita.get('fecha', 'N/A')
                    dentista = cita.get('dentista', 'N/A')
                    response_text += f"{i}. {fecha} - {dentista}\n"
            
            # Estadísticas
            total = len(citas)
            completadas = len(pasadas)
            canceladas_count = len(canceladas)
            
            response_text += f"\nResumen:\n"
            response_text += f"• Total de citas: {total}\n"
            response_text += f"• Citas completadas: {completadas}\n"
            if canceladas_count > 0:
                response_text += f"• Citas canceladas: {canceladas_count}\n"
            
            response_text += "\n¿Necesitas hacer algo con alguna de tus citas?"
            
            return {
                'response': response_text,
                'action': None,
                'next_step': 'inicial'
            }
            
        except Exception as e:
            print(f"Error en _handle_appointment_history: {e}")
            return {
                'response': "Hubo un error al consultar tu historial. Por favor intenta nuevamente.",
                'action': None,
                'next_step': 'inicial'
            }

    def _handle_confirm_payment(self, session_id: str, entities: Dict, context: Dict,
                                user_id: str, phone: str) -> Dict:
        """Maneja la confirmación de pago por parte del usuario"""
        try:
            # Obtener citas pendientes de pago del usuario
            citas = self.actions_service.get_user_appointments(
                user_id=user_id,
                phone=phone,
                status='confirmado'
            )
            
            if not citas:
                return {
                    'response': "No tienes citas pendientes de confirmación de pago.\n\nSi crees que esto es un error, por favor contacta con el consultorio.",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Filtrar solo las que tienen pago pendiente
            citas_pendientes = [c for c in citas if c.get('payment_status') == 'pending' or c.get('paymentStatus') == 'pending']
            
            if not citas_pendientes:
                return {
                    'response': "Todas tus citas ya tienen el pago confirmado.\n\n¿Necesitas algo más?",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Si solo hay una cita pendiente, confirmarla directamente
            if len(citas_pendientes) == 1:
                cita = citas_pendientes[0]
                response = f"Cita pendiente de confirmación:\n\n"
                response += f"Fecha: {cita.get('fecha', 'N/A')}\n"
                response += f"Hora: {cita.get('hora', 'N/A')}\n"
                response += f"Dentista: {cita.get('dentista', 'N/A')}\n\n"
                response += "Importante: Para confirmar tu pago, por favor contacta directamente con el consultorio para verificar y actualizar el estado de tu pago.\n\n"
                response += "Una vez confirmado, tu cita quedará asegurada y no será cancelada."
                
                return {
                    'response': response,
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Si hay múltiples citas, mostrarlas
            citas_text = []
            for i, c in enumerate(citas_pendientes, 1):
                citas_text.append(f"{i}. {c.get('fecha', 'N/A')} {c.get('hora', 'N/A')}")
            
            response = f"Tienes {len(citas_pendientes)} citas pendientes de pago:\n\n"
            response += "\n".join(citas_text)
            response += "\n\nPara confirmar el pago de cualquiera de estas citas, por favor contacta directamente con el consultorio."
            
            return {
                'response': response,
                'action': None,
                'next_step': 'inicial'
            }
            
        except Exception as e:
            print(f"Error en _handle_confirm_payment: {e}")
            return {
                'response': "Lo siento, hubo un error al verificar tus citas. Por favor intenta nuevamente o contacta con el consultorio.",
                'action': None,
                'next_step': 'inicial'
            }
    
    def _handle_check_payment_time(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja la consulta sobre tiempo restante para pagar"""
        try:
            # Obtener citas con pago pendiente
            citas = self.actions_service.get_user_appointments(
                user_id=user_id,
                phone=phone,
                status='confirmado'
            )
            
            if not citas:
                return {
                    'response': "No tienes citas programadas en este momento.\n\n¿Te gustaría agendar una? Escribe 'agendar cita'.",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Filtrar citas con pago pendiente
            from datetime import datetime
            citas_pendientes = []
            for c in citas:
                payment_status = c.get('payment_status') or c.get('paymentStatus')
                payment_deadline = c.get('payment_deadline') or c.get('paymentDeadline')
                
                if payment_status == 'pending' and payment_deadline:
                    # Calcular tiempo restante
                    if isinstance(payment_deadline, str):
                        deadline_dt = datetime.fromisoformat(payment_deadline)
                    else:
                        deadline_dt = payment_deadline
                    
                    hours_remaining = int((deadline_dt - datetime.now()).total_seconds() / 3600)
                    
                    if hours_remaining > 0:
                        citas_pendientes.append({
                            'fecha': c.get('fecha', 'N/A'),
                            'hora': c.get('hora', 'N/A'),
                            'hours_remaining': hours_remaining,
                            'deadline': deadline_dt
                        })
            
            if not citas_pendientes:
                return {
                    'response': "Todas tus citas están confirmadas o no requieren pago pendiente.\n\n¿Necesitas algo más?",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Mostrar información de tiempo restante
            response = "Tiempo restante para pagar tus citas:\n\n"
            
            for i, c in enumerate(citas_pendientes, 1):
                hours = c['hours_remaining']
                if hours > 24:
                    dias = hours // 24
                    horas_extra = hours % 24
                    time_text = f"{dias} día{'s' if dias > 1 else ''}"
                    if horas_extra > 0:
                        time_text += f" y {horas_extra} hora{'s' if horas_extra > 1 else ''}"
                elif hours > 1:
                    time_text = f"{hours} horas"
                else:
                    time_text = f"{hours} hora"
                
                # Indicador según urgencia
                if hours <= 2:
                    indicador = "URGENTE:"
                elif hours <= 12:
                    indicador = ""
                else:
                    indicador = ""
                
                response += f"Cita {i}:\n"
                response += f"   {c['fecha']} a las {c['hora']}\n"
                response += f"   Tiempo restante: {time_text}\n\n"
            
            response += "Tip: Confirma tu pago cuanto antes para asegurar tu cita."
            
            return {
                'response': response,
                'action': None,
                'next_step': 'inicial'
            }
            
        except Exception as e:
            print(f"Error en _handle_check_payment_time: {e}")
            return {
                'response': "Lo siento, hubo un error al consultar el tiempo de pago. Por favor intenta nuevamente.",
                'action': None,
                'next_step': 'inicial'
            }
    
    def _handle_services_info(self, context: Dict) -> Dict:
        """Maneja consultas sobre servicios disponibles"""
        try:
            # Obtener información de servicios desde ActionsService
            dentistas = self.actions_service.get_dentists_info(limit=5)
            consultorios = self.actions_service.get_consultorios_info(limit=3)
            
            response = "Servicios de Densora\n\n"
            response += "En Densora ofrecemos una amplia gama de servicios dentales:\n\n"
            
            # Servicios principales
            response += "Servicios Principales:\n"
            response += "• Limpieza dental\n"
            response += "• Ortodoncia (brackets, alineadores)\n"
            response += "• Estética dental (blanqueamiento, carillas)\n"
            response += "• Endodoncia (tratamiento de conductos)\n"
            response += "• Implantes dentales\n"
            response += "• Odontopediatría (niños)\n"
            response += "• Prótesis dentales\n"
            response += "• Consulta general\n\n"
            
            # Información de dentistas disponibles
            if dentistas:
                response += "**Nuestros Especialistas:**\n"
                for d in dentistas[:3]:
                    nombre = d.get('nombre', 'N/A')
                    especialidad = d.get('especialidad', 'Odontología General')
                    calificacion = d.get('calificacion', 0)
                    response += f"• Dr(a). {nombre} - {especialidad}"
                    if calificacion > 0:
                        response += f" ⭐ {calificacion:.1f}"
                    response += "\n"
                response += "\n"
            
            # Información de consultorios
            if consultorios:
                response += "Nuestros Consultorios:\n"
                for c in consultorios[:2]:
                    nombre = c.get('nombre', 'N/A')
                    response += f"• {nombre}\n"
                response += "\n"
            
            response += "¿Listo para agendar?\n"
            response += "Escribe 'agendar cita' y te ayudo a encontrar el mejor horario para ti."
            
            return {
                'response': response,
                'action': None,
                'next_step': 'inicial'
            }
            
        except Exception as e:
            print(f"Error en _handle_services_info: {e}")
            return {
                'response': "Servicios de Densora\n\nEn Densora ofrecemos:\n• Limpieza dental\n• Ortodoncia\n• Estética dental\n• Endodoncia\n• Implantes\n• Odontopediatría\n• Y más...\n\n¿Te gustaría agendar una cita? Escribe 'agendar cita'.",
                'action': None,
                'next_step': 'inicial'
            }
    
    def _handle_appointment_history(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja la consulta del historial completo de citas"""
        try:
            # Obtener todas las citas del usuario (incluyendo pasadas)
            citas_activas = self.actions_service.get_user_appointments(
                user_id=user_id,
                phone=phone
            )
            
            if not citas_activas:
                return {
                    'response': "No tienes citas registradas en tu historial.\n\n¿Te gustaría agendar tu primera cita? Escribe 'agendar cita'.",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # Separar citas por estado
            from datetime import datetime
            proximas = []
            pasadas = []
            canceladas = []
            
            now = datetime.now()
            
            for c in citas_activas:
                estado = c.get('estado', '').lower()
                fecha_str = c.get('fecha', '')
                
                # Intentar parsear la fecha
                try:
                    if isinstance(fecha_str, str) and '-' in fecha_str:
                        fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                    else:
                        fecha_dt = None
                except:
                    fecha_dt = None
                
                if estado == 'cancelada':
                    canceladas.append(c)
                elif fecha_dt and fecha_dt < now:
                    pasadas.append(c)
                else:
                    proximas.append(c)
            
            # Construir respuesta
            response = "Tu Historial de Citas\n\n"
            
            # Citas próximas
            if proximas:
                response += f"Próximas ({len(proximas)}):\n"
                for c in proximas[:5]:  # Máximo 5
                    fecha = c.get('fecha', 'N/A')
                    hora = c.get('hora', 'N/A')
                    dentista = c.get('dentista', 'N/A')
                    motivo = c.get('motivo', 'Consulta')
                    estado = c.get('estado', 'N/A')
                    
                    # Indicador de estado de pago
                    payment_status = c.get('payment_status') or c.get('paymentStatus')
                    payment_indicator = "[Pagado]" if payment_status == 'paid' else "[Pendiente]"
                    
                    response += f"  {payment_indicator} {fecha} - {hora}\n"
                    response += f"     Dr(a). {dentista}\n"
                    response += f"     {motivo}\n\n"
            
            # Citas pasadas
            if pasadas:
                response += f"Completadas ({len(pasadas)}):\n"
                for c in pasadas[:3]:  # Máximo 3
                    fecha = c.get('fecha', 'N/A')
                    dentista = c.get('dentista', 'N/A')
                    response += f"  • {fecha} - Dr(a). {dentista}\n"
                response += "\n"
            
            # Citas canceladas
            if canceladas:
                response += f"Canceladas ({len(canceladas)})\n\n"
            
            # Resumen
            total = len(citas_activas)
            response += f"Total de citas: {total}\n\n"
            response += "¿Necesitas agendar una nueva cita? Escribe 'agendar cita'."
            
            return {
                'response': response,
                'action': None,
                'next_step': 'inicial'
            }
            
        except Exception as e:
            print(f"Error en _handle_appointment_history: {e}")
            return {
                'response': "Lo siento, hubo un error al consultar tu historial. Por favor intenta nuevamente.",
                'action': None,
                'next_step': 'inicial'
            }

