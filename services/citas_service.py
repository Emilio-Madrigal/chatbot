from database.models import Cita, CitaRepository
from services.whatsapp_service import WhatsAppService
from datetime import datetime

class CitasService:
    def __init__(self):
        self.cita_repo=CitaRepository()
        self.whatsapp=WhatsAppService()
    
    def crear_cita(self, usuario_whatsapp:str, datos_cita:dict)-> bool:
        try:
            nueva_cita=Cita(
                usuario_whatsapp=usuario_whatsapp,
                nombre_cliente=datos_cita['nombre_cliente'],
                fecha=datos_cita['fecha'],
                hora=datos_cita['hora'],
                descripcion=datos_cita.get('descripcion', ''),
            )
            cita_id=self.cita_repo.crear_cita(nueva_cita)
            if cita_id:
                nueva_cita.id=cita_id
                self.whatsapp.send_confirmation_message(
                    usuario_whatsapp,nueva_cita,is_new=True
                )
                print(f"cita creada")
                return True
            else:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"error al crear tu cita, intenta nuevamente"
                )
                return False
        except Exception as e:
            print(f"error al crear cita: {e}")
            self.whatsapp.send_text_message(usuario_whatsapp,"ocurrio un error inseperado, intenta mas tarde")
            return False
    def obtener_citas_usuario(self,usuario_whatsapp:str,action_type:str="ver"):
        try:
            citas = self.cita_repo.obtener_citas_usuario(usuario_whatsapp)
            self.whatsapp.send_citas_list(usuario_whatsapp, citas, action_type)
            return len(citas) > 0
            
        except Exception as e:
            print(f"error obteniendo citas: {e}")
            self.whatsapp.send_text_message(
                usuario_whatsapp,
                "error al obtener tus citas. Intenta nuevamente."
            )
            return False
    def mostrar_detalles_cita(self,usuario_whatsapp:str,cita_id:str):
        try:
            cita=self.cita_repo.obtener_cita(cita_id)
            if cita and cita.usuario_whatsapp==usuario_whatsapp:
                self.whatsapp.send_cita_details(usuario_whatsapp,cita)
            else:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no se encontro la cita"
                )
        except Exception as e:
            print(f"error mostrando detalles:{e}")
            self.whatsapp.send_text_message(usuario_whatsapp,"error mostrando los detalles")
    def reagendar_cita(self, usuario_whatsapp:str, cita_id:str,nueva_fecha:str,nueva_hora:str)->bool:
        try:
            Cita+self.cita_repo.obtener_cita(cita_id)
            if not Cita or Cita.usuario_whatsapp!=usuario_whatsapp:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no existe la cita que intentas reagendar"
                )
                return False
            success=self.cita_repo.actualizar_cita(cita_id,nueva_fecha,nueva_hora)
            if success:
                Cita.fecha=nueva_fecha
                Cita.hora=nueva_hora
                self.whatsapp.send_confirmation_message(
                    usuario_whatsapp,Cita,is_new=False
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
            Cita=self.cita_repo.obtener_cita(cita_id)
            if not Cita or Cita.usuario_whatsapp!=usuario_whatsapp:
                self.whatsapp.send_text_message(
                    usuario_whatsapp,"no se encontro la cita"
                )
                return False
            success=self.cita_repo.eliminar_cita(cita_id)
            if success:
                fecha_formatted=datetime.strptime(Cita.fecha, '%Y-%m-%d').strftime('%d/%m/%Y')
                mensaje_cancelacion=f"""*CITA CANCELADA*
                *Cliente:* {Cita.nombre_cliente}
                *Fecha:* {fecha_formatted}
                *Hora:* {Cita.hora}
                Tu cita ha sido cancelada
                """
                self.whatsapp.send_text_message(usuario_whatsapp,mensaje_cancelacion)
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