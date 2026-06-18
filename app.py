import os
import secrets
import string
from datetime import datetime, timedelta, date, time

from dotenv import load_dotenv
load_dotenv()

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   jsonify, abort, send_from_directory, session)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from models import db, Setting, Section, Brand, NewModel, UsedBike, Appointment, Block
import notifications

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "static", "img", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-cambiar")
# Base de datos: usa DATABASE_URL (PostgreSQL en producción) si existe; si no, SQLite local.
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)  # SQLAlchemy
app.config["SQLALCHEMY_DATABASE_URI"] = _db_url or ("sqlite:///" + os.path.join(BASE, "instance", "motoskike.db"))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB por imagen

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "admin_login"


# ---------------------------------------------------------------- Auth
class Admin(UserMixin):
    id = "admin"


@login_manager.user_loader
def load_user(uid):
    return Admin() if uid == "admin" else None


# ---------------------------------------------------------------- Helpers
DEFAULT_SETTINGS = {
    "shop_name": "Motos Kike",
    "tagline": "Taller & Venta · Reparación, mantenimiento y venta de motos en Chiclana",
    "address": "Calle Caraza 21, Chiclana de la Frontera, Cádiz",
    "phone": "666475205",
    "email": "info@motoskike.es",
    "whatsapp": "666475205",
    "maps_url": "https://maps.google.com/?q=Calle+Caraza+21+Chiclana+de+la+Frontera",
    "instagram": "", "facebook": "", "tiktok": "", "youtube": "",
    "about": ("Somos una tienda-taller de reconocido prestigio y dilatada "
              "trayectoria en Chiclana de la Frontera. Venta de motos nuevas y de "
              "ocasión, reparación y mantenimiento de todas las marcas."),
    # horario de citas: día(0=lun..6=dom)=rangos separados por ; , tramos por coma
    "schedule": "0=09:30-13:30,17:00-20:00\n1=09:30-13:30,17:00-20:00\n2=09:30-13:30,17:00-20:00\n3=09:30-13:30,17:00-20:00\n4=09:30-13:30,17:00-20:00\n5=10:00-13:30",
    "fin_tin": "8.95",   # TIN % por defecto para la calculadora
    "fin_max_months": "60",
    "seo_title": "Motos Kike · Taller y venta de motos en Chiclana de la Frontera (Cádiz)",
    "seo_description": ("Taller y venta de motos en Chiclana de la Frontera. "
                        "Reparación, mantenimiento y motos de ocasión en la provincia de Cádiz. "
                        "Pide tu cita online."),
    "seo_keywords": ("taller de motos Chiclana, venta de motos Cádiz, reparación motos "
                     "Chiclana, mantenimiento motos Cádiz, motos de ocasión Chiclana"),
    "use_cookies": "1",
    # apariencia
    "theme": "dark",          # dark | light
    "c_accent": "", "c_bg": "", "c_text": "", "c_title": "",
}

DEFAULT_SECTIONS = [
    ("inicio", "Inicio", 0),
    ("marcas", "Marcas", 1),
    ("ocasion", "Ocasión", 3),
    ("cita", "Pide tu cita", 4),
    ("financiacion", "Financiación", 5),
    ("contacto", "Contacto", 6),
]


def get_settings():
    s = dict(DEFAULT_SETTINGS)
    for row in Setting.query.all():
        s[row.key] = row.value
    return s


def set_setting(key, value):
    row = db.session.get(Setting, key)
    if not row:
        row = Setting(key=key)
        db.session.add(row)
    row.value = value


def sections_map():
    return {s.slug: s for s in Section.query.all()}


def visible_sections():
    return Section.query.filter_by(visible=True).order_by(Section.order).all()


def cleanup_expired():
    """RGPD: anonimiza datos del cliente de anteayer en adelante (conservando el resto
    de la cita) y borra por completo las consultas sin cerrar muy antiguas. Las citas
    marcadas como completadas se eliminan en el momento de cerrarlas."""
    changed = False
    for a in Appointment.query.all():
        if a.needs_full_delete():
            db.session.delete(a)
            changed = True
        elif a.needs_anonymize() and a.has_personal_data():
            a.anonymize()
            changed = True
    if changed:
        db.session.commit()


