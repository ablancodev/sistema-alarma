"""Detección de movimiento barata con OpenCV.

Dos modos combinados:
- frame-a-frame: compara con la última imagen recibida.
- baseline: compara con una escena de referencia fija (opcional).

Mantiene estado en memoria; suficiente para una cámara. Si en el futuro hay
varias cámaras, habría que indexar el estado por cámara.
"""
import threading

import cv2
import numpy as np

import config

_lock = threading.Lock()

# Estado POR cámara: {camera: {"prev": gray, "baseline": gray, "capture": bool}}
# Cada móvil/cámara compara contra sus propias referencias.
_state: dict[str, dict] = {}

# Tamaño FIJO de proceso: así todos los frames son comparables aunque el móvil
# cambie de resolución u orientación entre fotos (si no, cv2.absdiff peta).
_PROC_WIDTH = 320
_PROC_HEIGHT = 240


def _cam_state(camera: str) -> dict:
    return _state.setdefault(camera, {"prev": None, "baseline": None, "capture": False})


def _to_gray(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    img = cv2.resize(img, (_PROC_WIDTH, _PROC_HEIGHT))
    return cv2.GaussianBlur(img, (21, 21), 0)


def request_baseline(camera: str = "default") -> None:
    """La próxima imagen de esa cámara se usará como escena de referencia."""
    with _lock:
        _cam_state(camera)["capture"] = True


def _changed_ratio(a, b) -> float:
    delta = cv2.absdiff(a, b)
    _, thresh = cv2.threshold(delta, config.MOTION_THRESHOLD, 255, cv2.THRESH_BINARY)
    return float(np.count_nonzero(thresh)) / thresh.size


def process(image_bytes: bytes, camera: str = "default") -> dict:
    """Devuelve {motion: bool, score: float, baseline_set: bool} para esa cámara."""
    gray = _to_gray(image_bytes)
    if gray is None:
        return {"motion": False, "score": 0.0, "error": "imagen ilegible"}

    with _lock:
        st = _cam_state(camera)
        baseline_set = False
        if st["capture"]:
            st["baseline"] = gray
            st["capture"] = False
            baseline_set = True

        score = 0.0
        if st["prev"] is not None:
            score = max(score, _changed_ratio(st["prev"], gray))
        if st["baseline"] is not None:
            score = max(score, _changed_ratio(st["baseline"], gray))

        st["prev"] = gray
        # El primer frame no tiene con qué compararse → sin movimiento.
        motion = score >= config.MOTION_MIN_RATIO

    return {"motion": bool(motion), "score": round(score, 4), "baseline_set": baseline_set}
