import json
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.dependencies import get_current_user, get_patient_service, get_doctor_service
from app.services.patient_service import PatientService
from app.services.doctor_service import DoctorService
from app.models import User, Doctor, Appointment, Prescription, Medicine, MedicalHistory, Notification, MasterMedicine, MasterDisease, MasterLabTest

router = APIRouter(prefix="/api/doctors/me", tags=["doctor-me"])


def get_doctor(current_user: User, db: Session) -> Doctor:
	if current_user.role != "DOCTOR":
		raise HTTPException(status_code=403, detail="Not authorized as doctor")
	doctor = db.query(Doctor).filter(Doctor.userId == current_user.id).first()
	if not doctor:
		raise HTTPException(status_code=404, detail="Doctor profile not found")
	return doctor


@router.get("/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
	return {"success": True, "stats": {"totalPatients": db.query(Appointment.patientId).filter(Appointment.doctorId == doctor.id).distinct().count(), "todayPatients": db.query(Appointment).filter(Appointment.doctorId == doctor.id, Appointment.date >= today).count(), "newPatientsThisMonth": 0, "totalPrescriptions": db.query(Prescription).filter(Prescription.doctorId == doctor.id).count(), "pendingAppointments": db.query(Appointment).filter(Appointment.doctorId == doctor.id, Appointment.status == "PENDING").count(), "completedConsultations": 0, "activeFollowups": 0, "recentReports": 0}}


@router.get("/patients")
def get_patients(search: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	patient_ids = list(set([r.patientId for r in db.query(Appointment.patientId).filter(Appointment.doctorId == doctor.id).all()] + [r.patientId for r in db.query(Prescription.patientId).filter(Prescription.doctorId == doctor.id).all()] + [r.userId for r in db.query(MedicalHistory.userId).filter(MedicalHistory.doctorId == doctor.id).all()]))
	if not patient_ids:
		return {"success": True, "patients": []}
	query = db.query(User).filter(User.id.in_(patient_ids))
	if search:
		query = query.filter(User.fullName.contains(search) | User.email.contains(search) | User.mobile.contains(search))
	patients = query.all()
	return {"success": True, "patients": [{"id": p.id, "fullName": p.fullName, "email": p.email, "mobile": p.mobile, "bloodGroup": p.bloodGroup, "gender": p.gender} for p in patients]}


@router.get("/patients/{patient_id}")
def get_patient_detail(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor_service.get_doctor_profile(current_user, db)
	patient = db.query(User).filter(User.id == patient_id).first()
	if not patient:
		raise HTTPException(status_code=404, detail="Patient not found")
	history = db.query(MedicalHistory).filter(MedicalHistory.userId == patient_id).order_by(MedicalHistory.visitDate.desc()).all()
	return {"success": True, "patient": {"id": patient.id, "fullName": patient.fullName, "email": patient.email, "mobile": patient.mobile, "bloodGroup": patient.bloodGroup, "gender": patient.gender}, "history": [{"id": h.id, "title": h.title, "visitDate": h.visitDate.isoformat() if h.visitDate else None} for h in history]}


class LinkPatientRequest(BaseModel):
	patientId: str


@router.post("/patients/link")
def link_patient(req: LinkPatientRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), patient_service: PatientService = Depends(get_patient_service), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	patient = db.query(User).filter(User.id == req.patientId).first()
	if not patient:
		raise HTTPException(status_code=404, detail="Patient not found")
	if patient.role != "PATIENT":
		raise HTTPException(status_code=400, detail="ID does not belong to a patient")
	# For linking patients we reuse the patient service helper
	patient_service.link_patient(db, doctor, patient, current_user.fullName)
	db.commit()
	return {"success": True, "message": "Patient successfully added to your list"}


class MedicineInput(BaseModel):
	name: str
	dosage: str
	frequency: str
	timing: Optional[str] = None
	duration: Optional[str] = None
	instructions: Optional[str] = None


class CreatePrescriptionRequest(BaseModel):
	patientId: str
	title: str
	diagnosis: Optional[str] = None
	notes: Optional[str] = None
	medicines: Optional[List[MedicineInput]] = []


@router.post("/prescriptions")
def create_prescription(req: CreatePrescriptionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	patient = db.query(User).filter(User.id == req.patientId).first()
	if not patient or patient.role != "PATIENT":
		raise HTTPException(status_code=400, detail="Invalid patient ID")
	prescription = Prescription(patientId=req.patientId, doctorId=doctor.id, title=req.title, diagnosis=req.diagnosis, notes=req.notes)
	db.add(prescription)
	db.flush()
	for med in req.medicines:
		db.add(Medicine(prescriptionId=prescription.id, name=med.name, dosage=med.dosage, frequency=med.frequency, timing=med.timing, duration=med.duration, instructions=med.instructions))
	db.commit()
	db.refresh(prescription)
	return {"success": True, "prescription": {"id": prescription.id, "title": prescription.title}}


@router.get("/prescriptions")
def get_prescriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	prescriptions = db.query(Prescription).filter(Prescription.doctorId == doctor.id).order_by(Prescription.issuedDate.desc()).all()
	return {"success": True, "prescriptions": [{"id": p.id, "title": p.title, "diagnosis": p.diagnosis, "status": p.status, "issuedDate": p.issuedDate.isoformat() if p.issuedDate else None, "medicines": [{"id": m.id, "name": m.name, "dosage": m.dosage, "frequency": m.frequency} for m in p.medicines]} for p in prescriptions]}


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	return {"success": True, "doctor": {"id": doctor.id, "specialization": doctor.specialization, "subSpecialization": doctor.subSpecialization, "qualifications": doctor.qualifications, "licenseNumber": doctor.licenseNumber, "registrationNumber": doctor.registrationNumber, "hospital": doctor.hospital, "clinicName": doctor.clinicName, "clinicAddress": doctor.clinicAddress, "experienceYears": doctor.experienceYears, "consultationFee": doctor.consultationFee, "languages": doctor.languages, "workingHours": doctor.workingHours, "bio": doctor.bio, "rating": doctor.rating, "verificationStatus": doctor.verificationStatus, "user": {"fullName": current_user.fullName, "email": current_user.email, "mobile": current_user.mobile}}}


@router.put("/profile")
def update_profile(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	for field in ["specialization", "subSpecialization", "qualifications", "licenseNumber", "registrationNumber", "hospital", "clinicName", "clinicAddress", "experienceYears", "previousExperience", "consultationFee", "languages", "workingHours", "bio"]:
		if field in data:
			val = data[field]
			if field == "experienceYears" and val is not None:
				val = int(val)
			if field == "consultationFee" and val is not None:
				val = float(val)
			setattr(doctor, field, val)
	if data.get("verificationStatus") == "PENDING":
		doctor.verificationStatus = "UNDER_REVIEW"
	db.commit()
	return {"success": True, "doctor": {"id": doctor.id}}


@router.get("/prescription-format")
def get_prescription_format(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	return {"success": True, "format": json.loads(doctor.prescriptionFormat) if doctor.prescriptionFormat else None}


@router.put("/prescription-format")
def update_prescription_format(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	doctor.prescriptionFormat = json.dumps(data)
	db.commit()
	return {"success": True, "message": "Prescription format updated"}


class VerifyPinRequest(BaseModel):
	secret: Optional[str] = None
	pin: Optional[str] = None


@router.post("/verify-pin")
def verify_pin(req: VerifyPinRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	if doctor.registrationNumber and req.secret == doctor.registrationNumber:
		return {"success": True}
	if doctor.securityPin and doctor.secretCode and doctor.securityPin == req.pin and doctor.secretCode == req.secret:
		return {"success": True}
	raise HTTPException(status_code=401, detail="Invalid security credentials")


@router.get("/id-card")
def get_id_card(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor = doctor_service.get_doctor_profile(current_user, db)
	return {"success": True, "doctor": {"id": doctor.id, "specialization": doctor.specialization, "licenseNumber": doctor.licenseNumber, "hospital": doctor.hospital, "user": {"fullName": current_user.fullName, "email": current_user.email, "mobile": current_user.mobile, "avatar": current_user.avatar}}}


@router.get("/masters/{master_type}")
def get_masters(master_type: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), doctor_service: DoctorService = Depends(get_doctor_service)):
	doctor_service.get_doctor_profile(current_user, db)
	if master_type == "medicine":
		data = [{"id": i.id, "name": i.name, "genericName": i.genericName} for i in db.query(MasterMedicine).all()]
	elif master_type == "disease":
		data = [{"id": i.id, "name": i.name, "icdCode": i.icdCode} for i in db.query(MasterDisease).all()]
	elif master_type == "labtest":
		data = [{"id": i.id, "name": i.name, "category": i.category} for i in db.query(MasterLabTest).all()]
	else:
		data = []
	return {"success": True, "data": data}