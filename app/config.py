"""Configuración centralizada leída de variables de entorno (.env)."""
import os


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# Captura
CAPTURE_INTERVAL_SECONDS = _float("CAPTURE_INTERVAL_SECONDS", 3)
JPEG_QUALITY = _float("JPEG_QUALITY", 0.6)

# Movimiento
MOTION_THRESHOLD = _int("MOTION_THRESHOLD", 25)
MOTION_MIN_RATIO = _float("MOTION_MIN_RATIO", 0.02)

# IA
AI_ENABLED = _bool("AI_ENABLED", False)
# La IA solo se llama si el cambio de escena supera este umbral (etapa 2).
# Suele ser >= MOTION_MIN_RATIO: detectas movimiento barato y solo interpretas
# con IA los cambios relevantes. Ej: 0.05 = solo si cambia >5% de la imagen.
AI_MIN_RATIO = _float("AI_MIN_RATIO", 0.05)
# Límite de tokens de la descripción: menos tokens = respuesta mucho más rápida.
AI_MAX_TOKENS = _int("AI_MAX_TOKENS", 40)
# Reducimos la imagen antes de enviarla al modelo (más rápido, misma utilidad).
AI_IMAGE_MAX_PX = _int("AI_IMAGE_MAX_PX", 512)
# Mantener el modelo cargado en memoria entre llamadas (evita recargas lentas).
AI_KEEP_ALIVE = os.getenv("AI_KEEP_ALIVE", "10m")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "moondream")
AI_PROMPT = os.getenv(
    "AI_PROMPT",
    "Describe brevemente qué se ve en esta imagen de una cámara de seguridad.",
)
ALERT_KEYWORDS = [
    k.strip().lower() for k in os.getenv("ALERT_KEYWORDS", "").split(",") if k.strip()
]

# Notificaciones: qué canales usar (solo se activan si tienen credenciales).
NOTIFY_CHANNELS = [
    c.strip().lower() for c in os.getenv("NOTIFY_CHANNELS", "telegram,email").split(",") if c.strip()
]

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Email
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = _int("SMTP_PORT", 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", ""))
EMAIL_TO = os.getenv("EMAIL_TO", "")
NOTIFY_COOLDOWN_SECONDS = _int("NOTIFY_COOLDOWN_SECONDS", 120)
# Cooldown independiente para el mensaje de interpretación de la IA, para que no
# lo bloquee el cooldown de la alerta base (van por separado).
AI_NOTIFY_COOLDOWN_SECONDS = _int("AI_NOTIFY_COOLDOWN_SECONDS", 120)

# Almacenamiento
DATA_DIR = os.getenv("DATA_DIR", "/data")
RETENTION_DAYS = _int("RETENTION_DAYS", 7)
