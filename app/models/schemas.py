"""
Pydantic schemas used for API request/response validation.
Keeping these separate from the SQLAlchemy models (database.py) is best practice -
it decouples your API contract from your DB schema.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# GPS Ping
# ---------------------------------------------------------------------------

class GPSPingCreate(BaseModel):
    bus_number: str
    latitude: float
    longitude: float
    speed_kmph: Optional[float] = 0.0


class GPSPingResponse(BaseModel):
    bus_id: int
    latitude: float
    longitude: float
    speed_kmph: float
    timestamp: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Bus status (what the chatbot will query)
# ---------------------------------------------------------------------------

class BusStatusResponse(BaseModel):
    bus_number: str
    latitude: float
    longitude: float
    speed_kmph: float
    last_updated: datetime
    nearest_stop_name: Optional[str] = None
    distance_to_stop_km: Optional[float] = None
    eta_minutes: Optional[float] = None
    status_text: str   # e.g. "On the way", "Delayed", "Stopped"


# ---------------------------------------------------------------------------
# Bus / Route / Stop management
# ---------------------------------------------------------------------------

class StopCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    sequence: int


class RouteCreate(BaseModel):
    name: str
    description: Optional[str] = None


class BusCreate(BaseModel):
    bus_number: str
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    route_id: Optional[int] = None


class StudentLink(BaseModel):
    student_code: str
    name: str
    stop_id: int
    route_id: int
    telegram_chat_id: Optional[str] = None
    whatsapp_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    bus_id: int
    alert_type: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
