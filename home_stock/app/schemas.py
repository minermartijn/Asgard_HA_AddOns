from typing import Optional
from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    name: str
    emoji: str = "📦"
    category: str = "other"
    quantity: int = Field(1, ge=0)
    low_threshold: int = Field(1, ge=0)
    unit: Optional[str] = None
    barcode: Optional[str] = None
    favorite: bool = False


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    low_threshold: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = None
    barcode: Optional[str] = None
    favorite: Optional[bool] = None


class ItemOut(ItemBase):
    id: int
    is_low: bool = False

    class Config:
        from_attributes = True


class AdjustRequest(BaseModel):
    delta: int


class SettingsBase(BaseModel):
    household_name: Optional[str] = ""
    language: Optional[str] = "nl"
    todo_entity_id: Optional[str] = "todo.shopping_list"
    auto_sync_todo: Optional[bool] = False
    expose_sensors: Optional[bool] = True


class SettingsOut(SettingsBase):
    id: int

    class Config:
        from_attributes = True
