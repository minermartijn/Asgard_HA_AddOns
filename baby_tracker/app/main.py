import os
import json
import logging
from datetime import datetime, date, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, init_db, engine
from . import crud, schemas, calculator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Baby Tracker", version="1.0.5")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


@app.on_event("startup")
def on_startup():
    init_db()
    # Schema migrations — safe to run on every startup (errors are silently ignored)
    _run_migrations()
    logger.info("Baby Tracker started - database initialized")


def _run_migrations():
    """Apply any incremental DB schema changes that CREATE TABLE cannot handle."""
    migrations = [
        "ALTER TABLE diaper_entries ADD COLUMN poop_color VARCHAR(20)",
    ]
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info("Migration applied: %s", sql)
            except Exception:
                # Column already exists or other benign error — skip
                conn.rollback()


# ──────────────── Server Time ────────────────

@app.get("/api/server-time")
def get_server_time():
    """Return the server's current local time and UTC offset.
    The frontend uses this to display times in the server's timezone,
    regardless of what timezone the user's browser reports."""
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
    defaults = {"language": "nl", "baby_name": "", "baby_birth_date": ""}
    if os.path.exists(opts_path):
        try:
            with open(opts_path) as f:
                return {**defaults, **json.load(f)}
        except Exception:
            pass
    return defaults


# ──────────────── Baby Profile ────────────────

@app.get("/api/baby", response_model=schemas.BabyOut)
def get_baby(db: Session = Depends(get_db)):
    return crud.get_or_create_baby(db)


@app.post("/api/baby", response_model=schemas.BabyOut)
def update_baby(data: schemas.BabyCreate, db: Session = Depends(get_db)):
    return crud.update_baby(db, data)


# ──────────────── Weight ────────────────

@app.get("/api/weights", response_model=List[schemas.WeightOut])
def list_weights(limit: int = 30, db: Session = Depends(get_db)):
    return crud.get_weights(db, limit=limit)


@app.post("/api/weights", response_model=schemas.WeightOut)
def add_weight(data: schemas.WeightCreate, db: Session = Depends(get_db)):
    return crud.create_weight(db, data)


