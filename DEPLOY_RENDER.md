# Desplegar en Render.com (GRATIS y FÁCIL)

## Paso 1: Preparar el código

1. **Crea un archivo `Procfile`** (sin extensión) en la raíz del proyecto:
   ```
   web: gunicorn app:app --bind 0.0.0.0:$PORT
   ```

2. **Asegúrate de que `requirements.txt` tenga gunicorn** (ya lo tiene)

## Paso 2: Subir a GitHub

1. Si no tienes repositorio, créalo en GitHub
2. Sube tu código:
   ```bash
   git init
   git add .
   git commit -m "Chatbot WhatsApp con Twilio"
   git remote add origin https://github.com/tu-usuario/tu-repo.git
   git push -u origin main
   ```

## Paso 3: Desplegar en Render

1. Ve a https://render.com y crea cuenta (gratis)
2. Click en **"New +"** → **"Web Service"**
3. Conecta tu repositorio de GitHub
4. Configura:
   - **Name**: chatbot-whatsapp
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Plan**: Free

5. **Agrega las variables de entorno**:
   - Click en **"Environment"**
   - Agrega cada una:
     ```
     TWILIO_ACCOUNT_SID = tu_account_sid
     TWILIO_AUTH_TOKEN = tu_auth_token
     TWILIO_WHATSAPP_NUMBER = whatsapp:+521234567890
     TWILIO_WEBHOOK_TOKEN = tu_token
     FIREBASE_PROJECT_ID = tu_proyecto
     # NO configures PORT manualmente - Render lo asigna automáticamente
     ```

6. Click en **"Create Web Service"**
7. Espera a que termine el deploy (5-10 minutos)
8. Obtendrás una URL: `https://chatbot-whatsapp.onrender.com`

## Paso 4: Configurar webhook en Twilio

1. Ve a https://console.twilio.com/
2. **Messaging** → **Settings** → **WhatsApp Senders**
3. Selecciona tu número de WhatsApp Business
4. En "Webhook URL", pon:
   ```
   https://chatbot-whatsapp.onrender.com/webhook
   ```
5. **HTTP Method**: POST
6. Guarda

## Paso 5: Probar

1. Envía un mensaje desde WhatsApp al número de Twilio
2. Escribe: `hola` o `menu`
3. El bot debería responder

## Nota sobre Render Free

- El servidor se "duerme" después de 15 minutos de inactividad
- La primera petición puede tardar 30-60 segundos (está "despertando")
- Para producción 24/7, necesitas el plan de pago ($7/mes)

## Alternativa: Railway.app

Similar a Render, también gratis:
1. Ve a https://railway.app
2. Conecta GitHub
3. Configura variables de entorno
4. Deploy automático


