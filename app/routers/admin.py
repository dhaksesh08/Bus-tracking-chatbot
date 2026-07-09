"""
Router: Admin-side management endpoints.
Used to set up buses, routes, stops, and link students/parents to a route+stop.
In a real deployment, these would be protected by admin authentication -
left out here for simplicity, but flagged in the README.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db, Bus, Route, Stop, Student, Alert
from app.models.schemas import BusCreate, RouteCreate, StopCreate, StudentLink, AlertResponse

router = APIRouter(prefix="/admin", tags=["Admin Management"])


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/routes")
def create_route(payload: RouteCreate, db: Session = Depends(get_db)):
    route = Route(name=payload.name, description=payload.description)
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.get("/routes")
def list_routes(db: Session = Depends(get_db)):
    return db.query(Route).all()


# ---------------------------------------------------------------------------
# Stops
# ---------------------------------------------------------------------------

@router.post("/routes/{route_id}/stops")
def add_stop(route_id: int, payload: StopCreate, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    stop = Stop(
        route_id=route_id,
        name=payload.name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        sequence=payload.sequence,
    )
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop


@router.get("/routes/{route_id}/stops")
def list_stops(route_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Stop)
        .filter(Stop.route_id == route_id)
        .order_by(Stop.sequence)
        .all()
    )


# ---------------------------------------------------------------------------
# Buses
# ---------------------------------------------------------------------------

@router.post("/buses")
def create_bus(payload: BusCreate, db: Session = Depends(get_db)):
    existing = db.query(Bus).filter(Bus.bus_number == payload.bus_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bus number already exists")

    bus = Bus(
        bus_number=payload.bus_number,
        driver_name=payload.driver_name,
        driver_phone=payload.driver_phone,
        route_id=payload.route_id,
    )
    db.add(bus)
    db.commit()
    db.refresh(bus)
    return bus


@router.get("/buses")
def list_buses(db: Session = Depends(get_db)):
    return db.query(Bus).all()


# ---------------------------------------------------------------------------
# Students (linking parent/student chat identity to a stop+route)
# ---------------------------------------------------------------------------

@router.post("/students/link")
def link_student(payload: StudentLink, db: Session = Depends(get_db)):
    """
    Links a student to a stop/route, and stores their Telegram chat ID
    and/or WhatsApp number so the bot knows where to send notifications.
    In production, this should be triggered via a self-service /register
    flow in the bot itself (see telegram_bot/bot.py) rather than only by admin.
    """
    existing = db.query(Student).filter(Student.student_code == payload.student_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student code already linked")

    student = Student(
        student_code=payload.student_code,
        name=payload.name,
        stop_id=payload.stop_id,
        route_id=payload.route_id,
        telegram_chat_id=payload.telegram_chat_id,
        whatsapp_number=payload.whatsapp_number,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/students")
def list_students(db: Session = Depends(get_db)):
    return db.query(Student).all()


# ---------------------------------------------------------------------------
# Alerts log
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db), unresolved_only: bool = False):
    query = db.query(Alert)
    if unresolved_only:
        query = query.filter(Alert.resolved == False)
    return query.order_by(Alert.created_at.desc()).all()