def gen_code(n=6):
    return "".join(secrets.choice(string.digits) for _ in range(n))


def parse_schedule(text):
    """Devuelve {weekday: [(start_time, end_time), ...]}"""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        d, ranges = line.split("=", 1)
        try:
            wd = int(d)
        except ValueError:
            continue
        tramos = []
        for r in ranges.split(","):
            r = r.strip()
            if "-" not in r:
                continue
            a, b = r.split("-")
            try:
                ha, ma = map(int, a.split(":"))
                hb, mb = map(int, b.split(":"))
                tramos.append((time(ha, ma), time(hb, mb)))
            except ValueError:
                continue
        out[wd] = tramos
    return out


def day_slots(day: date, private=False):
    """Todas las franjas de 30 min del día con su estado.
    status: free | booked | blocked | past
    Si private=True añade datos de la cita/bloqueo (solo admin).
    """
    sched = parse_schedule(get_settings()["schedule"])
    tramos = sched.get(day.weekday(), [])
    appts = {a.slot: a for a in Appointment.query.filter(
        Appointment.status != "cancelada").all()
        if a.slot and a.slot.date() == day}
    blocks = {b.slot: b for b in Block.query.all() if b.slot.date() == day}
    now = datetime.now()
    out = []
    for start, end in tramos:
        cur = datetime.combine(day, start)
        stop = datetime.combine(day, end)
        while cur < stop:
            if cur in blocks:
                st = "blocked"
            elif cur in appts:
                st = "booked"
            elif cur < now:
                st = "past"
            else:
                st = "free"
            item = {"t": cur.strftime("%H:%M"), "status": st}
            if private and st == "booked":
                a = appts[cur]
                item.update(id=a.id, code=a.code, name=a.name, phone=a.phone,
                            email=a.email, kind=a.kind, subject=a.subject, estado=a.status)
            elif private and st == "blocked":
                b = blocks[cur]
                item.update(block_id=b.id, reason=b.reason)
            out.append(item)
            cur += timedelta(minutes=30)
    return out


def free_slots(day: date):
    return [s["t"] for s in day_slots(day) if s["status"] == "free"]


def avail_level(day: date):
    """Nivel de disponibilidad del día: high | low | none | past | closed."""
    slots = day_slots(day)
    if not slots:
        return "closed"
    active = [s for s in slots if s["status"] != "past"]
    if not active:
        return "past"
    free = sum(1 for s in active if s["status"] == "free")
    if free == 0:
        return "none"
    return "high" if free / len(active) >= 0.5 else "low"


def month_availability(year: int, month: int, private=False):
    """Devuelve {dia: nivel} para el mes. Si private, marca días con bloqueos."""
    import calendar as _cal
    ndays = _cal.monthrange(year, month)[1]
    today = date.today()
    res = {}
    for d in range(1, ndays + 1):
        day = date(year, month, d)
        lvl = avail_level(day)
        if day < today:
            lvl = "past"
        info = {"level": lvl}
        if private:
            info["blocked"] = any(s["status"] == "blocked" for s in day_slots(day))
            info["booked"] = sum(1 for s in day_slots(day) if s["status"] == "booked")
        res[d] = info
    return res


@app.context_processor
def inject_globals():
    return {"S": get_settings(), "nav": visible_sections(),
            "section_visible": {s.slug for s in visible_sections()},
            "year": datetime.now().year}


# ==================================================================
#  RUTAS PÚBLICAS
# ==================================================================
@app.route("/")
def index():
    cleanup_expired()
    brands = Brand.query.filter_by(visible=True).order_by(Brand.order).all()
    used = UsedBike.query.filter_by(visible=True, sold=False).order_by(UsedBike.created.desc()).limit(3).all()
    return render_template("index.html", brands=brands, used=used)


