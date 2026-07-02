import os
import json
import time
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, init_db, engine, SessionLocal
from . import crud, schemas
from .ha_client import ha

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Home Stock", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

SENSOR_INTERVAL_SECONDS = 60


@app.on_event("startup")
def on_startup():
    init_db()
    _run_migrations()
    if ha.available:
        threading.Thread(target=_sensor_loop, daemon=True).start()
        logger.info("HA Core API available — sensor push loop started")
    else:
        logger.info("HA Core API not available — running standalone (no sensors/to-do sync)")
    logger.info("Home Stock started - database initialized")


def _run_migrations():
    """Apply incremental schema changes CREATE TABLE cannot handle.
    Each runs in its own try/except; a benign failure (column exists) is skipped."""
    migrations: List[str] = [
        # future-proofing lives here; add ALTER TABLE ... ADD COLUMN statements as the schema grows
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info("Migration applied: %s", sql)
            except Exception:
                conn.rollback()


# ──────────────── Sensor push (background) ────────────────

def push_sensors(db: Session):
    """Publish stock summary sensors to Home Assistant via the Core API."""
    settings = crud.get_or_create_settings(db)
    if not settings.expose_sensors or not ha.available:
        return
    prefix = settings.sensor_prefix or "home_stock"
    dash = crud.dashboard(db)
    low_items = crud.shopping_list(db)
    low_names = [i.name for i in low_items]
    out_names = [i.name for i in low_items if i.quantity == 0]
    try:
        ha.set_state(f"sensor.{prefix}_shopping_count", dash["low_count"], {
            "friendly_name": "Boodschappenlijst",
            "unit_of_measurement": "items",
            "icon": "mdi:cart",
            "items": low_names,
        })
        ha.set_state(f"sensor.{prefix}_out_of_stock", dash["out_count"], {
            "friendly_name": "Op voorraad (uitverkocht)",
            "unit_of_measurement": "items",
            "icon": "mdi:alert-circle-outline",
            "items": out_names,
        })
        ha.set_state(f"sensor.{prefix}_total_items", dash["total_items"], {
            "friendly_name": "Totaal producten",
            "unit_of_measurement": "items",
            "icon": "mdi:fridge-outline",
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("Sensor push failed: %s", e)


def perform_sync(db: Session) -> dict:
    """Push the current shopping list into the configured HA to-do list.
    Skips items already present (when the list supports get_items)."""
    settings = crud.get_or_create_settings(db)
    entity_id = settings.todo_entity_id or "todo.shopping_list"
    items = crud.shopping_list(db)

    existing = ha.get_todo_items(entity_id)  # None => dedupe unsupported
    existing_set = set(existing) if existing else set()

    synced, skipped, errors = 0, 0, []
    for it in items:
        if it.name in existing_set:
            skipped += 1
            continue
        try:
            ha.call_service("todo", "add_item", {"entity_id": entity_id, "item": it.name})
            synced += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"{it.name}: {e}")
    return {"synced": synced, "skipped": skipped, "total": len(items),
            "entity_id": entity_id, "errors": errors}


def _after_change_async():
    """Fire-and-forget refresh after a mutation: push sensors and, when the
    household enabled it, auto-sync the shopping list to HA. Non-blocking."""
    if not ha.available:
        return

    def _worker():
        db = SessionLocal()
        try:
            settings = crud.get_or_create_settings(db)
            push_sensors(db)
            if settings.auto_sync_todo:
                perform_sync(db)
        except Exception as e:  # noqa: BLE001
            logger.warning("async post-change refresh failed: %s", e)
        finally:
            db.close()

    threading.Thread(target=_worker, daemon=True).start()


def _sensor_loop():
    while True:
        db = SessionLocal()
        try:
            push_sensors(db)
        except Exception as e:  # noqa: BLE001
            logger.warning("sensor loop error: %s", e)
        finally:
            db.close()
        time.sleep(SENSOR_INTERVAL_SECONDS)


# ──────────────── Server Time ────────────────

@app.get("/api/server-time")
def get_server_time():
    now_local = datetime.now()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    offset_seconds = int((now_local - now_utc).total_seconds())
    return {
        "utc_offset_minutes": offset_seconds // 60,
        "local_time": now_local.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ──────────────── Config ────────────────

@app.get("/api/config")
def get_config():
    opts_path = "/data/options.json"
    defaults = {"language": "nl", "household_name": ""}
    if os.path.exists(opts_path):
        try:
            with open(opts_path) as f:
                return {**defaults, **json.load(f)}
        except Exception:
            pass
    return defaults


# ──────────────── Settings ────────────────

@app.get("/api/settings", response_model=schemas.SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return crud.get_or_create_settings(db)


@app.post("/api/settings", response_model=schemas.SettingsOut)
def save_settings(data: schemas.SettingsBase, db: Session = Depends(get_db)):
    settings = crud.update_settings(db, data)
    _after_change_async()
    return settings


# ──────────────── Items ────────────────

@app.get("/api/items", response_model=List[schemas.ItemOut])
def list_items(category: Optional[str] = None, low_only: bool = False, db: Session = Depends(get_db)):
    return crud.list_items(db, category=category, low_only=low_only)


@app.post("/api/items", response_model=schemas.ItemOut)
def add_item(data: schemas.ItemCreate, db: Session = Depends(get_db)):
    item = crud.add_item(db, data)
    _after_change_async()
    return item


@app.patch("/api/items/{item_id}", response_model=schemas.ItemOut)
def update_item(item_id: int, data: schemas.ItemUpdate, db: Session = Depends(get_db)):
    item = crud.update_item(db, item_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    _after_change_async()
    return item


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    if not crud.delete_item(db, item_id):
        raise HTTPException(status_code=404, detail="Not found")
    _after_change_async()
    return {"ok": True}


@app.post("/api/items/{item_id}/adjust", response_model=schemas.ItemOut)
def adjust_item(item_id: int, data: schemas.AdjustRequest, db: Session = Depends(get_db)):
    item = crud.adjust_quantity(db, item_id, data.delta)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    _after_change_async()
    return item


# ──────────────── Shopping list ────────────────

@app.get("/api/shopping-list", response_model=List[schemas.ItemOut])
def get_shopping_list(db: Session = Depends(get_db)):
    return crud.shopping_list(db)


@app.post("/api/shopping-list/sync")
def sync_shopping_list(db: Session = Depends(get_db)):
    """Push the current shopping list into the configured HA to-do list."""
    if not ha.available:
        raise HTTPException(status_code=503, detail="not_connected")
    return perform_sync(db)


# ──────────────── Home Assistant helpers ────────────────

@app.get("/api/ha/todo-lists")
def ha_todo_lists():
    if not ha.available:
        return {"available": False, "lists": []}
    try:
        return {"available": True, "lists": ha.get_todo_entities()}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "lists": [], "error": str(e)}


# ──────────────── Dashboard ────────────────

@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    return crud.dashboard(db)


# ──────────────── Static / Frontend (must be mounted last) ────────────────

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
