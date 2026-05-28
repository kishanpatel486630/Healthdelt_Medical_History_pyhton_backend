from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Doctor, User
from app.dependencies import get_doctor_service
from app.services.doctor_service import DoctorService

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("")
def list_doctors(search: Optional[str] = None, specialization: Optional[str] = None, db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	result = doctor_service.list_doctors(db, search=search, specialization=specialization)
	return {"success": True, "doctors": result}


@router.get("/{doctor_id}")
def get_doctor(doctor_id: str, db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	info = doctor_service.get_doctor_by_id(db, doctor_id)
	if not info:
		return {"success": False, "error": "Doctor not found"}
	return {"success": True, "doctor": info}
