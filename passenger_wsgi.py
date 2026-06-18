"""Punto de entrada para Passenger (cPanel "Setup Python App") y Plesk.

Passenger busca una variable llamada `application`. Aquí cargamos el .env,
inicializamos la base de datos (crea las tablas la primera vez) y exponemos la app.
NO ejecuta el servidor de desarrollo: en producción sirve Passenger/Apache.
"""
import os
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))

from app import app as application, init_db

init_db()
