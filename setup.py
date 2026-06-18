"""Configuración inicial: crea .env con claves seguras y datos de ejemplo.

Uso:
    python setup.py            -> crea .env (si no existe) y la base de datos
    python setup.py --password TUCLAVE   -> fija la contraseña del admin
"""
import os, base64, sys, secrets
from werkzeug.security import generate_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(BASE, ".env")


def make_env(password="admin1234"):
    if os.path.exists(ENV):
        print(".env ya existe, no se sobrescribe.")
        return
    aes = base64.urlsafe_b64encode(os.urandom(32)).decode()
    secret = secrets.token_hex(32)
    ph = generate_password_hash(password)
    with open(ENV, "w") as f:
        f.write(f"SECRET_KEY={secret}\n")
        f.write(f"AES_KEY={aes}\n")
        f.write("ADMIN_USERNAME=admin\n")
        f.write(f"ADMIN_PASSWORD_HASH={ph}\n")
        f.write("SMTP_HOST=mail.motoskike.es\nSMTP_PORT=465\nSMTP_USE_SSL=true\nSMTP_USE_TLS=false\n")
        f.write("SMTP_USER=info@motoskike.es\nSMTP_PASSWORD=\n")
        f.write("SMTP_FROM=Motos Kike <info@motoskike.es>\n")
        f.write("TELEGRAM_BOT_TOKEN=\n")
        f.write("TWILIO_ACCOUNT_SID=\nTWILIO_AUTH_TOKEN=\nTWILIO_WHATSAPP_FROM=\n")
        f.write("WHATSAPP_TOKEN=\nWHATSAPP_PHONE_ID=\n")
    print(f".env creado. Usuario: admin  ·  Contraseña: {password}")
    print("CAMBIA la contraseña con: python setup.py --password NUEVACLAVE")


def set_password(password):
    if not os.path.exists(ENV):
        make_env(password)
        return
    ph = generate_password_hash(password)
    lines = open(ENV).read().splitlines()
    out, done = [], False
    for l in lines:
        if l.startswith("ADMIN_PASSWORD_HASH="):
            out.append(f"ADMIN_PASSWORD_HASH={ph}"); done = True
        else:
            out.append(l)
    if not done:
        out.append(f"ADMIN_PASSWORD_HASH={ph}")
    open(ENV, "w").write("\n".join(out) + "\n")
    print("Contraseña del admin actualizada.")


def seed():
    from app import app, init_db
    from models import db, Brand
    init_db()
    with app.app_context():
        if not Brand.query.first():
            for i, n in enumerate(["Yamaha", "Honda", "BMW", "Kawasaki", "Suzuki",
                                    "SYM", "KYMCO", "Vespa", "Piaggio"]):
                db.session.add(Brand(name=n, order=i, visible=True))
            db.session.commit()
            print("Marcas de ejemplo añadidas.")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--password":
        set_password(sys.argv[2])
    else:
        make_env()
    seed()
    print("Listo. Arranca con: python app.py")
