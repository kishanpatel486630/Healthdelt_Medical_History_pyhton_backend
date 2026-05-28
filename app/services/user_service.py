from sqlalchemy.orm import Session
from typing import Optional
from app.models import User, EmergencyContact, MedicalHistory, Report, Prescription, AuditLog


class UserService:
    """Service for user-related operations."""

    def get_profile(self, db: Session, user: User) -> dict:
        db_user = db.query(User).filter(User.id == user.id).first()
        return {
            "id": db_user.id,
            "email": db_user.email,
            "mobile": db_user.mobile,
            "fullName": db_user.fullName,
            "role": db_user.role,
            "avatar": db_user.avatar,
            "bloodGroup": db_user.bloodGroup,
            "allergies": db_user.allergies,
            "chronicDisease": db_user.chronicDisease,
            "dateOfBirth": db_user.dateOfBirth,
            "gender": db_user.gender,
            "weight": db_user.weight,
            "height": db_user.height,
            "insuranceId": db_user.insuranceId,
            "createdAt": db_user.createdAt.isoformat() if db_user.createdAt else None,
            "doctorProfile": None,
            "emergencyContacts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "relation": c.relation,
                    "phone": c.phone,
                    "email": c.email,
                    "isPrimary": c.isPrimary,
                }
                for c in db_user.emergency_contacts
            ],
        }

    def update_profile(self, db: Session, user: User, data: dict) -> dict:
        db_user = db.query(User).filter(User.id == user.id).first()
        for field, value in data.items():
            setattr(db_user, field, value)
        db.add(AuditLog(userId=user.id, action="UPDATE_PROFILE", resource="user"))
        db.commit()
        return {"id": db_user.id, "fullName": db_user.fullName}

    def list_emergency_contacts(self, db: Session, user: User) -> list[dict]:
        contacts = db.query(EmergencyContact).filter(EmergencyContact.userId == user.id).all()
        return [
            {"id": c.id, "name": c.name, "relation": c.relation, "phone": c.phone, "email": c.email, "isPrimary": c.isPrimary}
            for c in contacts
        ]

    def add_emergency_contact(self, db: Session, user: User, payload: dict) -> dict:
        contact = EmergencyContact(userId=user.id, name=payload.get("name"), relation=payload.get("relation"), phone=payload.get("phone"), email=payload.get("email"), isPrimary=payload.get("isPrimary", False))
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return {"id": contact.id, "name": contact.name}

    def delete_emergency_contact(self, db: Session, user: User, contact_id: str) -> None:
        db.query(EmergencyContact).filter(EmergencyContact.id == contact_id, EmergencyContact.userId == user.id).delete()
        db.commit()

    def get_stats(self, db: Session, user: User) -> dict:
        total_consultations = db.query(MedicalHistory).filter(MedicalHistory.userId == user.id).count()
        total_reports = db.query(Report).filter(Report.userId == user.id).count()
        total_prescriptions = db.query(Prescription).filter(Prescription.patientId == user.id, Prescription.status == "ACTIVE").count()
        return {"totalConsultations": total_consultations, "totalReports": total_reports, "totalPrescriptions": total_prescriptions}