def _models_of(brand_name):
    bn = (brand_name or "").strip().lower()
    return [m for m in NewModel.query.filter_by(visible=True).order_by(NewModel.order).all()
            if (m.brand or "").strip().lower() == bn]


@app.route("/marcas")
def marcas():
    brands = Brand.query.filter_by(visible=True).order_by(Brand.order).all()
    counts = {b.id: len(_models_of(b.name)) for b in brands}
    return render_template("marcas.html", brands=brands, counts=counts)


@app.route("/marcas/<int:bid>")
def marca_modelos(bid):
    brand = Brand.query.get_or_404(bid)
    if not brand.visible:
        abort(404)
    models = _models_of(brand.name)
    return render_template("marca_modelos.html", brand=brand, models=models)


@app.route("/modelos")
def modelos():
    # El apartado de modelos se integró dentro de cada marca.
    return redirect(url_for("marcas"), code=301)


@app.route("/ocasion")
def ocasion():
    bikes = UsedBike.query.filter_by(visible=True).order_by(UsedBike.created.desc()).all()
    return render_template("ocasion.html", bikes=bikes)


@app.route("/ocasion/<int:bid>")
def ocasion_detail(bid):
    bike = UsedBike.query.get_or_404(bid)
    if not bike.visible:
        abort(404)
    return render_template("ocasion_detail.html", bike=bike)


@app.route("/financiacion")
def financiacion():
    return render_template("financiacion.html")


@app.route("/cita", methods=["GET", "POST"])
def cita():
    if request.method == "POST":
        cleanup_expired()
        kind = request.form.get("kind", "mantenimiento")
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        notes = request.form.get("notes", "").strip()
        if not name or (not phone and not email):
            flash("Indica tu nombre y al menos un teléfono o email.", "error")
            return redirect(url_for("cita"))

        slot = None
        if kind == "mantenimiento":
            d = request.form.get("date", "")
            t = request.form.get("time", "")
            try:
                slot = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
            except ValueError:
                flash("Selecciona una fecha y hora válidas.", "error")
                return redirect(url_for("cita"))
            # comprobar que sigue libre
            if t not in free_slots(slot.date()):
                flash("Esa hora ya no está disponible. Elige otra.", "error")
                return redirect(url_for("cita"))

        code = gen_code()
        while Appointment.query.filter_by(code=code).first():
            code = gen_code()
        appt = Appointment(code=code, kind=kind, slot=slot, subject=subject,
                           notes=notes, status="pendiente")
        appt.name, appt.phone, appt.email = name, phone, email
        db.session.add(appt)
        db.session.commit()

        results = notifications.notify_client(appt, get_settings(), "creada")
        sent = [c for c, ok, _ in results if ok]
        msg = f"Cita creada. Tu número de cita es {code}."
        if sent:
            msg += " Te hemos enviado la confirmación por " + ", ".join(sent) + "."
        flash(msg, "ok")
        return render_template("cita_ok.html", appt=appt)

    return render_template("cita.html")


@app.route("/api/slots")
def api_slots():
    """Franjas del día para el frontend: disponible u ocupada (sin revelar quién)."""
    d = request.args.get("date", "")
    try:
        day = datetime.strptime(d, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"slots": []})
    slots = [{"t": s["t"], "available": s["status"] == "free"} for s in day_slots(day)]
    return jsonify({"date": d, "slots": slots})


@app.route("/api/availability")
def api_availability():
    """Niveles de disponibilidad (color) de cada día del mes para el frontend."""
    try:
        y = int(request.args.get("year"))
        m = int(request.args.get("month"))
    except (TypeError, ValueError):
        today = date.today()
        y, m = today.year, today.month
    return jsonify({"year": y, "month": m, "days": month_availability(y, m)})


