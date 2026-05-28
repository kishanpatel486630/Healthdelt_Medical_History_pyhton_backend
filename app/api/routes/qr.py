from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user, get_qr_service
from app.models import User, MedicalHistory, Prescription
from app.services.qr_service import QrService

router = APIRouter(prefix="/api/qr", tags=["qr"])


class GenerateQrRequest(BaseModel):
	data: dict
	title: str = "qr-code"


@router.post("/generate")
def generate_qr(req: GenerateQrRequest, qr_service: QrService = Depends(get_qr_service)):
	return qr_service.build_qr_response(req.data, req.title)


@router.get("/patient/{patient_id}")
def patient_qr(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), qr_service: QrService = Depends(get_qr_service)):
	if current_user.role not in ("DOCTOR", "ADMIN") and current_user.id != patient_id:
		raise HTTPException(status_code=403, detail="Not authorized to access this QR code")

	patient = db.query(User).filter(User.id == patient_id, User.role == "PATIENT").first()
	if not patient:
		raise HTTPException(status_code=404, detail="Patient not found")

	return qr_service.build_qr_response(qr_service.build_patient_payload(patient), f"patient-{patient_id}")


@router.get("/medical-record/{record_id}")
def medical_record_qr(record_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), qr_service: QrService = Depends(get_qr_service)):
	record = db.query(MedicalHistory).filter(MedicalHistory.id == record_id).first()
	if not record:
		raise HTTPException(status_code=404, detail="Medical record not found")

	if current_user.role not in ("DOCTOR", "ADMIN") and current_user.id != record.userId:
		raise HTTPException(status_code=403, detail="Not authorized to access this QR code")

	return qr_service.build_qr_response(qr_service.build_medical_record_payload(record), f"record-{record_id}")


@router.get("/prescription/{prescription_id}")
def prescription_qr(prescription_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), qr_service: QrService = Depends(get_qr_service)):
	prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
	if not prescription:
		raise HTTPException(status_code=404, detail="Prescription not found")

	if current_user.role not in ("DOCTOR", "ADMIN") and current_user.id != prescription.patientId:
		raise HTTPException(status_code=403, detail="Not authorized to access this QR code")

	return qr_service.build_qr_response(qr_service.build_prescription_payload(prescription), f"prescription-{prescription_id}")
