import asyncio
from datetime import datetime
from database.models import Cita, CitaRepository
from services.whatsapp_service import WhatsAppService
from services.event_notifier import event_notifier

class CitasService:
    def __init__(self):
        self.cita_repo=CitaRepository()
        self.whatsapp=WhatsAppService()

    @staticmethod
    def _run_async(coro):
        """Ejecuta una corrutina sin bloquear Flask."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        else:
            return loop.create_task(coro)

    def _get_paciente_uid(self, usuario_whatsapp: str, paciente_id: str = None):
        """Obtiene el uid del paciente usando id explícito o teléfono."""
        if paciente_id:
            return paciente_id
        try:
            paciente = self.cita_repo.paciente_repo.buscar_por_telefono(usuario_whatsapp)
            return paciente.uid if paciente else None
        except Exception:
            return None

    def _date_to_str(self, fecha):
        if not fecha:
            return ''
        if isinstance(fecha, str):
            return fecha
        try:
            return fecha.strftime('%Y-%m-%d')
        except Exception:
            return str(fecha)

    def _notify_created(self, paciente_uid, cita: Cita):
        if not paciente_uid or not cita:
            return
        try:
            self._run_async(
                event_notifier.notify_appointment_created(
                    cita_id=cita.id,
                    paciente_id=paciente_uid,
                    fecha=self._date_to_str(cita.fecha),
                    hora=cita.horaInicio or cita.hora or '',
                    dentista_name=getattr(cita, 'dentistaName', None) or 'Dentista',
                    consultorio_name=getattr(cita, 'consultorioName', None) or 'Consultorio',
                    motivo=cita.motivo or '',
                    dentista_id=getattr(cita, 'dentistaId', None)
                )
            )
        except Exception as e:
            print(f"[notifier] error al notificar creación: {e}")

    def _notify_rescheduled(self, paciente_uid, cita: Cita, old_date, old_time, new_date, new_time):
        if not paciente_uid or not cita:
            return
        try:
            self._run_async(
                event_notifier.notify_appointment_rescheduled(
                    cita_id=cita.id,
                    paciente_id=paciente_uid,
                    old_date=self._date_to_str(old_date),
                    old_time=old_time or '',
                    new_date=self._date_to_str(new_date),
                    new_time=new_time or '',
                    dentista_name=getattr(cita, 'dentistaName', None) or 'Dentista'
                )
            )
        except Exception as e:
            print(f"[notifier] error al notificar reagendo: {e}")

    def _notify_cancelled(self, paciente_uid, cita: Cita):
        if not paciente_uid or not cita:
            return
        try:
            self._run_async(
                event_notifier.notify_appointment_cancelled(
                    cita_id=cita.id,
                    paciente_id=paciente_uid,
                    fecha=self._date_to_str(cita.fecha),
                    hora=cita.horaInicio or cita.hora or '',
                    motivo=cita.motivo or '',
                    dentista_id=getattr(cita, 'dentistaId', None)
                )
            )
        except Exception as e:
            print(f"[notifier] error al notificar cancelación: {e}")
    
    def crear_cita(self, usuario_whatsapp:str, datos_cita:dict, paciente_id:str=None, whatsapp_service=None)-> bool:
        try:
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            
            cita_id = self.cita_repo.crear_cita(usuario_whatsapp, datos_cita, paciente_id=paciente_id)
            if cita_id:
                # Obtener la cita creada para mostrar confirmación
                # Si tenemos paciente_id, buscar por paciente_id, sino por usuario_whatsapp
                if paciente_id:
                    from database.models import CitaRepository
                    cita_repo_temp = CitaRepository()
                    cita = cita_repo_temp.obtener_cita_por_id(paciente_id, cita_id)
                else:
                    cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
                
                if cita:
                    service.send_confirmation_message(
                        usuario_whatsapp, cita, is_new=True
                    )
                    paciente_uid = self._get_paciente_uid(usuario_whatsapp, paciente_id)
                    self._notify_created(paciente_uid, cita)
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
                    service.send_confirmation_message(
                        usuario_whatsapp, nueva_cita, is_new=True
                    )
                    paciente_uid = self._get_paciente_uid(usuario_whatsapp, paciente_id)
                    self._notify_created(paciente_uid, nueva_cita)
                    return True
            else:
                service.send_text_message(
                    usuario_whatsapp,"error al crear tu cita, intenta nuevamente"
                )
                return False
        except Exception as e:
            print(f"error al crear cita: {e}")
            import traceback
            traceback.print_exc()
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            service.send_text_message(usuario_whatsapp,"ocurrio un error inesperado, intenta mas tarde")
            return False
    def obtener_citas_usuario(self,usuario_whatsapp:str,action_type:str="ver", user_id=None, whatsapp_service=None):
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
            
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            service.send_citas_list(usuario_whatsapp, citas, action_type)
            return len(citas) > 0
            
        except Exception as e:
            print(f"error obteniendo citas: {e}")
            import traceback
            traceback.print_exc()
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            service.send_text_message(
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
    def reagendar_cita(self, usuario_whatsapp:str, cita_id:str,nueva_fecha:str,nueva_hora:str, paciente_id:str=None, whatsapp_service=None)->bool:
        try:
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            
            # Obtener cita por paciente_id o usuario_whatsapp
            if paciente_id:
                cita = self.cita_repo.obtener_cita_por_id(paciente_id, cita_id)
            else:
                cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
            
            if not cita:
                service.send_text_message(
                    usuario_whatsapp,"no existe la cita que intentas reagendar"
                )
                return False
            
            # Guardar datos previos para notificación
            old_date = self._date_to_str(cita.fecha) if cita else ''
            old_time = cita.horaInicio or cita.hora if cita else ''

            # Actualizar cita usando paciente_id o usuario_whatsapp
            if paciente_id:
                success = self.cita_repo.actualizar_cita_por_id(paciente_id, cita_id, nueva_fecha, nueva_hora)
            else:
                success = self.cita_repo.actualizar_cita(usuario_whatsapp, cita_id, nueva_fecha, nueva_hora)
            
            if success:
                # Actualizar objeto local para confirmación
                cita.fecha = nueva_fecha
                cita.horaInicio = nueva_hora
                cita.hora = nueva_hora
                service.send_confirmation_message(
                    usuario_whatsapp, cita, is_new=False
                )
                paciente_uid = self._get_paciente_uid(usuario_whatsapp, paciente_id)
                self._notify_rescheduled(
                    paciente_uid,
                    cita,
                    old_date,
                    old_time,
                    nueva_fecha,
                    nueva_hora
                )
                print(f"cita {cita_id} reagendada")
                return True
            else:
                service.send_text_message(
                    usuario_whatsapp,"no se pudo reagendar la cita. intenta nuevamente"
                )
                return False
        except Exception as e:
            print(f"error reagendando cita: {e}")
            import traceback
            traceback.print_exc()
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            service.send_text_message(
                usuario_whatsapp,"error reagendando cita"
            )    
            return False
    def cancelar_cita(self,usuario_whatsapp:str,cita_id:str, paciente_id:str=None, whatsapp_service=None)->bool:
        try:
            # Usar el servicio pasado como parámetro o el servicio por defecto
            service = whatsapp_service if whatsapp_service else self.whatsapp
            
            # Obtener cita por paciente_id o usuario_whatsapp
            if paciente_id:
                cita = self.cita_repo.obtener_cita_por_id(paciente_id, cita_id)
            else:
                cita = self.cita_repo.obtener_cita(usuario_whatsapp, cita_id)
            
            if not cita:
                service.send_text_message(
                    usuario_whatsapp,"no se encontro la cita"
                )
                return False
            
            # Eliminar cita usando paciente_id o usuario_whatsapp
            if paciente_id:
                success = self.cita_repo.eliminar_cita_por_id(paciente_id, cita_id)
            else:
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
                paciente_uid = self._get_paciente_uid(usuario_whatsapp, paciente_id)
                self._notify_cancelled(paciente_uid, cita)
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