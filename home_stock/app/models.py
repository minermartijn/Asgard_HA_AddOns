from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func
from .database import Base


class Item(Base):
    """A single stocked product in the household."""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    emoji = Column(String, default="📦")
    category = Column(String, default="other", index=True)
    quantity = Column(Integer, default=1)
    low_threshold = Column(Integer, default=1)  # "low" when quantity <= low_threshold
    unit = Column(String, nullable=True)
    barcode = Column(String, nullable=True)      # reserved for future barcode scanning
    favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Settings(Base):
    """Singleton (id=1) household configuration."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    household_name = Column(String, default="")
    language = Column(String, default="nl")
    todo_entity_id = Column(String, default="todo.shopping_list")
    auto_sync_todo = Column(Boolean, default=False)
    expose_sensors = Column(Boolean, default=True)
    sensor_prefix = Column(String, default="home_stock")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StockLog(Base):
    """Append-only log of quantity changes. Supports the future barcode/restock flow."""
    __tablename__ = "stock_log"

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), index=True)
    delta = Column(Integer, default=0)
    reason = Column(String, default="manual")   # manual | catalog | barcode | restock
    created_at = Column(DateTime, server_default=func.now())
