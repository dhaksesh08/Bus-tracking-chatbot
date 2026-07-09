"""
Router: Broadcast announcements to all students/parents on a given route
(e.g. "Bus 4 cancelled today"). Actual message sending is delegated to the
Telegram/WhatsApp bot services via simple HTTP calls or shared functions -
here we just queue/log the broadcast and expose it for the bots to pick up.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db, Student

router = APIRouter(prefix="/broadcast", tags=["Broadcast"])


class BroadcastRequest(BaseModel):
    route_id: Optional[int] = None   # if None, broadcast to everyone
    message: str


@router.post("/send")
def broadcast_message(payload: BroadcastRequest, db: Session = Depends(get_db)):
    """
    Returns the list of recipients (chat IDs / phone numbers) that should
    receive this message. The actual send happens in the bot process -
    this keeps the backend decoupled from messaging-platform specifics.

    In a production setup you'd likely call this internally and then loop
    over recipients from within the bot service directly.
    """
    query = db.query(Student).filter(Student.notifications_enabled == True)
    if payload.route_id is not None:
        query = query.filter(Student.route_id == payload.route_id)

    recipients = query.all()

    return {
        "message": payload.message,
        "recipient_count": len(recipients),
        "telegram_chat_ids": [s.telegram_chat_id for s in recipients if s.telegram_chat_id],
        "whatsapp_numbers": [s.whatsapp_number for s in recipients if s.whatsapp_number],
    }
