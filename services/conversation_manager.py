"""
💬 GESTOR DE CONVERSACIONES MEJORADO
Maneja el contexto y flujo de conversación del chatbot con ML
"""

from services.ml_service import MLService
from services.actions_service import ActionsService
from typing import Dict, List, Optional
from datetime import datetime

class ConversationManager:
    """
    Gestiona el flujo de conversación del chatbot con contexto y memoria
    """
    
    def __init__(self):
        self.ml_service = MLService()
        self.actions_service = ActionsService()
        self.conversations = {}  # Almacena el contexto de cada conversación
    
    def get_conversation_context(self, session_id: str) -> Dict:
        """Obtiene el contexto de una conversación"""
        if session_id not in self.conversations:
            self.conversations[session_id] = {
                'step': 'inicial',
                'intent': None,
                'entities': {},
                'user_data': {},
                'history': [],
                'mode': 'menu',  # 'menu' o 'agente'
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
        Procesa un mensaje del usuario y genera una respuesta
        
        Returns:
            Dict con:
            - response: str - Respuesta del bot
            - action: str - Acción realizada (si aplica)
            - entities: Dict - Entidades extraídas
            - next_step: str - Próximo paso en el flujo
        """
        # Obtener contexto
        context = self.get_conversation_context(session_id)
        current_step = context.get('step', 'inicial')
        current_mode = context.get('mode', 'menu')
        
        # Actualizar modo si se especifica
        if mode and mode in ['menu', 'agente']:
            context['mode'] = mode
            current_mode = mode
            self.update_conversation_context(session_id, {'mode': mode})
        
        # Actualizar datos del usuario si están disponibles
        if user_id or phone:
            user_data = self.actions_service.get_user_info(user_id=user_id, phone=phone)
            if user_data:
                context['user_data'] = user_data
            elif user_name:
                context['user_data'] = {'nombre': user_name}
        
        # Agregar mensaje al historial
        self.add_to_history(session_id, 'user', message)
        
        # Detectar cambio de modo
        message_lower = message.lower().strip()
        if 'modo agente' in message_lower or 'cambiar a agente' in message_lower:
            self.update_conversation_context(session_id, {'mode': 'agente'})
            return {
                'response': '🤖 Modo Agente activado. Ahora puedes hablar conmigo de forma natural. ¿En qué puedo ayudarte?',
                'action': 'mode_changed',
                'next_step': 'inicial',
                'mode': 'agente'
            }
        elif 'modo menú' in message_lower or 'modo menu' in message_lower or 'cambiar a menú' in message_lower or 'cambiar a menu' in message_lower:
            self.update_conversation_context(session_id, {'mode': 'menu', 'step': 'menu_principal'})
            return {
                'response': '📋 Modo Menú activado. Usa números para navegar:\n\n1️⃣ Agendar una cita\n2️⃣ Ver tus citas\n3️⃣ Reagendar una cita\n4️⃣ Cancelar una cita\n5️⃣ Información\n\n¿Qué te gustaría hacer?',
                'action': 'mode_changed',
                'next_step': 'menu_principal',
                'mode': 'menu'
            }
        
        # Procesar según el modo
        if current_mode == 'menu':
            # Modo Menú: Flujo guiado por números
            return self._process_menu_mode(session_id, message, context, user_id, phone)
        else:
            # Modo Agente: ML completo, conversación natural
            return self._process_agent_mode(session_id, message, context, user_id, phone)
    
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
        
        # Si no es número, usar ML básico para detectar intención
        intent_result = self.ml_service.classify_intent(message, context)
        intent = intent_result['intent']
        
        # En modo menú, solo procesar intenciones básicas
        if intent in ['saludar', 'ayuda']:
            entities = self.ml_service.extract_entities(message, intent, context)
            response_data = self._handle_intent(session_id, intent, entities, context)
            if response_data.get('response'):
                self.add_to_history(session_id, 'assistant', response_data['response'])
            return response_data
        
        # Para otras intenciones, sugerir usar números
        return {
            'response': 'En modo menú, por favor usa números para navegar:\n\n1️⃣ Agendar una cita\n2️⃣ Ver tus citas\n3️⃣ Reagendar una cita\n4️⃣ Cancelar una cita\n5️⃣ Información\n\nO escribe "modo agente" para conversación natural.',
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
        
        elif intent == 'despedirse':
            return {
                'response': '¡Hasta luego! Que tengas un excelente día. 🦷',
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

1️⃣ Agendar una cita
2️⃣ Ver tus citas
3️⃣ Reagendar una cita
4️⃣ Cancelar una cita
5️⃣ Información sobre nuestros servicios

¿Qué te gustaría hacer?

💡 Escribe "modo agente" para conversación natural."""
        else:
            response = f"""{saludo}¡Bienvenido a Densora! 🦷

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

1️⃣ Agendar una cita
2️⃣ Ver tus citas
3️⃣ Reagendar una cita
4️⃣ Cancelar una cita
5️⃣ Información sobre nuestros servicios

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
                        'response': "❌ No pude entender la fecha que mencionaste. Por favor, proporciona la fecha en formato día/mes/año (ej: 14/11/2025) o di 'mañana', 'hoy', etc.",
                        'action': None,
                        'next_step': 'seleccionando_fecha'
                    }
        
        # ========== CASO 1: TENEMOS FECHA Y HORA ==========
        # Si el usuario dio fecha Y hora desde el principio, CREAR LA CITA DIRECTAMENTE
        if fecha and hora:
            print(f"✅ CASO COMPLETO: Tenemos fecha ({fecha}) y hora ({hora}), creando cita directamente...")
            
            # Validar que la hora esté disponible
            horarios_disponibles = self.actions_service.get_available_times(
                user_id=user_id,
                phone=phone,
                fecha=fecha,
                nombre_dentista=entities.get('nombre_dentista')
            )
            
            if not horarios_disponibles:
                return {
                    'response': f"❌ Lo siento, no hay horarios disponibles para el {fecha}.\n\n¿Te gustaría elegir otra fecha?",
                    'action': None,
                    'next_step': 'seleccionando_fecha'
                }
            
            # Verificar que la hora solicitada esté disponible
            if hora not in horarios_disponibles:
                horarios_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(horarios_disponibles[:5])])
                return {
                    'response': f"⚠️ La hora {hora} no está disponible para el {fecha}.\n\n⏰ Horarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres?",
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
                motivo=motivo
            )
            
            if result['success']:
                self.update_conversation_context(session_id, {'step': 'inicial', 'mode': current_mode})
                return {
                    'response': f"✅ ¡Perfecto! Tu cita ha sido agendada exitosamente.\n\n📅 Fecha: {fecha}\n⏰ Hora: {hora}\n👤 Paciente: {nombre}\n💬 Motivo: {motivo}\n\nTe enviaremos un recordatorio antes de tu cita. ¡Gracias por usar Densora! 🦷",
                    'action': 'appointment_created',
                    'next_step': 'inicial'
                }
            else:
                return {
                    'response': f"❌ Lo siento, no pude agendar tu cita: {result.get('error', 'Error desconocido')}\n\nPor favor intenta nuevamente.",
                    'action': None,
                    'next_step': 'inicial'
                }
        
        # ========== CASO 2: SOLO TENEMOS FECHA ==========
        # Si tenemos fecha pero no hora, mostrar horarios disponibles
        if fecha and not hora:
            print(f"📅 CASO PARCIAL: Tenemos fecha ({fecha}) pero no hora, mostrando horarios...")
            
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
                    # Guardar horarios en el contexto
                    context['entities']['horarios_disponibles'] = horarios
                    self.update_conversation_context(session_id, {
                        'entities': {'fecha': fecha, 'horarios_disponibles': horarios}
                    })
                    return {
                        'response': f"📅 Fecha seleccionada: {fecha}\n\n⏰ Horarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres? (Escribe el número o la hora)",
                        'action': None,
                        'next_step': 'selecionando_hora',
                        'entities': {'fecha': fecha, 'horarios_disponibles': horarios}
                    }
                else:
                    return {
                        'response': f"❌ Lo siento, no hay horarios disponibles para el {fecha}.\n\n¿Te gustaría elegir otra fecha?",
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
                'response': f"📅 ¡Perfecto! Te ayudo a agendar tu cita.\n\nFechas disponibles:\n{fechas_text}\n\n¿Qué fecha prefieres? (Escribe el número o la fecha)",
                'action': None,
                'next_step': 'seleccionando_fecha',
                'entities': {'fechas_disponibles': fechas}
            }
        else:
            return {
                'response': "❌ Lo siento, no hay fechas disponibles en este momento.\n\nEsto puede deberse a que:\n• No tienes un consultorio asociado\n• No hay horarios configurados\n\nPor favor contacta directamente con el consultorio o intenta más tarde.\n\nEscribe *menu* para ver otras opciones.",
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
                        'response': f"✅ ¡Perfecto! Tu cita ha sido reagendada exitosamente.\n\n📅 Nueva fecha: {nueva_fecha}\n⏰ Nueva hora: {nueva_hora}\n\nTe enviaremos un recordatorio antes de tu cita.",
                        'action': 'appointment_rescheduled',
                        'next_step': 'inicial'
                    }
                else:
                    return {
                        'response': f"❌ No pude reagendar tu cita: {result.get('error', 'Error desconocido')}",
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
                        'response': f"📅 Nueva fecha seleccionada: {nueva_fecha}\n\n⏰ Horarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres?",
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
                        'response': f"🔄 Reagendando cita de {citas[cita_num]['fecha']} {citas[cita_num]['hora']}\n\n📅 Fechas disponibles:\n{fechas_text}\n\n¿Qué fecha prefieres?",
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
            'response': f"🔄 Reagendar Cita\n\nTus citas programadas:\n{citas_text}\n\n¿Cuál cita quieres reagendar? (Escribe el número)",
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
                        'response': "✅ Tu cita ha sido cancelada exitosamente.\n\nSi necesitas agendar una nueva cita, escribe *menu*.",
                        'action': 'appointment_cancelled',
                        'next_step': 'inicial'
                    }
                else:
                    return {
                        'response': f"❌ No pude cancelar tu cita: {result.get('error', 'Error desconocido')}",
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
                    'response': f"⚠️ ¿Estás seguro de que quieres cancelar esta cita?\n\n📅 {citas[cita_num]['fecha']} {citas[cita_num]['hora']}\n👤 {citas[cita_num]['nombre']}\n\nResponde *SI* para confirmar o *NO* para mantenerla.",
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
            'response': f"❌ Cancelar Cita\n\nTus citas programadas:\n{citas_text}\n\n¿Cuál cita quieres cancelar? (Escribe el número)",
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
            
            citas_text.append(f"{i}. 📅 {fecha_display} ⏰ {c['hora']}\n   👤 {c['nombre']}\n   🏥 {c['consultorio']}\n   📝 {c['motivo']}\n   📊 Estado: {c['estado']}")
        
        return {
            'response': f"📋 Tus Citas Programadas:\n\n" + "\n\n".join(citas_text) + "\n\n¿Necesitas hacer algún cambio? Escribe *3* para reagendar o *4* para cancelar.",
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
                    'response': f"📅 Fecha seleccionada: {fecha}\n\n⏰ Horarios disponibles:\n{horarios_text}\n\n¿Qué hora prefieres?",
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
                    'response': f"✅ ¡Perfecto! Tu cita ha sido agendada exitosamente.\n\n📅 Fecha: {fecha_display}\n⏰ Hora: {hora}\n👤 Paciente: {nombre}\n\nTe enviaremos un recordatorio antes de tu cita.",
                    'action': 'appointment_created',
                    'next_step': 'inicial'
                }
            else:
                return {
                    'response': f"❌ No pude agendar tu cita: {result.get('error', 'Error desconocido')}\n\nPor favor intenta nuevamente.",
                    'action': None,
                    'next_step': 'selecionando_hora'
                }
        
        return {
            'response': "Por favor selecciona una hora válida.",
            'action': None,
            'next_step': 'selecionando_hora'
        }

