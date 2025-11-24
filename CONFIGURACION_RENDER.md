# 🚀 Configuración para Render

## ✅ Ya está todo configurado

He creado los archivos necesarios para que tu chatbot funcione perfectamente en Render.

## 📁 Archivos creados/modificados

### 1. `render.yaml` (NUEVO)
- Configuración automática para Render
- Define el servicio web
- Configura health checks
- Auto-deploy desde main branch

### 2. `Procfile` (ya existía)
- Comando de inicio para Render
- Usa gunicorn para producción

### 3. `app.py` (MODIFICADO)
- Endpoint `/health` mejorado (Render lo usa para health checks)
- Endpoint `/ping` nuevo (para mantener el servicio activo)
- Inicialización mejorada de schedulers para Render

## 🔧 Configuración en Render

### Paso 1: Variables de Entorno

En el dashboard de Render, ve a tu servicio → Environment y agrega:

**Obligatorias:**
```
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
FIREBASE_PROJECT_ID=tu_project_id
```

**Opcionales (pero recomendadas):**
```
OPENAI_API_KEY=sk-... (para mejor NLP)
OPENAI_MODEL=gpt-4o (o gpt-4o-mini)
TOKEN_SECRET_KEY=tu-clave-secreta-super-segura
PORT=5000
```

### Paso 2: Health Check Path

En Render Dashboard → Settings → Health Check Path:
```
/health
```

Render hará ping a este endpoint cada 5 minutos para mantener el servicio activo.

### Paso 3: Build & Deploy

Render automáticamente:
1. Detecta el `render.yaml`
2. Instala dependencias (`requirements.txt`)
3. Ejecuta el build command
4. Inicia con gunicorn

## 🔄 ¿Cómo funciona el scheduler en Render?

### ✅ Funciona automáticamente

1. **Al iniciar el servicio:**
   - Render ejecuta `gunicorn app:app`
   - La app carga y ejecuta `init_schedulers()`
   - El scheduler se inicia automáticamente

2. **Mientras el servicio está activo:**
   - El scheduler ejecuta tareas programadas
   - Reintentos cada 30 minutos
   - Recordatorios según horarios configurados

3. **Si el servicio se duerme:**
   - Render lo despierta automáticamente cuando recibe una petición
   - El scheduler se reinicia automáticamente
   - No se pierde información (todo está en Firestore)

## 🛡️ Prevenir que se duerma (Plan Gratuito)

Render tiene un plan gratuito que se duerme después de 15 minutos de inactividad. Hay varias opciones:

### Opción 1: Health Check de Render (RECOMENDADO) ✅

Render automáticamente hace ping a `/health` cada 5 minutos si configuraste el Health Check Path. Esto mantiene el servicio activo.

**Configuración:**
1. Ve a Settings → Health Check Path
2. Pon: `/health`
3. Guarda

### Opción 2: UptimeRobot (GRATIS)

1. Ve a [UptimeRobot.com](https://uptimerobot.com)
2. Crea cuenta gratuita
3. Agrega un monitor HTTP(S)
4. URL: `https://tu-servicio.onrender.com/ping`
5. Intervalo: 5 minutos

Esto hará ping cada 5 minutos y mantendrá el servicio activo.

### Opción 3: Cron Job Externo (GRATIS)

Puedes usar un servicio como [cron-job.org](https://cron-job.org) para hacer ping:

1. Crea cuenta gratuita
2. Crea un nuevo cron job
3. URL: `https://tu-servicio.onrender.com/ping`
4. Frecuencia: Cada 5 minutos

### Opción 4: Upgrade a Plan de Pago

Si necesitas que nunca se duerma, Render tiene planes desde $7/mes que mantienen el servicio activo 24/7.

## 📊 Verificar que funciona

### 1. Revisar logs en Render

Ve a tu servicio → Logs y deberías ver:

```
🚀 Iniciando schedulers automáticos...
🔔 Iniciando sistema de recordatorios...
✅ Sistema de recordatorios iniciado correctamente
✅ Schedulers iniciados correctamente
```

### 2. Probar endpoints

```bash
# Health check
curl https://tu-servicio.onrender.com/health

# Ping
curl https://tu-servicio.onrender.com/ping

# Métricas
curl https://tu-servicio.onrender.com/api/metrics
```

### 3. Verificar scheduler

Cada 30 minutos deberías ver en los logs:

```
🔄 Procesando reintentos de mensajes...
✅ Procesados X reintentos de mensajes
```

## 🔍 Troubleshooting

### Problema: El servicio se duerme

**Solución:**
- Configura Health Check Path en Render: `/health`
- O usa UptimeRobot para hacer ping cada 5 minutos

### Problema: El scheduler no inicia

**Solución:**
1. Revisa los logs en Render
2. Verifica que las variables de entorno estén configuradas
3. Revisa que `serviceAccountKey.json` esté en el repositorio (o usa variables de entorno para Firebase)

### Problema: Los reintentos no se procesan

**Solución:**
1. Verifica que el servicio esté activo (no dormido)
2. Revisa los logs para ver si hay errores
3. Verifica que Firestore esté configurado correctamente

### Problema: Error al iniciar

**Solución:**
1. Revisa `requirements.txt` - asegúrate de que todas las dependencias estén listadas
2. Verifica que el puerto esté configurado correctamente (Render usa `$PORT`)
3. Revisa los logs de build en Render

## 📝 Comandos útiles

### Ver logs en tiempo real:
```bash
# En Render Dashboard → Logs
# O usando Render CLI:
render logs --service chatbot-whatsapp --tail
```

### Reiniciar servicio:
```bash
# En Render Dashboard → Manual Deploy → Clear build cache & deploy
```

### Verificar variables de entorno:
```bash
# En Render Dashboard → Environment
```

## 🎯 Resumen

✅ **Ya está todo configurado**
- `render.yaml` creado
- Endpoints de health check configurados
- Scheduler se inicia automáticamente
- Solo necesitas:
  1. Configurar variables de entorno en Render
  2. Configurar Health Check Path (opcional pero recomendado)
  3. Deployar

## 💡 Tips

1. **Usa Health Check Path** - Es la forma más fácil de mantener el servicio activo
2. **Monitorea los logs** - Te ayudará a detectar problemas temprano
3. **Configura alertas** - Render puede enviarte emails si el servicio falla
4. **Backup de variables** - Guarda tus variables de entorno en un lugar seguro

## ❓ ¿Preguntas?

Si algo no funciona:
1. Revisa los logs en Render Dashboard
2. Verifica que todas las variables de entorno estén configuradas
3. Prueba los endpoints `/health` y `/ping`
4. Verifica que el servicio no esté dormido