@app.route("/mi-cita", methods=["GET", "POST"])
def mi_cita():
    cleanup_expired()
    if request.method == "POST" and "code" in request.form:
        code = request.form.get("code", "").strip()
        contact = request.form.get("contact", "").strip().lower()
        appt = Appointment.query.filter_by(code=code).first()
        if appt and (contact == appt.phone.lower() or contact == appt.email.lower()):
            session["cita_code"] = code
            return redirect(url_for("mi_cita_manage"))
        flash("No encontramos una cita con esos datos.", "error")
    return render_template("mi_cita.html")


@app.route("/mi-cita/gestion", methods=["GET", "POST"])
def mi_cita_manage():
    code = session.get("cita_code")
    appt = Appointment.query.filter_by(code=code).first() if code else None
    if not appt:
        return redirect(url_for("mi_cita"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "cancel":
            appt.status = "cancelada"
            db.session.commit()
            notifications.notify_client(appt, get_settings(), "cancelada")
            flash("Cita cancelada.", "ok")
            session.pop("cita_code", None)
            return redirect(url_for("index"))
        if action == "reschedule" and appt.kind == "mantenimiento":
            d = request.form.get("date", "")
            t = request.form.get("time", "")
            try:
                slot = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
            except ValueError:
                flash("Fecha u hora no válidas.", "error")
                return redirect(url_for("mi_cita_manage"))
            if t not in free_slots(slot.date()):
                flash("Esa hora ya no está disponible.", "error")
                return redirect(url_for("mi_cita_manage"))
            appt.slot = slot
            appt.status = "pendiente"
            db.session.commit()
            notifications.notify_client(appt, get_settings(), "modificada")
            flash("Cita modificada.", "ok")
        return redirect(url_for("mi_cita_manage"))
    return render_template("mi_cita_manage.html", appt=appt)


@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        name = request.form.get("name", "")
        email = request.form.get("email", "")
        message = request.form.get("message", "")
        S = get_settings()
        body = f"Mensaje web de {name} ({email}):\n\n{message}"
        if S.get("email"):
            notifications.send_email(S["email"], "Contacto web", body)
        flash("Gracias, hemos recibido tu mensaje. Te responderemos lo antes posible.", "ok")
        return redirect(url_for("contacto"))
    return render_template("contacto.html")


@app.route("/cookies")
def cookies():
    return render_template("cookies.html")


@app.route("/privacidad")
def privacidad():
    return render_template("privacidad.html")


@app.route("/robots.txt")
def robots():
    return ("User-agent: *\nAllow: /\nSitemap: " + url_for("sitemap", _external=True),
            200, {"Content-Type": "text/plain"})


@app.route("/sitemap.xml")
def sitemap():
    pages = ["index", "marcas", "ocasion", "cita", "financiacion", "contacto"]
    urls = [url_for(p, _external=True) for p in pages]
    urls += [url_for("marca_modelos", bid=b.id, _external=True)
             for b in Brand.query.filter_by(visible=True).all()]
    urls += [url_for("ocasion_detail", bid=b.id, _external=True)
             for b in UsedBike.query.filter_by(visible=True).all()]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"<url><loc>{u}</loc></url>")
    xml.append("</urlset>")
    return "\n".join(xml), 200, {"Content-Type": "application/xml"}


# ==================================================================
#  ADMIN
# ==================================================================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        ok_user = u == os.environ.get("ADMIN_USERNAME", "admin")
        ph = os.environ.get("ADMIN_PASSWORD_HASH", "")
        if ok_user and ph and check_password_hash(ph, p):
            login_user(Admin())
            return redirect(url_for("admin_dashboard"))
        flash("Credenciales incorrectas.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/admin")
@login_required
def admin_dashboard():
    cleanup_expired()
    stats = {
        "brands": Brand.query.count(),
        "models": NewModel.query.count(),
        "used": UsedBike.query.count(),
        "appts": Appointment.query.filter(Appointment.status != "cancelada").count(),
    }
    upcoming = Appointment.query.filter(Appointment.slot != None).order_by(Appointment.slot).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, upcoming=upcoming)


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    if request.method == "POST":
        appearance = {"theme", "c_accent", "c_bg", "c_text", "c_title"}
        for k in list(DEFAULT_SETTINGS.keys()):
            if k in appearance:
                continue
            if k == "use_cookies":
                set_setting(k, "1" if request.form.get(k) else "0")
            else:
                set_setting(k, request.form.get(k, ""))
        # apariencia
        set_setting("theme", request.form.get("theme", "dark"))
        for ck in ("c_accent", "c_bg", "c_text", "c_title"):
            set_setting(ck, request.form.get(ck, "") if request.form.get("use_" + ck) else "")
        db.session.commit()
        flash("Ajustes guardados.", "ok")
        return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html")


