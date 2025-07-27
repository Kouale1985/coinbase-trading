# key_loader.py
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519

def load_ed25519_private_key(encoded_key):
    if encoded_key.startswith("ed25519:"):
        encoded_key = encoded_key[len("ed25519:"):]

    # Add base64 padding if needed
    missing_padding = len(encoded_key) % 4
    if missing_padding:
        encoded_key += "=" * (4 - missing_padding)

    raw_bytes = base64.b64decode(encoded_key)

    if len(raw_bytes) < 32:
        raise ValueError(f"Key too short: got {len(raw_bytes)} bytes")

    private_key_bytes = raw_bytes[:32]  # Only use first 32 bytes
    return ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
