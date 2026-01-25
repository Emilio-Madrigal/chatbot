import base64
import os
import json
from typing import Union, Dict, List, Any

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    print("Warning: 'cryptography' library not found. Decryption will fail.")
    AESGCM = None
    PBKDF2HMAC = None
    hashes = None

def derive_key(user_id: str, salt: bytes) -> bytes:
    """
    Derives a 256-bit AES key from the user_id using PBKDF2-HMAC-SHA256.
    Matches the client-side Logic:
    - Iterations: 100,000
    - Hash: SHA-256
    - Length: 32 bytes (256 bits)
    """
    if not user_id:
        raise ValueError("User ID is required to derive key")
        
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(user_id.encode('utf-8'))
    return key

def decrypt_string(encrypted_data: Dict[str, str], user_id: str) -> Union[str, None]:
    """
    Decrypts a single encrypted string entry.
    """
    if not encrypted_data or not encrypted_data.get('encrypted'):
        return None
        
    try:
        # Decode base64 components
        encrypted_bytes = base64.b64decode(encrypted_data['encrypted'])
        iv = base64.b64decode(encrypted_data['iv'])
        salt = base64.b64decode(encrypted_data['salt'])
        
        # Derive key
        key = derive_key(user_id, salt)
        
        # Decrypt using AES-GCM
        aesgcm = AESGCM(key)
        
        # AESGCM.decrypt takes (nonce, data, associated_data)
        # In this implementation, we don't use associated data (AAD) explicitely in JS side? 
        # JS crypto.subtle.encrypt(..., data) -> tag is append at the end usually for some libs, 
        # but Web Crypto API returns ciphertext + independent tag?
        # WAIT. JS `crypto.subtle.encrypt` with AES-GCM produces the ciphertext AND the authentication tag appended to it usually?
        # Actually, Web Crypto `encrypt` returns just the ciphertext+tag concatenated?
        # Let's check JS implementation: 
        # const encrypted = await crypto.subtle.encrypt(...)
        # const encryptedArray = new Uint8Array(encrypted);
        # return arrayBufferToBase64(encryptedArray)
        
        # Python cryptography AESGCM.decrypt expects the data to contain the tag at the end.
        # "The data to be decrypted. This must be the ciphertext with the authentication tag appended."
        # Web Crypto AES-GCM output IS ciphertext + tag.
        # So it should be compatible directly.
        
        decrypted_bytes = aesgcm.decrypt(iv, encrypted_bytes, None)
        return decrypted_bytes.decode('utf-8')
        
    except Exception as e:
        print(f"Error decrypting string: {e}")
        return None

def decrypt_object(obj: Any, user_id: str) -> Any:
    """
    Recursively decrypts an object/dict.
    """
    if not isinstance(obj, dict):
        return obj
    
    # If this dict represents an encrypted string field
    if obj.get('encrypted') and obj.get('iv') and obj.get('salt') and obj.get('algorithm') == 'AES-256-GCM':
        return decrypt_string(obj, user_id)
        
    # Standard dict, traverse keys
    decrypted = {}
    for key, value in obj.items():
        # Skip metadata fields
        if key.startswith('_encrypted') or key.startswith('_encryption'):
            continue
            
        if isinstance(value, dict):
            # Check if it's a nested encrypted object or just a dict
            decrypted[key] = decrypt_object(value, user_id)
        elif isinstance(value, list):
            # Process list items
            decrypted[key] = [decrypt_object(item, user_id) for item in value]
        else:
            decrypted[key] = value
            
    return decrypted

def decrypt_medical_history(historial_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Main entry point to decrypt full medical history.
    """
    if not historial_data or not historial_data.get('_encrypted'):
        return historial_data
        
    return decrypt_object(historial_data, user_id)
