"""Cifrado AES-256-GCM para los datos personales de las citas.

Cada valor se cifra con un nonce aleatorio de 96 bits. El resultado almacenado
es base64( nonce(12) + ciphertext + tag(16) ). La clave (32 bytes) viene de la
variable de entorno AES_KEY. Sin esa clave los datos son ilegibles.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _key() -> bytes:
    raw = os.environ.get("AES_KEY", "")
    if not raw:
        raise RuntimeError("Falta AES_KEY en el entorno. Genera una clave de 32 bytes.")
    key = base64.urlsafe_b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("AES_KEY debe ser exactamente 32 bytes (AES-256).")
    return key


def encrypt(plaintext: str) -> str:
    if plaintext is None:
        return ""
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        data = base64.b64decode(token)
        nonce, ct = data[:12], data[12:]
        aes = AESGCM(_key())
        return aes.decrypt(nonce, ct, None).decode("utf-8")
    except Exception:
        return "[ilegible]"
