from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Appointment, Notification

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.get("")
def list_appointments(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Appointment).filter(Appointment.patientId == current_user.id)
    if status:
        query = query.filter(Appointment.status == status)

    total = query.count()
    appointments = query.order_by(Appointment.date.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "success": True,
        "appointments": [
            {
                "id": a.id,
                "title": a.title,
                "type": a.type,
                "status": a.status,
                "date": a.date.isoformat() if a.date else None,
                "startTime": a.startTime,
                "endTime": a.endTime,
                "location": a.location,
                "meetingUrl": a.meetingUrl,
                "notes": a.notes,
                "createdAt": a.createdAt.isoformat() if a.createdAt else None,
            }
            for a in appointments
        ],
        "total": total,
        "page": page,
        "totalPages": max(1, -(-total // limit)),
    }


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.patientId == current_user.id
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {"success": True, "appointment": {"id": appointment.id, "title": appointment.title, "status": appointment.status}}


class BookAppointmentRequest(BaseModel):
    doctorId: str
    title: str
    date: str
    startTime: str
    type: Optional[str] = "IN_PERSON"
    endTime: Optional[str] = None
    location: Optional[str] = None
    meetingUrl: Optional[str] = None
    notes: Optional[str] = None


@router.post("", status_code=201)
def book_appointment(req: BookAppointmentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = Appointment(
        patientId=current_user.id,
        doctorId=req.doctorId,
        title=req.title,
        type=req.type,
        date=datetime.fromisoformat(req.date),
        startTime=req.startTime,
        endTime=req.endTime,
        location=req.location,
        meetingUrl=req.meetingUrl,
        notes=req.notes,
    )
    db.add(appointment)

    notif = Notification(
        userId=current_user.id,
        title="Appointment Booked",
        message=f'Your appointment "{req.title}" has been confirmed.',
        type="APPOINTMENT",
        actionUrl="/dashboard/appointments",
    )
    db.add(notif)

    db.commit()
    db.refresh(appointment)

    return {"success": True, "appointment": {"id": appointment.id, "title": appointment.title}}


@router.put("/{appointment_id}")
def reschedule(appointment_id: str, req: BookAppointmentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.patientId == current_user.id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if req.date:
        appt.date = datetime.fromisoformat(req.date)
    if req.startTime:
        appt.startTime = req.startTime
    if req.endTime:
        appt.endTime = req.endTime

    db.commit()
    return {"success": True, "appointment": {"id": appt.id}}


@router.delete("/{appointment_id}")
def cancel_appointment(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.patientId == current_user.id
    ).update({"status": "CANCELLED"})
    db.commit()
    return {"success": True, "message": "Appointment cancelled"}
