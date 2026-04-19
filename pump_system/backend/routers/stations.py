"""Station list / detail / history endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Alert, SensorReading, Station, get_db
from schemas import SensorReadingOut, StationOut, StationStatus
from services.alert_service import OFFLINE_AFTER, classify_level

router = APIRouter(prefix="/api/stations", tags=["stations"])


def _build_status(db: Session, station: Station) -> StationStatus:
    last = (
        db.query(SensorReading)
        .filter(SensorReading.station_id == station.id)
        .order_by(SensorReading.recorded_at.desc())
        .first()
    )
    active_alerts = (
        db.query(Alert)
        .filter(Alert.station_id == station.id, Alert.resolved_at.is_(None))
        .count()
    )

    status = "offline"
    if last is not None:
        if datetime.utcnow() - last.recorded_at > OFFLINE_AFTER:
            status = "offline"
        else:
            status = classify_level(station, last.water_level_m)

    return StationStatus(
        id=station.id,
        name=station.name,
        region=station.region,
        latitude=station.latitude,
        longitude=station.longitude,
        capacity_m3s=station.capacity_m3s,
        pump_count=station.pump_count,
        warn_level_m=station.warn_level_m,
        high_level_m=station.high_level_m,
        flood_level_m=station.flood_level_m,
        water_level_m=last.water_level_m if last else None,
        inflow_m3s=last.inflow_m3s if last else None,
        outflow_m3s=last.outflow_m3s if last else None,
        pumps_running=last.pumps_running if last else None,
        last_reported_at=last.recorded_at if last else None,
        status=status,
        active_alert_count=active_alerts,
    )


@router.get("", response_model=list[StationStatus])
def list_stations(db: Session = Depends(get_db)) -> list[StationStatus]:
    stations = db.query(Station).order_by(Station.id).all()
    return [_build_status(db, s) for s in stations]


@router.get("/{station_id}", response_model=StationStatus)
def get_station(station_id: int, db: Session = Depends(get_db)) -> StationStatus:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="station not found")
    return _build_status(db, station)


@router.get("/{station_id}/history", response_model=list[SensorReadingOut])
def get_history(
    station_id: int,
    hours: int = Query(default=24, ge=1, le=24 * 30),
    db: Session = Depends(get_db),
) -> list[SensorReading]:
    station = db.get(Station, station_id)
    if station is None:
        raise HTTPException(status_code=404, detail="station not found")
    since = datetime.utcnow() - timedelta(hours=hours)
    return (
        db.query(SensorReading)
        .filter(
            SensorReading.station_id == station_id,
            SensorReading.recorded_at >= since,
        )
        .order_by(SensorReading.recorded_at.asc())
        .all()
    )
