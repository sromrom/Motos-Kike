# Despliegue en PythonAnywhere

Guía paso a paso para publicar la web. Pensada para hacerse desde el navegador,
sin instalar nada en tu ordenador.

## Resumen honesto antes de empezar
- **Cuenta gratuita:** la web funciona en `tuusuario.pythonanywhere.com` y los datos se
  conservan. Perfecta para verla en marcha y probarla.
- **Plan "Hacker" (~5 $/mes):** necesario para usar el dominio propio `motoskike.es`
  Y para que el email de avisos salga (la cuenta gratuita bloquea el correo saliente).

---

## 1. Crear la cuenta
1. Entra en https://www.pythonanywhere.com y crea una cuenta (Create a Beginner account).
2. Anota tu **nombre de usuario**: lo usarás en las rutas (lo llamaremos `USUARIO`).

## 2. Subir el proyecto
1. Pestaña **Files**.
2. Arriba a la derecha, **Upload a file** → sube el `motos-kike.zip`.
3. Abre una consola: pestaña **Consoles** → **Bash**.
4. En la consola:
   ```bash
   unzip motos-kike.zip
   ls motos-kike      # debes ver app.py, static, templates, etc.
   ```

## 3. Crear el entorno e instalar dependencias
En la misma consola Bash:
```bash
cd ~/motos-kike
mkvirtualenv --python=/usr/bin/python3.10 motoskike
pip install -r requirements.txt
python setup.py
python setup.py --password TU_CONTRASEÑA_SEGURA
```
> Ejecuta `setup.py` **una sola vez**. Guarda una copia del `.env` que se genera
> (contiene la clave AES; sin ella los datos cifrados de las citas son irrecuperables).

Anota la ruta del virtualenv que crea: `/home/USUARIO/.virtualenvs/motoskike`

## 4. Crear la aplicación web
1. Pestaña **Web** → **Add a new web app** → **Next**.
2. Elige **Manual configuration** (NO "Flask") → **Python 3.10** → **Next**.
3. Ya creada, en esa misma pestaña Web configura:
   - **Source code:** `/home/USUARIO/motos-kike`
   - **Working directory:** `/home/USUARIO/motos-kike`
   - **Virtualenv:** `/home/USUARIO/.virtualenvs/motoskike`

## 5. Editar el archivo WSGI
En la pestaña Web, sección "Code", pincha en el enlace del **WSGI configuration file**
(algo como `/var/www/USUARIO_pythonanywhere_com_wsgi.py`). **Borra todo** su contenido y
pega esto (cambia USUARIO por el tuyo):
```python
import os, sys

path = '/home/USUARIO/motos-kike'
if path not in sys.path:
    sys.path.insert(0, path)

from dotenv import load_dotenv
load_dotenv(os.path.join(path, '.env'))

from app import app as application, init_db
init_db()
```
Guarda (Save).

## 6. Servir los archivos estáticos (CSS, imágenes)
En la pestaña Web, sección **Static files**, añade una fila:
- **URL:** `/static/`
- **Directory:** `/home/USUARIO/motos-kike/static`

## 7. Arrancar
Pulsa el botón verde **Reload** (arriba en la pestaña Web). Visita
`https://USUARIO.pythonanywhere.com`. El panel de administración está en `/admin`.

---

## 8. Email (requiere plan de pago)
La cuenta gratuita NO deja enviar correo. Con el plan Hacker:
1. Edita `~/motos-kike/.env` (pestaña Files) y rellena `SMTP_PASSWORD` de
   `info@motoskike.es` (host/puerto ya vienen puestos para OVH; ajusta si hace falta).
2. En una consola Bash: `cd ~/motos-kike && workon motoskike && python test_email.py tu_correo@ejemplo.com`
3. Reload de la web.

> SMTP de OVH para `info@motoskike.es` suele ser: host `ssl0.ovh.net`, puerto 465 (SSL).
> Si `mail.motoskike.es` no funciona, prueba `ssl0.ovh.net`.

## 9. Dominio propio motoskike.es (requiere plan de pago)
1. En PythonAnywhere, pestaña **Web** → en "Add a new web app" o en el campo de dominio,
   indica `www.motoskike.es`. PythonAnywhere te dará un destino **CNAME**
   (algo como `webapp-XXXX.pythonanywhere.com`).
2. En **OVH** (donde tienes el dominio) → zona DNS de `motoskike.es`:
   - Crea/edita un registro **CNAME** para `www` apuntando a ese destino de PythonAnywhere.
   - Para el dominio "a secas" (sin www), en OVH usa la **redirección** de `motoskike.es`
     hacia `www.motoskike.es` (los DNS no permiten CNAME en el dominio raíz).
3. En PythonAnywhere activa el **HTTPS** (te lo gestiona automáticamente una vez el DNS
   apunta bien). Los cambios de DNS pueden tardar unas horas en propagarse.

> El correo `info@motoskike.es` sigue funcionando en OVH sin tocar nada: solo cambiamos a
> dónde apunta la **web**, no el correo. (Importante: no borres los registros MX de OVH).

---

## Si algo falla
- **Error / página de PythonAnywhere:** pestaña Web → enlace **Error log**. Casi siempre es
  el WSGI mal escrito (revisa USUARIO) o dependencias sin instalar.
- **Sin CSS/imágenes:** revisa el mapeo de Static files del paso 6.
- **Email no sale:** ejecuta `test_email.py` y mira el error; prueba host `ssl0.ovh.net` 465.
