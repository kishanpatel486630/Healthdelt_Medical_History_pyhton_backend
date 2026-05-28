from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_patient_service
from app.models import User, Doctor, Appointment, Prescription, MedicalHistory, Notification
from app.services.patient_service import PatientService

router = APIRouter(prefix="/api/patients", tags=["patients"])


def require_doctor_or_admin(current_user: User = Depends(get_current_user)):
	if current_user.role not in ("DOCTOR", "ADMIN"):
		raise HTTPException(status_code=403, detail="Doctor access required")
	return current_user


def get_doctor_profile(current_user: User, db: Session) -> Doctor:
	doctor = db.query(Doctor).filter(Doctor.userId == current_user.id).first()
	if not doctor:
		raise HTTPException(status_code=404, detail="Doctor profile not found")
	return doctor


@router.get("")
def list_patients(
	search: Optional[str] = None,
	current_user: User = Depends(require_doctor_or_admin),
	db: Session = Depends(get_db),
):
	doctor = get_doctor_profile(current_user, db)

	patient_ids = list(set(
		[row.patientId for row in db.query(Appointment.patientId).filter(Appointment.doctorId == doctor.id).all()] +
		[row.patientId for row in db.query(Prescription.patientId).filter(Prescription.doctorId == doctor.id).all()] +
		[row.userId for row in db.query(MedicalHistory.userId).filter(MedicalHistory.doctorId == doctor.id).all()]
	))

	if not patient_ids:
		return {"success": True, "patients": []}

	query = db.query(User).filter(User.id.in_(patient_ids))
	if search:
		query = query.filter(
			User.fullName.contains(search) |
			User.email.contains(search) |
			User.mobile.contains(search)
		)

	patients = query.order_by(User.fullName.asc()).all()

	return {
		"success": True,
		"patients": [
			{
				"id": patient.id,
				"fullName": patient.fullName,
				"email": patient.email,
				"mobile": patient.mobile,
				"bloodGroup": patient.bloodGroup,
				"gender": patient.gender,
				"dateOfBirth": patient.dateOfBirth,
			}
			for patient in patients
		],
	}


@router.get("/{patient_id}")
def get_patient(
	patient_id: str,
	current_user: User = Depends(require_doctor_or_admin),
	db: Session = Depends(get_db),
):
	get_doctor_profile(current_user, db)

	patient = db.query(User).filter(User.id == patient_id, User.role == "PATIENT").first()
	if not patient:
		raise HTTPException(status_code=404, detail="Patient not found")

	histories = db.query(MedicalHistory).filter(MedicalHistory.userId == patient_id).order_by(MedicalHistory.visitDate.desc()).all()

	return {
		"success": True,
		"patient": {
			"id": patient.id,
			"fullName": patient.fullName,
			"email": patient.email,
			"mobile": patient.mobile,
			"bloodGroup": patient.bloodGroup,
			"gender": patient.gender,
			"createdAt": patient.createdAt.isoformat() if patient.createdAt else None,
		},
		"medicalRecords": [
			{
				"id": record.id,
				"title": record.title,
				"diagnosis": record.diagnosis,
				"visitType": record.visitType,
				"status": record.status,
				"visitDate": record.visitDate.isoformat() if record.visitDate else None,
			}
			for record in histories
		],
	}


class LinkPatientRequest(BaseModel):
	patientId: str


@router.post("/link")
def link_patient(
	req: LinkPatientRequest,
	current_user: User = Depends(require_doctor_or_admin),
	db: Session = Depends(get_db),
	patient_service: PatientService = Depends(get_patient_service),
):
	doctor = patient_service.get_doctor_profile(current_user, db)
	patient = db.query(User).filter(User.id == req.patientId, User.role == "PATIENT").first()
	if not patient:
		raise HTTPException(status_code=404, detail="Patient not found")

	patient_service.link_patient(db, doctor, patient, current_user.fullName)
	db.commit()

	return {"success": True, "message": "Patient successfully added to your list"}
