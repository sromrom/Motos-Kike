from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
import crypto

db = SQLAlchemy()


class Setting(db.Model):
    """Clave-valor para TODO lo editable: contacto, RRSS, textos, SEO, horarios."""
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, default="")


class Section(db.Model):
    """Apartados de la web que el admin puede mostrar/ocultar y reordenar."""
    slug = db.Column(db.String(40), primary_key=True)
    label = db.Column(db.String(80))
    visible = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)


class Brand(db.Model):
    """Marcas / proveedores de motos que se venden. Editable por el admin."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    logo_url = db.Column(db.String(300), default="")  # url o ruta a /static/img
    website = db.Column(db.String(300), default="")
    visible = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)


class NewModel(db.Model):
    """Modelos de moto disponibles actualmente (nuevos / en stock)."""
    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(80), default="")
    name = db.Column(db.String(120), nullable=False)
    cc = db.Column(db.String(20), default="")
    price = db.Column(db.String(40), default="")  # texto libre: "desde 3.200 €"
    description = db.Column(db.Text, default="")
    image_url = db.Column(db.String(300), default="")
    official_url = db.Column(db.String(300), default="")  # ficha en web oficial de la marca
    visible = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)


class UsedBike(db.Model):
    """Motos de ocasión (segunda mano). Solo visualización + contacto."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    brand = db.Column(db.String(80), default="")
    year = db.Column(db.String(10), default="")
    km = db.Column(db.String(20), default="")
    cc = db.Column(db.String(20), default="")
    price = db.Column(db.String(40), default="")
    description = db.Column(db.Text, default="")
    images = db.Column(db.Text, default="")  # urls separadas por coma
    sold = db.Column(db.Boolean, default=False)
    visible = db.Column(db.Boolean, default=True)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    def image_list(self):
        return [u.strip() for u in (self.images or "").split(",") if u.strip()]


class Appointment(db.Model):
    """Citas. Los datos personales se guardan CIFRADOS (AES-256)."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, index=True)  # nº de cita
    kind = db.Column(db.String(20), default="mantenimiento")  # mantenimiento | consulta
    slot = db.Column(db.DateTime, nullable=True)  # fecha/hora reservada (mantenimiento)
    status = db.Column(db.String(20), default="pendiente")  # pendiente|confirmada|cancelada
    subject = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")
    created = db.Column(db.DateTime, default=datetime.utcnow)

    # Datos personales cifrados
    _name = db.Column("name_enc", db.Text, default="")
    _phone = db.Column("phone_enc", db.Text, default="")
    _email = db.Column("email_enc", db.Text, default="")
    # Hashes en claro NO; guardamos versiones cifradas. Para login del cliente
    # comparamos el dato descifrado.

    # ---- propiedades que cifran/descifran de forma transparente ----
    @property
    def name(self):
        return crypto.decrypt(self._name)

    @name.setter
    def name(self, v):
        self._name = crypto.encrypt(v or "")

    @property
    def phone(self):
        return crypto.decrypt(self._phone)

    @phone.setter
    def phone(self, v):
        self._phone = crypto.encrypt(v or "")

    @property
    def email(self):
        return crypto.decrypt(self._email)

    @email.setter
    def email(self, v):
        self._email = crypto.encrypt(v or "")

    def anonymize(self):
        """Elimina los datos personales del cliente, conservando el resto de la cita."""
        self._name = ""
        self._phone = ""
        self._email = ""

    def has_personal_data(self):
        return bool(self._name or self._phone or self._email)

    def needs_anonymize(self):
        """Datos del cliente se borran de anteayer hacia atrás (hoy y ayer se conservan)."""
        ayer = date.today() - timedelta(days=1)
        if self.slot:
            return self.slot.date() < ayer
        # consultas sin fecha fija: a los 2 días
        return (datetime.utcnow() - self.created).days >= 2

    def needs_full_delete(self):
        """Borrado total del registro: consultas sin cerrar muy antiguas (>30 días)."""
        if not self.slot:
            return (datetime.utcnow() - self.created).days > 30
        return False


class Block(db.Model):
    """Franja de 30 min bloqueada manualmente por el administrador."""
    id = db.Column(db.Integer, primary_key=True)
    slot = db.Column(db.DateTime, unique=True, index=True, nullable=False)
    reason = db.Column(db.String(200), default="")
    created = db.Column(db.DateTime, default=datetime.utcnow)
