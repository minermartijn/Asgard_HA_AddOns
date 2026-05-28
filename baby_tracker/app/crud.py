"""
Database CRUD operations for Baby Tracker.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, date
from typing import List, Optional
import json

from . import models, schemas


# ──────────────── Baby ────────────────

def get_or_create_baby(db: Session) -> models.Baby:
    baby = db.query(models.Baby).first()
    if not baby:
        baby = models.Baby(name="Baby")
        db.add(baby)
        db.commit()
        db.refresh(baby)
    return baby


def update_baby(db: Session, data: schemas.BabyCreate) -> models.Baby:
    baby = get_or_create_baby(db)
    baby.name = data.name
    baby.birth_date = data.birth_date
    baby.gender = data.gender
    db.commit()
    db.refresh(baby)
    return baby


# ──────────────── Weight ────────────────

def get_weights(db: Session, limit: int = 30) -> List[models.WeightEntry]:
    return (
        db.query(models.WeightEntry)
        .order_by(desc(models.WeightEntry.measured_at))
        .limit(limit)
        .all()
    )


def get_latest_weight(db: Session) -> Optional[models.WeightEntry]:
    return (
        db.query(models.WeightEntry)
        .order_by(desc(models.WeightEntry.measured_at))
        .first()
    )


def create_weight(db: Session, data: schemas.WeightCreate) -> models.WeightEntry:
    entry = models.WeightEntry(
        baby_id=1,
        weight_g=data.weight_g,
        measured_at=data.measured_at or datetime.now(),
        notes=data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_weight(db: Session, entry_id: int) -> bool:
    entry = db.query(models.WeightEntry).filter(models.WeightEntry.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
        return True
    return False


# ──────────────── Feedings ────────────────

def get_feedings(db: Session, day: Optional[date] = None, limit: int = 50) -> List[models.FeedingEntry]:
    q = db.query(models.FeedingEntry)
    if day:
        start = datetime(day.year, day.month, day.day, 0, 0, 0)
        end = datetime(day.year, day.month, day.day, 23, 59, 59)
        q = q.filter(models.FeedingEntry.started_at.between(start, end))
    return q.order_by(desc(models.FeedingEntry.started_at)).limit(limit).all()


def get_last_feeding(db: Session) -> Optional[models.FeedingEntry]:
    return (
        db.query(models.FeedingEntry)
        .order_by(desc(models.FeedingEntry.started_at))
        .first()
    )


def create_feeding(db: Session, data: schemas.FeedingCreate) -> models.FeedingEntry:
    entry = models.FeedingEntry(
        baby_id=1,
        started_at=data.started_at or datetime.now(),
        amount_ml=data.amount_ml,
        feeding_type=data.feeding_type or "bottle",
        notes=data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_feeding(db: Session, entry_id: int) -> bool:
    entry = db.query(models.FeedingEntry).filter(models.FeedingEntry.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
        return True
    return False


# ──────────────── Diapers ────────────────

def get_diapers(db: Session, day: Optional[date] = None, limit: int = 50) -> List[models.DiaperEntry]:
    q = db.query(models.DiaperEntry)
    if day:
        start = datetime(day.year, day.month, day.day, 0, 0, 0)
        end = datetime(day.year, day.month, day.day, 23, 59, 59)
        q = q.filter(models.DiaperEntry.changed_at.between(start, end))
    return q.order_by(desc(models.DiaperEntry.changed_at)).limit(limit).all()


def create_diaper(db: Session, data: schemas.DiaperCreate) -> models.DiaperEntry:
    entry = models.DiaperEntry(
        baby_id=1,
        changed_at=data.changed_at or datetime.now(),
        diaper_type=data.diaper_type or "wet",
        poop_color=data.poop_color,
        notes=data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_diaper(db: Session, entry_id: int) -> bool:
    entry = db.query(models.DiaperEntry).filter(models.DiaperEntry.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
        return True
    return False


# ──────────────── Sleep ────────────────

def get_sleeps(db: Session, day: Optional[date] = None, limit: int = 20) -> List[models.SleepEntry]:
    q = db.query(models.SleepEntry)
    if day:
        start = datetime(day.year, day.month, day.day, 0, 0, 0)
        end = datetime(day.year, day.month, day.day, 23, 59, 59)
        q = q.filter(models.SleepEntry.started_at.between(start, end))
    return q.order_by(desc(models.SleepEntry.started_at)).limit(limit).all()


def get_active_sleep(db: Session) -> Optional[models.SleepEntry]:
    return (
        db.query(models.SleepEntry)
        .filter(models.SleepEntry.ended_at.is_(None))
        .order_by(desc(models.SleepEntry.started_at))
        .first()
    )


def create_sleep(db: Session, data: schemas.SleepCreate) -> models.SleepEntry:
    entry = models.SleepEntry(
        baby_id=1,
        started_at=data.started_at or datetime.now(),
        ended_at=data.ended_at,
        notes=data.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def end_sleep(db: Session) -> Optional[models.SleepEntry]:
    entry = get_active_sleep(db)
    if entry:
        entry.ended_at = datetime.now()
        db.commit()
        db.refresh(entry)
    return entry


def delete_sleep(db: Session, entry_id: int) -> bool:
    entry = db.query(models.SleepEntry).filter(models.SleepEntry.id == entry_id).first()
    if entry:
        db.delete(entry)
        db.commit()
        return True
    return False


# ──────────────── Feeding Settings ────────────────

def get_feeding_settings(db: Session) -> Optional[models.FeedingSettings]:
    return db.query(models.FeedingSettings).filter(models.FeedingSettings.baby_id == 1).first()


def upsert_feeding_settings(db: Session, data: schemas.FeedingSettingsCreate) -> models.FeedingSettings:
    settings = get_feeding_settings(db)
    blocked = json.dumps([bw.dict() for bw in (data.blocked_windows or [])])
    if not settings:
        settings = models.FeedingSettings(
            baby_id=1,
            weight_g=data.weight_g,
            num_feedings=data.num_feedings,
            first_feeding_time=data.first_feeding_time,
            last_feeding_time=data.last_feeding_time,
            blocked_windows=blocked,
            burp_buffer_minutes=data.burp_buffer_minutes,
        )
        db.add(settings)
    else:
        settings.weight_g = data.weight_g
        settings.num_feedings = data.num_feedings
        settings.first_feeding_time = data.first_feeding_time
        settings.last_feeding_time = data.last_feeding_time
        settings.blocked_windows = blocked
        settings.burp_buffer_minutes = data.burp_buffer_minutes
    db.commit()
    db.refresh(settings)
    return settings
