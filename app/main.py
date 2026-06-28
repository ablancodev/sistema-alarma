"""API del sistema de vigilancia.

Pipeline de /upload:
  1. recibir foto
  2. detectar movimiento (OpenCV)
  3. si hay movimiento:
       - si AI_ENABLED → describir con Ollama y filtrar por keywords
       - si no         → "Movimiento detectado"
       - guardar imagen + evento
       - enviar email (respetando cooldown)
"""
import asyncio
import re
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import config
import motion
import notify
import store
import vision


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init()
    store.cleanup()
    print(f"[main] Iniciado. IA={'ON' if config.AI_ENABLED else 'OFF'} "
          f"modelo={config.OLLAMA_MODEL if config.AI_ENABLED else '-'}")
    yield


app = FastAPI(title="Sistema de vigilancia", lifespan=lifespan)


def _clean_camera(name: str | None) -> str:
    """Normaliza el nombre de cámara a algo seguro para BD/ficheros/cooldowns."""
    name = (name or "").strip().lower()
    name = re.sub(r"[^a-z0-9_-]+", "-", name).strip("-")
    return name[:32] or "default"


@app.get("/health")
async def health():
    return {"ok": True, "ai_enabled": config.AI_ENABLED}


@app.get("/config")
async def client_config():
    """Parámetros que necesita la PWA del móvil."""
    return {
        "capture_interval_seconds": config.CAPTURE_INTERVAL_SECONDS,
        "jpeg_quality": config.JPEG_QUALITY,
        "ai_enabled": config.AI_ENABLED,
    }


@app.post("/baseline")
async def set_baseline(camera: str = "default"):
    cam = _clean_camera(camera)
    motion.request_baseline(cam)
    return {"ok": True, "camera": cam,
            "message": f"La próxima foto de '{cam}' fijará la escena de referencia."}


@app.get("/events")
async def events(limit: int = 50, camera: str | None = None):
    return store.recent(limit, _clean_camera(camera) if camera else None)


# Mantenemos referencia a las tareas en segundo plano para que no se recolecten.
_bg_tasks: set = set()


async def _handle_motion(image_bytes: bytes, score: float, camera: str) -> None:
    """Etapa 2 (en segundo plano): alerta base + IA opcional + guardado.

    Dos alertas independientes, con cooldown propio cada una y POR cámara
    (kind = "<cámara>:motion" / "<cámara>:ai"), para que una zona no silencie
    a otra:
      1. "motion": se manda YA al detectar movimiento (sin esperar a la IA).
      2. "ai": cuando el cambio supera AI_MIN_RATIO, la IA interpreta la escena
         y se manda un segundo mensaje con la descripción.
    """
    image_path = await asyncio.to_thread(store.save_image, image_bytes, camera)
    filename = image_path.split("/")[-1]
    when = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = camera.upper()

    # 1) Alerta base, inmediata.
    base_body = f"Movimiento detectado a las {when}.\nCambio en escena: {score * 100:.1f}%"
    base_res = await asyncio.to_thread(
        notify.alert, f"🔔 Movimiento en {label}", base_body, image_bytes, filename,
        f"{camera}:motion", config.NOTIFY_COOLDOWN_SECONDS,
    )

    # 2) Interpretación IA (si procede), como segundo mensaje con su propio cooldown.
    use_ai = config.AI_ENABLED and score >= config.AI_MIN_RATIO
    description = await vision.describe(image_bytes) if use_ai else None
    if description and vision.should_alert(description):
        ai_body = f"🧠 La IA interpreta ({label}):\n{description}\n\n(cambio {score * 100:.1f}%, {when})"
        await asyncio.to_thread(
            notify.alert, f"🧠 Interpretación IA · {label}", ai_body, image_bytes, filename,
            f"{camera}:ai", config.AI_NOTIFY_COOLDOWN_SECONDS,
        )

    alerted = bool(base_res.get("sent"))
    await asyncio.to_thread(store.record, camera, score, use_ai, description, image_path, alerted)


@app.post("/upload")
async def upload(file: UploadFile = File(...), camera: str = Form("default")):
    image_bytes = await file.read()
    if not image_bytes:
        return JSONResponse({"error": "imagen vacía"}, status_code=400)

    cam = _clean_camera(camera)
    result = motion.process(image_bytes, cam)

    if not result.get("motion"):
        return {"status": "idle", "camera": cam, "score": result.get("score", 0.0),
                "baseline_set": result.get("baseline_set", False)}

    # --- Etapa 1: hay movimiento → responde YA y procesa el resto en segundo plano.
    task = asyncio.create_task(_handle_motion(image_bytes, result["score"], cam))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    will_use_ai = config.AI_ENABLED and result["score"] >= config.AI_MIN_RATIO
    return {
        "status": "motion",
        "camera": cam,
        "score": result["score"],
        "ai": "processing" if will_use_ai else "skipped",
    }


# La PWA se sirve en la raíz (debe ir al final para no tapar las rutas de la API).
app.mount("/", StaticFiles(directory="static", html=True), name="static")
