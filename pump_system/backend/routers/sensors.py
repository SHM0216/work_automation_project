"""Sensor-reading ingestion endpoint used by the field gateway."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SensorReading, Station, get_db
from schemas import SensorBatchIn, SensorReadingIn
from services.alert_service import evaluate_reading, manager

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


def _store(db: Session, payload: SensorReadingIn) -> SensorReading:
    station = db.get(Station, payload.station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"station {payload.station_id} not found")
    reading = SensorReading(
        station_id=payload.station_id,
        water_level_m=payload.water_level_m,
        inflow_m3s=payload.inflow_m3s,
        outflow_m3s=payload.outflow_m3s,
        pumps_running=payload.pumps_running,
        recorded_at=payload.recorded_at or datetime.utcnow(),
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.post("/readings")
async def ingest_readings(
    payload: SensorBatchIn | SensorReadingIn,
    db: Session = Depends(get_db),
) -> dict:
    items = payload.readings if isinstance(payload, SensorBatchIn) else [payload]
    accepted = 0
    events_to_broadcast: list[dict] = []
    for item in items:
        reading = _store(db, item)
        events, _ = evaluate_reading(db, reading)
        events_to_broadcast.extend(events)
        accepted += 1

    for ev in events_to_broadcast:
        await manager.broadcast(ev)

    return {"accepted": accepted}
