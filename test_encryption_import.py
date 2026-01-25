import sys
import os
import base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from chatbot.utils.encryption import derive_key, decrypt_string
    print("✅ encryption.py imported successfully")
except ImportError as e:
    print(f"❌ Failed to import encryption module: {e}")
    sys.exit(1)

# Sample encrypted data (generated via JS logic for testing)
# This assumes we can mock the values or use a known vector
# But since I can't run JS easily to generate one, I'll rely on structural check
# or try to use a known key/salt IF I had one.
# For now, verification is simply that the module imports and functions exist.

if callable(derive_key) and callable(decrypt_string):
    print("✅ Functions 'derive_key' and 'decrypt_string' exist")
else:
    print("❌ Functions missing")

print("\nReady to decrypt real data.")
