# Despliegue en Render (gratis) + dominio y correo en OVH

La web se ejecuta en Render (gratis). El dominio `motoskike.es` y el correo
`info@motoskike.es` se quedan en OVH; solo apuntamos el dominio hacia Render.

## Importante (plan gratis de Render)
- **Se duerme** tras 15 min sin visitas → la primera carga tarda ~30-50 s. Lo arreglamos
  con un cron externo gratuito (paso 6).
- **Disco efímero** → por eso usamos **PostgreSQL** (persistente). Sin esto, perderías
  las citas y ajustes en cada redespliegue.

---

## 1. Base de datos PostgreSQL gratis (Neon)
Render borra sus bases de datos gratuitas a los pocos días, así que usamos **Neon**
(gratis y persistente):
1. Entra en https://neon.tech y crea una cuenta y un proyecto.
2. Copia la **connection string** (empieza por `postgresql://...` e incluye
   `?sslmode=require`). La usarás como `DATABASE_URL`.

## 2. Subir el código a GitHub
Render despliega desde un repositorio:
1. Crea una cuenta en https://github.com y un repositorio nuevo (privado vale).
2. Sube ahí el contenido de la carpeta `motos-kike` (puedes arrastrar los archivos en
   "Add file → Upload files", o usar GitHub Desktop).

## 3. Generar las claves
En tu ordenador (o en cualquier consola con Python):
```bash
python gen_keys.py TU_CONTRASEÑA_ADMIN
```
Copia los valores que imprime (`SECRET_KEY`, `AES_KEY`, `ADMIN_PASSWORD_HASH`).
**Guárdalos**: si cambias `AES_KEY` después, los datos cifrados serían irrecuperables.

## 4. Crear el servicio web en Render
1. Entra en https://render.com → **New** → **Web Service** → conecta tu repo de GitHub.
2. Configura:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn passenger_wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
   - **Plan:** Free
3. En **Environment** añade estas variables:
   | Clave | Valor |
   |---|---|
   | `SECRET_KEY` | (del paso 3) |
   | `AES_KEY` | (del paso 3) |
   | `ADMIN_USERNAME` | `admin` |
   | `ADMIN_PASSWORD_HASH` | (del paso 3) |
   | `DATABASE_URL` | (la de Neon, paso 1) |
   | `SMTP_HOST` | `ssl0.ovh.net` |
   | `SMTP_PORT` | `465` |
   | `SMTP_USE_SSL` | `true` |
   | `SMTP_USE_TLS` | `false` |
   | `SMTP_USER` | `info@motoskike.es` |
   | `SMTP_PASSWORD` | (la contraseña del correo) |
   | `SMTP_FROM` | `Motos Kike <info@motoskike.es>` |
4. **Create Web Service**. Render instala y arranca. Cuando termine, te da una URL tipo
   `https://motoskike.onrender.com`. Ábrela: la web debe funcionar. El admin en `/admin`.

> Las tablas se crean solas al arrancar. No hay que ejecutar nada más.

## 5. Email
Ya queda configurado con las variables SMTP de arriba. Para probarlo, en Render abre una
**Shell** (pestaña Shell del servicio) y ejecuta:
```bash
python test_email.py tu_correo@ejemplo.com
```
Debe decir `OK`. Si no, prueba `SMTP_HOST=mail.motoskike.es` o confirma la contraseña.

## 6. Cron para que no se duerma
Usa un pinger gratuito que visite la web cada pocos minutos:
1. Entra en https://cron-job.org (o UptimeRobot), crea una cuenta.
2. Crea un "cron job" que haga una petición **GET** a tu URL de Render
   (`https://motoskike.onrender.com/`) **cada 10 minutos**.
Eso la mantiene despierta y, de paso, dispara la limpieza diaria de datos.

## 7. Dominio motoskike.es (desde OVH)
1. En Render → tu servicio → **Settings → Custom Domains** → añade `www.motoskike.es`
   y `motoskike.es`. Render te indicará los registros DNS a crear.
2. En **OVH** (Web Cloud → tu dominio → **Zona DNS**):
   - Para `www`: crea un **CNAME** apuntando al destino que te da Render
     (algo como `motoskike.onrender.com.`).
   - Para el dominio raíz `motoskike.es`: añade el registro **A** con la IP que indique
     Render (o usa la redirección de OVH de `motoskike.es` → `www.motoskike.es`).
3. Render activa el **HTTPS** automáticamente cuando el DNS apunta bien (puede tardar
   unas horas en propagarse).

> El correo NO se toca: deja intactos los registros **MX** de OVH. Solo cambiamos los
> registros del sitio web (A/CNAME), no el correo.

---

## Si algo falla
- **Error al arrancar:** pestaña **Logs** del servicio en Render. Suele ser una variable
  de entorno sin poner (`AES_KEY`, `DATABASE_URL`) o la `DATABASE_URL` mal copiada.
- **Datos que desaparecen:** asegúrate de que `DATABASE_URL` (PostgreSQL) está puesta; si
  falta, usaría SQLite efímero y se borraría.
- **Email no sale:** `test_email.py` y prueba `ssl0.ovh.net` 465.
