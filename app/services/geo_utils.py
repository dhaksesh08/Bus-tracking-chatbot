"""
Geo-utility functions: distance calculation (Haversine formula), nearest-stop
lookup, and ETA estimation.
"""

import math
from sqlalchemy.orm import Session
from app.models.database import Stop, GPSPing


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two lat/long points in km.
    This is the standard way to measure distance between GPS coordinates.
    """
    R = 6371.0  # Earth radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def find_nearest_stop(db: Session, route_id: int, lat: float, lon: float):
    """Given a bus's current position, find the nearest stop on its route."""
    stops = db.query(Stop).filter(Stop.route_id == route_id).all()
    if not stops:
        return None, None

    nearest = None
    min_dist = float("inf")

    for stop in stops:
        dist = haversine_km(lat, lon, stop.latitude, stop.longitude)
        if dist < min_dist:
            min_dist = dist
            nearest = stop

    return nearest, min_dist


def estimate_eta_minutes(distance_km: float, speed_kmph: float) -> float:
    """
    Simple ETA estimate = distance / speed.
    Falls back to an assumed average city-bus speed (25 km/h) if the bus
    is currently stationary or speed data is missing/zero, so we don't
    divide by zero or return an infinite ETA.
    """
    effective_speed = speed_kmph if speed_kmph and speed_kmph > 3 else 25.0
    eta_hours = distance_km / effective_speed
    return round(eta_hours * 60, 1)


def get_status_text(speed_kmph: float, eta_minutes: float) -> str:
    """Human-friendly status string for chatbot responses."""
    if speed_kmph is not None and speed_kmph < 2:
        return "Stopped / Idle"
    if eta_minutes <= 2:
        return "Arriving now"
    if eta_minutes <= 10:
        return "Approaching your stop"
    return "On the way"


def get_latest_ping(db: Session, bus_id: int):
    """Fetch the most recent GPS ping for a given bus."""
    return (
        db.query(GPSPing)
        .filter(GPSPing.bus_id == bus_id)
        .order_by(GPSPing.timestamp.desc())
        .first()
    )
