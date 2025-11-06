# 🔧 SOLUCIÓN: Error de Puerto en Render

## ❌ El Problema

Render está buscando el puerto 5000, pero el servidor está usando otro puerto (10000) que Render asigna automáticamente.

## ✅ La Solución

**Render asigna el puerto automáticamente. NO debes configurar `PORT=5000` manualmente.**

### Paso 1: Eliminar PORT=5000 de Render

1. Ve a tu servicio en Render: https://dashboard.render.com
2. Click en tu servicio (chatbot-whatsapp)
3. Ve a la pestaña **"Environment"**
4. Busca la variable `PORT` con valor `5000`
5. **ELIMÍNALA** (click en el ícono de basura o "Delete")
6. **Guarda los cambios**

### Paso 2: Verificar el Procfile

El `Procfile` ya está correcto:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

Esto hace que gunicorn use el puerto que Render asigna automáticamente.

### Paso 3: Forzar un nuevo deploy

1. En Render, ve a tu servicio
2. Click en **"Manual Deploy"** → **"Deploy latest commit"**
3. Espera a que termine

## 🎯 Resultado Esperado

Después de eliminar `PORT=5000`, Render:
- Asignará un puerto automáticamente (puede ser 10000, 5000, u otro)
- Gunicorn usará ese puerto a través de `$PORT`
- Render detectará el puerto correctamente
- **NO verás más el error "Port scan timeout"**

## ⚠️ IMPORTANTE

- **NO** configures `PORT=5000` manualmente en Render
- **SÍ** deja que Render asigne el puerto automáticamente
- El `Procfile` usa `$PORT` para usar el puerto que Render asigna

## 📝 Variables de Entorno que SÍ debes tener:

✅ `TWILIO_ACCOUNT_SID`
✅ `TWILIO_AUTH_TOKEN`
✅ `TWILIO_WHATSAPP_NUMBER`
✅ `TWILIO_WEBHOOK_TOKEN`
✅ `FIREBASE_PROJECT_ID`

❌ **NO** `PORT` (Render lo asigna automáticamente)

