"""Envío de alertas por varios canales (Telegram y/o email).

- Telegram: instantáneo, simple (bot token + chat id), manda foto + texto.
- Email: SMTP clásico (opcional).

Cada canal solo se activa si tiene credenciales y está en NOTIFY_CHANNELS.
Local-first: si un canal falla (sin internet), su envío se encola y se
reintenta en la siguiente alerta. El cooldown evita saturar ante movimiento
continuo.
"""
import smtplib
import threading
import time
from email.message import EmailMessage

import httpx

import config

_lock = threading.Lock()
_last_sent: dict[str, float] = {}  # cooldown independiente por tipo de alerta (kind)
_queue: list[dict] = []  # items {subject, body, image_bytes, filename, pending:[canales]}


def _enabled_channels() -> list[str]:
    out = []
    if "telegram" in config.NOTIFY_CHANNELS and config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
        out.append("telegram")
    if "email" in config.NOTIFY_CHANNELS and config.SMTP_HOST and config.EMAIL_TO:
        out.append("email")
    return out


def _send_telegram(item: dict) -> None:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"{item['subject']}\n{item['body']}"[:1024]
    files = {"photo": (item["filename"], item["image_bytes"], "image/jpeg")}
    data = {"chat_id": config.TELEGRAM_CHAT_ID, "caption": caption}
    r = httpx.post(url, data=data, files=files, timeout=30)
    r.raise_for_status()


def _send_email(item: dict) -> None:
    msg = EmailMessage()
    msg["Subject"] = item["subject"]
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO
    msg.set_content(item["body"])
    if item["image_bytes"]:
        msg.add_attachment(item["image_bytes"], maintype="image", subtype="jpeg",
                           filename=item["filename"])
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
        server.starttls()
        if config.SMTP_USER:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)


_SENDERS = {"telegram": _send_telegram, "email": _send_email}


def _try_channels(item: dict) -> list[str]:
    """Intenta enviar por los canales pendientes del item. Devuelve los que fallaron."""
    failed = []
    for ch in list(item["pending"]):
        try:
            _SENDERS[ch](item)
            print(f"[notify] Enviado por {ch}")
        except Exception as exc:  # noqa: BLE001
            print(f"[notify] Falló {ch}: {exc}")
            failed.append(ch)
    return failed


def _flush_queue() -> None:
    """Reintenta los items encolados; conserva los canales que sigan fallando."""
    for item in list(_queue):
        item["pending"] = _try_channels(item)
        if not item["pending"]:
            _queue.remove(item)


def alert(subject: str, body: str, image_bytes: bytes, filename: str,
          kind: str = "motion", cooldown: int | None = None) -> dict:
    """Envía una alerta de un tipo (`kind`) con su propio cooldown.

    `kind` separa los cooldowns: p.ej. "motion" (alerta base) y "ai"
    (interpretación) no se bloquean entre sí.
    Devuelve {sent, channels, queued, skipped_cooldown}.
    """
    channels = _enabled_channels()
    if not channels:
        return {"sent": False, "reason": "ningún canal configurado"}

    cd = config.NOTIFY_COOLDOWN_SECONDS if cooldown is None else cooldown

    with _lock:
        now = time.time()
        if now - _last_sent.get(kind, 0.0) < cd:
            return {"sent": False, "skipped_cooldown": True, "kind": kind}
        _last_sent[kind] = now

        _flush_queue()  # primero intenta vaciar lo pendiente

        item = {"subject": subject, "body": body, "image_bytes": image_bytes,
                "filename": filename, "pending": channels}
        failed = _try_channels(item)
        if failed:
            item["pending"] = failed
            _queue.append(item)
            return {"sent": False, "channels": channels, "failed": failed, "queued": len(_queue)}
        return {"sent": True, "channels": channels, "queued": len(_queue)}
