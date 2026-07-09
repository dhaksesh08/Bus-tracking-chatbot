"""
Alert detection logic. Run periodically (or after every ping) to detect:
- Bus stopped/idle too long (possible breakdown)
- Bus significantly off-route (deviation)
- Bus delayed beyond expected threshold

This is intentionally simple/rule-based for v1. Can be made smarter later
(e.g. comparing against historical average trip times per segment).
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.database import GPSPing, Alert, Bus
from app.services.geo_utils import haversine_km, find_nearest_stop

# --- Tunable thresholds ---
STOPPED_THRESHOLD_MINUTES = 10      # bus hasn't moved meaningfully in this long
DEVIATION_THRESHOLD_KM = 1.5        # how far off-route before flagging
SPEED_MOVEMENT_THRESHOLD_KMPH = 2.0


def check_stopped_too_long(db: Session, bus_id: int) -> Alert | None:
    """
    Flags a bus that has reported near-zero speed for longer than the
    threshold - could indicate breakdown, traffic jam, or accident.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=STOPPED_THRESHOLD_MINUTES)

    recent_pings = (
        db.query(GPSPing)
        .filter(GPSPing.bus_id == bus_id, GPSPing.timestamp >= cutoff)
        .order_by(GPSPing.timestamp.asc())
        .all()
    )

    if len(recent_pings) < 2:
        return None  # not enough data yet

    all_stationary = all(
        (p.speed_kmph or 0) < SPEED_MOVEMENT_THRESHOLD_KMPH for p in recent_pings
    )

    if all_stationary:
        alert = Alert(
            bus_id=bus_id,
            alert_type="STOPPED",
            message=(
                f"Bus has shown minimal movement for over "
                f"{STOPPED_THRESHOLD_MINUTES} minutes. Possible breakdown, "
                f"traffic, or signal issue - please verify."
            ),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    return None


def check_route_deviation(db: Session, bus_id: int, route_id: int,
                           lat: float, lon: float) -> Alert | None:
    """
    Flags a bus that is unusually far from any stop on its assigned route,
    suggesting it has gone off the expected path.
    """
    nearest_stop, distance = find_nearest_stop(db, route_id, lat, lon)

    if nearest_stop is None:
        return None

    if distance > DEVIATION_THRESHOLD_KM:
        alert = Alert(
            bus_id=bus_id,
            alert_type="DEVIATION",
            message=(
                f"Bus is {distance:.2f} km away from the nearest expected "
                f"stop ({nearest_stop.name}), beyond the "
                f"{DEVIATION_THRESHOLD_KM} km threshold. Possible route deviation."
            ),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    return None


def run_all_checks(db: Session, bus: Bus, lat: float, lon: float):
    """Convenience wrapper to run every alert check after a new ping."""
    triggered = []

    stopped_alert = check_stopped_too_long(db, bus.id)
    if stopped_alert:
        triggered.append(stopped_alert)

    if bus.route_id:
        deviation_alert = check_route_deviation(db, bus.id, bus.route_id, lat, lon)
        if deviation_alert:
            triggered.append(deviation_alert)

    return triggered
