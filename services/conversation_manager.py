"""
GESTOR DE CONVERSACIONES - SOLO MENÚS
Sistema de menús estructurado sin IA/ML
"""

from services.menu_system import MenuSystem
from services.ml_service import MLService
from services.actions_service import ActionsService
from services.payment_service import PaymentService
from services.language_service import language_service
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
                       user_name: str = None, mode: str = 'hybrid',
                       context_extras: Dict = None) -> Dict:
        """
        Procesa mensajes usando un enfoque HÍBRIDO inteligente:
        1. Si el usuario está en un flujo específico (ej: agendando), sigue el flujo.
        2. Si el mensaje es un número, lo trata como opción de menú.
        3. Si es texto natural, usa IA para entender intención/problema.
        """
        # Obtener contexto
        context = self.get_conversation_context(session_id)
        current_step = context.get('step', 'inicial')
        
        print(f"[CONVERSATION_MANAGER] process_message - session_id={session_id}, msg='{message}', step={current_step}, mode={mode}")
        
        # Actualizar datos del usuario
        if user_id or phone:
            from services.actions_service import ActionsService
            # Solo instanciar si no existe para ahorrar recursos
            if not hasattr(self, 'actions_service'):
                self.actions_service = ActionsService()
            
            # Actualizar datos si es necesario (no en cada mensaje para optimizar)
            if not context.get('user_data'):
                user_data = self.actions_service.get_user_info(user_id=user_id, phone=phone)
                if user_data:
                    context['user_data'] = user_data
                    # Update language from user preferences
                    if user_data.get('preferredLanguage'):
                        context['language'] = user_data.get('preferredLanguage')
                    elif user_data.get('idioma'):
                        context['language'] = user_data.get('idioma')
                elif user_name:
                    context['user_data'] = {'nombre': user_name}
        
        # Agregar mensaje al historial
        self.add_to_history(session_id, 'user', message)

        # 0. Manejo de Multimedia (Contexto Extra)
        if context_extras:
            context.update(context_extras)
            if '[MEDIA_RECEIVED]' in message:
                print(f"[CONVERSATION_MANAGER] Multimedia detectada: {context_extras.get('media_url')}")
                # Si estamos pagando, asumir que es comprobante
                if context.get('intent') == 'confirmar_pago' or 'pago' in message.lower():
                     return self._handle_confirm_payment(session_id, {}, context, user_id, phone)
                
                # Respuesta genérica para imágenes
                return {
                    'response': "📷 He recibido tu imagen/archivo. Por ahora solo puedo guardarlo, un humano lo revisará pronto.",
                    'action': 'media_received',
                    'next_step': current_step
                }
        
        # LÓGICA HÍBRIDA MEJORADA
        
        # FAST PATH: Comandos de sistema - respuesta inmediata sin ML
        if message.lower().strip() in ['menu', 'menú', 'salir', 'cancelar', 'inicio']:
             result = self.menu_system.process_message(session_id, message, context, user_id, phone)
             self._update_context_and_history(session_id, result)
             return result

        # FAST PATH: Números simples - procesar directo con menú sin ML
        message_clean = message.strip()
        if message_clean.isdigit() and len(message_clean) <= 2:
            result = self.menu_system.process_message(session_id, message, context, user_id, phone)
            self._update_context_and_history(session_id, result)
            return result

        # 1.1 J.RF12: Keyword-based quick responses (solo para texto, no números)
        keyword_result = self._handle_keyword_response(message, context, user_id, phone)
        if keyword_result:
            self._update_context_and_history(session_id, keyword_result)
            return keyword_result


        # 1.5 Detección de Usuario Nuevo (Gap Analysis)
        # Si no tenemos user_id Y no estamos ya en el flujo de registro
        if not user_id and context.get('step') != 'registro_nombre':
            # Verificar si ya le pedimos el nombre
            if not context.get('registro_iniciado'):
                print(f"[CONVERSATION_MANAGER] Usuario nuevo detectado (sin ID). Iniciando flujo de registro.")
                self.update_conversation_context(session_id, {
                    'step': 'registro_nombre',
                    'registro_iniciado': True,
                    'last_intent_pending': 'unknown'  # Evitar llamada ML innecesaria
                })
                language = context.get('language', 'es')
                return {
                    'response': language_service.t('welcome_new_user', language),
                    'action': 'ask_name',
                    'next_step': 'registro_nombre'
                }

        # 1.6 Flujo de Registro Activo
        if context.get('step') == 'registro_nombre':
            nombre = message.strip()
            language = context.get('language', 'es')
            if len(nombre) < 3:
                 return {
                    'response': language_service.t('error_name_short', language),
                    'action': None,
                    'next_step': 'registro_nombre'
                }
            
            # Registrar usuario
            print(f"[CONVERSATION_MANAGER] Registrando usuario: {nombre}, {phone}")
            nuevo_usuario = self.actions_service.quick_register_user(phone, nombre)
            
            if nuevo_usuario:
                # Actualizar contexto con nuevo ID
                try:
                    user_id = nuevo_usuario['uid']
                    context['user_data'] = nuevo_usuario
                    
                    # Recuperar intención original si existía
                    intent_original = context.get('last_intent_pending')
                    response_text = language_service.t('register_success', language, name=nombre)
                    
                    self.update_conversation_context(session_id, {
                        'step': 'inicial', # Salir del flujo de registro
                        'registro_iniciado': False
                    })
                    
                    return {
                        'response': response_text,
                        'action': 'user_registered',
                        'next_step': 'inicial'
                    }
                except Exception as e:
                    print(f"Error procesando nuevo usuario: {e}")
            
            return {
                'response': language_service.t('register_error', language),
                'action': None,
                'next_step': 'inicial'
            }

        # 2. Si estamos en un paso que REQUIERE input específico (no 'inicial' ni 'menu_principal')

        # 2. Si estamos en un paso que REQUIERE input específico (no 'inicial' ni 'menu_principal')
        # Y el mensaje parece ser ese input (número, fecha, etc), usar sistema de menús/flujos
        steps_requiring_input = ['seleccionando_fecha', 'selecionando_hora', 'reagendando_fecha', 
                               'reagendando_hora', 'confirmando_cancelacion', 'esperando_nombre',
                               'esperando_descripcion']
        
        if current_step in steps_requiring_input:
            # Intentar procesar con sistema de menús primero
            # Si el sistema de menús dice "opción inválida" y es texto largo, quizás es una duda
            result = self.menu_system.process_message(session_id, message, context, user_id, phone)
            
            # Si el resultado es válido o avanza el paso, usarlo
            if result.get('next_step') != current_step or (result.get('action') and result.get('action') != 'error'):
                self._update_context_and_history(session_id, result)
                return result
            
            # Si el menú no lo entendió (ej: usuario preguntó algo en medio del flujo),
            # y es texto natural, dejar que el Agente IA intente ayudar
            if len(message) > 4 and not message.strip().isdigit():
                print(f"Input no reconocido en flujo {current_step}, intentando con Agente IA...")
                pass # Caer al bloque de Agente
            else:
                self._update_context_and_history(session_id, result)
                return result

        # 3. Si el mensaje es NUMÉRICO, priorizar menú (navegación rápida)
        if message.strip().isdigit():
             result = self.menu_system.process_message(session_id, message, context, user_id, phone)
             self._update_context_and_history(session_id, result)
             return result

        # 4. Para todo lo demás (texto natural, dudas, problemas), usar MODO AGENTE (IA)
        print("Usando MODO AGENTE para procesamiento de lenguaje natural")
        result = self._process_agent_mode(session_id, message, context, user_id, phone)
        
        self._update_context_and_history(session_id, result)
        return result

    def _update_context_and_history(self, session_id, result):
        """Helper para actualizar estado tras procesar"""
        if result.get('next_step'):
            self.update_conversation_context(session_id, {'step': result['next_step']})
        
        if result.get('response'):
            self.add_to_history(session_id, 'assistant', result['response'])
        
        # Marcar modo usado
        result['mode'] = 'hybrid'
    
    def _handle_keyword_response(self, message: str, context: Dict, 
                                  user_id: str, phone: str) -> Optional[Dict]:
        """
        J.RF12: Handles predefined keyword responses
        Returns None if no keyword matched, otherwise returns response dict
        """
        msg_lower = message.lower().strip()
        language = context.get('language', 'es')
        user_name = context.get('user_data', {}).get('nombre', '')
        web_url = 'https://www.densora.com'
        
        # Define keyword mappings with responses
        # Keywords map to response type
        keyword_map = {
            # Spanish keywords
            'ayuda': 'help',
            'help': 'help',
            'cita': 'appointment_info',
            'citas': 'appointment_info',
            'appointment': 'appointment_info',
            'appointments': 'appointment_info',
            'historial': 'medical_history',
            'historia': 'medical_history',
            'expediente': 'medical_history',
            'history': 'medical_history',
            'medical': 'medical_history',
            'contacto': 'contact',
            'contact': 'contact',
            'telefono': 'contact',
            'phone': 'contact',
            'reagendar': 'reschedule_info',
            'reprogramar': 'reschedule_info',
            'cambiar cita': 'reschedule_info',
            'reschedule': 'reschedule_info',
            'pagar': 'payment_info',
            'pago': 'payment_info',
            'pay': 'payment_info',
            'payment': 'payment_info',
            'precio': 'payment_info',
            'cost': 'payment_info',
            'reseña': 'reviews',
            'resena': 'reviews',
            'reseñas': 'reviews',
            'calificacion': 'reviews',
            'review': 'reviews',
            'reviews': 'reviews',
            'rating': 'reviews',
            'dentista': 'dentist_search',
            'dentist': 'dentist_search',
            'doctor': 'dentist_search',
            'consultorio': 'consultorio_search',
            'clinic': 'consultorio_search',
            'clinica': 'consultorio_search',
            'ubicacion': 'consultorio_search',
            'direccion': 'consultorio_search',
            'location': 'consultorio_search',
            'horario': 'schedule_info',
            'horarios': 'schedule_info',
            'hours': 'schedule_info',
            'disponibilidad': 'schedule_info',
            'available': 'schedule_info',
            'urgente': 'emergency',
            'emergencia': 'emergency',
            'urgent': 'emergency',
            'emergency': 'emergency',
            'dolor': 'emergency',
            'pain': 'emergency',
        }
        
        # Check if message starts with or equals any keyword
        matched_type = None
        for keyword, response_type in keyword_map.items():
            if msg_lower == keyword or msg_lower.startswith(keyword + ' '):
                matched_type = response_type
                break
        
        if not matched_type:
            return None
        
        # Generate response based on type
        print(f"[KEYWORD_HANDLER] Matched keyword type: {matched_type}")
        
        if matched_type == 'help':
            greeting = f"Hola {user_name}, " if user_name else "Hola, "
            if language == 'en':
                greeting = f"Hello {user_name}, " if user_name else "Hello, "

            response = language_service.t('keyword_help_response', language, name=user_name or '')
            return {
                'response': response,
                'action': 'keyword_help',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'appointment_info':
            # Check if user has upcoming appointments
            citas = self.actions_service.get_user_appointments(user_id=user_id, phone=phone, status='confirmado')
            
            if citas and len(citas) > 0:
                citas_texto = '\n'.join([
                    f"• {cita.get('fecha', 'N/A')} {cita.get('hora', '')} - Dr. {cita.get('dentista', 'N/A')}"
                    for cita in citas[:3]
                ])
                response = f"""*📅 Tus Próximas Citas:*

{citas_texto}

*¿Qué te gustaría hacer?*
1️⃣ Agendar una nueva cita
2️⃣ Reagendar una cita
3️⃣ Cancelar una cita
4️⃣ Ver detalles completos

Escribe el número de la opción."""
            else:
                response = """*📅 No tienes citas programadas actualmente.*

¿Te gustaría agendar una cita?

1️⃣ Sí, agendar ahora
2️⃣ Ver dentistas disponibles
3️⃣ Volver al menú

Escribe el número de la opción."""
            
            return {
                'response': response,
                'action': 'keyword_appointments',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'medical_history':
            response = f"""*📋 Historial Médico*

Tu historial médico es importante para recibir la mejor atención.

*Opciones:*
• Ver/Actualizar historial: {web_url}/historialMedico
• Compartir con dentista: Desde tu perfil

*¿Por qué es importante?*
✓ Permite al dentista conocer tu salud
✓ Agiliza tus consultas
✓ Mejora la atención personalizada

Escribe *"menu"* para volver al menú principal."""
            return {
                'response': response,
                'action': 'keyword_history',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'contact':
            response = language_service.t('keyword_contact_response', language)
            return {
                'response': response,
                'action': 'keyword_contact',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'reschedule_info':
            response = """*🔄 Reagendar Cita*

Para reagendar tu cita, necesito saber cuál deseas modificar.

*Opciones:*
1️⃣ Ver mis citas para reagendar
2️⃣ Tengo el código de la cita
3️⃣ Volver al menú

*Importante:*
⚠️ Reagenda con al menos 24h de anticipación
⚠️ Solo puedes reagendar 1 vez por cita

Escribe el número de la opción."""
            return {
                'response': response,
                'action': 'keyword_reschedule',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'payment_info':
            response = """*💳 Información de Pagos*

*Métodos de pago aceptados:*
• 💵 Efectivo - Pago en la cita
• 💳 Tarjeta - Pago online con Stripe
• 🏦 Transferencia - 2h para confirmar

*¿Tienes un pago pendiente?*
Escribe "ver citas" para revisar el estado.

*¿Necesitas comprobante?*
Lo recibirás por este chat tras el pago.

Escribe *"menu"* para volver al menú principal."""
            return {
                'response': response,
                'action': 'keyword_payment',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'reviews':
            response = f"""*⭐ Reseñas y Calificaciones*

*Tus opiniones nos ayudan a mejorar.*

Para dejar una reseña después de tu cita:
{web_url}/mis-resenas

*¿Tienes citas pendientes de calificar?*
Te enviaremos un enlace después de cada consulta.

Escribe *"menu"* para volver al menú principal."""
            return {
                'response': response,
                'action': 'keyword_reviews',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'dentist_search':
            # Get some dentists info
            dentistas = self.actions_service.get_dentists_info(limit=3)
            if dentistas:
                dentistas_texto = '\n'.join([
                    f"• Dr. {d.get('nombreCompleto', d.get('nombre', 'N/A'))} - {d.get('especialidad', 'General')}"
                    for d in dentistas
                ])
                response = f"""*👨‍⚕️ Dentistas Disponibles*

{dentistas_texto}

*Para buscar por especialidad:*
Escribe: "buscar [especialidad]"
Ej: "buscar ortodoncia"

*Para ver perfil completo:*
Visita: {web_url}/dentistas

Escribe *"menu"* para volver al menú principal."""
            else:
                response = """*👨‍⚕️ Dentistas*

No encontré dentistas registrados en este momento.

Visita nuestra web para más opciones:
www.densora.com/dentistas

Escribe *"menu"* para volver al menú principal."""
            
            return {
                'response': response,
                'action': 'keyword_dentist',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'consultorio_search':
            consultorios = self.actions_service.get_consultorios_info(limit=3)
            if consultorios:
                consultorios_texto = '\n'.join([
                    f"• {c.get('nombre', 'Consultorio')} - {c.get('direccion', {}).get('ciudad', 'N/A') if isinstance(c.get('direccion'), dict) else 'N/A'}"
                    for c in consultorios
                ])
                response = f"""*🏥 Consultorios Disponibles*

{consultorios_texto}

*Para ver ubicación y horarios:*
Visita: {web_url}/consultorios

Escribe *"menu"* para volver al menú principal."""
            else:
                response = """*🏥 Consultorios*

No encontré consultorios en este momento.

Visita nuestra web para más opciones:
www.densora.com/consultorios

Escribe *"menu"* para volver al menú principal."""
            
            return {
                'response': response,
                'action': 'keyword_consultorio',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'schedule_info':
            response = """*🕐 Horarios y Disponibilidad*

Los horarios varían según el dentista y consultorio.

*Para ver disponibilidad:*
1️⃣ Escribe "1" para agendar cita
2️⃣ Selecciona el servicio deseado
3️⃣ Te mostraré las fechas/horas disponibles

*Horario general de atención:*
Lun-Vie: 9:00 AM - 7:00 PM
Sábado: 9:00 AM - 2:00 PM

Escribe *"menu"* para volver al menú principal."""
            return {
                'response': response,
                'action': 'keyword_schedule',
                'next_step': 'menu_principal'
            }
        
        elif matched_type == 'emergency':
            response = """*🚨 ¿URGENCIA DENTAL?*

⚠️ *Si es una emergencia médica grave, llama al 911*

*Para atención urgente:*
📞 Línea de emergencias: +52 55 1234 5678
📍 Busca consultorios con atención 24h

*Síntomas que requieren atención inmediata:*
• Dolor intenso que no cede
• Sangrado abundante
• Hinchazón severa
• Traumatismo dental

*¿Necesitas agendar urgente?*
Escribe "1" y buscaré la cita más próxima disponible.

Escribe *"menu"* para volver al menú principal."""
            return {
                'response': response,
                'action': 'keyword_emergency',
                'next_step': 'menu_principal'
            }
        
        return None

    
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
        language = context.get('language', 'es')
        return {
            'response': f"{language_service.t('agent_fallback', language)}\n\n{self.menu_system.get_main_menu(language)}",
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
        
        # Robustez: Si la confianza es muy baja, ofrecer menú o ayuda
        elif confidence < 0.4:
            print(f"Confianza baja ({confidence}) para intent '{intent}'. Ofreciendo menú.")
            language = context.get('language', 'es')
            return {
                'response': f"{language_service.t('ai_confidence_low', language)}\n\n{self.menu_system.get_main_menu(language)}",
                'action': 'offer_menu',
                'next_step': 'menu_principal',
                'mode': 'menu' # Sugerir volver a menú
            }
            
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
                language = context.get('language', 'es')
                return {
                    'response': language_service.t('error_invalid_option', language),
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
                'response': 'Para contactarnos:\n\nTeléfono: [Número de contacto]\nEmail: contacto@densora.com\nWeb: localhost:4321\n\n¿Necesitas algo más?',
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
        
        elif intent == 'consultar_servicios' or intent == 'informacion_servicios':
            return self._handle_services_info(context)
        
        elif intent == 'ver_historial':
            return self._handle_appointment_history(context, user_id, phone)
        
        elif intent == 'buscar_dentista':
            return self._handle_search_dentist_intent(session_id, context, entities, message)
            
        elif intent == 'ver_resenas':
            return self._handle_reviews_intent(session_id, context, entities)
            
        elif intent == 'consultar_informacion':
            # Verificar si pide historial específicamente
            msg_lower = message.lower()
            if 'historial' in msg_lower or 'expediente' in msg_lower:
                return self._handle_native_history_view(context, user_id, phone)
            return self._handle_info_query(session_id, context, message)
            
        elif intent == 'ayuda':
            return self.menu_system._handle_help(context)

        elif intent == 'despedirse':
            return {
                'response': '¡Hasta luego! Que tengas un excelente día.',
                'action': None,
                'next_step': 'inicial'
            }
            
        elif intent == 'urgencia':
            return self._handle_emergency(context)

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

    def _handle_search_dentist_intent(self, session_id: str, context: Dict, entities: Dict, message: str) -> Dict:
        """Maneja la búsqueda de dentistas"""
        # Extraer query de búsqueda (especialidad o nombre)
        query = entities.get('especialidad') or entities.get('dentista') or message
        
        # Limpiar query básica
        ignore_words = ['busco', 'necesito', 'un', 'el', 'la', 'doctor', 'dentista', 'para']
        query_words = query.lower().split()
        clean_query = ' '.join([w for w in query_words if w not in ignore_words])
        
        resultados = self.actions_service.search_dentists(clean_query)
        
        if not resultados:
            return {
                'response': f"No encontré dentistas específicos para '{clean_query}', pero tenemos excelentes profesionales generales. ¿Te gustaría agendar una cita de valoración?",
                'action': 'offer_general_appointment',
                'next_step': context.get('step', 'inicial'),
                'mode': 'agent'
            }
        
        # Formatear resultados
        respuesta = f"Encontré {len(resultados)} dentistas:\n\n"
        for i, dentista in enumerate(resultados[:3]):
            respuesta += f"*{i+1}. {dentista['nombre']}* ({dentista['especialidad']})\n   ⭐ {dentista['calificacion']}\n   🏥 {dentista['ubicacion']}\n\n"
            
        respuesta += "¿Te gustaría agendar con alguno? (Escribe el nombre o 'agendar')"
        
        return {
            'response': respuesta,
            'action': 'search_results',
            'next_step': 'inicial', # Mantener en inicial para permitir flujo natural
            'mode': 'agent'
        }

    def _handle_reviews_intent(self, session_id: str, context: Dict, entities: Dict) -> Dict:
        """Maneja la visualización de reseñas"""
        dentista_name = entities.get('dentista')
        
        reseñas = self.actions_service.get_dentist_reviews(dentista_name)
        
        if not reseñas:
            return {
                'response': "Aún no hay reseñas disponibles para este criterio, pero todos nuestros doctores están certificados.",
                'action': None,
                'next_step': context.get('step'),
                'mode': 'agent'
            }
            
        respuesta = "*Opiniones recientes:*\n\n"
        for r in reseñas[:3]:
            respuesta += f"⭐ {r['calificacion']}/5 - {r['autor']}\n\"{r['comentario']}\"\n\n"
            
        return {
            'response': respuesta,
            'action': 'show_reviews',
            'next_step': context.get('step'),
            'mode': 'agent'
        }

    def _handle_native_history_view(self, context: Dict, user_id: str, phone: str) -> Dict:
        """Muestra historial médico nativo"""
        if not user_id and not phone:
             return {
                'response': "Necesitas iniciar sesión o registrarte para ver tu historial.",
                'action': 'require_auth',
                'next_step': context.get('step'),
                'mode': 'agent'
            }
            
        historial = self.actions_service.get_medical_history(user_id, phone)
        
        if not historial:
             return {
                'response': "No tienes historial médico registrado aún.",
                'action': None,
                'next_step': context.get('step'),
                'mode': 'agent'
            }
            
        respuesta = "*Tu Historial Médico (Reciente):*\n\n"
        for h in historial[:3]:
            respuesta += f"📅 {h['fecha']} - {h['tratamiento']}\n   Dr. {h['dentista']}\n\n"
            
        return {
            'response': respuesta,
            'action': 'show_history',
            'next_step': context.get('step'),
            'mode': 'agent'
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
        """Maneja la confirmación de pago automatizada"""
        try:
            # 1. Obtener citas pendientes
            citas = self.actions_service.get_user_appointments(
                user_id=user_id, phone=phone
            )
            # Filtrar manual si get_user_appointments no filtró por estado de pago
            citas_pendientes = []
            for c in citas:
                 # Check payment status variants
                 status = c.get('payment_status') or c.get('paymentStatus') or c.get('estado_pago')
                 if status in ['pending', 'pendiente', None]:
                     # Verificar si es cita futura
                     citas_pendientes.append(c)

            if not citas_pendientes:
                return {
                    'response': "No encontré citas pendientes de pago. ¡Todo está en orden!",
                    'action': None,
                    'next_step': 'inicial'
                }
            
            # 2. Si hay citas, confirmar
            # Simplificación: Si hay 1, confirmar esa. Si hay más, pedir ID (por ahora asumimos 1 o la más próxima)
            cita_a_confirmar = citas_pendientes[0]
            cita_id = cita_a_confirmar['id']
            
            # Llamar al servicio de pagos
            resultado = self.payment_service.confirmar_pago(
                cita_id=cita_id,
                metodo_confirmacion='whatsapp_bot',
                notas="Usuario reportó pago vía chat"
            )
            
            if resultado['success']:
                fecha = cita_a_confirmar.get('fecha', 'tu cita')
                return {
                    'response': f"✅ ¡Listo! He registrado tu reporte de pago para la cita del {fecha}.\n\nEstado actual: *Pendiente de Verificación*.\n\nEl consultorio validará tu pago pronto. Te avisaré cuando esté confirmado al 100%.",
                    'action': 'payment_reported',
                    'next_step': 'inicial'
                }
            else:
                return {
                    'response': f"Hubo un problema registrando tu pago: {resultado.get('error')}. Por favor intenta más tarde o contacta al consultorio.",
                    'action': 'error',
                    'next_step': 'inicial'
                }

        except Exception as e:
            print(f"Error en _handle_confirm_payment: {e}")
            return {
                'response': "Lo siento, ocurrió un error procesando tu solicitud. Por favor contacta al consultorio.",
                'action': 'error',
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
                        response += f" {calificacion:.1f}"
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

    def _handle_emergency(self, context: Dict) -> Dict:
        """Maneja solicitudes de urgencia/emergencia"""
        # Respuesta prioritaria
        response = "🚨 *ATENCIÓN DE URGENCIA* 🚨\n\n"
        response += "Si tienes dolor severo, sangrado incontrolable o infección grave:\n\n"
        response += "📞 *Llama INMEDIATAMENTE al: (55) 1234-5678* (Línea de Urgencias)\n\n"
        response += "O acude directamente a nuestra sucursal de urgencias:\n"
        response += "📍 Av. Reforma 123 (Abierto 24h)\n\n"
        response += "Si es una molestia menor que puede esperar a mañana, escribe 'agendar cita' para buscarte un espacio prioritario."
        
        return {
            'response': response,
            'action': 'emergency_info',
            'next_step': 'inicial',
            'mode': 'agent'
        }

