"""Notificaciones al cliente.

- Email: FUNCIONAL vía SMTP (rellena las variables SMTP_* en .env).
- Telegram: funcional si configuras TELEGRAM_BOT_TOKEN; necesitas el chat_id del
  cliente (el cliente debe escribir antes al bot; es una limitación de Telegram).
- WhatsApp: requiere cuenta de pago (Twilio o WhatsApp Cloud API de Meta).

Ninguna función "miente": si falta configuración, devuelve (False, motivo) y
NO simula un envío correcto.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import requests


def send_email(to_addr: str, subject: str, body: str):
    host = os.environ.get("SMTP_HOST")
    if not host:
        return False, "SMTP no configurado"
    if not to_addr:
        return False, "Sin email de destino"
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = os.environ.get("SMTP_FROM", os.environ.get("SMTP_USER", ""))
        msg["To"] = to_addr
        port = int(os.environ.get("SMTP_PORT", 587))
        use_ssl = os.environ.get("SMTP_USE_SSL", "").lower() == "true" or port == 465
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=20)
        else:
            server = smtplib.SMTP(host, port, timeout=20)
            if os.environ.get("SMTP_USE_TLS", "true").lower() == "true":
                server.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            server.login(user, os.environ.get("SMTP_PASSWORD", ""))
        server.send_message(msg)
        server.quit()
        return True, "ok"
    except Exception as e:
        return False, f"Error SMTP: {e}"


def send_telegram(chat_id: str, body: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False, "Telegram no configurado"
    if not chat_id:
        return False, "Sin chat_id del cliente"
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": body}, timeout=15)
        return (r.ok, "ok" if r.ok else r.text)
    except Exception as e:
        return False, str(e)


def send_whatsapp(phone: str, body: str):
    """Twilio o WhatsApp Cloud API según lo que esté configurado."""
    if not phone:
        return False, "Sin teléfono"
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    wa_token = os.environ.get("WHATSAPP_TOKEN")
    if sid:
        try:
            tok = os.environ.get("TWILIO_AUTH_TOKEN", "")
            frm = os.environ.get("TWILIO_WHATSAPP_FROM", "")
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                data={"From": frm, "To": f"whatsapp:{phone}", "Body": body},
                auth=(sid, tok), timeout=15)
            return (r.ok, "ok" if r.ok else r.text)
        except Exception as e:
            return False, str(e)
    if wa_token:
        try:
            pid = os.environ.get("WHATSAPP_PHONE_ID", "")
            r = requests.post(
                f"https://graph.facebook.com/v20.0/{pid}/messages",
                headers={"Authorization": f"Bearer {wa_token}"},
                json={"messaging_product": "whatsapp", "to": phone,
                      "type": "text", "text": {"body": body}}, timeout=15)
            return (r.ok, "ok" if r.ok else r.text)
        except Exception as e:
            return False, str(e)
    return False, "WhatsApp no configurado"


def notify_client(appt, settings, event="creada"):
    """Notifica por los canales disponibles. Devuelve lista de (canal, ok, info)."""
    shop = settings.get("shop_name", "Motos Kike")
    phone = settings.get("phone", "")
    when = appt.slot.strftime("%d/%m/%Y a las %H:%M") if appt.slot else "(a concretar presencialmente)"

    if event == "completada":
        subject = f"{shop} · ¡Tu moto está lista!"
        body = (f"{shop}\n\n"
                f"¡Buenas noticias! Tu moto ya está lista para ser recogida.\n"
                f"Nº de cita: {appt.code}\n\n"
                f"Puedes pasar a recogerla en nuestro horario habitual"
                + (f". Si tienes cualquier duda, llámanos al {phone}." if phone else ".") +
                f"\n\nGracias por confiar en {shop}.")
    else:
        subject = f"{shop} · Tu cita {appt.code}"
        body = (f"{shop} - Cita {event}\n"
                f"Nº de cita: {appt.code}\n"
                f"Tipo: {appt.kind}\n"
                f"Fecha: {when}\n"
                f"Asunto: {appt.subject}\n\n"
                f"Puedes consultar, modificar o cancelar tu cita en la web con tu nº de cita.")

    results = []
    if appt.email:
        ok, info = send_email(appt.email, subject, body)
        results.append(("email", ok, info))
    if appt.phone:
        ok, info = send_whatsapp(appt.phone, body)
        results.append(("whatsapp", ok, info))
    return results
