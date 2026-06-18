# Despliegue en cPanel (con acceso SSH)

Guía para publicar la web en tu hosting cPanel usando **Setup Python App** (Passenger).
El SSH lo usamos para instalar dependencias y crear la configuración.

> Si tu plan NO tiene "Setup Python App", al final tienes la alternativa para VPS con root.

## 1. Subir los archivos
Sube el contenido de la carpeta `motos-kike` a una carpeta de tu hosting, por ejemplo
`~/motoskike` (puedes usar el Administrador de archivos de cPanel o `scp`/`git`).

## 2. Crear la aplicación Python en cPanel
En cPanel → **Setup Python App** → **Create Application**:
- **Python version:** 3.10 o superior.
- **Application root:** `motoskike` (la carpeta donde subiste los archivos).
- **Application URL:** tu dominio (p. ej. `motoskike.es`).
- **Application startup file:** `passenger_wsgi.py`
- **Application Entry point:** `application`

Crea la aplicación. cPanel te creará un **entorno virtual** y te mostrará, arriba,
el comando para activarlo por SSH (algo como
`source /home/USUARIO/virtualenv/motoskike/3.10/bin/activate`).

## 3. Instalar dependencias y configurar (por SSH)
```bash
# 1) activa el entorno virtual (copia el comando exacto que muestra cPanel)
source /home/USUARIO/virtualenv/motoskike/3.10/bin/activate
cd ~/motoskike

# 2) instala dependencias
pip install -r requirements.txt

# 3) genera el .env (claves seguras) y la base de datos
python setup.py

# 4) cambia la contraseña del administrador
python setup.py --password TU_CONTRASEÑA_SEGURA
```

> ⚠️ Importante: ejecuta `python setup.py` **una sola vez**. Regenerar el `.env`
> cambiaría la clave AES y dejaría ilegibles los datos ya guardados. Haz una copia
> de seguridad del `.env` (contiene `AES_KEY` y `SECRET_KEY`).

## 4. Configurar el email
Edita `~/motoskike/.env` y rellena `SMTP_PASSWORD` (los demás datos de
`info@motoskike.es` ya vienen puestos). Prueba el envío:
```bash
python test_email.py tu_correo@ejemplo.com
```

## 5. Reiniciar la aplicación
En cPanel → Setup Python App → botón **Restart**. (O por SSH: `touch tmp/restart.txt`
dentro de la carpeta de la app.)

Visita tu dominio. El panel de administración está en `/admin`.

## 6. HTTPS (candado)
En cPanel → **SSL/TLS Status** → activa **AutoSSL** para tu dominio. Es gratis y
automático (Let's Encrypt).

## 7. (Opcional) Limpieza diaria garantizada
La web borra/anonimiza los datos de las citas al cargar cualquier página, así que con
tráfico normal ya se ejecuta. Si quieres asegurarlo aunque no haya visitas, crea un
**Cron Job** en cPanel (1 vez al día) que visite la web:
```
curl -s https://motoskike.es/ > /dev/null
```

---

## Comprobaciones rápidas si algo falla
- **Error 500 / página en blanco:** revisa `stderr.log` en la carpeta de la app, o el
  log de errores de cPanel. Casi siempre es una dependencia sin instalar (repite el paso 3)
  o el `.env` sin crear.
- **No se ven imágenes/CSS:** confirma que la carpeta `static/` se subió completa.
- **El email no sale:** ejecuta `python test_email.py` y mira el error exacto (host,
  puerto o contraseña). Prueba 465/SSL y, si no, 587/STARTTLS.

---

## Alternativa: VPS con acceso root (Gunicorn + Nginx)
Solo si en vez de hosting compartido tienes un servidor propio:
```bash
pip install gunicorn
python setup.py
gunicorn -w 3 -b 127.0.0.1:8000 passenger_wsgi:application   # o app:app
```
Luego Nginx como proxy inverso al puerto 8000 y Certbot para el HTTPS. Si vas por aquí,
dímelo y te paso el archivo de servicio systemd y la config de Nginx completos.
