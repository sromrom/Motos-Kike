# Motos Kike · Web (Flask)

Web + panel de administración para la tienda-taller **Motos Kike** (Calle Caraza 21,
Chiclana de la Frontera, Cádiz · 666475205).

## Puesta en marcha (local)

```bash
pip install -r requirements.txt
python setup.py                 # genera .env con claves seguras + datos de ejemplo
python app.py                   # arranca en http://127.0.0.1:5000
```

Admin por defecto: usuario `admin`, contraseña `admin1234`.
**Cámbiala enseguida:**

```bash
python setup.py --password TU_NUEVA_CLAVE
```

Panel de administración: `http://127.0.0.1:5000/admin`

## Qué hace (y qué necesita configuración)

| Función | Estado |
|---|---|
| Web pública moderna + responsive | ✅ Funciona |
| Marcas/proveedores, modelos, ocasión (CRUD admin) | ✅ Funciona |
| Mostrar/ocultar y ordenar apartados | ✅ Funciona |
| Todo el contenido editable desde el admin (contacto, RRSS, textos, SEO, horarios) | ✅ Funciona |
| Citas: pedir, ver, modificar, cancelar (cliente y admin) | ✅ Funciona |
| Huecos de 30 min para mantenimiento + cita de consulta | ✅ Funciona |
| Cifrado **AES-256-GCM** de datos personales | ✅ Funciona |
| Autoborrado de citas pasadas (RGPD) | ✅ Funciona |
| Calculadora de financiación | ✅ Funciona |
| Aviso de cookies + páginas legales | ✅ Funciona |
| SEO: meta tags, Open Graph, JSON-LD LocalBusiness, sitemap, robots | ✅ Funciona |
| Aviso de cita por **email (SMTP)** | ⚙️ Funciona al rellenar `SMTP_*` en `.env` |
| Aviso por **Telegram** | ⚙️ Necesita bot propio (`TELEGRAM_BOT_TOKEN`) y que el cliente escriba al bot |
| Aviso por **WhatsApp** | ⚙️ Requiere cuenta de pago (Twilio o WhatsApp Cloud API de Meta) |

> Las notificaciones por WhatsApp/Telegram **no están "simuladas"**: el código está
> listo, pero no enviarán nada hasta que pongas tus credenciales reales. WhatsApp a
> números de clientes exige sí o sí la API de WhatsApp Business (Twilio o Meta), que
> es de pago y requiere aprobación. Es una limitación de WhatsApp, no del código.

## Configurar el email de avisos (info@motoskike.es)

Los avisos al cliente (confirmación de cita y "tu moto está lista") salen por email
en cuanto rellenes los datos SMTP en el fichero `.env`.

1. Pide a tu proveedor de hosting los **datos SMTP de salida** de la cuenta
   `info@motoskike.es`. En cPanel/Plesk normalmente son:
   - **Servidor (host):** `mail.motoskike.es` (o el que te indiquen)
   - **Puerto:** `465` con SSL (recomendado) o `587` con STARTTLS
   - **Usuario:** `info@motoskike.es` (el email completo)
   - **Contraseña:** la de esa cuenta de correo
2. Edita `.env` y rellena `SMTP_PASSWORD` (el resto ya viene preconfigurado para
   `info@motoskike.es` en puerto 465/SSL; cámbialo si tu proveedor usa otros valores).
3. Comprueba que funciona:
   ```bash
   python test_email.py tu_correo_personal@ejemplo.com
   ```
   Debe imprimir `OK`. Si da error, te dirá el motivo exacto (host, puerto o
   credenciales) para que lo ajustes.

Nota: si el puerto es 465 pon `SMTP_PORT=465` y `SMTP_USE_SSL=true`; si es 587 pon
`SMTP_PORT=587`, `SMTP_USE_SSL=false` y `SMTP_USE_TLS=true`.

## Seguridad de datos

- Nombre, teléfono y email de las citas se guardan **cifrados** (AES-256-GCM) con la
  clave `AES_KEY` del `.env`. Si pierdes esa clave, los datos son irrecuperables: guárdala.
- Las citas se **borran solas** al pasar su fecha. Para forzar la limpieza periódica en
  producción puedes añadir un cron que haga una petición a la web, o se ejecuta sola en
  cada visita a la home/admin.

## Despliegue en producción (resumen)

No uses el servidor de desarrollo. Usa Gunicorn + Nginx:

```bash
pip install gunicorn
gunicorn -w 3 -b 127.0.0.1:8000 app:app
```

Pendiente para producción real: dominio + certificado HTTPS, servidor WSGI, y cambiar
la base de datos a PostgreSQL si el volumen crece (ahora usa SQLite, suficiente para empezar).

## Estructura

```
app.py            rutas (público + admin + API)
models.py         modelos de datos
crypto.py         cifrado AES-256
notifications.py  email / WhatsApp / Telegram
setup.py          generador de .env + datos de ejemplo
templates/        HTML (público y admin/)
static/           css, js, imágenes (logo y fotos de la tienda incluidas)
```
