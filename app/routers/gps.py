"""
Router: GPS data ingestion (from tracker hardware or simulator) and
bus status retrieval (used by the chatbots).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db, Bus, GPSPing
from app.models.schemas import GPSPingCreate, GPSPingResponse, BusStatusResponse
from app.services.geo_utils import (
    find_nearest_stop, estimate_eta_minutes, get_status_text, get_latest_ping
)
from app.services.alert_engine import run_all_checks

router = APIRouter(prefix="/gps", tags=["GPS Tracking"])


@router.post("/ping", response_model=GPSPingResponse)
def receive_gps_ping(payload: GPSPingCreate, db: Session = Depends(get_db)):
    """
    Endpoint that the GPS tracker (real hardware or simulator) calls
    every N seconds to report its current location.
    """
    bus = db.query(Bus).filter(Bus.bus_number == payload.bus_number).first()
    if not bus:
        raise HTTPException(status_code=404, detail=f"Bus '{payload.bus_number}' not found")

    ping = GPSPing(
        bus_id=bus.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        speed_kmph=payload.speed_kmph,
    )
    db.add(ping)
    db.commit()
    db.refresh(ping)

    # Run alert checks in the background of this request (kept synchronous
    # for simplicity in v1; move to a background task/queue for production)
    run_all_checks(db, bus, payload.latitude, payload.longitude)

    return ping


@router.get("/status/{bus_number}", response_model=BusStatusResponse)
def get_bus_status(bus_number: str, db: Session = Depends(get_db)):
    """
    Returns the latest known status of a bus: location, nearest stop,
    distance, ETA, and a human-readable status string.
    This is the primary endpoint the chatbots will call.
    """
    bus = db.query(Bus).filter(Bus.bus_number == bus_number).first()
    if not bus:
        raise HTTPException(status_code=404, detail=f"Bus '{bus_number}' not found")

    latest = get_latest_ping(db, bus.id)
    if not latest:
        raise HTTPException(status_code=404, detail="No GPS data received yet for this bus")

    nearest_stop, distance = (None, None)
    eta = None
    if bus.route_id:
        nearest_stop, distance = find_nearest_stop(db, bus.route_id, latest.latitude, latest.longitude)
        if nearest_stop and distance is not None:
            eta = estimate_eta_minutes(distance, latest.speed_kmph)

    status_text = get_status_text(latest.speed_kmph, eta if eta is not None else 999)

    return BusStatusResponse(
        bus_number=bus.bus_number,
        latitude=latest.latitude,
        longitude=latest.longitude,
        speed_kmph=latest.speed_kmph,
        last_updated=latest.timestamp,
        nearest_stop_name=nearest_stop.name if nearest_stop else None,
        distance_to_stop_km=round(distance, 2) if distance is not None else None,
        eta_minutes=eta,
        status_text=status_text,
    )


@router.get("/all-buses")
def get_all_buses_status(db: Session = Depends(get_db)):
    """Returns latest status for every active bus - used by the admin dashboard."""
    buses = db.query(Bus).filter(Bus.is_active == True).all()
    results = []

    for bus in buses:
        latest = get_latest_ping(db, bus.id)
        if latest:
            results.append({
                "bus_number": bus.bus_number,
                "latitude": latest.latitude,
                "longitude": latest.longitude,
                "speed_kmph": latest.speed_kmph,
                "last_updated": latest.timestamp,
            })
        else:
            results.append({
                "bus_number": bus.bus_number,
                "latitude": None,
                "longitude": None,
                "speed_kmph": None,
                "last_updated": None,
                "note": "No data received yet"
            })

    return results
