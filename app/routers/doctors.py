from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Doctor, User

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("")
def list_doctors(
    search: Optional[str] = None,
    specialization: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Doctor).filter(Doctor.verificationStatus == "VERIFIED")

    if specialization:
        query = query.filter(Doctor.specialization == specialization)

    doctors = query.all()

    result = []
    for d in doctors:
        user = db.query(User).filter(User.id == d.userId).first()
        if search and user:
            if search.lower() not in (user.fullName or "").lower() and search.lower() not in (d.specialization or "").lower():
                continue
        result.append({
            "id": d.id,
            "specialization": d.specialization,
            "hospital": d.hospital,
            "rating": d.rating,
            "consultationFee": d.consultationFee,
            "user": {
                "fullName": user.fullName if user else None,
                "avatar": user.avatar if user else None,
            },
        })

    return {"success": True, "doctors": result}


@router.get("/{doctor_id}")
def get_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"success": False, "error": "Doctor not found"}

    user = db.query(User).filter(User.id == doctor.userId).first()

    return {
        "success": True,
        "doctor": {
            "id": doctor.id,
            "specialization": doctor.specialization,
            "hospital": doctor.hospital,
            "rating": doctor.rating,
            "bio": doctor.bio,
            "user": {
                "fullName": user.fullName if user else None,
                "email": user.email if user else None,
                "avatar": user.avatar if user else None,
            },
        },
    }
