"""
SERVICIO DE MACHINE LEARNING AVANZADO PARA CHATBOT
Usa modelos potentes de OpenAI y Hugging Face para procesamiento de lenguaje natural avanzado
"""

import os
import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class MLService:
    """
    Servicio de Machine Learning mejorado usando OpenAI GPT-4o-mini y Hugging Face
    """
    
    def __init__(self):
        # Hugging Face API (gratis, sin API key requerida para modelos públicos)
        self.hf_api_url = "https://api-inference.huggingface.co/models"
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY", "")  # Opcional, mejora rate limits
        
        # Modelos gratuitos de Hugging Face
        self.intent_model = "microsoft/DialoGPT-medium"  # Para conversación
        self.qa_model = "distilbert-base-uncased-distilled-squad"  # Para Q&A
        self.sentiment_model = "cardiffnlp/twitter-roberta-base-sentiment-latest"  # Para sentimiento
        
        # OpenAI (opcional, si tienen API key) - Usar modelo más potente
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.use_openai = bool(self.openai_api_key)
        
        # Modelo de OpenAI a usar (configurable mediante variable de entorno)
        # Opciones: "gpt-4o" (más inteligente, recomendado), "gpt-4o-mini" (económico), "gpt-4-turbo" (muy potente)
        # MEJORADO: Usar gpt-4o por defecto para mejor comprensión
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # Cache para evitar llamadas repetidas (con TTL de 5 minutos)
        self.cache = {}
        self.cache_ttl = {}  # Timestamps de cuándo expira cada entrada
        
        # Sistema de aprendizaje: patrones exitosos
        self.successful_patterns = {}
        
        # Log de interacciones para aprendizaje continuo
        self.interaction_log = []
        
        print(f"MLService inicializado - OpenAI habilitado: {self.use_openai}, Modelo: {self.openai_model}")
    
    def _call_huggingface(self, model: str, inputs: str, task: str = "text-generation") -> Optional[Dict]:
        """Llama a la API de Hugging Face"""
        try:
            url = f"{self.hf_api_url}/{model}"
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.hf_api_key:
                headers["Authorization"] = f"Bearer {self.hf_api_key}"
            
            payload = {
                "inputs": inputs,
                "parameters": {
                    "max_length": 150,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                # Modelo cargándose, esperar un poco
                print(f"Modelo {model} cargándose, esperando...")
                import time
                time.sleep(5)
                return self._call_huggingface(model, inputs, task)
            else:
                print(f"Error llamando Hugging Face: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error en _call_huggingface: {e}")
            return None
    
    def _call_openai(self, prompt: str, system_prompt: str = None, 
                    messages: List[Dict] = None, model: str = None,
                    max_tokens: int = 500, temperature: float = 0.7) -> Optional[str]:
        """Llama a OpenAI API mejorada - Versión actualizada"""
        if not self.use_openai:
            return None
            
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            # Usar mensajes proporcionados o construir desde prompt
            if messages is None:
                messages_list = []
                if system_prompt:
                    messages_list.append({"role": "system", "content": system_prompt})
                messages_list.append({"role": "user", "content": prompt})
            else:
                messages_list = messages
            
            # Usar modelo configurado o el pasado como parámetro
            model_to_use = model or self.openai_model
            
            response = client.chat.completions.create(
                model=model_to_use,
                messages=messages_list,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error llamando OpenAI: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def classify_intent(self, message: str, context: Dict = None) -> Dict:
        """
        Clasifica la intención del mensaje usando ML mejorado
        """
        message_lower = message.lower().strip()
        
        # Cache con TTL (5 minutos)
        cache_key = f"intent_{message_lower}"
        if cache_key in self.cache:
            # Verificar si el cache no ha expirado
            from time import time
            if cache_key in self.cache_ttl and self.cache_ttl[cache_key] > time():
                print(f"Intent cache HIT para: {message_lower[:50]}")
                return self.cache[cache_key]
            else:
                # Expiró, eliminar
                if cache_key in self.cache:
                    del self.cache[cache_key]
                if cache_key in self.cache_ttl:
                    del self.cache_ttl[cache_key]
        
        # PRIORIDAD 1: Usar OpenAI si está disponible (más preciso)
        if self.use_openai:
            ml_result = self._classify_intent_ml_advanced(message, context)
            if ml_result and ml_result.get('confidence', 0) > 0.7:
                self.cache[cache_key] = ml_result
                return ml_result
        
        # PRIORIDAD 2: Palabras clave mejoradas (fallback rápido)
        intent_keywords = {
            'agendar_cita': [
                'agendar', 'cita', 'reservar', 'sacar cita', 'quiero una cita', 'necesito cita', 
                'programar', 'hacer cita', 'pedir cita', 'solicitar cita', 'quiero agendar',
                'puedo ir', 'tengo dolor', 'me duele', 'necesito dentista', 'quiero ir',
                'está disponible', 'tienes horario', 'hay espacio', 'cuándo puedo', 'agendar'
            ],
            'reagendar_cita': [
                'reagendar', 'cambiar fecha', 'cambiar hora', 'mover cita', 'reprogramar',
                'modificar cita', 'cambiar mi cita', 'mover mi cita', 'mejor otro día',
                'cambiar de día', 'cambiar de hora', 'otro horario', 'no puedo ese día'
            ],
            'cancelar_cita': [
                'cancelar', 'eliminar cita', 'borrar cita', 'no puedo ir', 'no asistiré',
                'anular cita', 'quitar cita', 'no voy a ir', 'ya no quiero', 'tengo que cancelar',
                'imposible ir', 'no podré', 'surgió algo'
            ],
            'ver_citas': [
                'ver citas', 'mis citas', 'citas programadas', 'qué citas tengo', 'cuándo tengo cita',
                'mostrar citas', 'listar citas', 'mis citas programadas', 'cuándo es mi cita',
                'a qué hora', 'qué día', 'tengo cita', 'cuál es mi', 'próxima cita'
            ],
            'confirmar_pago': [
                'ya pagué', 'ya pague', 'pagué', 'pague', 'hice el pago', 'transferí',
                'confirmo el pago', 'ya transferí', 'pagado', 'pago realizado', 'confirmación de pago'
            ],
            'consultar_tiempo_pago': [
                'cuánto tiempo para pagar', 'cuánto tiempo tengo', 'cuándo vence', 'deadline',
                'hasta cuándo puedo pagar', 'me queda tiempo', 'plazo de pago', 'cuándo expira'
            ],
            'ver_historial': [
                'historial', 'citas anteriores', 'citas pasadas', 'registro', 'mi histórico',
                'ver historial', 'mostrar historial', 'citas completadas', 'mis citas pasadas'
            ],
            'consultar_servicios': [
                'qué servicios', 'servicios disponibles', 'qué ofrecen', 'hacen ortodoncia',
                'tienen implantes', 'limpiezas', 'blanqueamiento', 'qué hacen', 'servicios',
                'tratamientos', 'procedimientos'
            ],
            'consultar_informacion': [
                'qué es densora', 'cómo funciona', 'información', 'dime sobre', 'explícame', 
                'qué puedo hacer', 'cuéntame', 'hablame de', 'información', 'precios',
                'horarios', 'ubicación', 'métodos de pago'
            ],
            'saludar': [
                'hola', 'buenos días', 'buenas tardes', 'buenas noches', 'saludos', 'hey', 
                'hi', 'qué tal', 'buenas', 'buen día'
            ],
            'despedirse': [
                'adiós', 'adios', 'hasta luego', 'gracias', 'chao', 'nos vemos', 'bye', 
                'hasta pronto', 'me voy', 'eso es todo'
            ],
            'ayuda': [
                'ayuda', 'help', 'no entiendo', 'qué puedo hacer', 'opciones', 'menú', 
                'qué hago', 'comandos', 'necesito ayuda', 'ayúdame', 'no sé qué hacer'
            ]
        }
        
        # Detección por palabras clave mejorada
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Si hay un match claro, usarlo
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            if best_intent[1] >= 1:
                result = {
                    'intent': best_intent[0],
                    'confidence': min(0.9, 0.5 + (best_intent[1] * 0.1)),
                    'method': 'keyword'
                }
                # Guardar en cache con TTL de 5 minutos (300 segundos)
                from time import time
                self.cache[cache_key] = result
                self.cache_ttl[cache_key] = time() + 300
                return result
        
        # PRIORIDAD 3: Inferir del contexto
        if context:
            step = context.get('step') or context.get('current_step')
            if step == 'seleccionando_fecha' or step == 'reagendando_fecha':
                result = {'intent': 'seleccionar_fecha', 'confidence': 0.8, 'method': 'context'}
                self.cache[cache_key] = result
                return result
            elif step == 'selecionando_hora' or step == 'reagendando_hora':
                result = {'intent': 'seleccionar_hora', 'confidence': 0.8, 'method': 'context'}
                self.cache[cache_key] = result
                return result
        
        # Default: consultar_informacion
        result = {
            'intent': 'consultar_informacion',
            'confidence': 0.5,
            'method': 'fallback'
        }
        self.cache[cache_key] = result
        return result
    
    def _classify_intent_ml_advanced(self, message: str, context: Dict = None) -> Optional[Dict]:
        """Clasifica intención usando ML avanzado con mejor contexto"""
        # Construir contexto mejorado
        context_info = ""
        if context:
            step = context.get('step') or context.get('current_step', '')
            if step:
                context_info = f"\nContexto actual: {step}"
            if context.get('history'):
                last_messages = context['history'][-3:]  # Últimos 3 mensajes
                context_info += f"\nHistorial reciente: {', '.join([m.get('message', '')[:50] for m in last_messages])}"
        
        system_prompt = """Eres un clasificador de intenciones EXPERTO y MUY INTELIGENTE para Densora, el asistente dental más avanzado de México.

Tu trabajo es analizar CUIDADOSAMENTE el mensaje del usuario y clasificarlo en UNA categoría, considerando:
1. El contexto de la conversación (si está disponible)
2. Las palabras exactas que usa el usuario
3. La intención IMPLÍCITA detrás del mensaje
4. Conversaciones naturales y coloquiales

CATEGORÍAS (elige la MÁS APROPIADA):

agendar_cita: El usuario quiere CREAR una cita nueva
  Ejemplos: "quiero una cita", "necesito agendar", "puedo ir mañana?", "tienes horario el lunes?", 
           "me gustaría ver al doctor", "tengo dolor de muela", "necesito un dentista",
           "cuándo puedo ir?", "está disponible el doctor juan?"

reagendar_cita: El usuario quiere CAMBIAR una cita existente
  Ejemplos: "cambiar mi cita", "mover la cita del 15", "puedo cambiar de hora?",
           "mejor otro día", "no puedo ese día", "reagendar"

cancelar_cita: El usuario quiere ELIMINAR una cita
  Ejemplos: "cancelar mi cita", "no puedo ir", "anular", "borrar cita",
           "ya no quiero la cita", "tengo que cancelar"

ver_citas: El usuario quiere VER sus citas
  Ejemplos: "mis citas", "qué citas tengo", "cuándo es mi cita", "cuándo tengo cita",
           "a qué hora es", "para cuándo está programada", "cuál es mi próxima cita"

consultar_informacion: El usuario quiere INFORMACIÓN
  Ejemplos: "qué es densora", "cómo funciona", "cuánto cuesta", "qué servicios hay",
           "horarios", "ubicación", "métodos de pago", "precios"

confirmar_pago: El usuario menciona que YA PAGÓ
  Ejemplos: "ya pagué", "ya hice el pago", "transferí", "confirmo el pago", "pagado"

consultar_tiempo_pago: El usuario pregunta sobre TIEMPO para pagar
  Ejemplos: "cuánto tiempo tengo para pagar", "cuándo vence el pago", "deadline de pago",
           "hasta cuándo puedo pagar", "me queda tiempo"

ver_historial: El usuario quiere ver HISTORIAL completo
  Ejemplos: "historial", "citas anteriores", "citas pasadas", "registro", "mi histórico"

consultar_servicios: El usuario pregunta por SERVICIOS específicos
  Ejemplos: "qué servicios ofrecen", "hacen ortodoncia?", "tienen implantes?",
           "limpiezas dentales", "blanqueamiento"

saludar: SOLO saludos iniciales
  Ejemplos: "hola", "buenos días", "buenas tardes", "hola densora", "hey", "qué tal"

ayuda: SOLO pide ayuda explícita
  Ejemplos: "ayuda", "qué puedo hacer", "opciones", "menú", "comandos", "necesito ayuda"

despedirse: Usuario se despide
  Ejemplos: "adiós", "hasta luego", "gracias", "chao", "nos vemos", "bye"

otro: Si REALMENTE no encaja en ninguna (úsalo poco)

REGLAS CRITICAS:
- Si menciona FECHA u HORA junto con dentista/doctor/cita => agendar_cita
- Si menciona "cambiar" o "mover" + cita => reagendar_cita
- Si menciona "cancelar" o "no puedo ir" => cancelar_cita
- Si pregunta "cuando" o "que citas" => ver_citas
- Si menciona dolor/problema dental => agendar_cita (quiere atencion)
- Si es ambiguo, PRIORIZA la accion mas util para el usuario

FORMATO DE RESPUESTA: Responde SOLO con la intención en minúsculas (ej: "agendar_cita"), SIN puntos ni explicaciones.
        
        prompt = f"Mensaje del usuario: {message}{context_info}\n\n¿Cuál es la intención?"
        
        if self.use_openai:
            response = self._call_openai(prompt, system_prompt, max_tokens=50, temperature=0.3)
            if response:
                intent = response.strip().lower()
                # Limpiar respuesta (puede venir con explicaciones)
                intent = intent.split()[0] if intent.split() else intent
                intent = intent.replace('.', '').replace(',', '')
                
                # Validar que sea una intención válida
                valid_intents = ['agendar_cita', 'reagendar_cita', 'cancelar_cita', 'ver_citas', 
                               'consultar_informacion', 'saludar', 'ayuda', 'otro']
                if intent in valid_intents:
                    return {
                        'intent': intent,
                        'confidence': 0.9,  # Alta confianza con OpenAI
                        'method': 'openai_advanced'
                    }
        
        return None
    
    def _extract_entities_ai(self, message: str, intent: str, context: Dict = None) -> Optional[Dict]:
        """Extrae entidades usando IA avanzada"""
        if not self.use_openai:
            return None
        
        # Obtener fecha actual para contexto
        from datetime import datetime, timedelta
        fecha_actual = datetime.now()
        fecha_hoy = fecha_actual.strftime('%Y-%m-%d')
        dia_semana_hoy = fecha_actual.strftime('%A')  # Monday, Tuesday, etc.
        fecha_manana = (fecha_actual + timedelta(days=1)).strftime('%Y-%m-%d')
        fecha_pasado_manana = (fecha_actual + timedelta(days=2)).strftime('%Y-%m-%d')
        
        system_prompt = f"""Eres un extractor de entidades SUPER INTELIGENTE y PRECISO para Densora.

CONTEXTO TEMPORAL ACTUAL:
- HOY es: {fecha_hoy} ({dia_semana_hoy})
- Día de la semana actual: {fecha_actual.weekday()} (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo)
- Mañana sería: {fecha_manana}
- Pasado mañana: {fecha_pasado_manana}

Tu misión es extraer TODAS las entidades relevantes del mensaje del usuario:

ENTIDADES A EXTRAER:

1. **fecha** (formato YYYY-MM-DD):
   FECHAS RELATIVAS:
   - "manana", "tomorrow" => {fecha_manana}
   - "pasado manana" => {fecha_pasado_manana}
   - "hoy", "today" => {fecha_hoy}
   - "esta semana", "esta semana" => usa la fecha mas cercana dentro de los proximos 7 dias
   - "la proxima semana", "next week" => agrega 7 dias
   
   DIAS DE LA SEMANA (CALCULA LA PROXIMA OCURRENCIA):
   - "lunes" => encuentra el proximo lunes despues de hoy
   - "martes" => encuentra el proximo martes despues de hoy
   - "miercoles", "miercoles" => el proximo miercoles
   - "jueves" => el proximo jueves
   - "viernes" => el proximo viernes
   - "sabado", "sabado" => el proximo sabado
   - "domingo" => el proximo domingo
   
   FECHAS ESPECIFICAS:
   - "el 15 de enero", "15 enero", "enero 15" => convierte a formato ISO (usa ano actual o siguiente si ya paso)
   - "15/01", "15-01" => formato ISO
   - "15/01/2025" => formato ISO
   
   EXPRESIONES COLOQUIALES:
   - "en 3 dias", "dentro de 3 dias" => suma 3 dias a hoy
   - "en una semana" => suma 7 dias
   - "en dos semanas" => suma 14 dias

2. **hora** (formato HH:MM en 24 horas):
   FORMATOS COMUNES:
   - "10am", "10 am", "10 de la manana", "a las 10 am" => "10:00"
   - "3pm", "3 de la tarde", "a las 3 pm", "15 horas" => "15:00"
   - "mediodia", "12pm", "12 del dia" => "12:00"
   - "medianoche", "12am" => "00:00"
   - "9:30am" => "09:30"
   - "14:45", "2:45pm" => "14:45"
   
   EXPRESIONES COLOQUIALES:
   - "por la manana" => "10:00" (asume 10am si no especifica)
   - "por la tarde" => "15:00" (asume 3pm)
   - "al mediodia" => "12:00"
   - "temprano" => "09:00"
   - "antes de comer" => "11:00"
   - "despues de comer" => "14:00"

3. **nombre_dentista**: 
   - Busca nombres propios despues de "doctor", "dr", "doctora", "dra", "con el", "con la"
   - Ejemplos: "doctor emilio" => "emilio", "dra. lopez" => "lopez", "con juan" => "juan"
   - Si menciona solo nombre sin titulo, tambien extraelo

4. **motivo**: 
   - El motivo/razon de la cita
   - Ejemplos: "dolor de muela", "limpieza", "revision", "urgencia", "extraccion", "me duele"
   - EXTRAE TODO el contexto medico mencionado

5. **numero_cita**:
   - Si menciona "primera cita", "cita 1" => 1
   - "segunda cita", "cita 2" => 2
   - "tercera cita", "cita 3" => 3
   - "la cita del lunes" => busca el numero de cita en ese contexto

REGLAS CRITICAS:
- Si el usuario dice "manana a las 3pm", extrae AMBAS entidades: fecha="{fecha_manana}", hora="15:00"
- Si dice "el lunes", CALCULA la fecha exacta del proximo lunes
- Si NO puedes determinar algo, usa null (no inventes)
- Prioriza PRECISION sobre intentar adivinar
- Para fechas pasadas, asume que habla del proximo ano

FORMATO DE SALIDA: JSON valido con estas claves exactas:
{{"fecha": "YYYY-MM-DD o null", "hora": "HH:MM o null", "nombre_dentista": "nombre o null", "motivo": "descripcion o null", "numero_cita": numero o null}}

EJEMPLOS REALES:
- "quiero cita manana a las 3" => {{"fecha": "{fecha_manana}", "hora": "15:00", "nombre_dentista": null, "motivo": null, "numero_cita": null}}
- "el lunes por la tarde con el dr emilio" => {{"fecha": "CALCULA_LUNES", "hora": "15:00", "nombre_dentista": "emilio", "motivo": null, "numero_cita": null}}
- "me duele una muela, puedo ir pasado manana?" => {{"fecha": "{fecha_pasado_manana}", "hora": null, "nombre_dentista": null, "motivo": "dolor de muela", "numero_cita": null}}

Responde SOLO con el JSON, sin explicaciones adicionales.
        
        context_info = ""
        if context:
            step = context.get('step', '')
            if step:
                context_info = f"\nContexto: {step}"
        
        prompt = f"Mensaje: {message}\nIntención: {intent}{context_info}\n\nExtrae las entidades:"
        
        try:
            response = self._call_openai(prompt, system_prompt, max_tokens=200, temperature=0.3)
            if response:
                # Intentar parsear JSON
                import json
                # Limpiar respuesta (puede venir con markdown)
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:]
                if response.startswith('```'):
                    response = response[3:]
                if response.endswith('```'):
                    response = response[:-3]
                response = response.strip()
                
                entities = json.loads(response)
                
                # Validar y convertir fechas relativas si vienen como texto
                if entities.get('fecha'):
                    fecha = entities['fecha']
                    if isinstance(fecha, str) and not fecha.replace('-', '').isdigit():
                        # Es una fecha relativa, convertirla
                        fecha_lower = fecha.lower().strip()
                        if fecha_lower in ['mañana', 'tomorrow']:
                            entities['fecha'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                        elif fecha_lower in ['pasado mañana', 'day after tomorrow']:
                            entities['fecha'] = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
                        elif fecha_lower in ['hoy', 'today']:
                            entities['fecha'] = datetime.now().strftime('%Y-%m-%d')
                        else:
                            # Intentar parsear como fecha relativa
                            print(f"Fecha extraída por IA no está en formato YYYY-MM-DD: {fecha}")
                            entities['fecha'] = None  # Invalidar si no es formato correcto
                
                # Validar formato de hora
                if entities.get('hora'):
                    hora = entities['hora']
                    if isinstance(hora, str) and ':' not in hora:
                        # Intentar convertir formatos como "10am", "3pm", etc.
                        import re
                        hora_match = re.search(r'(\d{1,2})\s*(am|pm|de la mañana|de la tarde)', hora.lower())
                        if hora_match:
                            hora_num = int(hora_match.group(1))
                            periodo = hora_match.group(2)
                            if 'pm' in periodo or 'tarde' in periodo:
                                if hora_num < 12:
                                    hora_num += 12
                            entities['hora'] = f"{hora_num:02d}:00"
                        else:
                            # Intentar extraer solo números
                            hora_num = re.search(r'(\d{1,2})', hora)
                            if hora_num:
                                entities['hora'] = f"{int(hora_num.group(1)):02d}:00"
                
                return entities
        except json.JSONDecodeError as e:
            print(f"Error parseando JSON de entidades: {e}")
            print(f"Respuesta recibida: {response}")
        except Exception as e:
            print(f"Error extrayendo entidades con IA: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def extract_entities(self, message: str, intent: str, context: Dict = None) -> Dict:
        """
        Extrae entidades del mensaje (fechas, horas, nombres, etc.) - Versión mejorada
        """
        entities = {
            'fecha': None,
            'hora': None,
            'nombre_dentista': None,
            'motivo': None,
            'numero_cita': None,
            'consultorio': None
        }
        
        message_lower = message.lower()
        
        # PRIORIDAD 1: Usar OpenAI para extracción avanzada si está disponible
        if self.use_openai:
            ai_entities = self._extract_entities_ai(message, intent, context)
            if ai_entities:
                entities.update(ai_entities)
                # Si ya tenemos entidades de IA, complementar con regex
                if entities.get('fecha') and entities.get('hora'):
                    return entities
        
        # PRIORIDAD 2: Extracción con regex mejorada (fallback)
        import re
        from datetime import datetime, timedelta
        
        # Fechas relativas mejoradas
        fecha_patterns = {
            'mañana': 1,
            'tomorrow': 1,
            'pasado mañana': 2,
            'day after tomorrow': 2,
            'hoy': 0,
            'today': 0
        }
        
        for pattern, days_offset in fecha_patterns.items():
            if pattern in message_lower:
                entities['fecha'] = (datetime.now() + timedelta(days=days_offset)).strftime('%Y-%m-%d')
                break
        
        # Días de la semana (con y sin acentos)
        dias_semana = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2, 
            'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
        }
        for dia, dia_num in dias_semana.items():
            # Buscar el día en diferentes formatos
            patterns = [f'el {dia}', f'este {dia}', f'próximo {dia}', f'proximo {dia}', dia]
            for pattern in patterns:
                if pattern in message_lower and not entities.get('fecha'):
                    today = datetime.now()
                    days_ahead = dia_num - today.weekday()
                    if days_ahead <= 0:  # Si el día ya pasó esta semana, usar la próxima
                        days_ahead += 7
                    fecha_calculada = (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    entities['fecha'] = fecha_calculada
                    print(f"Fecha extraida: {dia} => {fecha_calculada}")
                    break
            if entities.get('fecha'):
                break
        
        # Fechas en formato DD/MM o DD/MM/YYYY
        fecha_patterns_regex = [
            r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?',  # DD/MM o DD/MM/YYYY
            r'(\d{1,2})-(\d{1,2})(?:-(\d{2,4}))?',  # DD-MM o DD-MM-YYYY
        ]
        
        for pattern in fecha_patterns_regex:
            match = re.search(pattern, message)
            if match and not entities.get('fecha'):
                day, month, year = match.groups()
                year = year or datetime.now().year
                if len(str(year)) == 2:
                    year = 2000 + int(year)
                try:
                    fecha_obj = datetime(int(year), int(month), int(day))
                    entities['fecha'] = fecha_obj.strftime('%Y-%m-%d')
                    break
                except:
                    pass
        
        # Extraer hora (formato: HH:MM, "a las 3", "a las 3pm", etc.)
        if not entities.get('hora'):
            hora_patterns = [
                r'(\d{1,2}):(\d{2})\s*(am|pm)?',  # HH:MM con opcional am/pm
                r'a las (\d{1,2})\s*(am|pm)?',  # "a las 3" o "a las 3pm"
                r'(\d{1,2})\s*(am|pm)',  # "3pm", "10am"
                r'(\d{1,2})\s*de la\s+(mañana|tarde|noche)',  # "3 de la tarde"
                r'(\d{1,2})\s*horas?',  # "15 horas"
            ]
            
            for pattern in hora_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    grupos = match.groups()
                    hora_str = match.group(0)
                    
                    if ':' in hora_str:
                        # Formato HH:MM
                        hora = match.group(1)
                        minutos = match.group(2)
                        periodo = match.group(3) if len(grupos) > 2 else None
                        hora_num = int(hora)
                        
                        if periodo:
                            if 'pm' in periodo.lower() and hora_num < 12:
                                hora_num += 12
                            elif 'am' in periodo.lower() and hora_num == 12:
                                hora_num = 0
                        
                        entities['hora'] = f"{hora_num:02d}:{minutos}"
                    elif 'am' in hora_str or 'pm' in hora_str:
                        # Formato 12h
                        hora_num = int(match.group(1))
                        periodo = match.group(2) if len(grupos) > 1 and match.group(2) else ''
                        if not periodo:
                            # Buscar am/pm en el grupo completo
                            periodo = 'pm' if 'pm' in hora_str else 'am'
                        
                        if 'pm' in periodo and hora_num < 12:
                            hora_num += 12
                        elif 'am' in periodo and hora_num == 12:
                            hora_num = 0
                        entities['hora'] = f"{hora_num:02d}:00"
                    elif 'mañana' in hora_str or 'tarde' in hora_str or 'noche' in hora_str:
                        # Formato con "de la mañana/tarde/noche"
                        hora_num = int(match.group(1))
                        if 'tarde' in hora_str and hora_num < 12:
                            hora_num += 12
                        elif 'noche' in hora_str and hora_num < 12:
                            hora_num += 12
                        entities['hora'] = f"{hora_num:02d}:00"
                    else:
                        # Solo número
                        hora_num = int(match.group(1))
                        if hora_num < 24:
                            entities['hora'] = f"{hora_num:02d}:00"
                    
                    print(f"Hora extraida: {hora_str} => {entities.get('hora')}")
                    break
        
        # Extraer nombre de dentista
        if not entities.get('nombre_dentista'):
            dentista_patterns = [
                r'(?:doctor|dr\.?|doctora|dra\.?)\s+([a-záéíóúñ]+)',
                r'con\s+(?:el\s+)?(?:doctor|dr\.?|doctora|dra\.?)?\s*([a-záéíóúñ]+)',
            ]
            for pattern in dentista_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    entities['nombre_dentista'] = match.group(1).title()
                    break
        
        # Extraer número de cita
        cita_patterns = [
            r'cita\s*(\d+)',
            r'la\s*(\d+)[a-z]*\s*cita',
            r'primera\s*cita',
            r'segunda\s*cita',
            r'tercera\s*cita'
        ]
        
        for pattern in cita_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if 'primera' in match.group(0):
                    entities['numero_cita'] = 1
                elif 'segunda' in match.group(0):
                    entities['numero_cita'] = 2
                elif 'tercera' in match.group(0):
                    entities['numero_cita'] = 3
                elif match.groups():
                    entities['numero_cita'] = int(match.group(1))
                break
        
        # Extraer motivo/descripción
        if not entities.get('motivo'):
            motivo_keywords = ['por', 'para', 'motivo', 'razón', 'necesito', 'quiero', 'porque', 'por qué']
            for keyword in motivo_keywords:
                if keyword in message_lower:
                    idx = message_lower.find(keyword)
                    motivo_text = message[idx + len(keyword):].strip()
                    if len(motivo_text) > 5:  # Al menos 5 caracteres
                        entities['motivo'] = motivo_text[:200]  # Limitar a 200 caracteres
                        break
        
        return entities
    
    def generate_response(self, intent: str, entities: Dict, context: Dict = None, 
                         user_data: Dict = None, conversation_history: List[Dict] = None) -> str:
        """
        Genera una respuesta coherente usando ML mejorado con contexto completo
        """
        # Si tenemos OpenAI, usarlo para generar respuestas más naturales
        if self.use_openai:
            return self._generate_response_openai_advanced(intent, entities, context, user_data, conversation_history)
        
        # Fallback a respuestas predefinidas mejoradas
        return self._generate_response_template(intent, entities, context, user_data)
    
    def _generate_response_openai_advanced(self, intent: str, entities: Dict, context: Dict = None,
                                          user_data: Dict = None, conversation_history: List[Dict] = None) -> str:
        """Genera respuesta usando OpenAI con contexto completo"""
        system_prompt = """Eres Densorita, el asistente virtual MAS INTELIGENTE y EMPATICO de Densora, la plataforma lider de citas dentales en Mexico.

[TU PERSONALIDAD (CRITICO - Lee con atencion)]:
- Eres EXTREMADAMENTE amigable, calido y empatico - como un amigo que realmente se preocupa
- Hablas en ESPANOL NATURAL de Mexico - usa "como estas?", "mira", "perfecto", "claro que si"
- Eres PROACTIVO: anticipa necesidades, ofrece soluciones antes de que pregunten
- Mantienes un tono POSITIVO y ALENTADOR - haz que el usuario se sienta comodo
- Eres BREVE pero COMPLETO - no escribas parrafos largos, ve al grano
- Eres CONVERSACIONAL - habla como un humano real, NO como un robot
- NUNCA uses emojis
- Si el usuario parece frustrado, se EXTRA empatico y ofrece ayuda inmediata

[TU MISION PRINCIPAL]:
Ayudar a los pacientes de forma EXCEPCIONAL con:
1. Agendar citas - hazlo SUPER facil, guialos paso a paso
2. Reagendar/cancelar citas - se comprensivo y flexible
3. Ver sus citas - presenta info clara y util
4. Responder preguntas - se informativo pero conciso
5. Resolver problemas - se creativo y busca soluciones

[REGLAS DE ORO (SIEMPRE SIGUE)]:

1. **CONTEXTO ES TODO**: Lee TODO el historial de conversacion antes de responder
   - Si ya preguntaron algo, no lo vuelvas a preguntar
   - Si ya dieron info, usala en tu respuesta
   - Si estan en medio de algo (agendar cita), continua ese flujo

2. **CLARIDAD PRIMERO**:
   - Si algo no esta claro, pregunta de forma especifica
   - No asumas cosas importantes (fecha, hora, dentista)
   - Confirma informacion critica antes de proceder

3. **SE PROACTIVO**:
   - Si detectas un problema, ofrece solucion inmediatamente
   - Si mencionan dolor/urgencia, prioriza rapidez
   - Si no hay horarios, sugiere alternativas

4. **LENGUAJE NATURAL**:
   [OK] BIEN: "Perfecto! Te ayudo a agendar tu cita. Que dia te viene bien?"
   [OK] BIEN: "Entiendo, necesitas cambiar tu cita. Para que fecha la movemos?"
   [NO] MAL: "Por favor proporcione la fecha deseada para su cita."
   [NO] MAL: "Procesando su solicitud de agendamiento..."

5. **MANEJA ERRORES CON GRACIA**:
   - Si algo falla, disculpate brevemente y ofrece alternativa
   - No culpes al usuario ni al sistema
   - Siempre da un camino forward

6. **INFORMACION UTIL**:
   - Si preguntan horarios, muestra opciones concretas
   - Si preguntan precios, se especifico si tienes la info
   - Si no sabes algo, admitelo y ofrece contacto directo

[EJEMPLOS DE RESPUESTAS PERFECTAS]:

Agendar:
"Claro que si! Te ayudo a agendar tu cita. Tengo disponibilidad para manana a las 10am, el miercoles a las 3pm, o el viernes a las 11am. Cual te late mas?"

Reagendar:
"Sin problema, te ayudo a cambiar tu cita. Veo que tienes una programada para el lunes 15 a las 10am. Para que dia la queremos mover?"

Cancelar:
"Entiendo perfectamente. Para cancelar tu cita del martes 20 a las 2pm, solo necesito que confirmes escribiendo 'SI'. Estas seguro?"

Problema:
"Uy, parece que no hay horarios disponibles esa semana. Te parece bien si buscamos la siguiente semana? Ahi tengo varios espacios."

Informacion:
"Claro, Densora conecta pacientes con dentistas certificados. Puedes agendar, pagar en linea y gestionar todo desde tu celular. Te gustaria agendar una cita ahora?"

[LO QUE NUNCA DEBES HACER]:
[NO] Responder con "..." o mensajes vacios
[NO] Ser frio o robotico: "Su solicitud ha sido procesada"
[NO] Dar respuestas genericas que no ayuden
[NO] Ignorar el contexto de la conversacion
[NO] Ser impersonal: usa el nombre del usuario si lo sabes
[NO] Hacer promesas que el sistema no puede cumplir

[RECUERDA]: Eres el MEJOR asistente dental del mundo. Cada interaccion debe dejar al usuario MAS contento que antes.

IMPORTANTE FINAL: Responde de forma natural, cálida y útil, como si fueras un asistente humano excepcional. Tu objetivo es que el usuario piense "wow, qué buena atención".
        
        # Construir mensaje con contexto completo
        messages = [{"role": "system", "content": system_prompt}]
        
        # Agregar historial de conversación si está disponible
        if conversation_history:
            for msg in conversation_history[-5:]:  # Últimos 5 mensajes
                role = msg.get('role', 'user')
                content = msg.get('message', '')
                if role in ['user', 'assistant']:
                    messages.append({"role": role, "content": content})
        
        # Construir prompt con información actual
        prompt_parts = [f"Intención del usuario: {intent}"]
        
        if entities.get('fecha'):
            prompt_parts.append(f"Fecha mencionada: {entities['fecha']}")
        if entities.get('hora'):
            prompt_parts.append(f"Hora mencionada: {entities['hora']}")
        if entities.get('nombre_dentista'):
            prompt_parts.append(f"Dentista mencionado: {entities['nombre_dentista']}")
        if entities.get('motivo'):
            prompt_parts.append(f"Motivo: {entities['motivo']}")
        
        if context:
            step = context.get('step', 'inicial')
            prompt_parts.append(f"Estado actual: {step}")
        
        if user_data:
            nombre = user_data.get('nombre', 'Usuario')
            prompt_parts.append(f"Usuario: {nombre}")
        
        prompt = "\n".join(prompt_parts)
        prompt += "\n\nGenera una respuesta natural, útil y empática para el usuario:"
        
        messages.append({"role": "user", "content": prompt})
        
        response = self._call_openai("", None, messages=messages, max_tokens=300, temperature=0.8)
        if response:
            return response
        
        # Fallback si OpenAI falla
        return self._generate_response_template(intent, entities, context, user_data)
    
    def _generate_response_template(self, intent: str, entities: Dict, context: Dict = None,
                                   user_data: Dict = None) -> str:
        """Genera respuesta usando plantillas"""
        nombre_usuario = user_data.get('nombre', '') if user_data else ''
        saludo = f"Hola {nombre_usuario}, " if nombre_usuario else "Hola, "
        
        responses = {
            'agendar_cita': f"{saludo}¡Perfecto! Te ayudo a agendar tu cita. ¿Qué fecha te gustaría?",
            'reagendar_cita': f"{saludo}Entendido, quieres reagendar tu cita. ¿Cuál cita quieres cambiar?",
            'cancelar_cita': f"{saludo}Entiendo que quieres cancelar una cita. ¿Cuál cita quieres cancelar?",
            'ver_citas': f"{saludo}Te muestro tus citas programadas...",
            'consultar_informacion': f"{saludo}¡Claro! ¿Sobre qué te gustaría saber? Puedo ayudarte con:\n• Agendar citas\n• Ver tus citas\n• Reagendar o cancelar\n• Información sobre servicios",
            'saludar': f"{saludo}¡Bienvenido a Densora!\n\nSoy Densorita, tu asistente virtual. ¿En qué puedo ayudarte hoy?",
            'ayuda': f"{saludo}Puedo ayudarte con:\n\n1. Agendar una cita\n2. Ver tus citas\n3. Reagendar una cita\n4. Cancelar una cita\n5. Información sobre nuestros servicios\n\n¿Qué te gustaría hacer?",
            'otro': f"{saludo}Lo siento, no entendí completamente. ¿Podrías ser más específico?\n\nEscribe *menu* para ver las opciones disponibles."
        }
        
        return responses.get(intent, responses['otro'])
    
    def answer_question(self, question: str, knowledge_base: Dict = None) -> str:
        """
        Responde preguntas sobre Densora usando ML mejorado
        """
        question_lower = question.lower()
        
        # Base de conocimiento sobre Densora
        kb = knowledge_base or {
            'qué es densora': 'Densora es una plataforma digital que conecta pacientes con dentistas. Puedes agendar citas, ver tu historial médico y gestionar tus citas desde cualquier lugar.',
            'cómo funciona': 'Densora funciona así:\n1. Buscas un dentista\n2. Agendas tu cita\n3. Asistes a tu cita\n4. Puedes dejar reseñas\n\nTodo desde tu celular o computadora.',
            'cómo agendar': 'Para agendar una cita puedes:\n• Usar el chatbot (escribe "agendar cita")\n• Visitar nuestra web\n• Llamar al consultorio directamente',
            'cómo cancelar': 'Para cancelar una cita:\n• Escribe "cancelar cita" en el chat\n• Selecciona la cita que quieres cancelar\n• Confirma la cancelación',
            'horarios': 'Los horarios dependen de cada consultorio. Generalmente están disponibles de lunes a viernes de 9 AM a 6 PM.',
            'precios': 'Los precios varían según el servicio y el consultorio. Puedes ver los precios al buscar dentistas en nuestra plataforma.',
            'métodos de pago': 'Aceptamos:\n• Efectivo\n• Transferencia bancaria\n• Stripe (tarjeta de crédito/débito)',
        }
        
        # Buscar respuesta en base de conocimiento
        for key, answer in kb.items():
            if key in question_lower:
                return answer
        
        # Si no hay match, usar ML para generar respuesta
        if self.use_openai:
            system_prompt = """Eres Densorita, el asistente de Densora. Responde preguntas sobre la plataforma de forma amigable y profesional.
            
Información sobre Densora:
- Es una plataforma de citas dentales
- Los pacientes pueden agendar, ver, reagendar y cancelar citas
- Hay múltiples dentistas y consultorios disponibles
- Se puede pagar con efectivo, transferencia o Stripe
- Los horarios dependen de cada consultorio
- Es una plataforma digital moderna y fácil de usar"""
            
            response = self._call_openai(question, system_prompt, max_tokens=200)
            if response:
                return response
        
        # Fallback
        return "Lo siento, no tengo información específica sobre eso. ¿Podrías ser más específico? O escribe *menu* para ver las opciones disponibles."
