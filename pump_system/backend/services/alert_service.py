"""Alert evaluation + WebSocket broadcast service."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import WebSocket
from sqlalchemy.orm import Session

from database import Alert, SensorReading, Station, SessionLocal

log = logging.getLogger(__name__)

OFFLINE_AFTER = timedelta(seconds=60)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


class ConnectionManager:
    """Tracks connected WebSocket clients and fans out broadcast messages."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, default=str)
        async with self._lock:
            targets = list(self._clients)
        for ws in targets:
            try:
                await ws.send_text(data)
            except Exception:  # noqa: BLE001 - drop broken connections
                await self.disconnect(ws)


manager = ConnectionManager()


def classify_level(station: Station, water_level_m: float) -> str:
    if water_level_m >= station.flood_level_m:
        return "critical"
    if water_level_m >= station.high_level_m:
        return "warning"
    if water_level_m >= station.warn_level_m:
        return "info"
    return "normal"


def _active_alert(db: Session, station_id: int) -> Alert | None:
    return (
        db.query(Alert)
        .filter(Alert.station_id == station_id, Alert.resolved_at.is_(None))
        .order_by(Alert.triggered_at.desc())
        .first()
    )


def evaluate_reading(
    db: Session, reading: SensorReading
) -> tuple[list[dict[str, Any]], str]:
    """Create/resolve alerts for a new sensor reading.

    Returns a list of broadcast payloads (to be sent via WebSocket) and the
    computed status level so the caller can include it in the HTTP response.
    """
    station = db.get(Station, reading.station_id)
    if station is None:
        return [], "offline"

    level = classify_level(station, reading.water_level_m)
    events: list[dict[str, Any]] = []

    # Always broadcast the reading
    events.append(
        {
            "type": "reading",
            "station_id": station.id,
            "water_level_m": reading.water_level_m,
            "inflow_m3s": reading.inflow_m3s,
            "outflow_m3s": reading.outflow_m3s,
            "pumps_running": reading.pumps_running,
            "status": level,
            "timestamp": _iso(reading.recorded_at),
        }
    )

    existing = _active_alert(db, station.id)
    if level == "normal":
        if existing is not None:
            existing.resolved_at = datetime.utcnow()
            db.commit()
            events.append({"type": "resolved", "alert_id": existing.id, "station_id": station.id})
        return events, level

    # Escalation or new alert
    if existing is None or existing.level != level:
        if existing is not None and existing.level != level:
            existing.resolved_at = datetime.utcnow()
            events.append({"type": "resolved", "alert_id": existing.id, "station_id": station.id})
        alert = Alert(
            station_id=station.id,
            level=level,
            water_level_m=reading.water_level_m,
            message=_build_message(station, level, reading.water_level_m),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        events.append(
            {
                "type": "alert",
                "alert_id": alert.id,
                "station_id": station.id,
                "station_name": station.name,
                "level": alert.level,
                "message": alert.message,
                "water_level_m": alert.water_level_m,
                "triggered_at": _iso(alert.triggered_at),
            }
        )
    return events, level


def _build_message(station: Station, level: str, water_level_m: float) -> str:
    if level == "critical":
        return f"{station.name} 월류 위험 (수위 {water_level_m:.2f}m ≥ {station.flood_level_m:.2f}m)"
    if level == "warning":
        return f"{station.name} 고수위 경보 (수위 {water_level_m:.2f}m ≥ {station.high_level_m:.2f}m)"
    if level == "info":
        return f"{station.name} 주의 수위 도달 (수위 {water_level_m:.2f}m)"
    if level == "offline":
        return f"{station.name} 통신 두절"
    return f"{station.name} 상태 확인 필요"


async def offline_watchdog(poll_seconds: int = 30) -> None:
    """Background task that raises 'offline' alerts for stale stations."""
    while True:
        try:
            await asyncio.sleep(poll_seconds)
            cutoff = datetime.utcnow() - OFFLINE_AFTER
            with SessionLocal() as db:
                stations = db.query(Station).all()
                for station in stations:
                    last = (
                        db.query(SensorReading)
                        .filter(SensorReading.station_id == station.id)
                        .order_by(SensorReading.recorded_at.desc())
                        .first()
                    )
                    if last is None or last.recorded_at >= cutoff:
                        continue
                    existing = _active_alert(db, station.id)
                    if existing and existing.level == "offline":
                        continue
                    if existing:
                        existing.resolved_at = datetime.utcnow()
                    alert = Alert(
                        station_id=station.id,
                        level="offline",
                        water_level_m=last.water_level_m if last else None,
                        message=_build_message(station, "offline", 0.0),
                    )
                    db.add(alert)
                    db.commit()
                    db.refresh(alert)
                    await manager.broadcast(
                        {
                            "type": "alert",
                            "alert_id": alert.id,
                            "station_id": station.id,
                            "station_name": station.name,
                            "level": "offline",
                            "message": alert.message,
                            "triggered_at": _iso(alert.triggered_at),
                        }
                    )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            log.exception("offline_watchdog iteration failed")
