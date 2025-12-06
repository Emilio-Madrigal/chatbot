# 📱 Configurar Webhook de WhatsApp en Twilio Sandbox

## Pasos para configurar el webhook en el Sandbox de Twilio

### 1. Obtener la URL de tu webhook en Render

Tu chatbot está desplegado en Render y tiene un endpoint `/webhook`. La URL completa será:
```
https://tu-app-en-render.onrender.com/webhook
```

**Importante:** Asegúrate de que:
- Tu aplicación en Render esté corriendo
- El endpoint `/webhook` esté accesible públicamente (sin autenticación)
- La URL use HTTPS (Render lo proporciona automáticamente)

### 2. Acceder a Twilio Console

1. Ve a [Twilio Console](https://console.twilio.com/)
2. Inicia sesión con tu cuenta
3. En el menú lateral, ve a **Messaging** → **Try it out** → **Send a WhatsApp message**

### 3. Configurar el Sandbox

1. En la sección **Sandbox**, verás tu número de sandbox: `+1 415 523 8886`
2. Verás el código de unión: `join stranger-parts.` (o el que tengas configurado)
3. Haz clic en **Configure** o busca la opción **Sandbox Settings**

### 4. Configurar el Webhook URL

En la configuración del Sandbox, encontrarás dos campos:

#### **WHEN A MESSAGE COMES IN** (Cuando llega un mensaje)
```
https://tu-app-en-render.onrender.com/webhook
```

#### **STATUS CALLBACK URL** (Opcional - para recibir actualizaciones de estado)
```
https://tu-app-en-render.onrender.com/webhook/status
```
(Opcional, solo si tienes un endpoint para esto)

### 5. Método HTTP

Asegúrate de que el método HTTP sea **POST** (debería ser el predeterminado).

### 6. Guardar la configuración

Haz clic en **Save** para guardar los cambios.

### 7. Verificar que funciona

1. Envía un mensaje de WhatsApp al número del sandbox: `+1 415 523 8886`
2. Asegúrate de estar unido al sandbox (envía `join stranger-parts.` si es necesario)
3. Envía un mensaje de prueba como "hola" o "menu"
4. Revisa los logs de Render para ver si el webhook está recibiendo los mensajes

## 🔍 Verificar que el webhook funciona

### En Render:
1. Ve a tu servicio en Render
2. Haz clic en **Logs**
3. Deberías ver logs cuando llegue un mensaje:
   ```
   ============================================================
   WEBHOOK RECIBIDO
   ============================================================
   Request method: POST
   From: whatsapp:+5213330362181
   Body: hola
   ```

### En Twilio Console:
1. Ve a **Monitor** → **Logs** → **Messaging**
2. Deberías ver los mensajes entrantes y salientes
3. Si hay errores, aparecerán aquí

## ⚠️ Solución de problemas

### El webhook no recibe mensajes:
1. **Verifica la URL**: Asegúrate de que la URL sea correcta y accesible
2. **Verifica HTTPS**: Twilio requiere HTTPS, Render lo proporciona automáticamente
3. **Verifica el endpoint**: El endpoint debe aceptar POST y responder rápidamente
4. **Revisa los logs de Render**: Puede haber errores en tu código

### Error 404:
- Verifica que la ruta `/webhook` exista en tu aplicación Flask
- Verifica que la URL en Twilio sea exactamente la correcta

### Error 500:
- Revisa los logs de Render para ver el error específico
- Asegúrate de que todas las dependencias estén instaladas
- Verifica que las variables de entorno estén configuradas

### El mensaje llega pero no hay respuesta:
- Verifica que tu código esté enviando una respuesta válida
- Asegúrate de que el formato del número de teléfono sea correcto
- Revisa que el número esté en el sandbox

## 📝 Notas importantes

1. **Sandbox vs Producción**: 
   - En sandbox solo puedes enviar mensajes a números que se hayan unido al sandbox
   - Para producción necesitarás verificar tu número de WhatsApp Business

2. **Formato de números**:
   - Los números deben estar en formato: `whatsapp:+5213330362181`
   - El código ya está actualizado para agregar el "1" inicial automáticamente

3. **Rate Limits**:
   - El sandbox tiene límites de velocidad
   - No envíes demasiados mensajes de prueba muy rápido

## 🔄 Actualizar el código

El código del chatbot ya está actualizado para:
- ✅ Formatear números correctamente para el sandbox
- ✅ Agregar el "1" inicial cuando sea necesario
- ✅ Manejar mensajes entrantes del webhook

Solo necesitas:
1. Hacer commit y push del código actualizado a tu repositorio
2. Render debería hacer deploy automáticamente
3. Configurar el webhook en Twilio Console como se explica arriba

