from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class BpRecordBase(BaseModel):
    systolic: int = Field(ge=60, le=260)
    diastolic: int = Field(ge=30, le=200)
    heart_rate: Optional[int] = Field(default=None, ge=30, le=220)
    measured_at: datetime
    source: Literal["manual", "ocr"] = "manual"
    image_id: Optional[str] = Field(default=None, max_length=64)
    note: Optional[str] = Field(default=None, max_length=500)


class BpRecordCreate(BpRecordBase):
    pass


class BpRecordUpdate(BaseModel):
    systolic: Optional[int] = Field(default=None, ge=60, le=260)
    diastolic: Optional[int] = Field(default=None, ge=30, le=200)
    heart_rate: Optional[int] = Field(default=None, ge=30, le=220)
    measured_at: Optional[datetime] = None
    note: Optional[str] = Field(default=None, max_length=500)


class BpRecordOut(BpRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class BpRecordListOut(BaseModel):
    total: int
    page: int
    size: int
    items: list[BpRecordOut]


class BpRecordStats(BaseModel):
    count: int
    systolic_avg: Optional[float] = None
    systolic_max: Optional[int] = None
    systolic_min: Optional[int] = None
    diastolic_avg: Optional[float] = None
    diastolic_max: Optional[int] = None
    diastolic_min: Optional[int] = None
    heart_rate_avg: Optional[float] = None
    window_days: int


class BpForecastPoint(BaseModel):
    date: str
    systolic: float
    diastolic: float


class BpRecordForecast(BaseModel):
    window: int
    points: list[BpForecastPoint]
    trend: str
    message: Optional[str] = None
