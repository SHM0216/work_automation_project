"""Pydantic schemas for request/response bodies."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StationBase(BaseModel):
    name: str
    region: str
    latitude: float
    longitude: float
    capacity_m3s: float
    pump_count: int
    warn_level_m: float
    high_level_m: float
    flood_level_m: float


class StationOut(StationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class StationStatus(StationOut):
    water_level_m: Optional[float] = None
    inflow_m3s: Optional[float] = None
    outflow_m3s: Optional[float] = None
    pumps_running: Optional[int] = None
    last_reported_at: Optional[datetime] = None
    status: Literal["normal", "info", "warning", "critical", "offline"] = "offline"
    active_alert_count: int = 0


class SensorReadingIn(BaseModel):
    station_id: int
    water_level_m: float = Field(..., ge=0)
    inflow_m3s: Optional[float] = Field(default=None, ge=0)
    outflow_m3s: Optional[float] = Field(default=None, ge=0)
    pumps_running: int = Field(default=0, ge=0)
    recorded_at: Optional[datetime] = None


class SensorBatchIn(BaseModel):
    readings: list[SensorReadingIn]


class SensorReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_id: int
    water_level_m: float
    inflow_m3s: Optional[float]
    outflow_m3s: Optional[float]
    pumps_running: int
    recorded_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    station_id: int
    level: str
    message: str
    water_level_m: Optional[float]
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]


class PushTokenIn(BaseModel):
    token: str
    platform: Literal["expo", "ios", "android"] = "expo"
