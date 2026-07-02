import os
from typing import Optional, List

from sqlalchemy.orm import Session

from . import models, schemas


def _mark(item: models.Item) -> models.Item:
    """Attach the derived `is_low` flag (transient attribute for serialization)."""
    if item is not None:
        item.is_low = item.quantity <= item.low_threshold
    return item


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("true", "1", "yes", "on")


# ──────────────── Items ────────────────

def list_items(db: Session, category: Optional[str] = None, low_only: bool = False) -> List[models.Item]:
    q = db.query(models.Item)
    if category:
        q = q.filter(models.Item.category == category)
    items = q.order_by(models.Item.category, models.Item.name).all()
    items = [_mark(i) for i in items]
    if low_only:
        items = [i for i in items if i.is_low]
    return items


def get_item(db: Session, item_id: int) -> Optional[models.Item]:
    return _mark(db.query(models.Item).filter(models.Item.id == item_id).first())


def add_item(db: Session, data: schemas.ItemCreate) -> models.Item:
    item = models.Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    if item.quantity:
        db.add(models.StockLog(item_id=item.id, delta=item.quantity, reason="catalog"))
        db.commit()
    return _mark(item)


def update_item(db: Session, item_id: int, data: schemas.ItemUpdate) -> Optional[models.Item]:
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return _mark(item)


def delete_item(db: Session, item_id: int) -> bool:
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def adjust_quantity(db: Session, item_id: int, delta: int, reason: str = "manual") -> Optional[models.Item]:
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return None
    item.quantity = max(0, (item.quantity or 0) + delta)
    db.add(models.StockLog(item_id=item_id, delta=delta, reason=reason))
    db.commit()
    db.refresh(item)
    return _mark(item)


def shopping_list(db: Session) -> List[models.Item]:
    return list_items(db, low_only=True)


def dashboard(db: Session) -> dict:
    items = list_items(db)
    low = [i for i in items if i.is_low]
    out = [i for i in items if i.quantity == 0]
    categories: dict = {}
    for i in items:
        categories[i.category] = categories.get(i.category, 0) + 1
    return {
        "total_items": len(items),
        "low_count": len(low),
        "out_count": len(out),
        "categories": categories,
    }


# ──────────────── Settings ────────────────

def get_or_create_settings(db: Session) -> models.Settings:
    s = db.query(models.Settings).filter(models.Settings.id == 1).first()
    if not s:
        # Seed the singleton from the add-on options (exported as env vars by run.sh).
        s = models.Settings(
            id=1,
            household_name=os.getenv("HOUSEHOLD_NAME", "") or "",
            language=os.getenv("LANGUAGE", "nl") or "nl",
            todo_entity_id=os.getenv("TODO_ENTITY", "todo.shopping_list") or "todo.shopping_list",
            auto_sync_todo=_env_bool("AUTO_SYNC_TODO", False),
            expose_sensors=_env_bool("EXPOSE_SENSORS", True),
        )
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def update_settings(db: Session, data: schemas.SettingsBase) -> models.Settings:
    s = get_or_create_settings(db)
    for key, value in data.model_dump(exclude_unset=True).items():
        # map the schema's public name to the model column
        if key == "todo_entity_id":
            s.todo_entity_id = value
        else:
            setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s
