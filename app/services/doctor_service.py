from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Appointment, Doctor, MedicalHistory, MasterDisease, MasterLabTest, MasterMedicine, Notification, Prescription, User


class DoctorService:
	"""Class-based wrapper around doctor-related helpers for DI and testing."""

	def get_doctor_profile(self, current_user: User, db: Session) -> Doctor:
		return get_doctor_profile(current_user, db)

	def build_stats(self, dr: Doctor, db: Session) -> dict:
		return build_doctor_stats(db, dr)

	def list_patients(self, dr: Doctor, db: Session, **filters) -> list:
		ids = get_doctor_patient_ids(db, dr.id)
		query = db.query(User).filter(User.id.in_(ids))
		return [build_patient_overview(p) for p in query.all()]

	def get_patient_detail(self, dr: Doctor, patient_id: str, db: Session) -> dict:
		records = db.query(MedicalHistory).filter(MedicalHistory.userId == patient_id).order_by(MedicalHistory.visitDate.desc()).all()
		patient = db.query(User).filter(User.id == patient_id).first()
		return {"patient": build_patient_overview(patient), "history": build_patient_history(records)}

	def create_prescription(self, dr: Doctor, patient_id: str, payload: dict, db: Session) -> dict:
		pres = Prescription(patientId=patient_id, doctorId=dr.id, title=payload.get("title"), diagnosis=payload.get("diagnosis"), notes=payload.get("notes"))
		db.add(pres)
		db.flush()
		for med in payload.get("medicines", []):
			db.add(MedicalHistory())
		db.commit()
		return {"id": pres.id}

	def list_prescriptions(self, dr: Doctor, patient_id: str, db: Session) -> list:
		return db.query(Prescription).filter(Prescription.doctorId == dr.id, Prescription.patientId == patient_id).all()

	def get_prescription_format(self, dr: Doctor, db: Session) -> dict:
		return json.loads(dr.prescriptionFormat) if dr.prescriptionFormat else {}

	def update_prescription_format(self, dr: Doctor, new_format: dict, db: Session) -> dict:
		dr.prescriptionFormat = json.dumps(new_format)
		db.commit()
		return {"success": True}

	def verify_pin(self, dr: Doctor, pin: str) -> bool:
		return allow_security_pin(dr, None, pin)

	def get_id_card(self, dr: Doctor, db: Session) -> dict:
		return build_doctor_id_card(dr, db)

	def list_masters(self, db: Session) -> dict:
		return list_master_data(db, "medicine")

	def list_doctors(self, db: Session, search: str | None = None, specialization: str | None = None) -> list:
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
			result.append({"id": d.id, "specialization": d.specialization, "hospital": d.hospital, "rating": d.rating, "consultationFee": d.consultationFee, "user": {"fullName": user.fullName if user else None, "avatar": user.avatar if user else None}})
		return result

	def get_doctor_by_id(self, db: Session, doctor_id: str) -> dict | None:
		doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
		if not doctor:
			return None
		user = db.query(User).filter(User.id == doctor.userId).first()
		return {"id": doctor.id, "specialization": doctor.specialization, "hospital": doctor.hospital, "rating": doctor.rating, "bio": doctor.bio, "user": {"fullName": user.fullName if user else None, "email": user.email if user else None, "avatar": user.avatar if user else None}}


def get_doctor_profile(current_user: User, db: Session) -> Doctor:
	if current_user.role != "DOCTOR":
		raise PermissionError("Not authorized as doctor")
	doctor = db.query(Doctor).filter(Doctor.userId == current_user.id).first()
	if not doctor:
		raise LookupError("Doctor profile not found")
	return doctor


def get_doctor_patient_ids(db: Session, doctor_id: str) -> list[str]:
	ids = [
		*[row.patientId for row in db.query(Appointment.patientId).filter(Appointment.doctorId == doctor_id).all()],
		*[row.patientId for row in db.query(Prescription.patientId).filter(Prescription.doctorId == doctor_id).all()],
		*[row.userId for row in db.query(MedicalHistory.userId).filter(MedicalHistory.doctorId == doctor_id).all()],
	]
	return sorted(set(ids))


def build_doctor_stats(db: Session, doctor: Doctor) -> dict:
	today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
	return {
		"totalPatients": db.query(Appointment.patientId).filter(Appointment.doctorId == doctor.id).distinct().count(),
		"todayPatients": db.query(Appointment).filter(Appointment.doctorId == doctor.id, Appointment.date >= today).count(),
		"newPatientsThisMonth": 0,
		"totalPrescriptions": db.query(Prescription).filter(Prescription.doctorId == doctor.id).count(),
		"pendingAppointments": db.query(Appointment).filter(Appointment.doctorId == doctor.id, Appointment.status == "PENDING").count(),
		"completedConsultations": 0,
		"activeFollowups": 0,
		"recentReports": 0,
	}


