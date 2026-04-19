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


# 22개 펌프장 초기 데이터
# (서울시 주요 빗물펌프장 사례를 참고한 가상 데이터)
INITIAL_STATIONS: list[dict] = [
    {"name": "망원1 빗물펌프장",  "region": "마포구",   "latitude": 37.5550, "longitude": 126.9015, "capacity_m3s":  45.0, "pump_count": 4, "warn_level_m": 2.0, "high_level_m": 3.0, "flood_level_m": 3.8},
    {"name": "망원2 빗물펌프장",  "region": "마포구",   "latitude": 37.5564, "longitude": 126.8970, "capacity_m3s":  38.0, "pump_count": 3, "warn_level_m": 1.8, "high_level_m": 2.8, "flood_level_m": 3.6},
    {"name": "합정 빗물펌프장",   "region": "마포구",   "latitude": 37.5493, "longitude": 126.9139, "capacity_m3s":  30.0, "pump_count": 3, "warn_level_m": 1.6, "high_level_m": 2.5, "flood_level_m": 3.2},
    {"name": "신월 빗물펌프장",   "region": "양천구",   "latitude": 37.5302, "longitude": 126.8299, "capacity_m3s":  52.0, "pump_count": 5, "warn_level_m": 2.1, "high_level_m": 3.1, "flood_level_m": 4.0},
    {"name": "목동 빗물펌프장",   "region": "양천구",   "latitude": 37.5367, "longitude": 126.8748, "capacity_m3s":  40.0, "pump_count": 4, "warn_level_m": 1.9, "high_level_m": 2.9, "flood_level_m": 3.7},
    {"name": "강서 빗물펌프장",   "region": "강서구",   "latitude": 37.5509, "longitude": 126.8495, "capacity_m3s":  42.0, "pump_count": 4, "warn_level_m": 1.9, "high_level_m": 2.9, "flood_level_m": 3.7},
    {"name": "가양 빗물펌프장",   "region": "강서구",   "latitude": 37.5611, "longitude": 126.8541, "capacity_m3s":  35.0, "pump_count": 3, "warn_level_m": 1.7, "high_level_m": 2.6, "flood_level_m": 3.4},
    {"name": "구로 빗물펌프장",   "region": "구로구",   "latitude": 37.4954, "longitude": 126.8874, "capacity_m3s":  33.0, "pump_count": 3, "warn_level_m": 1.7, "high_level_m": 2.6, "flood_level_m": 3.3},
    {"name": "개봉 빗물펌프장",   "region": "구로구",   "latitude": 37.4934, "longitude": 126.8587, "capacity_m3s":  28.0, "pump_count": 3, "warn_level_m": 1.5, "high_level_m": 2.4, "flood_level_m": 3.1},
    {"name": "시흥 빗물펌프장",   "region": "금천구",   "latitude": 37.4566, "longitude": 126.9027, "capacity_m3s":  36.0, "pump_count": 3, "warn_level_m": 1.8, "high_level_m": 2.7, "flood_level_m": 3.5},
    {"name": "봉천 빗물펌프장",   "region": "관악구",   "latitude": 37.4779, "longitude": 126.9514, "capacity_m3s":  32.0, "pump_count": 3, "warn_level_m": 1.7, "high_level_m": 2.6, "flood_level_m": 3.3},
    {"name": "신림 빗물펌프장",   "region": "관악구",   "latitude": 37.4842, "longitude": 126.9294, "capacity_m3s":  44.0, "pump_count": 4, "warn_level_m": 2.0, "high_level_m": 3.0, "flood_level_m": 3.8},
    {"name": "사당 빗물펌프장",   "region": "동작구",   "latitude": 37.4765, "longitude": 126.9817, "capacity_m3s":  38.0, "pump_count": 4, "warn_level_m": 1.9, "high_level_m": 2.8, "flood_level_m": 3.6},
    {"name": "노량진 빗물펌프장", "region": "동작구",   "latitude": 37.5133, "longitude": 126.9428, "capacity_m3s":  29.0, "pump_count": 3, "warn_level_m": 1.6, "high_level_m": 2.5, "flood_level_m": 3.2},
    {"name": "반포 빗물펌프장",   "region": "서초구",   "latitude": 37.5044, "longitude": 126.9956, "capacity_m3s":  48.0, "pump_count": 4, "warn_level_m": 2.0, "high_level_m": 3.0, "flood_level_m": 3.9},
    {"name": "서초 빗물펌프장",   "region": "서초구",   "latitude": 37.4921, "longitude": 127.0081, "capacity_m3s":  34.0, "pump_count": 3, "warn_level_m": 1.7, "high_level_m": 2.6, "flood_level_m": 3.4},
    {"name": "강남역 빗물펌프장", "region": "강남구",   "latitude": 37.4979, "longitude": 127.0276, "capacity_m3s":  60.0, "pump_count": 5, "warn_level_m": 2.2, "high_level_m": 3.2, "flood_level_m": 4.2},
    {"name": "삼성 빗물펌프장",   "region": "강남구",   "latitude": 37.5140, "longitude": 127.0565, "capacity_m3s":  41.0, "pump_count": 4, "warn_level_m": 1.9, "high_level_m": 2.9, "flood_level_m": 3.7},
    {"name": "잠실 빗물펌프장",   "region": "송파구",   "latitude": 37.5133, "longitude": 127.1000, "capacity_m3s":  46.0, "pump_count": 4, "warn_level_m": 2.0, "high_level_m": 3.0, "flood_level_m": 3.9},
    {"name": "석촌 빗물펌프장",   "region": "송파구",   "latitude": 37.5064, "longitude": 127.1060, "capacity_m3s":  31.0, "pump_count": 3, "warn_level_m": 1.6, "high_level_m": 2.5, "flood_level_m": 3.3},
    {"name": "천호 빗물펌프장",   "region": "강동구",   "latitude": 37.5386, "longitude": 127.1238, "capacity_m3s":  37.0, "pump_count": 3, "warn_level_m": 1.8, "high_level_m": 2.7, "flood_level_m": 3.5},
    {"name": "성내 빗물펌프장",   "region": "강동구",   "latitude": 37.5319, "longitude": 127.1261, "capacity_m3s":  33.0, "pump_count": 3, "warn_level_m": 1.7, "high_level_m": 2.6, "flood_level_m": 3.4},
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
