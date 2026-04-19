"""SQLAlchemy models and 22-station seed data for the pump monitoring system."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Boolean,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DB_PATH = Path(__file__).parent / "pump_system.db"
SQLALCHEMY_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    region = Column(String(64), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_m3s = Column(Float, nullable=False)
    pump_count = Column(Integer, nullable=False, default=2)

    warn_level_m = Column(Float, nullable=False)
    high_level_m = Column(Float, nullable=False)
    flood_level_m = Column(Float, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    readings = relationship(
        "SensorReading", back_populates="station", cascade="all, delete-orphan"
    )
    alerts = relationship(
        "Alert", back_populates="station", cascade="all, delete-orphan"
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False, index=True)
    water_level_m = Column(Float, nullable=False)
    inflow_m3s = Column(Float, nullable=True)
    outflow_m3s = Column(Float, nullable=True)
    pumps_running = Column(Integer, nullable=False, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    station = relationship("Station", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False, index=True)
    level = Column(String(16), nullable=False)  # info | warning | critical | offline
    message = Column(Text, nullable=False)
    water_level_m = Column(Float, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    station = relationship("Station", back_populates="alerts")


class PushDevice(Base):
    __tablename__ = "push_devices"

    id = Column(Integer, primary_key=True)
    token = Column(String(256), nullable=False, unique=True)
    platform = Column(String(16), nullable=False, default="expo")
    enabled = Column(Boolean, nullable=False, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# 22개 펌프장 초기 데이터 (대구광역시 실제 펌프장)
# capacity_m3s: 배수용량 (최대, m³/min → m³/s 환산)
# warn_level_m: 가동수위  /  flood_level_m: 한계수위
# high_level_m: 가동·한계 중간점(≈2/3)
INITIAL_STATIONS: list[dict] = [
    {"name": "월성펌프장",     "region": "달서구",     "latitude": 35.8295, "longitude": 128.5325, "capacity_m3s": 235.8, "pump_count": 33, "warn_level_m": 1.5, "high_level_m": 3.7, "flood_level_m": 4.9},
    {"name": "죽곡펌프장",     "region": "달성군 다사읍", "latitude": 35.8660, "longitude": 128.4620, "capacity_m3s":  13.3, "pump_count":  3, "warn_level_m": 5.4, "high_level_m": 6.7, "flood_level_m": 7.4},
    {"name": "성서5차펌프장",  "region": "달성군 다사읍", "latitude": 35.8520, "longitude": 128.4750, "capacity_m3s":  17.2, "pump_count":  6, "warn_level_m": 1.3, "high_level_m": 2.1, "flood_level_m": 2.5},
    {"name": "이현펌프장",     "region": "서구",       "latitude": 35.8735, "longitude": 128.5590, "capacity_m3s":  25.3, "pump_count":  8, "warn_level_m": 2.0, "high_level_m": 3.0, "flood_level_m": 3.5},
    {"name": "3공단펌프장",    "region": "서구",       "latitude": 35.8780, "longitude": 128.5500, "capacity_m3s":  26.3, "pump_count": 12, "warn_level_m": 2.2, "high_level_m": 3.7, "flood_level_m": 4.5},
    {"name": "비산펌프장",     "region": "서구",       "latitude": 35.8760, "longitude": 128.5480, "capacity_m3s":   4.7, "pump_count":  3, "warn_level_m": 2.0, "high_level_m": 4.0, "flood_level_m": 5.0},
    {"name": "팔달펌프장",     "region": "북구",       "latitude": 35.9200, "longitude": 128.5520, "capacity_m3s":  17.2, "pump_count":  5, "warn_level_m": 4.5, "high_level_m": 5.4, "flood_level_m": 5.9},
    {"name": "노곡펌프장",     "region": "북구",       "latitude": 35.9050, "longitude": 128.5730, "capacity_m3s":   8.0, "pump_count":  2, "warn_level_m": 1.4, "high_level_m": 4.1, "flood_level_m": 5.5},
    {"name": "조야펌프장",     "region": "북구",       "latitude": 35.9020, "longitude": 128.5680, "capacity_m3s":  30.0, "pump_count":  4, "warn_level_m": 1.4, "high_level_m": 4.1, "flood_level_m": 5.5},
    {"name": "침산펌프장",     "region": "북구",       "latitude": 35.8925, "longitude": 128.5890, "capacity_m3s":  12.5, "pump_count":  6, "warn_level_m": 3.7, "high_level_m": 4.6, "flood_level_m": 5.0},
    {"name": "산격펌프장",     "region": "북구",       "latitude": 35.8950, "longitude": 128.6095, "capacity_m3s":   9.8, "pump_count":  5, "warn_level_m": 2.0, "high_level_m": 3.7, "flood_level_m": 4.5},
    {"name": "봉무펌프장",     "region": "동구",       "latitude": 35.9020, "longitude": 128.6470, "capacity_m3s":  36.5, "pump_count":  7, "warn_level_m": 5.2, "high_level_m": 7.0, "flood_level_m": 8.0},
    {"name": "동촌펌프장",     "region": "동구",       "latitude": 35.8885, "longitude": 128.6495, "capacity_m3s":  46.0, "pump_count":  8, "warn_level_m": 1.5, "high_level_m": 3.2, "flood_level_m": 4.0},
    {"name": "신암펌프장",     "region": "동구",       "latitude": 35.8770, "longitude": 128.6280, "capacity_m3s":  37.9, "pump_count":  5, "warn_level_m": 7.2, "high_level_m": 9.1, "flood_level_m": 10.0},
    {"name": "방촌펌프장",     "region": "동구",       "latitude": 35.8815, "longitude": 128.6685, "capacity_m3s":   2.3, "pump_count":  4, "warn_level_m": 2.0, "high_level_m": 4.0, "flood_level_m": 5.0},
    {"name": "방촌2펌프장",    "region": "동구",       "latitude": 35.8825, "longitude": 128.6710, "capacity_m3s":   9.2, "pump_count":  5, "warn_level_m": 3.7, "high_level_m": 4.5, "flood_level_m": 4.9},
    {"name": "팔현펌프장",     "region": "수성구",     "latitude": 35.8370, "longitude": 128.6820, "capacity_m3s":  11.0, "pump_count":  4, "warn_level_m": 3.7, "high_level_m": 4.9, "flood_level_m": 5.5},
    {"name": "율하펌프장",     "region": "동구",       "latitude": 35.8665, "longitude": 128.7045, "capacity_m3s":  11.3, "pump_count":  5, "warn_level_m": 6.8, "high_level_m": 7.8, "flood_level_m": 8.3},
    {"name": "서재펌프장",     "region": "달성군 다사읍", "latitude": 35.8450, "longitude": 128.4680, "capacity_m3s":   5.8, "pump_count":  3, "warn_level_m": 4.0, "high_level_m": 4.3, "flood_level_m": 4.5},
    {"name": "서재2펌프장",    "region": "달성군 다사읍", "latitude": 35.8430, "longitude": 128.4650, "capacity_m3s":  18.7, "pump_count":  5, "warn_level_m": 4.0, "high_level_m": 5.3, "flood_level_m": 6.0},
    {"name": "창리펌프장",     "region": "달성군 구지면", "latitude": 35.6490, "longitude": 128.4350, "capacity_m3s":  44.6, "pump_count":  5, "warn_level_m": 5.4, "high_level_m": 6.9, "flood_level_m": 7.6},
    {"name": "가천펌프장",     "region": "수성구",     "latitude": 35.8300, "longitude": 128.7120, "capacity_m3s":   9.2, "pump_count":  4, "warn_level_m": 3.5, "high_level_m": 5.3, "flood_level_m": 6.2},
]


def get_db():
    """FastAPI dependency that yields a scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and seed the 22 pump stations on first run."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(Station).count() == 0:
            db.add_all([Station(**row) for row in INITIAL_STATIONS])
            db.commit()
