"""Interpretación de la escena con Ollama (modelo de visión local).

Solo se usa cuando AI_ENABLED=true. Si falla (Ollama caído, timeout), devuelve
None y el pipeline degrada a "movimiento detectado" sin descripción.
"""
import base64
import io

import httpx
from PIL import Image

import config


def _shrink(image_bytes: bytes) -> bytes:
    """Reduce la imagen antes de mandarla al modelo (más rápido)."""
    try:
        im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        im.thumbnail((config.AI_IMAGE_MAX_PX, config.AI_IMAGE_MAX_PX))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=70)
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - si falla, usamos la original
        return image_bytes


async def describe(image_bytes: bytes) -> str | None:
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": config.AI_PROMPT,
        "images": [base64.b64encode(_shrink(image_bytes)).decode("ascii")],
        "stream": False,
        "keep_alive": config.AI_KEEP_ALIVE,
        "options": {"num_predict": config.AI_MAX_TOKENS},
    }
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(f"{config.OLLAMA_URL}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = (data.get("response") or "").strip()
            return text or None
    except Exception as exc:  # noqa: BLE001 - degradamos con gracia
        print(f"[vision] Ollama no disponible: {exc}")
        return None


def should_alert(description: str | None) -> bool:
    """Filtro por palabras clave. Sin keywords configuradas → siempre alerta."""
    if not config.ALERT_KEYWORDS:
        return True
    if not description:
        return True  # si la IA falló, mejor avisar que callar
    low = description.lower()
    return any(k in low for k in config.ALERT_KEYWORDS)
