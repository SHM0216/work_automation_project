"""Alert query / acknowledge / resolve endpoints."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import Alert, PushDevice, get_db
from schemas import AlertOut, PushTokenIn
from services.alert_service import manager

router = APIRouter(tags=["alerts"])


@router.get("/api/alerts", response_model=list[AlertOut])
def list_alerts(
    station_id: int | None = Query(default=None),
    level: str | None = Query(default=None, pattern="^(info|warning|critical|offline)$"),
    active_only: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[Alert]:
    q = db.query(Alert)
    if station_id is not None:
        q = q.filter(Alert.station_id == station_id)
    if level is not None:
        q = q.filter(Alert.level == level)
    if active_only:
        q = q.filter(Alert.resolved_at.is_(None))
    return q.order_by(Alert.triggered_at.desc()).limit(limit).all()


@router.post("/api/alerts/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        await manager.broadcast(
            {"type": "acknowledged", "alert_id": alert.id, "station_id": alert.station_id}
        )
    return alert


@router.post("/api/alerts/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")
    if alert.resolved_at is None:
        alert.resolved_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        await manager.broadcast(
            {"type": "resolved", "alert_id": alert.id, "station_id": alert.station_id}
        )
    return alert


@router.post("/api/devices/push-token")
def register_push_token(payload: PushTokenIn, db: Session = Depends(get_db)) -> dict:
    existing = db.query(PushDevice).filter(PushDevice.token == payload.token).first()
    if existing:
        existing.enabled = True
        existing.platform = payload.platform
        db.commit()
        return {"status": "updated", "id": existing.id}
    device = PushDevice(token=payload.token, platform=payload.platform)
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"status": "created", "id": device.id}