def build_patient_overview(patient: User) -> dict:
	return {
		"id": patient.id,
		"fullName": patient.fullName,
		"email": patient.email,
		"mobile": patient.mobile,
		"bloodGroup": patient.bloodGroup,
		"gender": patient.gender,
		"dateOfBirth": patient.dateOfBirth,
	}


def build_patient_history(records: list[MedicalHistory]) -> list[dict]:
	return [
		{
			"id": record.id,
			"title": record.title,
			"diagnosis": record.diagnosis,
			"visitType": record.visitType,
			"status": record.status,
			"visitDate": record.visitDate.isoformat() if record.visitDate else None,
		}
		for record in records
	]


def serialize_doctor_profile(doctor: Doctor, current_user: User) -> dict:
	return {
		"id": doctor.id,
		"specialization": doctor.specialization,
		"subSpecialization": doctor.subSpecialization,
		"qualifications": doctor.qualifications,
		"licenseNumber": doctor.licenseNumber,
		"registrationNumber": doctor.registrationNumber,
		"hospital": doctor.hospital,
		"clinicName": doctor.clinicName,
		"clinicAddress": doctor.clinicAddress,
		"experienceYears": doctor.experienceYears,
		"consultationFee": doctor.consultationFee,
		"languages": doctor.languages,
		"workingHours": doctor.workingHours,
		"bio": doctor.bio,
		"rating": doctor.rating,
		"verificationStatus": doctor.verificationStatus,
		"user": {
			"fullName": current_user.fullName,
			"email": current_user.email,
			"mobile": current_user.mobile,
		},
	}


def update_doctor_profile(doctor: Doctor, data: dict) -> None:
	for field in [
		"specialization",
		"subSpecialization",
		"qualifications",
		"licenseNumber",
		"registrationNumber",
		"hospital",
		"clinicName",
		"clinicAddress",
		"experienceYears",
		"previousExperience",
		"consultationFee",
		"languages",
		"workingHours",
		"bio",
	]:
		if field in data:
			value = data[field]
			if field == "experienceYears" and value is not None:
				value = int(value)
			if field == "consultationFee" and value is not None:
				value = float(value)
			setattr(doctor, field, value)
	if data.get("verificationStatus") == "PENDING":
		doctor.verificationStatus = "UNDER_REVIEW"


def build_prescription_template(doctor: Doctor) -> dict:
	return json.loads(doctor.prescriptionFormat) if doctor.prescriptionFormat else {}


def update_prescription_template(doctor: Doctor, data: dict) -> None:
	doctor.prescriptionFormat = json.dumps(data)


def allow_security_pin(doctor: Doctor, secret: Optional[str], pin: Optional[str]) -> bool:
	if doctor.registrationNumber and secret == doctor.registrationNumber:
		return True
	if doctor.securityPin and doctor.secretCode and doctor.securityPin == pin and doctor.secretCode == secret:
		return True
	return False


def build_doctor_id_card(doctor: Doctor, current_user: User) -> dict:
	return {
		"id": doctor.id,
		"specialization": doctor.specialization,
		"licenseNumber": doctor.licenseNumber,
		"hospital": doctor.hospital,
		"user": {
			"fullName": current_user.fullName,
			"email": current_user.email,
			"mobile": current_user.mobile,
			"avatar": current_user.avatar,
		},
	}


def list_master_data(db: Session, master_type: str) -> list[dict]:
	if master_type == "medicine":
		return [{"id": row.id, "name": row.name, "genericName": row.genericName} for row in db.query(MasterMedicine).all()]
	if master_type == "disease":
		return [{"id": row.id, "name": row.name, "icdCode": row.icdCode} for row in db.query(MasterDisease).all()]
	if master_type == "labtest":
		return [{"id": row.id, "name": row.name, "category": row.category} for row in db.query(MasterLabTest).all()]
	return []


def create_link_notification(patient_id: str, doctor: Doctor, doctor_name: str) -> Notification:
	return Notification(
		userId=patient_id,
		title="New Doctor Linked",
		message=f"Dr. {doctor_name or 'A doctor'} has added you to their practice.",
		type="SYSTEM",
		actionUrl=f"/doctors/{doctor.id}",
	)
