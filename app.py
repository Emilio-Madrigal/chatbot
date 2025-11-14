from flask import Flask,request,jsonify
from flask_cors import CORS
from config import Config
from services.whatsapp_service import WhatsAppService
from services.citas_service import CitasService
from services.conversation_manager import ConversationManager
from datetime import datetime
import json

app=Flask(__name__)
app.config.from_object(Config)

# Configuración de CORS para el endpoint web
# Permitir todos los orígenes temporalmente para debug (en producción, especifica los dominios)
CORS(app, resources={
    r"/api/web/chat": {
        "origins": "*",  # Temporalmente permitir todos los orígenes para debug
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

WhatsApp_service=WhatsAppService()
citas_service=CitasService()
conversation_manager=ConversationManager()  # Nuevo gestor de conversaciones con ML
user_states={}

@app.route('/webhook',methods=['GET'])
def verify_webhook():
    """Verificación de webhook para Twilio (opcional, Twilio no requiere GET)"""
    # Twilio no usa verificación GET como Meta, pero mantenemos por compatibilidad
    print("GET request recibido en /webhook")
    return "OK", 200

@app.route('/health',methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está corriendo"""
    return jsonify({
        "status": "ok",
        "service": "chatbot-whatsapp",
        "twilio_configured": bool(Config.TWILIO_ACCOUNT_SID)
    }), 200

@app.route('/api/web/chat', methods=['OPTIONS'])
def web_chat_options():
    """Manejar preflight CORS"""
    return '', 200

@app.route('/api/web/chat', methods=['POST'])
def web_chat():
    """Endpoint para el chat web con ML mejorado"""
    try:
        print(f"WEB CHAT REQUEST - Headers: {dict(request.headers)}")
        print(f"WEB CHAT REQUEST - Origin: {request.headers.get('Origin', 'No Origin')}")
        
        data = request.get_json()
        if not data:
            print("ERROR: No se recibió JSON en el request")
            return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
            
        message_body = data.get('message')
        session_id = data.get('session_id')
        platform = data.get('platform', 'web')  # 'web' por defecto
        user_id = data.get('user_id')  # ID del usuario autenticado
        phone = data.get('phone')  # Teléfono del usuario
        user_name = data.get('user_name')  # Nombre del usuario

        if not message_body or not session_id:
            print(f"ERROR: Faltan parámetros - message: {bool(message_body)}, session_id: {bool(session_id)}")
            return jsonify({'success': False, 'error': 'Message and session_id are required'}), 400

        print(f"WEB CHAT RECIBIDO - Session ID: {session_id}, Message: {message_body}, User ID: {user_id}, Phone: {phone}")

        # Obtener modo del request (menu o agente)
        mode = data.get('mode', None)  # 'menu' o 'agente'
        
        # Procesar el mensaje usando el nuevo sistema de ML
        bot_response_text = ''
        current_mode = None
        try:
            response_data = conversation_manager.process_message(
                session_id=session_id,
                message=message_body,
                user_id=user_id,
                phone=phone,
                user_name=user_name,
                mode=mode
            )
            bot_response_text = response_data.get('response', '')
            current_mode = response_data.get('mode', None)
            print(f"ML procesó correctamente - Response: {bot_response_text[:100]}...")
        except Exception as ml_error:
            print(f"Error en ML, usando fallback: {ml_error}")
            import traceback
            traceback.print_exc()
            # Fallback al sistema anterior si ML falla
            bot_response_text = process_web_message(session_id, message_body, platform, user_id=user_id, phone=phone, user_name=user_name)

        # Si la respuesta está vacía o es solo "...", usar un mensaje por defecto
        if not bot_response_text or bot_response_text.strip() == "" or bot_response_text.strip() == "...":
            print(f"WEB CHAT RESPUESTA VACÍA - Usando mensaje por defecto")
            bot_response_text = "Lo siento, no pude procesar tu mensaje. Por favor, intenta nuevamente o escribe *menu* para ver las opciones disponibles."
        
        print(f"WEB CHAT RESPUESTA - Response: {bot_response_text[:200]}...")

        return jsonify({
            'success': True,
            'response': bot_response_text,
            'session_id': session_id,
            'mode': current_mode if 'current_mode' in locals() else None
        })

    except Exception as e:
        print(f"ERROR en web_chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/webhook',methods=['POST'])
def webhook():
    """Webhook para recibir mensajes de Twilio"""
    try:
        # Log de depuración - ver qué está llegando
        print("="*60)
        print("WEBHOOK RECIBIDO")
        print("="*60)
        print(f"Request method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Form data: {dict(request.form)}")
        print(f"Values: {dict(request.values)}")
        print("="*60)
        
        # Twilio envía datos como form-data, no JSON
        from_number = request.values.get('From', '') or request.form.get('From', '')
        message_body = request.values.get('Body', '') or request.form.get('Body', '')
        message_sid = request.values.get('MessageSid', '') or request.form.get('MessageSid', '')
        num_media = request.values.get('NumMedia', '0') or request.form.get('NumMedia', '0')
        
        print(f"Webhook Twilio recibido:")
        print(f"  From: {from_number}")
        print(f"  Body: {message_body}")
        print(f"  MessageSid: {message_sid}")
        
        # Si no hay datos, puede ser que Twilio esté enviando en otro formato
        if not from_number and not message_body:
            print("ADVERTENCIA: No se recibieron datos del webhook")
            # Intentar leer como JSON por si acaso
            try:
                json_data = request.get_json()
                print(f"Datos JSON recibidos: {json_data}")
            except:
                pass
        
        # Limpiar el número (Twilio envía como whatsapp:+521234567890)
        # Extraer solo el número sin el prefijo whatsapp:
        if from_number and from_number.startswith('whatsapp:'):
            from_number = from_number.replace('whatsapp:', '')
        
        # Procesar el mensaje
        if message_body:
            print(f"Procesando mensaje: {message_body}")
            
            # Detectar si es una respuesta a botones interactivos
            # Los botones interactivos envían el texto del botón como mensaje
            # Primero intentamos detectar si es el texto exacto de un botón
            state = user_states.get(from_number, {})
            current_step = state.get('step', 'inicial')
            
            # Mapeo de textos de botones a IDs según el contexto
            button_text_to_id = {}
            
            if current_step == 'menu_principal':
                button_text_to_id = {
                    'Agendar Cita': 'agendar_cita',
                    'Agendar Cita': 'agendar_cita',
                    'Ver Mis Citas': 'ver_citas',
                    'Ver Mis Citas': 'ver_citas',
                    'Gestionar': 'gestionar_citas',
                    'Gestionar': 'gestionar_citas'
                }
            elif current_step in ['seleccionando_fecha', 'reagendando_fecha']:
                # Las fechas se detectan por formato o por el texto del botón
                fechas_disponibles = state.get('fechas_disponibles', [])
                for i, fecha_ts in enumerate(fechas_disponibles[:3], 1):
                    if hasattr(fecha_ts, 'strftime'):
                        fecha_display = fecha_ts.strftime('%d/%m')
                        fecha_str = fecha_ts.strftime('%Y-%m-%d')
                    else:
                        fecha_display = str(fecha_ts)
                        fecha_str = fecha_ts
                    button_text_to_id[fecha_display] = f"fecha_{fecha_str}"
            elif current_step in ['selecionando_hora', 'reagendando_hora']:
                # Las horas se detectan por formato o por el texto del botón
                horarios_disponibles = state.get('horarios_disponibles', [])
                for i, slot in enumerate(horarios_disponibles[:3], 1):
                    hora_inicio = slot.get('horaInicio', slot.get('inicio', ''))
                    from datetime import datetime
                    try:
                        hora_obj = datetime.strptime(hora_inicio, '%H:%M')
                        hora_display = hora_obj.strftime('%I:%M %p').lstrip('0')
                        button_text_to_id[hora_display] = f"hora_{hora_inicio}"
                    except:
                        button_text_to_id[hora_inicio] = f"hora_{hora_inicio}"
            
            # Verificar si el mensaje coincide con el texto de un botón
            message_clean = message_body.strip()
            if message_clean in button_text_to_id:
                button_id = button_text_to_id[message_clean]
                print(f"Botón detectado por texto: '{message_clean}' -> {button_id}")
                handle_button_response_extended(from_number, button_id)
            elif message_body.strip().isdigit():
                # Es una respuesta numérica a botones
                print(f"Es respuesta numérica: {message_body.strip()}")
                handle_button_response_extended(from_number, f"button_{message_body.strip()}")
            else:
                # Es un mensaje de texto normal - usar ML mejorado
                print(f"Es mensaje de texto: {message_body}")
                try:
                    # Intentar obtener user_id desde Firestore usando el teléfono
                    from services.actions_service import ActionsService
                    actions_service = ActionsService()
                    user_info = actions_service.get_user_info(phone=from_number)
                    user_id = user_info.get('uid') if user_info else None
                    user_name = user_info.get('nombre') if user_info else None
                    
                    # Intentar usar el nuevo sistema de ML
                    # En WhatsApp, detectar modo desde el mensaje o usar 'menu' por defecto
                    mode = None
                    message_lower = message_body.lower()
                    if 'modo agente' in message_lower or 'modo agente' in message_lower:
                        mode = 'agente'
                    elif 'modo menú' in message_lower or 'modo menu' in message_lower:
                        mode = 'menu'
                    
                    response_data = conversation_manager.process_message(
                        session_id=from_number,
                        message=message_body,
                        user_id=user_id,  # Obtener desde Firestore
                        phone=from_number,
                        user_name=user_name,
                        mode=mode
                    )
                    response_text = response_data.get('response', '')
                    
                    if response_text:
                        WhatsApp_service.send_text_message(from_number, response_text)
                    else:
                        # Fallback al sistema anterior
                        handle_text_message_extended(from_number, message_body)
                except Exception as ml_error:
                    print(f"Error en ML para WhatsApp, usando fallback: {ml_error}")
                    import traceback
                    traceback.print_exc()
                    # Fallback al sistema anterior si ML falla
                handle_text_message_extended(from_number, message_body)
        else:
            print("ADVERTENCIA: message_body está vacío")
        
        # Responder a Twilio (requerido)
        response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message></Message>
</Response>"""
        print("Respondiendo a Twilio con XML")
        return response, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        print(f"ERROR en webhook Twilio: {e}")
        import traceback
        traceback.print_exc()
        # Aún así responder a Twilio para que no reintente
        response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message></Message>
</Response>"""
        return response, 200, {'Content-Type': 'text/xml'}

def process_message(message_data):
    """Función legacy para compatibilidad (no se usa con Twilio)"""
    try:
        messages = message_data.get('messages', [])
        
        for message in messages:
            from_number = message['from']
            message_type = message['type']
            
            print(f"mensaje desde {from_number}, de tipo: {message_type}")
            
            if message_type == 'text':
                text_content = message['text']['body']
                handle_text_message_extended(from_number, text_content)
            
            elif message_type == 'interactive':
                interactive_content = message['interactive']
                handle_interactive_message(from_number, interactive_content)
            
            else:
                print(f"tipo de mensaje invalido: {message_type}")
    except Exception as e:
        print(f"error procesando mensaje: {e}")

def handle_text_message(from_number,text):
    try:
        text_lower = text.lower().strip()
        text_original = text.strip()

        state=user_states.get(from_number,{})
        current_step=state.get('step','inicial')

        # Manejar respuestas numéricas a botones (Twilio no tiene botones interactivos)
        if text_original.isdigit():
            button_num = int(text_original)
            # Mapear según el contexto del estado
            if current_step == 'menu_principal':
                if button_num == 1:
                    handle_button_response_extended(from_number, 'agendar_cita')
                elif button_num == 2:
                    handle_button_response_extended(from_number, 'ver_citas')
                elif button_num == 3:
                    handle_button_response_extended(from_number, 'gestionar_citas')
                else:
                    WhatsApp_service.send_text_message(from_number, "Opción inválida. Por favor selecciona 1, 2 o 3.")
                return
            elif current_step == 'seleccionando_fecha':
                # Es selección de fecha
                handle_button_response_extended(from_number, f"fecha_option_{button_num}")
                return
            elif current_step == 'seleccionando_hora' or current_step == 'selecionando_hora':
                # Es selección de hora
                handle_button_response_extended(from_number, f"hora_option_{button_num}")
                return
            # Si no coincide con ningún contexto, tratar como texto normal

        if text_lower in ['hola', 'menu', 'inicio', 'start', 'ayuda']:
            WhatsApp_service.send_main_menu(from_number)
            user_states[from_number] = {'step': 'menu_principal'}
            return
        elif current_step=='esperando_nombre_cliente':
            user_states[from_number]['nombre_cliente']=text
            user_states[from_number]['step']='esperando_descripcion'
            WhatsApp_service.send_text_message(
                from_number,f"*cliente:* {text}\n\n Ahora describe el motivo brevemente"
            )
        elif current_step=='esperando_descripcion':
            user_states[from_number]['descripcion']=text
            
            # Obtener user_id del estado si está disponible (para web)
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            
            success=citas_service.crear_cita(
                from_number,
                user_states[from_number],
                paciente_id=user_id,
                whatsapp_service=WhatsApp_service
            )

            if success:
                del user_states[from_number]
                WhatsApp_service.send_text_message(
                    from_number,"escribe *menu* para que aparezca el menu principal"
                )
        else:
            WhatsApp_service.send_text_message(
                from_number,"¡Hola! Soy tu asistente densorita.\n\nEscribe *menu* para ver las opciones disponibles."
            )
    except Exception as e:
        print(f"error manejando mensaje de texto: {e}")
        WhatsApp_service.send_text_message(
            from_number,"Ocurrio un error, escribe *menu* para volver al menu principal"
        )
def handle_interactive_message(from_number,interactive_data):
    try:
        interaction_type=interactive_data['type']
        print(f'Interaccion: {interaction_type}')

        if interaction_type=='button_reply':
            button_id=interactive_data['button_reply']['id']
            handle_button_response_extended(from_number,button_id)
        elif interaction_type=='list_reply':
            list_id=interactive_data['list_reply']['id']
            handle_list_response(from_number,list_id)
    except Exception as e:
        print(f"error manejado interracion: {e}")
def handle_button_response(from_number,button_id):
    try:
        # Si viene como button_X, extraer el número
        if button_id.startswith('button_'):
            button_num = button_id.replace('button_', '')
            # Mapear número a botón según el último mensaje enviado
            # Por ahora, manejamos respuestas numéricas directamente
            print(f"Respuesta numerica recibida: {button_num}")
            # Convertir respuesta numérica a acción según contexto
            # Esto se manejará en handle_text_message_extended
            return
        
        print(f"boton presionado: {button_id}")
        if button_id=='agendar_cita':
            # Obtener fechas dinámicas del último consultorio
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            
            # Obtener user_id y phone del estado si están disponibles (para web)
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            phone = state.get('phone')
            
            print(f"AGENDAR_CITA - from_number: {from_number}, user_id: {user_id}, phone: {phone}")
            
            # Obtener paciente por ID o teléfono, priorizando user_id
            paciente = None
            if user_id:
                print(f"Buscando paciente por user_id: {user_id}")
                paciente = cita_repo.obtener_paciente_por_id(user_id)
                print(f"Paciente encontrado por ID: {paciente is not None}")
            
            if not paciente and (phone or from_number):
                telefono_buscar = phone or from_number
                print(f"Buscando paciente por teléfono: {telefono_buscar}")
                paciente = cita_repo.obtener_paciente_por_telefono(telefono_buscar)
                print(f"Paciente encontrado por teléfono: {paciente is not None}")
            
            fechas_disponibles = []
            
            if paciente:
                print(f"Paciente encontrado: {paciente.uid if hasattr(paciente, 'uid') else 'N/A'}")
                try:
                    ultimo_consultorio = cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
                    if ultimo_consultorio:
                        print(f"Último consultorio encontrado: {ultimo_consultorio}")
                        from datetime import datetime
                        fecha_base = datetime.now()
                        fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
                        
                        fechas_disponibles = cita_repo.obtener_fechas_disponibles(
                            ultimo_consultorio['dentistaId'],
                            ultimo_consultorio['consultorioId'],
                            fecha_timestamp,
                            cantidad=3
                        )
                        print(f"Fechas disponibles encontradas: {len(fechas_disponibles)}")
                        # Guardar fechas en estado para mapeo numérico
                        user_states[from_number] = {
                            'step': 'seleccionando_fecha',
                            'fechas_disponibles': fechas_disponibles,
                            'user_id': user_id,
                            'phone': phone,
                            'paciente_uid': paciente.uid,
                            'ultimo_consultorio': ultimo_consultorio
                        }
                    else:
                        print("No se encontró último consultorio para el paciente")
                        user_states[from_number] = {
                            'step': 'seleccionando_fecha',
                            'user_id': user_id,
                            'phone': phone,
                            'paciente_uid': paciente.uid
                        }
                except Exception as e:
                    print(f"Error obteniendo último consultorio: {e}")
                    import traceback
                    traceback.print_exc()
                    user_states[from_number] = {
                        'step': 'seleccionando_fecha',
                        'user_id': user_id,
                        'phone': phone
                    }
            else:
                print(f"Paciente no encontrado - user_id: {user_id}, phone: {phone or from_number}")
                user_states[from_number] = {
                    'step': 'seleccionando_fecha',
                    'user_id': user_id,
                    'phone': phone
                }
            
            WhatsApp_service.send_date_selection(from_number, fechas_disponibles)
        elif button_id=='ver_citas':
            # Si hay user_id en el estado (para web), usarlo
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            phone = state.get('phone')
            print(f"VER CITAS - from_number: {from_number}, user_id: {user_id}, phone: {phone}")
            try:
                # Pasar WhatsApp_service para que use el servicio correcto (puede ser WebResponseCaptureService)
                citas_service.obtener_citas_usuario(from_number,'ver', user_id=user_id, whatsapp_service=WhatsApp_service)
            except Exception as e:
                print(f"Error en ver_citas: {e}")
                import traceback
                traceback.print_exc()
                WhatsApp_service.send_text_message(from_number, f"Error al obtener tus citas: {str(e)}")
        elif button_id=='gestionar_citas':
            WhatsApp_service.send_management_menu(from_number)
        elif button_id=='reagendar_cita':
            # Si hay user_id en el estado (para web), usarlo
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            citas_service.obtener_citas_usuario(from_number,'reagendar', user_id=user_id, whatsapp_service=WhatsApp_service)
        elif button_id=='cancelar_cita':
            # Si hay user_id en el estado (para web), usarlo
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            citas_service.obtener_citas_usuario(from_number,'cancelar', user_id=user_id, whatsapp_service=WhatsApp_service)
        elif button_id=='volver_menu':
            WhatsApp_service.send_main_menu(from_number)
            user_states[from_number]={'step':'menu_principal'}
        elif button_id.startswith('fecha_'):
            fecha_seleccionada=button_id.replace('fecha_','')
            user_states[from_number]['fecha']=fecha_seleccionada
            user_states[from_number]['step']='selecionando_hora'
            
            # Obtener horarios dinámicos del último consultorio
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            
            # Obtener user_id y phone del estado si están disponibles (para web)
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            phone = state.get('phone')
            
            # Obtener paciente por ID o teléfono
            paciente = cita_repo.obtener_paciente(telefono=phone or from_number, paciente_id=user_id)
            horarios_disponibles = []
            
            if paciente:
                ultimo_consultorio = cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
                if ultimo_consultorio:
                    from datetime import datetime
                    fecha_dt = datetime.strptime(fecha_seleccionada, '%Y-%m-%d')
                    fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
                    
                    horarios_disponibles = cita_repo.obtener_horarios_disponibles(
                        ultimo_consultorio['dentistaId'],
                        ultimo_consultorio['consultorioId'],
                        fecha_timestamp
                    )
                    # Guardar horarios en estado para detección de botones
                    user_states[from_number]['horarios_disponibles'] = horarios_disponibles
            
            WhatsApp_service.send_time_selection(from_number, fecha_seleccionada, horarios_disponibles)
        elif button_id.startswith('hora_') or button_id.startswith('hora_option_'):
            # Manejar selección de hora
            if button_id.startswith('hora_option_'):
                # Es una respuesta numérica
                state = user_states.get(from_number, {})
                horarios_disponibles = state.get('horarios_disponibles', [])
                button_num = int(button_id.replace('hora_option_', '')) - 1
                if 0 <= button_num < len(horarios_disponibles):
                    slot = horarios_disponibles[button_num]
                    hora_seleccionada = slot.get('horaInicio', slot.get('inicio', ''))
                else:
                    # Fallback a horarios por defecto
                    horas_default = ['09:00', '11:00', '14:00']
                    if 0 <= button_num < len(horas_default):
                        hora_seleccionada = horas_default[button_num]
                    else:
                        WhatsApp_service.send_text_message(from_number, "Opción inválida. Por favor selecciona una hora válida.")
                        return
            else:
                hora_seleccionada = button_id.replace('hora_', '')
            
            user_states[from_number]['hora'] = hora_seleccionada
            user_states[from_number]['step'] = 'esperando_nombre_cliente'

            fecha = user_states[from_number]['fecha']
            from datetime import datetime
            fecha_formatted = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
            
            WhatsApp_service.send_text_message(
                from_number,
                f"*Fecha:* {fecha_formatted}\n*Hora:* {hora_seleccionada}\n\n¿Cuál es el *nombre completo* del paciente?"
                )
        elif button_id.startswith('reagendar_'):
            cita_id=button_id.replace('reagendar_','')
            user_states[from_number]={
                'step':'reagendando_fecha',
                'cita_id': cita_id
            }
            # Obtener fechas dinámicas
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            
            # Obtener user_id y phone del estado si están disponibles (para web)
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            phone = state.get('phone')
            
            # Obtener paciente por ID o teléfono
            paciente = cita_repo.obtener_paciente(telefono=phone or from_number, paciente_id=user_id)
            fechas_disponibles = []
            
            if paciente:
                ultimo_consultorio = cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
                if ultimo_consultorio:
                    from datetime import datetime
                    fecha_base = datetime.now()
                    fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
                    
                    fechas_disponibles = cita_repo.obtener_fechas_disponibles(
                        ultimo_consultorio['dentistaId'],
                        ultimo_consultorio['consultorioId'],
                        fecha_timestamp,
                        cantidad=3
                    )
            
            WhatsApp_service.send_date_selection(from_number, fechas_disponibles)
        elif button_id.startswith('cancelar_'):
            cita_id=button_id.replace('cancelar_','')
            
            # Obtener user_id del estado si está disponible (para web)
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            phone = state.get('phone')
            
            WhatsApp_service.send_text_message(
                from_number,"¿Estás seguro de que quieres cancelar esta cita?\n\nResponde *SI* para confirmar o *NO* para mantenerla.",
            )
            user_states[from_number]={
                'step':'confurmando_cancelacion',
                'cita_id': cita_id,
                'user_id': user_id,
                'phone': phone
            }
            # No cancelar todavía, solo guardar el estado para confirmación
    except Exception as e:
        print(f"error con el bototn: {e}")
def handle_list_response(from_number,list_id):
    try:
        print(f"Lista seleccionada: {list_id}")
        if '_' in list_id:
            action,cita_id=list_id.split('_',1)
            if action=='ver':
                citas_service.mostrar_detalles_cita(from_number,cita_id)
            elif action=='reagendar':
                user_states[from_number]={
                    'step':'reagendando_fecha',
                    'cita_id':cita_id
                }
                # Obtener fechas dinámicas
                from database.models import CitaRepository
                cita_repo = CitaRepository()
                paciente = cita_repo.obtener_paciente_por_telefono(from_number)
                fechas_disponibles = []
                
                if paciente:
                    ultimo_consultorio = cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
                    if ultimo_consultorio:
                        from datetime import datetime
                        fecha_base = datetime.now()
                        fecha_timestamp = datetime.combine(fecha_base.date(), datetime.min.time())
                        
                        fechas_disponibles = cita_repo.obtener_fechas_disponibles(
                            ultimo_consultorio['dentistaId'],
                            ultimo_consultorio['consultorioId'],
                            fecha_timestamp,
                            cantidad=3
                        )
                
                WhatsApp_service.send_date_selection(from_number, fechas_disponibles)
            elif action=="cancelar":
                WhatsApp_service.send_text_message(
                    from_number,"¿Estás seguro de que quieres cancelar esta cita?\n\nResponde *SI* para confirmar o *NO* para mantenerla.",
                )
                user_states[from_number]={
                    'step':'confirmando_cancelacion',
                    'cita_id':cita_id
                }
    except Exception as e:
        print(f"error manejando lista: {e}")
def handle_reagendamiento(from_number, button_id):
    try:
        state = user_states.get(from_number, {})
        current_step = state.get('step', '')
        
        print(f"handle_reagendamiento - from_number: {from_number}, button_id: {button_id}, step: {current_step}")
        
        # Solo procesar si estamos en un paso de reagendamiento
        if current_step == 'reagendando_fecha' and button_id.startswith('fecha_'):
            nueva_fecha = button_id.replace('fecha_', '')
            user_states[from_number]['nueva_fecha'] = nueva_fecha
            user_states[from_number]['step'] = 'reagendando_hora'
            
            # Obtener horarios dinámicos
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            
            # Obtener user_id y phone del estado si están disponibles (para web)
            state = user_states.get(from_number, {})
            user_id = state.get('user_id')
            phone = state.get('phone')
            
            # Obtener paciente por ID o teléfono
            paciente = cita_repo.obtener_paciente(telefono=phone or from_number, paciente_id=user_id)
            horarios_disponibles = []
            
            if paciente:
                ultimo_consultorio = cita_repo.obtener_ultimo_consultorio_paciente(paciente.uid)
                if ultimo_consultorio:
                    from datetime import datetime
                    fecha_dt = datetime.strptime(nueva_fecha, '%Y-%m-%d')
                    fecha_timestamp = datetime.combine(fecha_dt.date(), datetime.min.time())
                    
                    horarios_disponibles = cita_repo.obtener_horarios_disponibles(
                        ultimo_consultorio['dentistaId'],
                        ultimo_consultorio['consultorioId'],
                        fecha_timestamp
                    )
                    # Guardar horarios en estado para detección de botones
                    user_states[from_number]['horarios_disponibles'] = horarios_disponibles
            
            WhatsApp_service.send_time_selection(from_number, nueva_fecha, horarios_disponibles)
            return True
        
        elif current_step == 'reagendando_hora' and (button_id.startswith('hora_') or button_id.startswith('hora_option_')):
            # Manejar selección de hora (puede ser hora_ o hora_option_)
            if button_id.startswith('hora_option_'):
                # Es una respuesta numérica
                horarios_disponibles = state.get('horarios_disponibles', [])
                button_num = int(button_id.replace('hora_option_', '')) - 1
                if 0 <= button_num < len(horarios_disponibles):
                    slot = horarios_disponibles[button_num]
                    nueva_hora = slot.get('horaInicio', slot.get('inicio', ''))
                else:
                    WhatsApp_service.send_text_message(from_number, "Opción inválida. Por favor selecciona una hora válida.")
                    return True
            else:
                nueva_hora = button_id.replace('hora_', '')
            
            cita_id = state.get('cita_id')
            nueva_fecha = state.get('nueva_fecha')
            
            # Obtener user_id del estado si está disponible (para web)
            user_id = state.get('user_id')

            success = citas_service.reagendar_cita(
                from_number, 
                cita_id, 
                nueva_fecha, 
                nueva_hora,
                paciente_id=user_id,
                whatsapp_service=WhatsApp_service
            )
            
            if success:
                del user_states[from_number]
                WhatsApp_service.send_text_message(
                    from_number,
                    "Escribe *menu* para realizar otra acción."
                )
            return True
        
        # Si no es un paso de reagendamiento, retornar False para que continúe con handle_button_response
        print(f"handle_reagendamiento - No es paso de reagendamiento, retornando False")
        return False
    
    except Exception as e:
        print(f"Error en reagendamiento: {e}")
        import traceback
        traceback.print_exc()
        return False
def handle_cancelacion(from_number, text):
    try:
        state = user_states.get(from_number, {})
        
        if state.get('step') == 'confirmando_cancelacion':
            text_upper = text.upper().strip()
            cita_id = state.get('cita_id')
            
            if text_upper == 'SI' or text_upper == 'SÍ':
                # Obtener user_id del estado si está disponible (para web)
                user_id = state.get('user_id')
                
                success = citas_service.cancelar_cita(
                    from_number, 
                    cita_id,
                    paciente_id=user_id,
                    whatsapp_service=WhatsApp_service
                )
                
                if success:
                    del user_states[from_number]
                    WhatsApp_service.send_text_message(
                        from_number,
                        "Escribe *menu* para agendar una nueva cita o realizar otra acción."
                    )
            
            elif text_upper == 'NO':
                # No cancelar
                del user_states[from_number]
                WhatsApp_service.send_text_message(
                    from_number,
                    "Perfecto, tu cita se mantiene programada.\n\nEscribe *menu* para realizar otra acción."
                )
            
            else:
                WhatsApp_service.send_text_message(
                    from_number,
                    "Por favor responde *SI* para cancelar o *NO* para mantener la cita."
                )
            
            return True
    
    except Exception as e:
        print(f"Error manejando cancelación: {e}")
        return False
    
def handle_text_message_extended(from_number, text):
    if handle_cancelacion(from_number, text):
        return

    handle_text_message(from_number, text)

def handle_button_response_extended(from_number, button_id):
    if handle_reagendamiento(from_number, button_id):
        return
    handle_button_response(from_number, button_id)

def process_web_button_response(session_id, button_id, response_messages, user_id=None, phone=None):
    """Procesa respuestas de botones para web usando la misma lógica que WhatsApp"""
    # Obtener user_id y phone del estado si no se pasaron como parámetros
    state = user_states.get(session_id, {})
    if not user_id:
        user_id = state.get('user_id')
    if not phone:
        phone = state.get('phone')
    
    # Crear servicio de captura
    class WebResponseCaptureService:
        def send_text_message(self, to_number, message):
            print(f"WebResponseCaptureService.send_text_message: {message[:100]}")
            response_messages.append(message)
        def send_main_menu(self, to_number):
            menu_text = """¡Hola! Bienvenido a Densora.

¿Qué te gustaría hacer hoy?

*Opciones disponibles:*
1. Agendar Cita
2. 👀 Ver Mis Citas
3. Gestionar Citas

Escribe el *número* de la opción que deseas (1, 2 o 3)."""
            print(f"WebResponseCaptureService.send_main_menu")
            response_messages.append(menu_text)
        def send_management_menu(self, to_number):
            print(f"WebResponseCaptureService.send_management_menu")
            response_messages.append("¿Qué deseas gestionar?\n1. Reagendar Cita\n2. Cancelar Cita\n3. Volver al Menú Principal")
        def send_date_selection(self, to_number, dates):
            print(f"WebResponseCaptureService.send_date_selection: {len(dates) if dates else 0} fechas")
            if not dates or len(dates) == 0:
                response_messages.append("Lo siento, no hay fechas disponibles en este momento.\n\nPor favor, contacta directamente con el consultorio o intenta más tarde.\n\nEscribe *menu* para volver al menú principal.")
            else:
                date_options = "\n".join([f"{i+1}. {d.strftime('%d/%m/%Y')}" for i, d in enumerate(dates)])
                response_messages.append(f"Por favor, selecciona una fecha:\n{date_options}")
        def send_time_selection(self, to_number, date, times):
            time_options = "\n".join([f"{i+1}. {t.get('horaInicio', t.get('inicio', ''))}" for i, t in enumerate(times)]) if times else "No hay horarios disponibles"
            print(f"WebResponseCaptureService.send_time_selection: {len(times) if times else 0} horarios")
            response_messages.append(f"Para la fecha {date}, selecciona una hora:\n{time_options}")
        def send_confirmation_message(self, to_number, cita, is_new):
            action = "creada" if is_new else "reagendada"
            fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y') if isinstance(cita.fecha, str) else cita.fecha.strftime('%d/%m/%Y')
            print(f"WebResponseCaptureService.send_confirmation_message")
            response_messages.append(f"Tu cita ha sido {action} con éxito:\n*Cliente:* {cita.nombre_cliente}\n*Fecha:* {fecha_formatted}\n*Hora:* {cita.horaInicio or cita.hora}"),
        def send_citas_list(self, to_number, citas, action_type):
            print(f"WebResponseCaptureService.send_citas_list: {len(citas)} citas, action_type: {action_type}")
            if not citas:
                response_messages.append("No tienes citas programadas.\n\nEscribe *menu* para agendar una nueva cita.")
                return
            list_items = []
            for i, cita in enumerate(citas):
                try:
                    # Manejar diferentes formatos de fecha
                    if isinstance(cita.fecha, datetime):
                        fecha_str = cita.fecha.strftime('%d/%m/%Y')
                    elif isinstance(cita.fecha, str):
                        try:
                            fecha_obj = datetime.strptime(cita.fecha, '%Y-%m-%d')
                            fecha_str = fecha_obj.strftime('%d/%m/%Y')
                        except:
                            fecha_str = cita.fecha
                    else:
                        fecha_str = str(cita.fecha)
                    
                    hora = cita.horaInicio or cita.hora or 'N/A'
                    nombre = cita.nombre_cliente or 'Sin nombre'
                    list_items.append(f"{i+1}. {nombre} - {fecha_str} {hora}")
                except Exception as e:
                    print(f"Error formateando cita {i+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    list_items.append(f"{i+1}. Cita {i+1}")
            
            action_messages = {
                "ver": "Tus citas programadas:",
                "reagendar": "Selecciona la cita que deseas reagendar:",
                "cancelar": "Selecciona la cita que deseas cancelar:"
            }
            header = action_messages.get(action_type, "Tus citas:")
            response_messages.append(f"{header}\n" + "\n".join(list_items) + "\n\nEscribe el *número* de la cita para ver más detalles.")
        def send_cita_details(self, to_number, cita):
            fecha_formatted = cita.fecha.strftime('%d/%m/%Y') if isinstance(cita.fecha, datetime) else cita.fecha
            print(f"WebResponseCaptureService.send_cita_details")
            response_messages.append(f"*Detalles de la Cita*\n*Cliente:* {cita.nombre_cliente}\n*Fecha:* {fecha_formatted}\n*Hora:* {cita.horaInicio or cita.hora}\n*Motivo:* {cita.motivo}\n*Estado:* {cita.estado}")
        def send_interactive_buttons(self, to_number, header, body, buttons, content_sid=None):
            # Para web, convertir botones a texto numerado
            button_text = "\n".join([f"{i+1}. {btn.get('title', btn.get('id', ''))}" for i, btn in enumerate(buttons)])
            print(f"WebResponseCaptureService.send_interactive_buttons")
            response_messages.append(f"{header}\n\n{body}\n\n{button_text}")
    
    # Reemplazar WhatsAppService temporalmente
    global WhatsApp_service
    original_whatsapp_service = WhatsApp_service
    WhatsApp_service = WebResponseCaptureService()
    
    try:
        # Para web, usar phone o user_id cuando sea necesario
        # Crear un identificador temporal que será usado por handle_button_response
        user_identifier = phone or user_id or session_id
        
        print(f"PROCESS_WEB_BUTTON_RESPONSE - user_identifier: {user_identifier}, button_id: {button_id}")
        
        # Si tenemos user_id o phone, actualizar el estado tanto con session_id como con user_identifier
        # Esto asegura que handle_button_response pueda encontrar el estado
        if user_id or phone:
            # Guardar el identificador en el estado para que las funciones lo usen
            state['user_identifier'] = user_identifier
            state['user_id'] = user_id
            state['phone'] = phone
            # Guardar el estado con session_id (para mantener consistencia)
            user_states[session_id] = state
            # También guardar el estado con user_identifier para que handle_button_response lo encuentre
            if user_identifier != session_id:
                user_states[user_identifier] = state.copy()
            print(f"Estado actualizado: user_id={user_id}, phone={phone}, guardado con session_id y user_identifier")
        
        # Usar la misma lógica que handle_button_response_extended
        if handle_reagendamiento(session_id, button_id):
            print(f"handle_reagendamiento retornó True, response_messages tiene {len(response_messages)} mensajes")
            if len(response_messages) == 0:
                response_messages.append("Error procesando reagendamiento. Por favor, intenta nuevamente.")
            return
        
        print(f"Llamando handle_button_response con user_identifier: {user_identifier}, button_id: {button_id}")
        handle_button_response(user_identifier, button_id)
        print(f"Después de handle_button_response, response_messages tiene {len(response_messages)} mensajes")
        
        # Sincronizar el estado de vuelta al session_id después de handle_button_response
        if user_identifier != session_id and user_identifier in user_states:
            user_states[session_id] = user_states[user_identifier].copy()
        
        # Si no hay mensajes, agregar un mensaje de error
        if len(response_messages) == 0:
            print(f"ERROR: No se generaron mensajes para button_id: {button_id}")
            response_messages.append("Lo siento, hubo un error procesando tu solicitud. Por favor, intenta nuevamente o escribe *menu* para volver al menú principal.")
    except Exception as e:
        print(f"ERROR en process_web_button_response: {e}")
        import traceback
        traceback.print_exc()
        if len(response_messages) == 0:
            response_messages.append(f"Error procesando tu solicitud: {str(e)}\n\nEscribe *menu* para volver al menú principal.")
    finally:
        # Restaurar el servicio original
        WhatsApp_service = original_whatsapp_service

def process_web_message(session_id, message_body, platform, user_id=None, phone=None, user_name=None):
    """Adaptar la lógica existente para el chat web - usa la misma lógica que WhatsApp"""
    text_lower = message_body.lower().strip()
    text_original = message_body.strip()

    state = user_states.get(session_id, {})
    current_step = state.get('step', 'inicial')
    
    # Guardar user_id y phone en el estado para usarlos después
    if user_id:
        state['user_id'] = user_id
    if phone:
        state['phone'] = phone
    if user_name:
        state['user_name'] = user_name
    user_states[session_id] = state
    
    response_messages = []  # Para acumular las respuestas del bot
    
    # Verificar si es una respuesta numérica (como en WhatsApp)
    if text_original.isdigit():
        button_num = int(text_original)
        # Mapear según el contexto del estado (igual que en handle_text_message)
        if current_step == 'menu_principal':
            if button_num == 1:
                button_id = 'agendar_cita'
            elif button_num == 2:
                button_id = 'ver_citas'
            elif button_num == 3:
                button_id = 'gestionar_citas'
            else:
                button_id = None
        elif current_step == 'seleccionando_fecha' or current_step == 'reagendando_fecha':
            button_id = f"fecha_option_{button_num}"
        elif current_step == 'selecionando_hora' or current_step == 'reagendando_hora':
            button_id = f"hora_option_{button_num}"
        elif current_step == 'gestion_citas':
            if button_num == 1:
                button_id = 'reagendar_cita'
            elif button_num == 2:
                button_id = 'cancelar_cita'
            elif button_num == 3:
                button_id = 'volver_menu'
            else:
                button_id = None
        elif current_step == 'seleccionando_cita_reagendar' or current_step == 'seleccionando_cita_cancelar':
            # Obtener citas y mapear número a cita_id
            from services.citas_service import CitasService
            citas_service_temp = CitasService()
            # Usar phone o user_id si están disponibles, sino usar session_id como fallback
            user_identifier = phone or user_id or session_id
            citas = citas_service_temp.obtener_citas_usuario_web(user_identifier, user_id=user_id, phone=phone)
            if 0 <= button_num - 1 < len(citas):
                cita_id = citas[button_num - 1]['id']
                if current_step == 'seleccionando_cita_reagendar':
                    button_id = f"reagendar_{cita_id}"
                else:
                    button_id = f"cancelar_{cita_id}"
            else:
                button_id = None
        else:
            button_id = None
        
        # Si se identificó un botón, procesarlo como respuesta de botón
        if button_id:
            print(f"Procesando button_id: {button_id} para session_id: {session_id}")
            # Procesar como respuesta de botón usando la misma lógica que WhatsApp
            process_web_button_response(session_id, button_id, response_messages, user_id=user_id, phone=phone)
            result = "\n".join(response_messages) if response_messages else "Lo siento, hubo un error procesando tu solicitud. Por favor, intenta nuevamente o escribe *menu*."
            print(f"Resultado de process_web_button_response: {len(response_messages)} mensajes, resultado: {result[:100]}")
            return result

    # Crear servicio de captura (reutilizar el mismo que en process_web_button_response)
    class WebResponseCaptureService:
        def send_text_message(self, to_number, message):
            response_messages.append(message)
        def send_main_menu(self, to_number):
            menu_text = """¡Hola! Bienvenido a Densora.

¿Qué te gustaría hacer hoy?

*Opciones disponibles:*
1. Agendar Cita
2. 👀 Ver Mis Citas
3. Gestionar Citas

Escribe el *número* de la opción que deseas (1, 2 o 3)."""
            response_messages.append(menu_text)
        def send_management_menu(self, to_number):
            response_messages.append("¿Qué deseas gestionar?\n1. Reagendar Cita\n2. Cancelar Cita\n3. Volver al Menú Principal")
        def send_date_selection(self, to_number, dates):
            date_options = "\n".join([f"{i+1}. {d.strftime('%d/%m/%Y')}" for i, d in enumerate(dates)])
            response_messages.append(f"Por favor, selecciona una fecha:\n{date_options}")
        def send_time_selection(self, to_number, date, times):
            time_options = "\n".join([f"{i+1}. {t.get('horaInicio', t.get('inicio', ''))}" for i, t in enumerate(times)])
            response_messages.append(f"Para la fecha {date}, selecciona una hora:\n{time_options}")
        def send_confirmation_message(self, to_number, cita, is_new):
            action = "creada" if is_new else "reagendada"
            fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y') if isinstance(cita.fecha, str) else cita.fecha.strftime('%d/%m/%Y')
            response_messages.append(f"Tu cita ha sido {action} con éxito:\n*Cliente:* {cita.nombre_cliente}\n*Fecha:* {fecha_formatted}\n*Hora:* {cita.horaInicio or cita.hora}"),
        def send_citas_list(self, to_number, citas, action_type):
            if not citas:
                response_messages.append("No tienes citas programadas.\n\nEscribe *menu* para agendar una nueva cita.")
                return
            list_items = []
            for i, cita in enumerate(citas):
                try:
                    # Manejar diferentes formatos de fecha
                    if isinstance(cita.fecha, datetime):
                        fecha_str = cita.fecha.strftime('%d/%m/%Y')
                    elif isinstance(cita.fecha, str):
                        try:
                            fecha_obj = datetime.strptime(cita.fecha, '%Y-%m-%d')
                            fecha_str = fecha_obj.strftime('%d/%m/%Y')
                        except:
                            fecha_str = cita.fecha
                    else:
                        fecha_str = str(cita.fecha)
                    
                    hora = cita.horaInicio or cita.hora or 'N/A'
                    nombre = cita.nombre_cliente or 'Sin nombre'
                    list_items.append(f"{i+1}. {nombre} - {fecha_str} {hora}")
                except Exception as e:
                    print(f"Error formateando cita {i+1}: {e}")
                    list_items.append(f"{i+1}. Cita {i+1}")
            
            action_messages = {
                "ver": "Tus citas programadas:",
                "reagendar": "Selecciona la cita que deseas reagendar:",
                "cancelar": "Selecciona la cita que deseas cancelar:"
            }
            header = action_messages.get(action_type, "Tus citas:")
            response_messages.append(f"{header}\n" + "\n".join(list_items) + "\n\nEscribe el *número* de la cita para ver más detalles.")
        def send_cita_details(self, to_number, cita):
            fecha_formatted = cita.fecha.strftime('%d/%m/%Y') if isinstance(cita.fecha, datetime) else cita.fecha
            response_messages.append(f"*Detalles de la Cita*\n*Cliente:* {cita.nombre_cliente}\n*Fecha:* {fecha_formatted}\n*Hora:* {cita.horaInicio or cita.hora}\n*Motivo:* {cita.motivo}\n*Estado:* {cita.estado}")
        def send_interactive_buttons(self, to_number, header, body, buttons, content_sid=None):
            # Para web, convertir botones a texto numerado
            button_text = "\n".join([f"{i+1}. {btn.get('title', btn.get('id', ''))}" for i, btn in enumerate(buttons)])
            response_messages.append(f"{header}\n\n{body}\n\n{button_text}")

    # Reemplazar WhatsAppService con nuestro capturador de respuestas
    global WhatsApp_service
    original_whatsapp_service = WhatsApp_service
    WhatsApp_service = WebResponseCaptureService()
    
    try:
        # Usar la MISMA lógica que handle_text_message_extended
        # Esto asegura que funcione exactamente igual que WhatsApp
        handle_text_message_extended(session_id, message_body)
    except Exception as e:
        print(f"ERROR en process_web_message: {e}")
        import traceback
        traceback.print_exc()
        if len(response_messages) == 0:
            response_messages.append(f"Error procesando tu mensaje: {str(e)}\n\nEscribe *menu* para volver al menú principal.")
    finally:
        # Restaurar el servicio original de WhatsApp
        WhatsApp_service = original_whatsapp_service

    result = "\n".join(response_messages) if response_messages else "Lo siento, no pude procesar tu mensaje. Por favor, intenta nuevamente o escribe *menu*."
    print(f"process_web_message retornando: {len(response_messages)} mensajes, resultado: {result[:100]}")
    return result

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', Config.PORT))
    print(f"Puerto: {port}")
    print(f"Debug: {Config.DEBUG}")
    print("Servidor listo")
    
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0', 
        port=port
    )