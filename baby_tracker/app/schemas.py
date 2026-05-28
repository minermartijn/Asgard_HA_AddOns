from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ──────────────── Baby ────────────────

class BabyBase(BaseModel):
    name: str = "Baby"
    birth_date: Optional[str] = None
    gender: Optional[str] = None


class BabyCreate(BabyBase):
    pass


class BabyOut(BabyBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────── Weight ────────────────

class WeightCreate(BaseModel):
    weight_g: float = Field(..., gt=0, le=30000)
    measured_at: Optional[datetime] = None
    notes: Optional[str] = None


class WeightOut(WeightCreate):
    id: int
    baby_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────── Feeding ────────────────

class FeedingCreate(BaseModel):
    started_at: Optional[datetime] = None
    amount_ml: Optional[float] = Field(None, gt=0, le=500)
    feeding_type: Optional[str] = "bottle"
    notes: Optional[str] = None


class FeedingOut(FeedingCreate):
    id: int
    baby_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────── Diaper ────────────────

class DiaperCreate(BaseModel):
    changed_at: Optional[datetime] = None
    diaper_type: str = "wet"
    poop_color: Optional[str] = None
    notes: Optional[str] = None


class DiaperOut(DiaperCreate):
    id: int
    baby_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────── Sleep ────────────────

class SleepCreate(BaseModel):
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None


class SleepOut(SleepCreate):
    id: int
    baby_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────── Schedule / Settings ────────────────

class BlockedWindow(BaseModel):
    start: str          # "HH:MM"
    end: str            # "HH:MM"
    label: Optional[str] = ""


class FeedingSettingsCreate(BaseModel):
    weight_g: Optional[float] = Field(None, gt=0, le=30000)
    num_feedings: int = Field(6, ge=1, le=15)
    first_feeding_time: str = "06:00"
    last_feeding_time: Optional[str] = None
    blocked_windows: Optional[List[BlockedWindow]] = []
    burp_buffer_minutes: int = Field(20, ge=0, le=60)


class FeedingSettingsOut(FeedingSettingsCreate):
    id: int
    baby_id: int
    calculated_amount_ml: Optional[float] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ──────────────── Calculator ────────────────

class CalcRequest(BaseModel):
    weight_g: float = Field(..., gt=0, le=30000)
    num_feedings: int = Field(..., ge=1, le=15)


class CalcResult(BaseModel):
    weight_g: float
    num_feedings: int
    daily_total_ml: float
    per_feeding_ml: float
    per_feeding_rounded: float   # rounded to nearest 5
    formula: str


# ──────────────── Schedule Calculate ────────────────

class ScheduleRequest(BaseModel):
    num_feedings: int = Field(..., ge=1, le=15)
    first_feeding_time: str
    last_feeding_time: Optional[str] = None
    blocked_windows: Optional[List[BlockedWindow]] = []
    burp_buffer_minutes: int = Field(20, ge=0, le=60)


class ScheduleResult(BaseModel):
    feeding_times: List[str]   # ["HH:MM", ...]
    intervals_minutes: List[int]
    warnings: List[str]