@app.route("/admin/sections", methods=["GET", "POST"])
@login_required
def admin_sections():
    if request.method == "POST":
        for s in Section.query.all():
            s.visible = bool(request.form.get(f"vis_{s.slug}"))
            try:
                s.order = int(request.form.get(f"ord_{s.slug}", s.order))
            except ValueError:
                pass
        db.session.commit()
        flash("Apartados actualizados.", "ok")
        return redirect(url_for("admin_sections"))
    secs = Section.query.order_by(Section.order).all()
    return render_template("admin/sections.html", secs=secs)


# ---- subida de imágenes (usada por marcas/modelos/ocasión) ----
@app.route("/admin/upload", methods=["POST"])
@login_required
def admin_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "sin archivo"}), 400
    name = f"{secrets.token_hex(8)}_{secure_filename(f.filename)}"
    f.save(os.path.join(UPLOAD_DIR, name))
    return jsonify({"url": url_for("static", filename=f"img/uploads/{name}")})


# ---- Marcas / proveedores ----
@app.route("/admin/brands", methods=["GET", "POST"])
@login_required
def admin_brands():
    if request.method == "POST":
        bid = request.form.get("id")
        b = db.session.get(Brand, int(bid)) if bid else Brand()
        b.name = request.form.get("name", "")
        b.logo_url = request.form.get("logo_url", "")
        b.website = request.form.get("website", "")
        b.visible = bool(request.form.get("visible"))
        b.order = int(request.form.get("order") or 0)
        db.session.add(b)
        db.session.commit()
        flash("Marca guardada.", "ok")
        return redirect(url_for("admin_brands"))
    brands = Brand.query.order_by(Brand.order).all()
    return render_template("admin/brands.html", brands=brands)


@app.route("/admin/brands/<int:bid>/delete", methods=["POST"])
@login_required
def admin_brand_delete(bid):
    b = db.session.get(Brand, bid)
    if b:
        db.session.delete(b)
        db.session.commit()
        flash("Marca eliminada.", "ok")
    return redirect(url_for("admin_brands"))


# ---- Modelos nuevos ----
@app.route("/admin/models", methods=["GET", "POST"])
@login_required
def admin_models():
    if request.method == "POST":
        mid = request.form.get("id")
        m = db.session.get(NewModel, int(mid)) if mid else NewModel()
        for f in ("brand", "name", "cc", "price", "description", "image_url", "official_url"):
            setattr(m, f, request.form.get(f, ""))
        m.visible = bool(request.form.get("visible"))
        m.order = int(request.form.get("order") or 0)
        db.session.add(m)
        db.session.commit()
        flash("Modelo guardado.", "ok")
        return redirect(url_for("admin_models"))
    models = NewModel.query.order_by(NewModel.order).all()
    brands = Brand.query.order_by(Brand.order).all()
    return render_template("admin/models.html", models=models, brands=brands)


@app.route("/admin/models/<int:mid>/delete", methods=["POST"])
@login_required
def admin_model_delete(mid):
    m = db.session.get(NewModel, mid)
    if m:
        db.session.delete(m)
        db.session.commit()
        flash("Modelo eliminado.", "ok")
    return redirect(url_for("admin_models"))


