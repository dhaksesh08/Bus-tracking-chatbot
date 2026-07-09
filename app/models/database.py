"""
Database models for the Bus Tracker system.
Uses SQLAlchemy ORM with SQLite for local development.
Swap SQLALCHEMY_DATABASE_URL to a PostgreSQL URL for production.
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Boolean, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Database connection setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "bus_tracker.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    bus_number = Column(String, unique=True, index=True, nullable=False)   # e.g. "BUS-04"
    driver_name = Column(String, nullable=True)
    driver_phone = Column(String, nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    route = relationship("Route", back_populates="buses")
    pings = relationship("GPSPing", back_populates="bus")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)          # e.g. "Route 4 - Tiruppur to Campus"
    description = Column(Text, nullable=True)

    buses = relationship("Bus", back_populates="route")
    stops = relationship("Stop", back_populates="route", order_by="Stop.sequence")


class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    name = Column(String, nullable=False)           # e.g. "Avinashi Road Stop"
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    sequence = Column(Integer, nullable=False)       # order of stop on the route

    route = relationship("Route", back_populates="stops")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    student_code = Column(String, unique=True, index=True)   # institution roll/ID
    stop_id = Column(Integer, ForeignKey("stops.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=True)

    # Messaging identifiers - a student/parent links one or both
    telegram_chat_id = Column(String, unique=True, nullable=True, index=True)
    whatsapp_number = Column(String, unique=True, nullable=True, index=True)

    notifications_enabled = Column(Boolean, default=True)


class GPSPing(Base):
    """A single GPS data point received from a bus tracker (real or simulated)."""
    __tablename__ = "gps_pings"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed_kmph = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    bus = relationship("Bus", back_populates="pings")


class Alert(Base):
    """Log of alerts raised by the system (delay, deviation, breakdown, etc.)."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    alert_type = Column(String, nullable=False)   # DELAY, DEVIATION, STOPPED, ARRIVED
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)


def init_db():
    """Create all tables. Call once at startup."""
    Base.metadata.create_all(bind=engine)
