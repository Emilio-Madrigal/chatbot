"""
Utilidades para normalizar números de teléfono
"""

def normalize_phone_for_database(phone: str) -> str:
    """
    Normaliza un número de teléfono para buscar en Firestore.
    
    En Firestore, los números se guardan como "+523330362181" (sin el prefijo "whatsapp:" 
    y sin el "1" extra que Twilio agrega para el sandbox).
    
    Esta función:
    1. Quita el prefijo "whatsapp:" si existe
    2. Si el número empieza con "+1" seguido de un código de país (ej: +152...), 
       quita el "1" extra para que quede +52...
    3. Si el número empieza con "+52" seguido de "1" (ej: +521...), 
       quita el "1" extra para que quede +52...
    4. Retorna el número normalizado
    
    Args:
        phone: Número de teléfono en cualquier formato (ej: "whatsapp:+5213330362181")
    
    Returns:
        Número normalizado para buscar en Firestore (ej: "+523330362181")
    """
    if not phone:
        return phone
    
    # Quitar el prefijo "whatsapp:" si existe
    normalized = phone.replace('whatsapp:', '').strip()
    
    # Caso 1: Si el número empieza con "+1" seguido de un código de país de 2 dígitos,
    # quitar el "1" extra
    # Ejemplo: "+1523330362181" -> "+523330362181"
    if normalized.startswith('+1') and len(normalized) > 3:
        # Verificar si después de "+1" hay un código de país de 2 dígitos
        # (como 52 para México)
        if len(normalized) >= 4 and normalized[2:4].isdigit():
            # Quitar el "1" extra: "+1" + código_país -> "+" + código_país
            normalized = '+' + normalized[2:]
    
    # Caso 2: Si el número empieza con "+52" seguido de "1", quitar el "1" extra
    # Ejemplo: "+5213330362181" -> "+523330362181"
    if normalized.startswith('+52') and len(normalized) > 3:
        # Si después de "+52" hay un "1", quitarlo
        if len(normalized) >= 4 and normalized[3] == '1':
            # Quitar el "1" extra: "+52" + "1" + número -> "+52" + número
            normalized = '+52' + normalized[4:]
    
    return normalized

