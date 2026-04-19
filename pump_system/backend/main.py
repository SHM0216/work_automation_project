"""FastAPI entrypoint for the pump monitoring backend."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import init_db
from routers import alerts, sensors, stations
from services.alert_service import manager, offline_watchdog

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("pump_system")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    watchdog_task = asyncio.create_task(offline_watchdog())
    log.info("pump_system backend started")
    try:
        yield
    finally:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass
        log.info("pump_system backend stopped")


app = FastAPI(
    title="Pump Station Monitoring API",
    version="1.0.0",
    description="22개 빗물펌프장 실시간 감시 + 경보 시스템",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(sensors.router)
app.include_router(alerts.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time feed: clients receive reading/alert/resolved messages."""
    await manager.connect(websocket)
    try:
        while True:
            # We don't expect client -> server messages, but keep the socket open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:  # noqa: BLE001
        await manager.disconnect(websocket)
