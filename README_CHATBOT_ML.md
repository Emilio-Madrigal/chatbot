# 🤖 CHATBOT INTELIGENTE DE DENSORA CON MACHINE LEARNING

## 📋 Descripción

Chatbot inteligente con Machine Learning que funciona tanto en WhatsApp (vía Twilio) como en la web. Utiliza modelos gratuitos de Hugging Face y opcionalmente OpenAI para procesamiento de lenguaje natural avanzado.

## ✨ Características

- **🧠 Machine Learning**: Procesamiento de lenguaje natural con modelos gratuitos
- **💬 Conversación Natural**: Entiende lenguaje natural, no solo comandos
- **📅 Gestión de Citas**: Agendar, reagendar y cancelar citas de forma inteligente
- **🔍 Extracción de Entidades**: Detecta fechas, horas, nombres y motivos automáticamente
- **🌐 Multiplataforma**: Funciona en WhatsApp y Web con el mismo backend
- **💾 Contexto y Memoria**: Mantiene el contexto de la conversación
- **🔄 Fallback Inteligente**: Si ML falla, usa sistema de palabras clave

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
cd chatbot
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Crea un archivo `.env` en la carpeta `chatbot/`:

```env
# Twilio (Requerido)
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_WEBHOOK_TOKEN=tu_webhook_token

# Firebase (Requerido)
FIREBASE_PROJECT_ID=tu_project_id
FIREBASE_CREDENTIALS_PATH=serviceAccountKey.json

# OpenAI (Opcional - mejora las respuestas)
OPENAI_API_KEY=tu_openai_api_key

# Hugging Face (Opcional - mejora rate limits)
HUGGINGFACE_API_KEY=tu_huggingface_api_key

# Puerto (Opcional)
PORT=5000
FLASK_ENV=production
```

### 3. Configurar Firebase

1. Descarga tu `serviceAccountKey.json` desde Firebase Console
2. Colócalo en la carpeta `chatbot/`
3. Asegúrate de que tenga permisos para leer/escribir en Firestore

### 4. Configurar Twilio

1. Ve a Twilio Console → Messaging → WhatsApp Sandbox
2. Configura el webhook URL: `https://tu-render-url.onrender.com/webhook`
3. Guarda el número de WhatsApp de Twilio

## 🎯 Uso

### Ejecutar Localmente

```bash
python app.py
```

### Ejecutar en Render

1. Conecta tu repositorio a Render
2. Configura las variables de entorno en Render Dashboard
3. Render detectará automáticamente el `Procfile` y desplegará

## 📱 Endpoints

### 1. Webhook de Twilio (WhatsApp)

**URL**: `POST /webhook`

Recibe mensajes de WhatsApp desde Twilio.

### 2. Chat Web

**URL**: `POST /api/web/chat`

**Body**:
```json
{
  "message": "Hola, quiero agendar una cita",
  "session_id": "unique_session_id",
  "user_id": "firebase_user_id",  // Opcional
  "phone": "521234567890",  // Opcional
  "user_name": "Juan Pérez"  // Opcional
}
```

**Response**:
```json
{
  "success": true,
  "response": "¡Hola! Te ayudo a agendar tu cita...",
  "session_id": "unique_session_id"
}
```

### 3. Health Check

**URL**: `GET /health`

Verifica que el servidor está funcionando.

## 🧠 Intenciones Soportadas

El chatbot puede entender las siguientes intenciones:

- **agendar_cita**: "Quiero agendar una cita", "Necesito una cita", etc.
- **reagendar_cita**: "Quiero cambiar mi cita", "Reagendar cita", etc.
- **cancelar_cita**: "Cancelar mi cita", "No puedo ir", etc.
- **ver_citas**: "Ver mis citas", "Qué citas tengo", etc.
- **consultar_informacion**: "Qué es Densora", "Cómo funciona", etc.
- **saludar**: "Hola", "Buenos días", etc.
- **ayuda**: "Ayuda", "Menú", "Qué puedo hacer", etc.

## 📅 Ejemplos de Uso

### Agendar una Cita

**Usuario**: "Hola, quiero agendar una cita para mañana a las 3pm"

**Bot**: 
```
📅 Fecha seleccionada: 2024-01-15

⏰ Horarios disponibles:
1. 14:00
2. 15:00
3. 16:00

¿Qué hora prefieres?
```

### Reagendar una Cita

**Usuario**: "Quiero cambiar mi cita del 15 de enero"

**Bot**:
```
🔄 Reagendando cita de 2024-01-15 14:00

📅 Fechas disponibles:
1. 2024-01-16
2. 2024-01-17
3. 2024-01-18

¿Qué fecha prefieres?
```

### Consultar Información

**Usuario**: "Qué es Densora?"

**Bot**:
```
Densora es una plataforma digital que conecta pacientes con dentistas. 
Puedes agendar citas, ver tu historial médico y gestionar tus citas 
desde cualquier lugar.
```

## 🔧 Configuración Avanzada

### Usar OpenAI (Opcional)

Si tienes una API key de OpenAI, el chatbot generará respuestas más naturales:

1. Obtén tu API key de https://platform.openai.com/
2. Agrega `OPENAI_API_KEY=tu_key` al `.env`
3. El chatbot usará GPT-3.5-turbo automáticamente

### Usar Hugging Face API Key (Opcional)

Mejora los rate limits de Hugging Face:

1. Crea cuenta en https://huggingface.co/
2. Obtén tu API key
3. Agrega `HUGGINGFACE_API_KEY=tu_key` al `.env`

### Personalizar Respuestas

Edita `services/ml_service.py` para personalizar:
- Intenciones detectadas
- Respuestas predefinidas
- Base de conocimiento

## 🐛 Solución de Problemas

### El chatbot no responde

1. Verifica que las variables de entorno estén configuradas
2. Revisa los logs en Render/consola
3. Verifica que Firebase esté conectado correctamente

### Error con OpenAI

Si OpenAI falla, el chatbot automáticamente usa el sistema de palabras clave como fallback.

### Error con Hugging Face

Si Hugging Face está cargando el modelo, espera unos segundos y vuelve a intentar.

## 📊 Estructura del Código

```
chatbot/
├── app.py                          # Aplicación Flask principal
├── config.py                       # Configuración
├── services/
│   ├── ml_service.py              # Servicio de Machine Learning
│   ├── conversation_manager.py    # Gestor de conversaciones
│   ├── actions_service.py         # Servicio de acciones (Firestore)
│   ├── whatsapp_service.py        # Servicio de WhatsApp
│   └── citas_service.py           # Servicio de citas
├── database/
│   ├── database.py                # Conexión a Firebase
│   └── models.py                  # Modelos de datos
└── requirements.txt               # Dependencias
```

## 🔐 Seguridad

- Todas las comunicaciones usan HTTPS
- Los tokens de API se almacenan en variables de entorno
- Firestore Security Rules protegen los datos
- Validación de requests de Twilio

## 📝 Notas

- El chatbot funciona mejor con usuarios autenticados (con `user_id`)
- Si no hay `user_id`, usa el teléfono como identificador
- El contexto se mantiene durante la conversación
- Los mensajes se guardan en el historial (últimos 10)

## 🆘 Soporte

Para problemas o preguntas:
1. Revisa los logs en Render
2. Verifica la configuración de variables de entorno
3. Consulta la documentación de Twilio y Firebase

---

**Desarrollado para Densora** 🦷

