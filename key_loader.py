import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

def load_ed25519_private_key(encoded_key: str):
    """
    Takes the `ed25519:...` key string from Coinbase and returns a usable private key object.
    """
    if encoded_key.startswith("ed25519:"):
        encoded_key = encoded_key.split("ed25519:")[1]

    raw_bytes = base64.b64decode(encoded_key)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)

    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
