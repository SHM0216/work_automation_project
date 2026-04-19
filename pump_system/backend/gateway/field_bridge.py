"""Field bridge: read on-site sensors and push them to the backend.

This gateway is designed to run on a small industrial PC or Raspberry Pi next
to the pump station's PLC. It periodically reads the current water level (and
optionally flow / pump status) and POSTs the values to the backend's
`/api/sensors/readings` endpoint. If the backend is unreachable, readings are
buffered locally and re-sent on the next successful round trip so no data is
lost during short network outages.

The actual hardware integration is pluggable via the `SensorSource` interface.
Two sources ship with the bridge:

* `ModbusSensorSource` - reads holding registers from a Modbus TCP device.
  Requires `pymodbus` (optional, imported lazily).
* `SimulatedSensorSource` - produces sine-wave style readings for testing.

Usage:

    python field_bridge.py --backend http://server:8000 --station-id 3
    python field_bridge.py --backend http://server:8000 --station-id 3 \
        --modbus-host 10.0.0.50 --modbus-port 502 --level-register 100
    python field_bridge.py --backend http://server:8000 --station-id 3 --simulate
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import math
import random
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import httpx

log = logging.getLogger("field_bridge")

MAX_BUFFER = 2000  # readings to keep if backend is offline


@dataclass
class Reading:
    station_id: int
    water_level_m: float
    inflow_m3s: float | None
    outflow_m3s: float | None
    pumps_running: int
    recorded_at: datetime

    def to_payload(self) -> dict:
        return {
            "station_id": self.station_id,
            "water_level_m": round(self.water_level_m, 3),
            "inflow_m3s": self.inflow_m3s,
            "outflow_m3s": self.outflow_m3s,
            "pumps_running": self.pumps_running,
            "recorded_at": self.recorded_at.isoformat(),
        }


class SensorSource(Protocol):
    def read(self, station_id: int) -> Reading: ...


class SimulatedSensorSource:
    """Generates synthetic water-level data useful for demos and tests."""

    def __init__(self, base: float = 1.5, amplitude: float = 1.2) -> None:
        self._t0 = time.time()
        self._base = base
        self._amplitude = amplitude

    def read(self, station_id: int) -> Reading:
        t = time.time() - self._t0
        # Slow sine + small noise, offset per station so they're not identical.
        offset = (station_id * 0.37) % math.tau
        level = self._base + self._amplitude * math.sin(t / 120.0 + offset)
        level += random.uniform(-0.05, 0.05)
        level = max(0.0, level)
        pumps = 0 if level < 1.8 else 1 if level < 2.5 else 2
        return Reading(
            station_id=station_id,
            water_level_m=level,
            inflow_m3s=round(random.uniform(0.5, 4.0), 2),
            outflow_m3s=round(pumps * 2.5, 2),
            pumps_running=pumps,
            recorded_at=datetime.now(timezone.utc),
        )


class ModbusSensorSource:
    """Modbus TCP holding-register reader. pymodbus is imported lazily."""

    def __init__(
        self,
        host: str,
        port: int = 502,
        level_register: int = 0,
        inflow_register: int | None = None,
        outflow_register: int | None = None,
        pump_register: int | None = None,
        scale: float = 0.01,
    ) -> None:
        self._host = host
        self._port = port
        self._level_register = level_register
        self._inflow_register = inflow_register
        self._outflow_register = outflow_register
        self._pump_register = pump_register
        self._scale = scale
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from pymodbus.client import ModbusTcpClient  # type: ignore
        except ImportError as err:  # pragma: no cover
            raise RuntimeError(
                "pymodbus is required for ModbusSensorSource (pip install pymodbus)"
            ) from err
        self._client = ModbusTcpClient(self._host, port=self._port)
        self._client.connect()
        return self._client

    def _read_register(self, client, address: int | None) -> float | None:
        if address is None:
            return None
        rr = client.read_holding_registers(address=address, count=1)
        if rr.isError():
            raise IOError(f"modbus read error at {address}: {rr}")
        return rr.registers[0] * self._scale

    def read(self, station_id: int) -> Reading:
        client = self._ensure_client()
        level = self._read_register(client, self._level_register) or 0.0
        inflow = self._read_register(client, self._inflow_register)
        outflow = self._read_register(client, self._outflow_register)
        pumps_raw = self._read_register(client, self._pump_register)
        pumps = int(round(pumps_raw)) if pumps_raw is not None else 0
        return Reading(
            station_id=station_id,
            water_level_m=level,
            inflow_m3s=inflow,
            outflow_m3s=outflow,
            pumps_running=pumps,
            recorded_at=datetime.now(timezone.utc),
        )


class FieldBridge:
    def __init__(
        self,
        backend_url: str,
        station_id: int,
        source: SensorSource,
        interval_s: float = 5.0,
        timeout_s: float = 5.0,
    ) -> None:
        self._backend_url = backend_url.rstrip("/")
        self._station_id = station_id
        self._source = source
        self._interval = interval_s
        self._timeout = timeout_s
        self._buffer: deque[Reading] = deque(maxlen=MAX_BUFFER)

    async def run(self) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while True:
                try:
                    reading = self._source.read(self._station_id)
                    self._buffer.append(reading)
                    await self._flush(client)
                except Exception:  # noqa: BLE001
                    log.exception("reading/transmit failed, will retry")
                await asyncio.sleep(self._interval)

    async def _flush(self, client: httpx.AsyncClient) -> None:
        if not self._buffer:
            return
        batch = [r.to_payload() for r in list(self._buffer)]
        resp = await client.post(
            f"{self._backend_url}/api/sensors/readings",
            json={"readings": batch},
        )
        resp.raise_for_status()
        log.info("uploaded %d reading(s)", len(batch))
        self._buffer.clear()


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pump station field bridge")
    p.add_argument("--backend", required=True, help="Backend base URL, e.g. http://host:8000")
    p.add_argument("--station-id", type=int, required=True)
    p.add_argument("--interval", type=float, default=5.0)

    p.add_argument("--simulate", action="store_true", help="Use the simulated sensor source")

    p.add_argument("--modbus-host")
    p.add_argument("--modbus-port", type=int, default=502)
    p.add_argument("--level-register", type=int, default=0)
    p.add_argument("--inflow-register", type=int)
    p.add_argument("--outflow-register", type=int)
    p.add_argument("--pump-register", type=int)
    p.add_argument("--modbus-scale", type=float, default=0.01)

    return p.parse_args()


def _build_source(args: argparse.Namespace) -> SensorSource:
    if args.simulate or not args.modbus_host:
        if not args.simulate:
            log.warning("no --modbus-host given; falling back to --simulate")
        return SimulatedSensorSource()
    return ModbusSensorSource(
        host=args.modbus_host,
        port=args.modbus_port,
        level_register=args.level_register,
        inflow_register=args.inflow_register,
        outflow_register=args.outflow_register,
        pump_register=args.pump_register,
        scale=args.modbus_scale,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    bridge = FieldBridge(
        backend_url=args.backend,
        station_id=args.station_id,
        source=_build_source(args),
        interval_s=args.interval,
    )
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        log.info("shutting down")


if __name__ == "__main__":
    main()
