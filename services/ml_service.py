"""
🧠 SERVICIO DE MACHINE LEARNING PARA CHATBOT
Usa modelos gratuitos de Hugging Face para procesamiento de lenguaje natural
"""

import os
import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class MLService:
    """
    Servicio de Machine Learning usando Hugging Face Inference API (gratis)
    Alternativamente puede usar OpenAI si está configurado
    """
    
    def __init__(self):
        # Hugging Face API (gratis, sin API key requerida para modelos públicos)
        self.hf_api_url = "https://api-inference.huggingface.co/models"
        self.hf_api_key = os.getenv("HUGGINGFACE_API_KEY", "")  # Opcional, mejora rate limits
        
        # Modelos gratuitos de Hugging Face
        self.intent_model = "microsoft/DialoGPT-medium"  # Para conversación
        self.qa_model = "distilbert-base-uncased-distilled-squad"  # Para Q&A
        self.sentiment_model = "cardiffnlp/twitter-roberta-base-sentiment-latest"  # Para sentimiento
        
        # OpenAI (opcional, si tienen API key)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.use_openai = bool(self.openai_api_key)
        
        # Cache para evitar llamadas repetidas
        self.cache = {}
        
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
                print(f"⚠️ Modelo {model} cargándose, esperando...")
                import time
                time.sleep(5)
                return self._call_huggingface(model, inputs, task)
            else:
                print(f"❌ Error llamando Hugging Face: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error en _call_huggingface: {e}")
            return None
    
    def _call_openai(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """Llama a OpenAI API (si está configurado)"""
        if not self.use_openai:
            return None
            
        try:
            import openai
            openai.api_key = self.openai_api_key
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Modelo más barato
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Error llamando OpenAI: {e}")
            return None
    
    def classify_intent(self, message: str, context: Dict = None) -> Dict:
        """
        Clasifica la intención del mensaje usando ML
        
        Intenciones posibles:
        - agendar_cita
        - reagendar_cita
        - cancelar_cita
        - ver_citas
        - consultar_informacion
        - saludar
        - despedirse
        - ayuda
        - otro
        """
        message_lower = message.lower().strip()
        
        # Cache simple
        cache_key = f"intent_{message_lower}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Palabras clave para intenciones (fallback si ML falla)
        intent_keywords = {
            'agendar_cita': ['agendar', 'cita', 'reservar', 'sacar cita', 'quiero una cita', 'necesito cita', 'programar'],
            'reagendar_cita': ['reagendar', 'cambiar fecha', 'cambiar hora', 'mover cita', 'reprogramar'],
            'cancelar_cita': ['cancelar', 'eliminar cita', 'borrar cita', 'no puedo ir', 'no asistiré'],
            'ver_citas': ['ver citas', 'mis citas', 'citas programadas', 'qué citas tengo', 'cuándo tengo cita'],
            'consultar_informacion': ['qué es', 'cómo funciona', 'información', 'dime sobre', 'explícame', 'qué puedo hacer'],
            'saludar': ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'saludos', 'hey'],
            'despedirse': ['adiós', 'hasta luego', 'gracias', 'chao', 'nos vemos'],
            'ayuda': ['ayuda', 'help', 'no entiendo', 'qué puedo hacer', 'opciones', 'menú']
        }
        
        # Detección por palabras clave (método rápido)
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Si hay un match claro, usarlo
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            if best_intent[1] >= 1:  # Al menos una palabra clave
                result = {
                    'intent': best_intent[0],
                    'confidence': min(0.9, 0.5 + (best_intent[1] * 0.1)),
                    'method': 'keyword'
                }
                self.cache[cache_key] = result
                return result
        
        # Si no hay match claro, usar ML (si está disponible)
        if self.use_openai:
            ml_result = self._classify_intent_ml(message, context)
            if ml_result:
                self.cache[cache_key] = ml_result
                return ml_result
        
        # Fallback: intentar inferir del contexto
        if context and context.get('current_step'):
            step = context['current_step']
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
    
    def _classify_intent_ml(self, message: str, context: Dict = None) -> Optional[Dict]:
        """Clasifica intención usando ML (OpenAI o Hugging Face)"""
        system_prompt = """Eres un clasificador de intenciones para un chatbot de citas dentales.
        
Analiza el mensaje del usuario y clasifica su intención en una de estas categorías:
- agendar_cita: quiere agendar una nueva cita
- reagendar_cita: quiere cambiar fecha/hora de una cita existente
- cancelar_cita: quiere cancelar una cita
- ver_citas: quiere ver sus citas programadas
- consultar_informacion: quiere información sobre el servicio
- saludar: saludo inicial
- ayuda: pide ayuda o menú
- otro: otra cosa

Responde SOLO con el nombre de la intención, nada más."""
        
        if self.use_openai:
            response = self._call_openai(message, system_prompt)
            if response:
                intent = response.strip().lower()
                # Validar que sea una intención válida
                valid_intents = ['agendar_cita', 'reagendar_cita', 'cancelar_cita', 'ver_citas', 
                               'consultar_informacion', 'saludar', 'ayuda', 'otro']
                if intent in valid_intents:
                    return {
                        'intent': intent,
                        'confidence': 0.85,
                        'method': 'openai'
                    }
        
        return None
    
    def extract_entities(self, message: str, intent: str) -> Dict:
        """
        Extrae entidades del mensaje (fechas, horas, nombres, etc.)
        """
        entities = {
            'fecha': None,
            'hora': None,
            'nombre': None,
            'motivo': None,
            'numero_cita': None
        }
        
        message_lower = message.lower()
        
        # Extraer fecha (formato: DD/MM, DD/MM/YYYY, "mañana", "pasado mañana", etc.)
        import re
        from datetime import datetime, timedelta
        
        # Fechas relativas
        if 'mañana' in message_lower or 'tomorrow' in message_lower:
            entities['fecha'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'pasado mañana' in message_lower:
            entities['fecha'] = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        elif 'hoy' in message_lower or 'today' in message_lower:
            entities['fecha'] = datetime.now().strftime('%Y-%m-%d')
        
        # Fechas en formato DD/MM o DD/MM/YYYY
        fecha_patterns = [
            r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?',  # DD/MM o DD/MM/YYYY
            r'(\d{1,2})-(\d{1,2})(?:-(\d{2,4}))?',  # DD-MM o DD-MM-YYYY
        ]
        
        for pattern in fecha_patterns:
            match = re.search(pattern, message)
            if match:
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
        hora_patterns = [
            r'(\d{1,2}):(\d{2})',  # HH:MM
            r'a las (\d{1,2})',  # "a las 3"
            r'(\d{1,2})\s*(am|pm)',  # "3pm", "10am"
        ]
        
        for pattern in hora_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if ':' in match.group(0):
                    # Formato HH:MM
                    entities['hora'] = match.group(0)
                elif 'am' in match.group(0) or 'pm' in match.group(0):
                    # Formato 12h
                    hora_num = int(match.group(1))
                    periodo = match.group(2) if len(match.groups()) > 1 else ''
                    if 'pm' in periodo and hora_num < 12:
                        hora_num += 12
                    elif 'am' in periodo and hora_num == 12:
                        hora_num = 0
                    entities['hora'] = f"{hora_num:02d}:00"
                else:
                    # Solo número
                    hora_num = int(match.group(1))
                    if hora_num < 24:
                        entities['hora'] = f"{hora_num:02d}:00"
                break
        
        # Extraer número de cita (si menciona "cita 1", "la primera", etc.)
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
        
        # Extraer motivo/descripción (texto después de palabras clave)
        motivo_keywords = ['por', 'para', 'motivo', 'razón', 'necesito', 'quiero']
        for keyword in motivo_keywords:
            if keyword in message_lower:
                idx = message_lower.find(keyword)
                motivo_text = message[idx + len(keyword):].strip()
                if len(motivo_text) > 5:  # Al menos 5 caracteres
                    entities['motivo'] = motivo_text[:200]  # Limitar a 200 caracteres
                    break
        
        return entities
    
    def generate_response(self, intent: str, entities: Dict, context: Dict = None, 
                         user_data: Dict = None) -> str:
        """
        Genera una respuesta coherente usando ML basada en la intención y entidades
        """
        # Si tenemos OpenAI, usarlo para generar respuestas más naturales
        if self.use_openai:
            return self._generate_response_openai(intent, entities, context, user_data)
        
        # Fallback a respuestas predefinidas mejoradas
        return self._generate_response_template(intent, entities, context, user_data)
    
    def _generate_response_openai(self, intent: str, entities: Dict, context: Dict = None,
                                  user_data: Dict = None) -> str:
        """Genera respuesta usando OpenAI"""
        system_prompt = """Eres Densorita, el asistente virtual de Densora, una plataforma de citas dentales.
        
Eres amigable, profesional y siempre intentas ayudar a los pacientes.
Responde en español, de forma natural y conversacional.
Sé breve pero completo en tus respuestas."""
        
        # Construir prompt con contexto
        prompt_parts = [f"Intención del usuario: {intent}"]
        
        if entities.get('fecha'):
            prompt_parts.append(f"Fecha mencionada: {entities['fecha']}")
        if entities.get('hora'):
            prompt_parts.append(f"Hora mencionada: {entities['hora']}")
        if entities.get('motivo'):
            prompt_parts.append(f"Motivo: {entities['motivo']}")
        
        if context:
            prompt_parts.append(f"Contexto: {context.get('current_step', 'inicial')}")
        
        if user_data:
            prompt_parts.append(f"Usuario: {user_data.get('nombre', 'Usuario')}")
        
        prompt = "\n".join(prompt_parts)
        prompt += "\n\nGenera una respuesta natural y útil para el usuario:"
        
        response = self._call_openai(prompt, system_prompt)
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
            'saludar': f"{saludo}¡Bienvenido a Densora! 🦷\n\nSoy Densorita, tu asistente virtual. ¿En qué puedo ayudarte hoy?",
            'ayuda': f"{saludo}Puedo ayudarte con:\n\n1️⃣ Agendar una cita\n2️⃣ Ver tus citas\n3️⃣ Reagendar una cita\n4️⃣ Cancelar una cita\n5️⃣ Información sobre nuestros servicios\n\n¿Qué te gustaría hacer?",
            'otro': f"{saludo}Lo siento, no entendí completamente. ¿Podrías ser más específico?\n\nEscribe *menu* para ver las opciones disponibles."
        }
        
        return responses.get(intent, responses['otro'])
    
    def answer_question(self, question: str, knowledge_base: Dict = None) -> str:
        """
        Responde preguntas sobre Densora usando ML y base de conocimiento
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
- Los horarios dependen de cada consultorio"""
            
            response = self._call_openai(question, system_prompt)
            if response:
                return response
        
        # Fallback
        return "Lo siento, no tengo información específica sobre eso. ¿Podrías ser más específico? O escribe *menu* para ver las opciones disponibles."

