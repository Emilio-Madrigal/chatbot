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
                       user_name: str = None) -> Dict:
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
        
        # Actualizar datos del usuario si están disponibles
        if user_id or phone:
            user_data = self.actions_service.get_user_info(user_id=user_id, phone=phone)
            if user_data:
                context['user_data'] = user_data
            elif user_name:
                context['user_data'] = {'nombre': user_name}
        
        # Agregar mensaje al historial
        self.add_to_history(session_id, 'user', message)
        
        # Clasificar intención usando ML
        intent_result = self.ml_service.classify_intent(message, context)
        intent = intent_result['intent']
        confidence = intent_result['confidence']
        
        # Extraer entidades
        entities = self.ml_service.extract_entities(message, intent)
        
        # Actualizar contexto
        context['intent'] = intent
        context['entities'].update(entities)
        
        # Procesar según la intención
        response_data = self._handle_intent(session_id, intent, entities, context)
        
        # Agregar respuesta al historial
        if response_data.get('response'):
            self.add_to_history(session_id, 'assistant', response_data['response'])
        
        return response_data
    
    def _handle_intent(self, session_id: str, intent: str, entities: Dict, 
                      context: Dict) -> Dict:
        """Maneja cada intención y genera la respuesta apropiada"""
        user_data = context.get('user_data', {})
        user_id = user_data.get('uid')
        phone = user_data.get('telefono')
        current_step = context.get('step', 'inicial')
        
        # Manejar según intención
        if intent == 'saludar':
            return self._handle_greeting(context)
        
        elif intent == 'ayuda' or intent == 'consultar_informacion':
            return self._handle_help(context, entities)
        
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
        response = self.ml_service.generate_response('saludar', {}, context, context.get('user_data'))
        return {
            'response': response,
            'action': None,
            'next_step': 'menu_principal'
        }
    
    def _handle_help(self, context: Dict, entities: Dict) -> Dict:
        """Maneja solicitudes de ayuda"""
        question = entities.get('motivo', '')
        if question:
            # Intentar responder la pregunta específica
            answer = self.ml_service.answer_question(question)
            response = answer
        else:
            response = self.ml_service.generate_response('ayuda', entities, context, context.get('user_data'))
        
        return {
            'response': response,
            'action': None,
            'next_step': 'menu_principal'
        }
    
    def _handle_schedule_appointment(self, session_id: str, entities: Dict, 
                                   context: Dict, user_id: str, phone: str) -> Dict:
        """Maneja el agendamiento de citas"""
        current_step = context.get('step', 'inicial')
        
        # Si ya tenemos fecha y hora, crear la cita
        if current_step == 'selecionando_hora' and entities.get('hora'):
            fecha = context.get('entities', {}).get('fecha') or context.get('fecha_seleccionada')
            hora = entities.get('hora')
            nombre = context.get('nombre_cliente') or context.get('user_data', {}).get('nombre', 'Paciente')
            motivo = entities.get('motivo') or context.get('motivo', 'Consulta general')
            
            if fecha and hora:
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
                    return {
                        'response': f"✅ ¡Perfecto! Tu cita ha sido agendada exitosamente.\n\n📅 Fecha: {fecha}\n⏰ Hora: {hora}\n👤 Paciente: {nombre}\n\nTe enviaremos un recordatorio antes de tu cita. ¡Gracias por usar Densora! 🦷",
                        'action': 'appointment_created',
                        'next_step': 'inicial'
                    }
                else:
                    return {
                        'response': f"❌ Lo siento, no pude agendar tu cita: {result.get('error', 'Error desconocido')}\n\nPor favor intenta nuevamente o escribe *menu* para ver las opciones.",
                        'action': None,
                        'next_step': current_step
                    }
        
        # Si tenemos fecha pero no hora, pedir hora
        if current_step == 'seleccionando_fecha' or entities.get('fecha'):
            fecha = entities.get('fecha')
            if fecha:
                self.update_conversation_context(session_id, {
                    'step': 'selecionando_hora',
                    'fecha_seleccionada': fecha
                })
                
                # Obtener horarios disponibles
                horarios = self.actions_service.get_available_times(
                    user_id=user_id,
                    phone=phone,
                    fecha=fecha
                )
                
                if horarios:
                    horarios_text = "\n".join([f"{i+1}. {h}" for i, h in enumerate(horarios[:5])])
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
            fechas_text = "\n".join([f"{i+1}. {f}" for i, f in enumerate(fechas)])
            self.update_conversation_context(session_id, {'step': 'seleccionando_fecha'})
            return {
                'response': f"📅 ¡Perfecto! Te ayudo a agendar tu cita.\n\nFechas disponibles:\n{fechas_text}\n\n¿Qué fecha prefieres? (Escribe el número o la fecha)",
                'action': None,
                'next_step': 'seleccionando_fecha',
                'entities': {'fechas_disponibles': fechas}
            }
        else:
            return {
                'response': "❌ Lo siento, no hay fechas disponibles en este momento.\n\nPor favor contacta directamente con el consultorio o intenta más tarde.\n\nEscribe *menu* para ver otras opciones.",
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
                'response': "No tienes citas programadas actualmente.\n\nEscribe *agendar cita* para agendar una nueva.",
                'action': None,
                'next_step': 'menu_principal'
            }
        
        citas_text = "\n".join([
            f"📅 {c['fecha']} ⏰ {c['hora']}\n👤 {c['nombre']}\n🏥 {c['consultorio']}\n📝 {c['motivo']}\n📊 Estado: {c['estado']}\n"
            for c in citas
        ])
        
        return {
            'response': f"📋 Tus Citas Programadas:\n\n{citas_text}\n\n¿Necesitas hacer algún cambio? Escribe *reagendar* o *cancelar*.",
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
        nombre = context.get('user_data', {}).get('nombre', 'Paciente')
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
                return {
                    'response': f"✅ ¡Perfecto! Tu cita ha sido agendada exitosamente.\n\n📅 Fecha: {fecha}\n⏰ Hora: {hora}\n👤 Paciente: {nombre}\n\nTe enviaremos un recordatorio antes de tu cita.",
                    'action': 'appointment_created',
                    'next_step': 'inicial'
                }
        
        return {
            'response': "Por favor selecciona una hora válida.",
            'action': None,
            'next_step': 'selecionando_hora'
        }

