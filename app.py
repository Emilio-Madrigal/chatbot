from flask import Flask,request,jsonify
from config import Config
from services.whatsapp_service import WhatsAppService
from services.citas_service import CitasService
import json

app=Flask(__name__)
app.config.from_object(Config)

WhatsApp_service=WhatsAppService()
citas_service=CitasService()
user_states={}

@app.route('/webhook',methods=['GET'])
def verify_webhook():
    verify_token=request.args.get('hub.verify_token')
    challenge=request.args.get('hub.challenge')

    print(f"verificando webhook: {verify_token}")

    if verify_token==Config.WHATSAPP_VERIFY_TOKEN:
        print("webhook verificado")
        return challenge
    else:
        print("verificacion fallida")
        return "Error de verificacion",403
    
@app.route('/webhook',methods=['POST'])
def webhook():
    try:
        data=request.get_json()
        print(f"webhook recibido: {json.dumps(data,indent=2)}")
        if 'entry' in data:
                    for entry in data['entry']:
                        if 'changes' in entry:
                            for change in entry['changes']:
                                if 'value' in change and 'messages' in change['value']:
                                    process_message(change['value'])
        return jsonify({"status": "success"}),200
    except Exception as e:
        print(f"error en webhook: {e}")
        return jsonify({"status":"error","message":str(e)}),500
def process_message(message_data):
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

        state=user_states.get(from_number,{})
        current_step=state.get('step','inicial')

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
            success=citas_service.crear_cita(from_number,user_states[from_number])

            if success:
                del user_states[from_number]
                WhatsApp_service.send_text_message(
                    from_number,"escribe *menu* para que aparezca el menu principal"
                )
        else:
            WhatsApp_service.send_text_message(
                from_number,"👋 ¡Hola! Soy tu asistente densorita.\n\nEscribe *menu* para ver las opciones disponibles."
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
        print(f"boton presionado: {button_id}")
        if button_id=='agendar_cita':
            # Obtener fechas dinámicas del último consultorio
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
            user_states[from_number]={'step':'seleccionando_fecha'}
        elif button_id=='ver_citas':
            citas_service.obtener_citas_usuario(from_number,'ver')
        elif button_id=='gestionar_citas':
            WhatsApp_service.send_management_menu(from_number)
        elif button_id=='reagendar_cita':
            citas_service.obtener_citas_usuario(from_number,'reagendar')
        elif button_id=='cancelar_cita':
            citas_service.obtener_citas_usuario(from_number,'cancelar')
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
            paciente = cita_repo.obtener_paciente_por_telefono(from_number)
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
            
            WhatsApp_service.send_time_selection(from_number, fecha_seleccionada, horarios_disponibles)
        elif button_id.startswith('hora_'):
            hora_seleccionada = button_id.replace('hora_', '')
            user_states[from_number]['hora'] = hora_seleccionada
            user_states[from_number]['step'] = 'esperando_nombre_cliente'

            fecha = user_states[from_number]['fecha']
            from datetime import datetime
            fecha_formatted = datetime.strptime(fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
            
            WhatsApp_service.send_text_message(
                from_number,
                f"📅 *Fecha:* {fecha_formatted}\n⏰ *Hora:* {hora_seleccionada}\n\n👤 ¿Cuál es el *nombre completo* del paciente?"
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
        elif button_id.startswith('cancelar_'):
            cita_id=button_id.replace('cancelar_','')
            WhatsApp_service.send_text_message(
                from_number,"⚠️ ¿Estás seguro de que quieres cancelar esta cita?\n\nResponde *SI* para confirmar o *NO* para mantenerla."
            )
            user_states[from_number]={
                'step':'confurmando_cancelacion',
                'cita_id': cita_id
            }
            citas_service.cancelar_cita(from_number,cita_id)
    except Exception as e:
        print(f"error con el bototn: {e}")
def handle_list_response(from_number,list_id):
    try:
        print(f"📋 Lista seleccionada: {list_id}")
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
                    from_number,"⚠️ ¿Estás seguro de que quieres cancelar esta cita?\n\nResponde *SI* para confirmar o *NO* para mantenerla."
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
        
        if state.get('step') == 'reagendando_fecha' and button_id.startswith('fecha_'):
            nueva_fecha = button_id.replace('fecha_', '')
            user_states[from_number]['nueva_fecha'] = nueva_fecha
            user_states[from_number]['step'] = 'reagendando_hora'
            
            # Obtener horarios dinámicos
            from database.models import CitaRepository
            cita_repo = CitaRepository()
            paciente = cita_repo.obtener_paciente_por_telefono(from_number)
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
            
            WhatsApp_service.send_time_selection(from_number, nueva_fecha, horarios_disponibles)
        
        elif state.get('step') == 'reagendando_hora' and button_id.startswith('hora_'):
            nueva_hora = button_id.replace('hora_', '')
            cita_id = state.get('cita_id')
            nueva_fecha = state.get('nueva_fecha')

            success = citas_service.reagendar_cita(from_number, cita_id, nueva_fecha, nueva_hora)
            
            if success:

                del user_states[from_number]

                WhatsApp_service.send_text_message(
                    from_number,
                    "Escribe *menu* para realizar otra acción."
                )
            
        return True
    
    except Exception as e:
        print(f"Error en reagendamiento: {e}")
        return False
def handle_cancelacion(from_number, text):
    try:
        state = user_states.get(from_number, {})
        
        if state.get('step') == 'confirmando_cancelacion':
            text_upper = text.upper().strip()
            cita_id = state.get('cita_id')
            
            if text_upper == 'SI' or text_upper == 'SÍ':
                success = citas_service.cancelar_cita(from_number, cita_id)
                
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
                    "✅ Perfecto, tu cita se mantiene programada.\n\nEscribe *menu* para realizar otra acción."
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

if __name__ == '__main__':
    print(f"📡 Puerto: {Config.PORT}")
    print(f"🔧 Debug: {Config.DEBUG}")
    print("listo")
    
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0', 
        port=Config.PORT
    )