from database.models import Cita, CitaRepository
from services.whatsapp_service import WhatsAppService
from datetime import datetime

class CitasService:
    def __init__(self):
        self.cita_repo=CitaRepository()
        self.whatsapp=WhatsAppService()
    
    def crear_cita(self, usuario_whatsapp:str, datos_cita:dict)-> bool:
        try:
            cita_id = self.cita_repo.crear_cita(usuario_whatsapp, datos_cita)
            if cita_id:
                # Obtener la cita creada para mostrar confirmación
                cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
                if cita:
                    self.whatsapp.send_confirmation_message(
                        usuario_whatsapp, cita, is_new=True
                    )
                    print(f"cita creada: {cita_id}")
                    return True
                else:
                    # Si no se puede obtener, crear objeto temporal para confirmación
                    from database.models import Cita
                    nueva_cita = Cita(
                        id=cita_id,
                        nombre_cliente=datos_cita.get('nombre_cliente'),
                        fecha=datos_cita.get('fecha'),
                        horaInicio=datos_cita.get('hora'),
                        motivo=datos_cita.get('descripcion', ''),
                        estado='confirmado'
                    )
                    self.whatsapp.send_confirmation_message(
                        usuario_whatsapp, nueva_cita, is_new=True
                    )
                    return True
            else:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"error al crear tu cita, intenta nuevamente"
                )
                return False
        except Exception as e:
            print(f"error al crear cita: {e}")
            self.whatsapp.send_text_message(usuario_whatsapp,"ocurrio un error inesperado, intenta mas tarde")
            return False
    def obtener_citas_usuario(self,usuario_whatsapp:str,action_type:str="ver", user_id=None):
        try:
            print(f"obtener_citas_usuario - usuario_whatsapp: {usuario_whatsapp}, user_id: {user_id}, action_type: {action_type}")
            # Si tenemos user_id, usar directamente obtener_citas_paciente
            if user_id:
                print(f"Buscando citas por user_id: {user_id}")
                citas = self.cita_repo.obtener_citas_paciente(user_id)
            else:
                print(f"Buscando citas por usuario_whatsapp: {usuario_whatsapp}")
                citas = self.cita_repo.obtener_citas_usuario(usuario_whatsapp)
            print(f"Encontradas {len(citas)} citas")
            self.whatsapp.send_citas_list(usuario_whatsapp, citas, action_type)
            return len(citas) > 0
            
        except Exception as e:
            print(f"error obteniendo citas: {e}")
            import traceback
            traceback.print_exc()
            self.whatsapp.send_text_message(
                usuario_whatsapp,
                f"Error al obtener tus citas: {str(e)}\n\nIntenta nuevamente o escribe *menu* para volver al menú principal."
            )
            return False
    def mostrar_detalles_cita(self,usuario_whatsapp:str,cita_id:str):
        try:
            cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
            if cita:
                self.whatsapp.send_cita_details(usuario_whatsapp, cita)
            else:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no se encontro la cita"
                )
        except Exception as e:
            print(f"error mostrando detalles:{e}")
            self.whatsapp.send_text_message(usuario_whatsapp,"error mostrando los detalles")
    def reagendar_cita(self, usuario_whatsapp:str, cita_id:str,nueva_fecha:str,nueva_hora:str)->bool:
        try:
            cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
            if not cita:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no existe la cita que intentas reagendar"
                )
                return False
            success = self.cita_repo.actualizar_cita(usuario_whatsapp, cita_id, nueva_fecha, nueva_hora)
            if success:
                # Actualizar objeto local para confirmación
                cita.fecha = nueva_fecha
                cita.horaInicio = nueva_hora
                cita.hora = nueva_hora
                self.whatsapp.send_confirmation_message(
                    usuario_whatsapp, cita, is_new=False
                )
                print(f"cita {cita_id} reagendada")
                return True
            else:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no se pudo reagendar la cita. intenta nuevamente"
                )
                return False
        except Exception as e:
            print(f"error reagendando cita: {e}")
            self.whatsapp.send_text_message(
                usuario_whatsapp,"error reagendando cita"
            )    
            return False
    def cancelar_cita(self,usuario_whatsapp:str,cita_id:str)->bool:
        try:
            cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
            if not cita:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no se encontro la cita"
                )
                return False
            success = self.cita_repo.eliminar_cita(usuario_whatsapp, cita_id)
            if success:
                fecha_formatted = ''
                if cita.fecha:
                    if isinstance(cita.fecha, str):
                        fecha_formatted = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
                    else:
                        fecha_formatted = cita.fecha.strftime('%d/%m/%Y')
                
                mensaje_cancelacion = f"""*CITA CANCELADA*
*Cliente:* {cita.nombre_cliente or 'N/A'}
*Fecha:* {fecha_formatted}
*Hora:* {cita.horaInicio or cita.hora or 'N/A'}
Tu cita ha sido cancelada"""
                self.whatsapp.send_text_message(usuario_whatsapp, mensaje_cancelacion)
                print(f"Cita cancelada {cita_id}")
                return True
            else:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no se pudo cancelar la cita. intenta nuevamente"
                )
                return False
        except Exception as e:
            print(f"error cancelando cita: {e}")
            self.whatsapp.send_text_message(
                usuario_whatsapp,"error cancelando cita"
            )    
            return False
    def validar_disponibilidad(self, fecha: str, hora: str) -> bool:
        try:
            fecha_cita=datetime.strptime(fecha,'%y-%m-%d')
            fecha_actual=datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
            
            if fecha_cita<fecha_actual:
                return False
            
            hora_obj=datetime.strptime(hora,'%H:%M').time()
            hora_inicio=datetime.strptime('09:00','%H:%M').time()
            hora_fin=datetime.strptime('17:00','%H:%M').time()

            if hora_obj<hora_inicio or hora_obj>hora_fin:
                return False
            
            #desdes mas verificaciones contra conflictos con otras citas,dias festivox etc me da flojera
            return True
        except Exception as e:
            print(f"error validando disponibilidad: {e}")
            return False
    
    def obtener_citas_usuario_web(self, usuario_whatsapp: str, user_id=None, phone=None):
        """
        Obtiene las citas del usuario para la web (solo devuelve datos, no envía por WhatsApp)
        Puede usar user_id, phone o usuario_whatsapp como identificador
        """
        try:
            # Si tenemos user_id, usar directamente obtener_citas_paciente
            if user_id:
                citas = self.cita_repo.obtener_citas_paciente(user_id)
            # Si tenemos phone, buscar por teléfono
            elif phone:
                citas = self.cita_repo.obtener_citas_usuario(phone)
            # Fallback a usuario_whatsapp (session_id)
            else:
                citas = self.cita_repo.obtener_citas_usuario(usuario_whatsapp)
            
            # Convertir a formato simple para la web
            citas_formateadas = []
            for cita in citas:
                fecha_str = ''
                if cita.fecha:
                    if isinstance(cita.fecha, str):
                        fecha_str = datetime.strptime(cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
                    else:
                        fecha_str = cita.fecha.strftime('%d/%m/%Y')
                
                citas_formateadas.append({
                    'id': cita.id,
                    'nombre_cliente': cita.nombre_cliente or 'N/A',
                    'fecha': fecha_str,
                    'hora': cita.horaInicio or cita.hora or 'N/A',
                    'motivo': cita.motivo or 'N/A',
                    'estado': cita.estado or 'confirmado'
                })
            return citas_formateadas
        except Exception as e:
            print(f"error obteniendo citas para web: {e}")
            return []