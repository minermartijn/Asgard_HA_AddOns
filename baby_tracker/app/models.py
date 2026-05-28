from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.sql import func
from .database import Base


class Baby(Base):
    __tablename__ = "babies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, default="Baby")
    birth_date = Column(String(20), nullable=True)   # YYYY-MM-DD
    gender = Column(String(10), nullable=True)       # boy, girl, other
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WeightEntry(Base):
    __tablename__ = "weight_entries"

    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, nullable=False, default=1)
    weight_g = Column(Float, nullable=False)
    measured_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class FeedingEntry(Base):
    __tablename__ = "feeding_entries"

    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime, nullable=False)
    amount_ml = Column(Float, nullable=True)
    # bottle, breast_left, breast_right, both_breasts, solid
    feeding_type = Column(String(20), default="bottle")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class DiaperEntry(Base):
    __tablename__ = "diaper_entries"

    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, nullable=False, default=1)
    changed_at = Column(DateTime, nullable=False)
    # wet, dirty, both, dry
    diaper_type = Column(String(20), nullable=False, default="wet")
    poop_color = Column(String(20), nullable=True)  # hex color or None
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class SleepEntry(Base):
    __tablename__ = "sleep_entries"

    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class FeedingSettings(Base):
    __tablename__ = "feeding_settings"

    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, nullable=False, default=1)
    weight_g = Column(Float, nullable=True)
    num_feedings = Column(Integer, default=6)
    first_feeding_time = Column(String(5), default="06:00")   # HH:MM
    last_feeding_time = Column(String(5), nullable=True)       # HH:MM optional
    # JSON: [{"start": "HH:MM", "end": "HH:MM", "label": "string"}]
    blocked_windows = Column(Text, default="[]")
    burp_buffer_minutes = Column(Integer, default=20)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
