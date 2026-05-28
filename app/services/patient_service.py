"""Patient service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Appointment, Doctor, MedicalHistory, Notification, Prescription, User


def require_doctor_or_admin(current_user: User) -> User:
	if current_user.role not in ("DOCTOR", "ADMIN"):
		raise PermissionError("Doctor access required")
	return current_user


def get_doctor_profile(current_user: User, db: Session) -> Doctor:
	doctor = db.query(Doctor).filter(Doctor.userId == current_user.id).first()
	if not doctor:
		raise LookupError("Doctor profile not found")
	return doctor


def get_patient_ids_for_doctor(db: Session, doctor_id: str) -> list[str]:
	patient_ids = [
		*[row.patientId for row in db.query(Appointment.patientId).filter(Appointment.doctorId == doctor_id).all()],
		*[row.patientId for row in db.query(Prescription.patientId).filter(Prescription.doctorId == doctor_id).all()],
		*[row.userId for row in db.query(MedicalHistory.userId).filter(MedicalHistory.doctorId == doctor_id).all()],
	]
	return sorted(set(patient_ids))


def filter_patients(query, search: str | None):
	if search:
		return query.filter(User.fullName.contains(search) | User.email.contains(search) | User.mobile.contains(search))
	return query


def build_patient_summary(patient: User) -> dict:
	return {
		"id": patient.id,
		"fullName": patient.fullName,
		"email": patient.email,
		"mobile": patient.mobile,
		"bloodGroup": patient.bloodGroup,
		"gender": patient.gender,
		"dateOfBirth": patient.dateOfBirth,
	}


def build_patient_detail(patient: User, histories: list[MedicalHistory]) -> dict:
	return {
		"id": patient.id,
		"fullName": patient.fullName,
		"email": patient.email,
		"mobile": patient.mobile,
		"bloodGroup": patient.bloodGroup,
		"gender": patient.gender,
		"createdAt": patient.createdAt.isoformat() if patient.createdAt else None,
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


def link_patient_record(db: Session, doctor: Doctor, patient: User, doctor_name: str | None) -> Notification:
	existing = db.query(MedicalHistory).filter(
		MedicalHistory.userId == patient.id,
		MedicalHistory.doctorId == doctor.id,
		MedicalHistory.title == "Patient Linked to Doctor Profile",
	).first()
	if not existing:
		db.add(
			MedicalHistory(
				userId=patient.id,
				doctorId=doctor.id,
				title="Patient Linked to Doctor Profile",
				notes="Initial link established by doctor.",
				visitType="CONSULTATION",
				status="COMPLETED",
				visitDate=datetime.now(UTC),
			)
		)
	notification = Notification(
		userId=patient.id,
		title="New Doctor Linked",
		message=f"Dr. {doctor_name or 'A doctor'} has added you to their practice.",
		type="SYSTEM",
		actionUrl=f"/doctors/{doctor.id}",
	)
	db.add(notification)
	return notification


class PatientService:
	"""Wrapper for patient-related helpers for DI."""

	def __init__(self):
		pass

	def require_doctor_or_admin(self, current_user: User) -> User:
		return require_doctor_or_admin(current_user)

	def get_doctor_profile(self, current_user: User, db: Session) -> Doctor:
		return get_doctor_profile(current_user, db)

	def link_patient(self, db: Session, doctor: Doctor, patient: User, doctor_name: str | None) -> Notification:
		return link_patient_record(db, doctor, patient, doctor_name)
