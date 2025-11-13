# 🚀 INSTRUCCIONES RÁPIDAS - CHATBOT DENSORA

## ⚡ Configuración Rápida

### 1. Variables de Entorno en Render

Ve a tu servicio en Render → Environment y agrega:

```
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
FIREBASE_PROJECT_ID=tu_project_id
OPENAI_API_KEY=tu_key (opcional pero recomendado)
```

### 2. Archivo serviceAccountKey.json

1. Descarga desde Firebase Console → Project Settings → Service Accounts
2. Sube el archivo a Render usando el dashboard o SCP
3. Asegúrate de que la ruta sea correcta en las variables de entorno

### 3. Webhook de Twilio

1. Ve a Twilio Console → Messaging → WhatsApp Sandbox
2. Configura webhook: `https://tu-app.onrender.com/webhook`
3. Guarda los cambios

## 🧪 Probar el Chatbot

### Desde WhatsApp

Envía un mensaje a tu número de Twilio:
- "Hola"
- "Quiero agendar una cita"
- "Ver mis citas"
- "Qué es Densora"

### Desde la Web

Usa el endpoint `/api/web/chat`:

```javascript
fetch('https://tu-app.onrender.com/api/web/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "Hola, quiero agendar una cita",
    session_id: "unique_id",
    user_id: "firebase_user_id",  // Si el usuario está autenticado
    phone: "521234567890"
  })
})
```

## 🎯 Características Principales

✅ **Entiende lenguaje natural**: No necesitas comandos exactos
✅ **Agenda citas**: "Quiero una cita mañana a las 3pm"
✅ **Reagenda citas**: "Cambiar mi cita del 15"
✅ **Cancela citas**: "Cancelar mi cita"
✅ **Consulta información**: "Qué es Densora?"
✅ **Funciona en WhatsApp y Web**: Mismo backend

## 🔧 Troubleshooting

### El bot no responde
- Verifica que el webhook esté configurado en Twilio
- Revisa los logs en Render
- Verifica las variables de entorno

### Error de Firebase
- Verifica que `serviceAccountKey.json` esté en la raíz
- Revisa que `FIREBASE_PROJECT_ID` sea correcto
- Verifica permisos en Firestore Security Rules

### Respuestas genéricas
- Agrega `OPENAI_API_KEY` para respuestas más naturales
- Verifica que el usuario tenga `user_id` o `phone` configurado

## 📚 Documentación Completa

Ver `README_CHATBOT_ML.md` para documentación detallada.

