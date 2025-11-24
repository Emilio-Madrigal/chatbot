# 🤖 Cómo Funciona el Sistema Automático (SIN Cron Job)

## ✅ Ya está todo configurado automáticamente

**¡Buenas noticias!** No necesitas configurar ningún cron job. El sistema ya está programado para ejecutarse automáticamente usando **APScheduler** (un scheduler de Python que ya está en tu proyecto).

## 🔄 ¿Qué se ejecuta automáticamente?

### 1. **Procesamiento de Reintentos** (cada 30 minutos)
- ✅ Se ejecuta automáticamente cada 30 minutos
- ✅ Reenvía mensajes que fallaron anteriormente
- ✅ Máximo 2 reintentos por mensaje
- ✅ No necesitas hacer nada, funciona solo

### 2. **Recordatorios de Citas** (varios horarios)
- ✅ Recordatorios 24 horas antes (cada hora)
- ✅ Recordatorios 2 horas antes (cada hora a los 30 minutos)
- ✅ Verificación de pagos pendientes (cada 6 horas)
- ✅ Recordatorios de historial médico (diario a las 10 AM)
- ✅ Solicitud de reseñas (diario a las 6 PM)
- ✅ Cancelación automática de citas sin pago (cada 2 horas)

## 🚀 ¿Cómo se inicia?

Cuando ejecutas tu aplicación Flask, el sistema automáticamente:

1. **Inicia el scheduler** al arrancar la app
2. **Programa todas las tareas** automáticamente
3. **Ejecuta las tareas** en los horarios programados
4. **Sigue funcionando** mientras la app esté corriendo

### Para iniciar la app:

```bash
# Opción 1: Directamente con Python
cd chatbot
python app.py

# Opción 2: Con Flask
flask run

# Opción 3: Con gunicorn (producción)
gunicorn app:app
```

## 📋 Archivos que manejan esto

### `chatbot/scheduler/reminder_scheduler.py`
- Contiene el `ReminderScheduler` que maneja todas las tareas programadas
- Ya incluye el procesamiento de reintentos (agregado recientemente)

### `chatbot/app.py`
- Al inicio, llama a `init_schedulers()` que inicia todo automáticamente
- No necesitas hacer nada manual

## 🔍 ¿Cómo verificar que está funcionando?

### 1. Revisar los logs al iniciar:

Cuando inicies la app, deberías ver:

```
🚀 Iniciando schedulers automáticos...
🔔 Iniciando sistema de recordatorios...
✅ Sistema de recordatorios iniciado correctamente
✅ Schedulers iniciados correctamente
```

### 2. Ver logs de ejecución:

Cada 30 minutos verás en los logs:

```
🔄 Procesando reintentos de mensajes...
✅ Procesados X reintentos de mensajes
```

O si no hay reintentos:

```
🔄 Procesando reintentos de mensajes...
ℹ️ No hay reintentos pendientes
```

## ⚙️ ¿Quieres cambiar la frecuencia?

Si quieres cambiar cada cuánto se procesan los reintentos, edita `chatbot/scheduler/reminder_scheduler.py`:

```python
# Cambiar de cada 30 minutos a cada 15 minutos:
trigger=CronTrigger(minute='*/15', timezone=self.mexico_tz)

# Cambiar a cada hora:
trigger=CronTrigger(minute=0, timezone=self.mexico_tz)

# Cambiar a cada 5 minutos (para testing):
trigger=CronTrigger(minute='*/5', timezone=self.mexico_tz)
```

## 🐛 ¿Qué pasa si la app se reinicia?

- ✅ El scheduler se reinicia automáticamente
- ✅ Todas las tareas se reprograman
- ✅ Los reintentos pendientes se siguen procesando
- ✅ No se pierde información (todo está en Firestore)

## 📊 ¿Dónde se guardan los reintentos?

Los reintentos pendientes se guardan en Firestore en la colección:
- `whatsapp_retry_queue`

Puedes verlos en la consola de Firebase si quieres.

## 🎯 Resumen

**NO necesitas:**
- ❌ Configurar cron jobs
- ❌ Configurar tareas programadas en el sistema operativo
- ❌ Llamar manualmente a endpoints
- ❌ Hacer nada especial

**SÍ necesitas:**
- ✅ Solo mantener la app corriendo
- ✅ Eso es todo! 🎉

## 💡 Tip para Producción

Si usas un servicio como **Heroku**, **Railway**, **Render**, etc., asegúrate de que:

1. La app esté corriendo 24/7 (no se duerma)
2. Si usas el plan gratuito que se duerme, considera usar un servicio como **UptimeRobot** para hacer ping cada 5 minutos y mantenerla despierta

O mejor aún, usa un servicio que no se duerma como:
- Railway (tiene plan gratuito que no se duerme)
- Render (plan gratuito se duerme, pero puedes usar un worker)
- Google Cloud Run (puede configurarse para no dormirse)

## ❓ ¿Preguntas?

Si algo no funciona:
1. Revisa los logs al iniciar la app
2. Verifica que veas el mensaje "✅ Schedulers iniciados correctamente"
3. Espera 30 minutos y revisa los logs para ver si se ejecutó el procesamiento de reintentos

