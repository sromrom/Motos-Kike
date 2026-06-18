"""Genera los valores que tienes que pegar en las Environment Variables de Render.

Uso:
    python gen_keys.py TU_CONTRASEÑA_ADMIN

Imprime SECRET_KEY, AES_KEY y ADMIN_PASSWORD_HASH listos para copiar.
GUARDA estos valores: si cambias AES_KEY luego, los datos cifrados ya guardados
quedarán ilegibles.
"""
import os
import sys
import base64
import secrets
from werkzeug.security import generate_password_hash

pwd = sys.argv[1] if len(sys.argv) > 1 else "cambia-esta-clave"
print("SECRET_KEY=" + secrets.token_hex(32))
print("AES_KEY=" + base64.urlsafe_b64encode(os.urandom(32)).decode())
print("ADMIN_USERNAME=admin")
print("ADMIN_PASSWORD_HASH=" + generate_password_hash(pwd))
print()
print(f"(Contraseña del admin: {pwd}  -> cámbiala por una segura)")