# ---- Ocasión ----
@app.route("/admin/used", methods=["GET", "POST"])
@login_required
def admin_used():
    if request.method == "POST":
        uid = request.form.get("id")
        u = db.session.get(UsedBike, int(uid)) if uid else UsedBike()
        for f in ("title", "brand", "year", "km", "cc", "price", "description", "images"):
            setattr(u, f, request.form.get(f, ""))
        u.sold = bool(request.form.get("sold"))
        u.visible = bool(request.form.get("visible"))
        db.session.add(u)
        db.session.commit()
        flash("Moto de ocasión guardada.", "ok")
        return redirect(url_for("admin_used"))
    bikes = UsedBike.query.order_by(UsedBike.created.desc()).all()
    return render_template("admin/used.html", bikes=bikes)


@app.route("/admin/used/<int:uid>/delete", methods=["POST"])
@login_required
def admin_used_delete(uid):
    u = db.session.get(UsedBike, uid)
    if u:
        db.session.delete(u)
        db.session.commit()
        flash("Moto eliminada.", "ok")
    return redirect(url_for("admin_used"))


# ---- Citas ----
@app.route("/admin/appointments")
@login_required
def admin_appointments():
    cleanup_expired()
    appts = Appointment.query.order_by(Appointment.created.desc()).all()
    return render_template("admin/appointments.html", appts=appts)


