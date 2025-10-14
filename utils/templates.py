def get_welcome_message():
    return """👋 ¡Hola! Bienvenido al *Sistema de Citas Médicas*

            Soy tu asistente virtual y estoy aquí para ayudarte con:

            📅 *Agendar* nuevas citas
            👀 *Ver* tus citas programadas  
            🔄 *Reagendar* citas existentes
            ❌ *Cancelar* citas si es necesario

            Escribe *menu* en cualquier momento para ver las opciones.

            ¿Cómo puedo ayudarte hoy?"""

def get_error_message():
    return """*Oops! Algo salió mal*

            Hubo un problema.

            💡 *¿Qué puedes hacer?*
            • Escribe *menu* para empezar de nuevo
            • Verifica que tu mensaje sea claro
            • Intenta nuevamente en unos minutos

            ¡Estamos aquí para ayudarte! 🤖"""

def get_maintenance_message():
    return """🔧 *Sistema en Mantenimiento*

            Estamos realizando mejoras para brindarte un mejor servicio.

            ⏱️ *Tiempo estimado:* 10-15 minutos
            🔄 Por favor, intenta nuevamente más tarde

            ¡Gracias por tu paciencia!"""