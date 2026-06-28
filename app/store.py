"""Persistencia: imágenes de alertas en disco + eventos en SQLite."""
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import config

_lock = threading.Lock()
_db_path = os.path.join(config.DATA_DIR, "events.db")
_img_dir = os.path.join(config.DATA_DIR, "images")


def init() -> None:
    os.makedirs(_img_dir, exist_ok=True)
    with sqlite3.connect(_db_path) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                camera TEXT DEFAULT 'default',
                score REAL,
                ai_enabled INTEGER,
                description TEXT,
                image_path TEXT,
                alerted INTEGER
            )"""
        )
        # Migración: añadir 'camera' a bases de datos creadas antes del multi-cámara.
        cols = [r[1] for r in db.execute("PRAGMA table_info(events)")]
        if "camera" not in cols:
            db.execute("ALTER TABLE events ADD COLUMN camera TEXT DEFAULT 'default'")


def save_image(image_bytes: bytes, camera: str = "default") -> str:
    name = f"{camera}_{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jpg"
    path = os.path.join(_img_dir, name)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


def record(camera: str, score: float, ai_enabled: bool, description, image_path: str,
           alerted: bool) -> None:
    with _lock, sqlite3.connect(_db_path) as db:
        db.execute(
            "INSERT INTO events (ts, camera, score, ai_enabled, description, image_path, alerted)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                camera,
                score,
                int(ai_enabled),
                description,
                image_path,
                int(alerted),
            ),
        )


def recent(limit: int = 50, camera: str | None = None) -> list[dict]:
    with sqlite3.connect(_db_path) as db:
        db.row_factory = sqlite3.Row
        if camera:
            rows = db.execute(
                "SELECT * FROM events WHERE camera = ? ORDER BY id DESC LIMIT ?",
                (camera, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def cleanup() -> None:
    """Borra imágenes y eventos más antiguos que RETENTION_DAYS (0 = nunca)."""
    if config.RETENTION_DAYS <= 0:
        return
    cutoff = time.time() - config.RETENTION_DAYS * 86400
    for name in os.listdir(_img_dir):
        path = os.path.join(_img_dir, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass
    cutoff_iso = (datetime.now() - timedelta(days=config.RETENTION_DAYS)).isoformat()
    with _lock, sqlite3.connect(_db_path) as db:
        db.execute("DELETE FROM events WHERE ts < ?", (cutoff_iso,))