@app.route("/admin/appointments/<int:aid>", methods=["POST"])
@login_required
def admin_appt_update(aid):
    a = db.session.get(Appointment, aid)
    if not a:
        abort(404)
    action = request.form.get("action")
    back = request.form.get("back", "")
    dest = redirect(back) if back else redirect(url_for("admin_appointments"))
    event = "actualizada"
    if action == "status":
        a.status = request.form.get("status", a.status)
        if a.status == "completada":
            event = "completada"
    elif action == "complete":
        a.status = "completada"
        event = "completada"
        action = "status"  # para que se notifique abajo
    elif action == "slot":
        try:
            a.slot = datetime.strptime(request.form.get("slot"), "%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            flash("Fecha no válida.", "error")
    elif action == "delete":
        db.session.delete(a)
        db.session.commit()
        flash("Cita eliminada.", "ok")
        return dest
    db.session.commit()
    if action in ("status", "slot"):
        results = notifications.notify_client(a, get_settings(), event)
        sent = [c for c, ok, _ in results if ok]
        if event == "completada":
            # Tras avisar al cliente, se elimina todo el registro (datos incluidos).
            db.session.delete(a)
            db.session.commit()
            flash("Cita completada y datos eliminados." +
                  (" Aviso de recogida enviado por " + ", ".join(sent) + "." if sent else
                   " (Configura el email para avisar automáticamente al cliente.)"), "ok")
            return dest
    flash("Cita actualizada.", "ok")
    return dest


# ----------------------------- AGENDA -----------------------------
@app.route("/admin/agenda")
@login_required
def admin_agenda():
    cleanup_expired()
    sched = parse_schedule(get_settings()["schedule"])
    names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    rows = []
    for wd in range(7):
        tr = sched.get(wd, [])
        def hm(i, j):
            try:
                return tr[i][j].strftime("%H:%M")
            except IndexError:
                return ""
        rows.append({"wd": wd, "name": names[wd], "closed": len(tr) == 0,
                     "t1s": hm(0, 0), "t1e": hm(0, 1), "t2s": hm(1, 0), "t2e": hm(1, 1)})
    return render_template("admin/agenda.html", sched_rows=rows)


@app.route("/admin/api/availability")
@login_required
def admin_api_availability():
    try:
        y = int(request.args.get("year")); m = int(request.args.get("month"))
    except (TypeError, ValueError):
        t = date.today(); y, m = t.year, t.month
    return jsonify({"year": y, "month": m, "days": month_availability(y, m, private=True)})


@app.route("/admin/api/day")
@login_required
def admin_api_day():
    try:
        day = datetime.strptime(request.args.get("date"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify({"slots": [], "summary": []})
    slots = day_slots(day, private=True)
    summary = sorted(
        [s for s in slots if s["status"] in ("booked", "blocked")],
        key=lambda s: s["t"])
    return jsonify({"date": request.args.get("date"), "slots": slots, "summary": summary})


@app.route("/admin/agenda/block", methods=["POST"])
@login_required
def admin_block():
    d = request.form.get("date"); t = request.form.get("time")
    reason = request.form.get("reason", "").strip()
    try:
        slot = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        flash("Franja no válida.", "error")
        return redirect(url_for("admin_agenda"))
    if not db.session.query(Block).filter_by(slot=slot).first():
        db.session.add(Block(slot=slot, reason=reason))
        db.session.commit()
        flash(f"Franja {t} del {d} bloqueada.", "ok")
    return redirect(url_for("admin_agenda") + f"?d={d}")


@app.route("/admin/agenda/unblock", methods=["POST"])
@login_required
def admin_unblock():
    b = db.session.get(Block, int(request.form.get("block_id")))
    d = request.form.get("date", "")
    if b:
        db.session.delete(b); db.session.commit()
        flash("Franja desbloqueada.", "ok")
    return redirect(url_for("admin_agenda") + (f"?d={d}" if d else ""))


@app.route("/admin/agenda/add", methods=["POST"])
@login_required
def admin_add_appt():
    d = request.form.get("date"); t = request.form.get("time")
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    subject = request.form.get("subject", "").strip()
    try:
        slot = datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        flash("Franja no válida.", "error"); return redirect(url_for("admin_agenda"))
    if not name:
        flash("Indica el nombre del cliente.", "error")
        return redirect(url_for("admin_agenda") + f"?d={d}")
    if t not in free_slots(slot.date()):
        flash("Esa franja ya no está libre.", "error")
        return redirect(url_for("admin_agenda") + f"?d={d}")
    code = gen_code()
    while Appointment.query.filter_by(code=code).first():
        code = gen_code()
    a = Appointment(code=code, kind="mantenimiento", slot=slot, subject=subject,
                    status="confirmada", notes="Alta manual (admin)")
    a.name, a.phone, a.email = name, phone, email
    db.session.add(a); db.session.commit()
    notifications.notify_client(a, get_settings(), "creada")
    flash(f"Cita {code} creada para {name}.", "ok")
    return redirect(url_for("admin_agenda") + f"?d={d}")


@app.route("/admin/schedule", methods=["POST"])
@login_required
def admin_schedule():
    """Guarda el horario de citas a partir del editor por día (2 tramos)."""
    lines = []
    for wd in range(7):
        if request.form.get(f"closed_{wd}"):
            continue
        tramos = []
        for n in (1, 2):
            a = request.form.get(f"d{wd}_{n}_start", "").strip()
            b = request.form.get(f"d{wd}_{n}_end", "").strip()
            if a and b:
                tramos.append(f"{a}-{b}")
        if tramos:
            lines.append(f"{wd}=" + ",".join(tramos))
    set_setting("schedule", "\n".join(lines))
    db.session.commit()
    flash("Horario de citas guardado.", "ok")
    return redirect(url_for("admin_agenda"))


# ==================================================================
def init_db():
    with app.app_context():
        db.create_all()
        # migración suave (solo SQLite): añadir columnas nuevas si la BD es antigua
        if db.engine.url.get_backend_name() == "sqlite":
            try:
                cols = [r[1] for r in db.session.execute(
                    db.text("PRAGMA table_info(new_model)")).fetchall()]
                if cols and "official_url" not in cols:
                    db.session.execute(db.text(
                        "ALTER TABLE new_model ADD COLUMN official_url VARCHAR(300) DEFAULT ''"))
                    db.session.commit()
            except Exception:
                db.session.rollback()
        # quitar el apartado público "modelos" (integrado en marcas)
        old = db.session.get(Section, "modelos")
        if old:
            db.session.delete(old)
            db.session.commit()
        # secciones por defecto
        if not Section.query.first():
            for slug, label, order in DEFAULT_SECTIONS:
                db.session.add(Section(slug=slug, label=label, order=order, visible=True))
            db.session.commit()


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