@app.delete("/api/weights/{entry_id}")
def delete_weight(entry_id: int, db: Session = Depends(get_db)):
    if not crud.delete_weight(db, entry_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ──────────────── Feedings ────────────────

@app.get("/api/feedings", response_model=List[schemas.FeedingOut])
def list_feedings(day: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    d = None
    if day:
        try:
            d = date.fromisoformat(day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")
    return crud.get_feedings(db, day=d, limit=limit)


@app.post("/api/feedings", response_model=schemas.FeedingOut)
def add_feeding(data: schemas.FeedingCreate, db: Session = Depends(get_db)):
    return crud.create_feeding(db, data)


@app.delete("/api/feedings/{entry_id}")
def delete_feeding(entry_id: int, db: Session = Depends(get_db)):
    if not crud.delete_feeding(db, entry_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ──────────────── Diapers ────────────────

@app.get("/api/diapers", response_model=List[schemas.DiaperOut])
def list_diapers(day: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    d = None
    if day:
        try:
            d = date.fromisoformat(day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format (YYYY-MM-DD)")
    return crud.get_diapers(db, day=d, limit=limit)


@app.post("/api/diapers", response_model=schemas.DiaperOut)
def add_diaper(data: schemas.DiaperCreate, db: Session = Depends(get_db)):
    return crud.create_diaper(db, data)


@app.delete("/api/diapers/{entry_id}")
def delete_diaper(entry_id: int, db: Session = Depends(get_db)):
    if not crud.delete_diaper(db, entry_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ──────────────── Sleep ────────────────

@app.get("/api/sleep", response_model=List[schemas.SleepOut])
def list_sleep(day: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db)):
    d = None
    if day:
        try:
            d = date.fromisoformat(day)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    return crud.get_sleeps(db, day=d, limit=limit)


@app.get("/api/sleep/active", response_model=Optional[schemas.SleepOut])
def get_active_sleep(db: Session = Depends(get_db)):
    return crud.get_active_sleep(db)


@app.post("/api/sleep", response_model=schemas.SleepOut)
def start_sleep(data: schemas.SleepCreate, db: Session = Depends(get_db)):
    return crud.create_sleep(db, data)


@app.post("/api/sleep/end", response_model=Optional[schemas.SleepOut])
def end_sleep(db: Session = Depends(get_db)):
    result = crud.end_sleep(db)
    if not result:
        raise HTTPException(status_code=404, detail="No active sleep session")
    return result


@app.delete("/api/sleep/{entry_id}")
def delete_sleep(entry_id: int, db: Session = Depends(get_db)):
    if not crud.delete_sleep(db, entry_id):
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


# ──────────────── Calculator ────────────────

@app.post("/api/calculator", response_model=schemas.CalcResult)
def calc_feeding(data: schemas.CalcRequest):
    result = calculator.calculate_feeding_amount(data.weight_g, data.num_feedings)
    return schemas.CalcResult(**result)


# ──────────────── Schedule Settings ────────────────

@app.get("/api/schedule/settings")
def get_schedule_settings(db: Session = Depends(get_db)):
    settings = crud.get_feeding_settings(db)
    if not settings:
        return {
            "weight_g": None,
            "num_feedings": 6,
            "first_feeding_time": "06:00",
            "last_feeding_time": None,
            "blocked_windows": [],
            "burp_buffer_minutes": 20,
            "calculated_amount_ml": None,
        }
    blocked = json.loads(settings.blocked_windows or "[]")
    amount = None
    if settings.weight_g and settings.num_feedings:
        r = calculator.calculate_feeding_amount(settings.weight_g, settings.num_feedings)
        amount = r["per_feeding_rounded"]
    return {
        "id": settings.id,
        "weight_g": settings.weight_g,
        "num_feedings": settings.num_feedings,
        "first_feeding_time": settings.first_feeding_time,
        "last_feeding_time": settings.last_feeding_time,
        "blocked_windows": blocked,
        "burp_buffer_minutes": settings.burp_buffer_minutes,
        "calculated_amount_ml": amount,
        "updated_at": settings.updated_at,
    }


@app.post("/api/schedule/settings")
def save_schedule_settings(data: schemas.FeedingSettingsCreate, db: Session = Depends(get_db)):
    settings = crud.upsert_feeding_settings(db, data)
    blocked = json.loads(settings.blocked_windows or "[]")
    amount = None
    if settings.weight_g and settings.num_feedings:
        r = calculator.calculate_feeding_amount(settings.weight_g, settings.num_feedings)
        amount = r["per_feeding_rounded"]
    return {"ok": True, "calculated_amount_ml": amount}


@app.post("/api/schedule/calculate", response_model=schemas.ScheduleResult)
def calculate_schedule(data: schemas.ScheduleRequest):
    result = calculator.calculate_schedule(
        num_feedings=data.num_feedings,
        first_feeding_time=data.first_feeding_time,
        last_feeding_time=data.last_feeding_time,
        blocked_windows=[bw.dict() for bw in (data.blocked_windows or [])],
        burp_buffer_minutes=data.burp_buffer_minutes,
    )
    return schemas.ScheduleResult(**result)


@app.get("/api/schedule/today")
def get_today_schedule(db: Session = Depends(get_db)):
    settings = crud.get_feeding_settings(db)
    if not settings:
        return {"feeding_times": [], "intervals_minutes": [], "warnings": [], "amount_ml": None}

    blocked = json.loads(settings.blocked_windows or "[]")
    result = calculator.calculate_schedule(
        num_feedings=settings.num_feedings,
        first_feeding_time=settings.first_feeding_time,
        last_feeding_time=settings.last_feeding_time,
        blocked_windows=blocked,
        burp_buffer_minutes=settings.burp_buffer_minutes,
    )
    amount = None
    if settings.weight_g:
        r = calculator.calculate_feeding_amount(settings.weight_g, settings.num_feedings)
        amount = r["per_feeding_rounded"]
    result["amount_ml"] = amount
    return result


# ──────────────── Dashboard ────────────────

@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    today = date.today()
    feedings_today = crud.get_feedings(db, day=today)
    diapers_today = crud.get_diapers(db, day=today)
    last_feeding = crud.get_last_feeding(db)
    latest_weight = crud.get_latest_weight(db)
    active_sleep = crud.get_active_sleep(db)
    settings = crud.get_feeding_settings(db)

    schedule = {"feeding_times": [], "amount_ml": None, "warnings": []}
    if settings:
        blocked = json.loads(settings.blocked_windows or "[]")
        sched = calculator.calculate_schedule(
            num_feedings=settings.num_feedings,
            first_feeding_time=settings.first_feeding_time,
            last_feeding_time=settings.last_feeding_time,
            blocked_windows=blocked,
            burp_buffer_minutes=settings.burp_buffer_minutes,
        )
        amount = None
        if settings.weight_g:
            r = calculator.calculate_feeding_amount(settings.weight_g, settings.num_feedings)
            amount = r["per_feeding_rounded"]
        schedule = {**sched, "amount_ml": amount, "num_feedings": settings.num_feedings}

    # Serialize safely
    def serialize_feeding(f):
        return {
            "id": f.id,
            "started_at": f.started_at.isoformat() if f.started_at else None,
            "amount_ml": f.amount_ml,
            "feeding_type": f.feeding_type,
            "notes": f.notes,
        }

    def serialize_diaper(d):
        return {
            "id": d.id,
            "changed_at": d.changed_at.isoformat() if d.changed_at else None,
            "diaper_type": d.diaper_type,
            "poop_color": d.poop_color,
            "notes": d.notes,
        }

    return {
        "today": today.isoformat(),
        "feedings_today": [serialize_feeding(f) for f in feedings_today],
        "diapers_today": [serialize_diaper(d) for d in diapers_today],
        "last_feeding": serialize_feeding(last_feeding) if last_feeding else None,
        "latest_weight": {
            "weight_g": latest_weight.weight_g,
            "measured_at": latest_weight.measured_at.isoformat(),
        } if latest_weight else None,
        "active_sleep": {
            "started_at": active_sleep.started_at.isoformat(),
        } if active_sleep else None,
        "schedule": schedule,
    }


# ──────────────── Static / Frontend ────────────────

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
