"""Prueba el envío de email con la configuración del .env.

Uso:
    python test_email.py destino@ejemplo.com

Si no pasas destino, se envía a SMTP_USER (a ti mismo).
Imprime 'OK' o el error exacto que devuelve el servidor, útil para
ajustar host/puerto/usuario/contraseña.
"""
import sys
from dotenv import load_dotenv
load_dotenv()
import os
import notifications

to = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SMTP_USER", "")
if not to:
    print("Indica un destino: python test_email.py tu@correo.com")
    sys.exit(1)

print(f"Host: {os.environ.get('SMTP_HOST')}  Puerto: {os.environ.get('SMTP_PORT')}  "
      f"SSL: {os.environ.get('SMTP_USE_SSL')}  Usuario: {os.environ.get('SMTP_USER')}")
ok, info = notifications.send_email(
    to, "Prueba Motos Kike", "Esto es un email de prueba desde la web de Motos Kike. "
    "Si lo recibes, el envío de avisos funciona correctamente.")
print("RESULTADO:", "OK ✅" if ok else "ERROR ❌", "-", info)
