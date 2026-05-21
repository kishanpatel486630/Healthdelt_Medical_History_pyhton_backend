from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, MedicalHistory, Report, Prescription, EmergencyContact, AuditLog, RefreshToken
from app.security import verify_password, get_password_hash

router = APIRouter(prefix="/api/users", tags=["users"])


# ── GET CURRENT USER PROFILE ──────────────────────────────────
@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "mobile": user.mobile,
            "fullName": user.fullName,
            "role": user.role,
            "avatar": user.avatar,
            "bloodGroup": user.bloodGroup,
            "allergies": user.allergies,
            "chronicDisease": user.chronicDisease,
            "dateOfBirth": user.dateOfBirth,
            "gender": user.gender,
            "weight": user.weight,
            "height": user.height,
            "insuranceId": user.insuranceId,
            "createdAt": user.createdAt.isoformat() if user.createdAt else None,
            "doctorProfile": None,  # TODO: serialize if exists
            "emergencyContacts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "relation": c.relation,
                    "phone": c.phone,
                    "email": c.email,
                    "isPrimary": c.isPrimary,
                }
                for c in user.emergency_contacts
            ],
        },
    }


# ── UPDATE PROFILE ────────────────────────────────────────────
class UpdateProfileRequest(BaseModel):
    fullName: Optional[str] = None
    mobile: Optional[str] = None
    bloodGroup: Optional[str] = None
    allergies: Optional[str] = None
    chronicDisease: Optional[str] = None
    dateOfBirth: Optional[str] = None
    gender: Optional[str] = None
    weight: Optional[str] = None
    height: Optional[str] = None
    avatar: Optional[str] = None


@router.put("/me")
def update_profile(
    req: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user.id).first()

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    audit = AuditLog(userId=user.id, action="UPDATE_PROFILE", resource="user")
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": "Profile updated",
        "user": {"id": user.id, "fullName": user.fullName},
    }


# ── CHANGE PASSWORD ───────────────────────────────────────────
class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


@router.put("/me/password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(req.currentPassword, current_user.passwordHash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.passwordHash = get_password_hash(req.newPassword)

    # Revoke all refresh tokens
    db.query(RefreshToken).filter(RefreshToken.userId == current_user.id).update({"isRevoked": True})

    audit = AuditLog(userId=current_user.id, action="PASSWORD_CHANGE", resource="user")
    db.add(audit)
    db.commit()

    return {"success": True, "message": "Password changed. Please log in again on other devices."}


# ── EMERGENCY CONTACTS ───────────────────────────────────────
@router.get("/me/emergency-contacts")
def get_emergency_contacts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contacts = db.query(EmergencyContact).filter(EmergencyContact.userId == current_user.id).all()
    return {
        "success": True,
        "contacts": [
            {
                "id": c.id,
                "name": c.name,
                "relation": c.relation,
                "phone": c.phone,
                "email": c.email,
                "isPrimary": c.isPrimary,
            }
            for c in contacts
        ],
    }


class AddContactRequest(BaseModel):
    name: str
    relation: str
    phone: str
    email: Optional[str] = None
    isPrimary: Optional[bool] = False


@router.post("/me/emergency-contacts", status_code=201)
def add_emergency_contact(
    req: AddContactRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = EmergencyContact(
        userId=current_user.id,
        name=req.name,
        relation=req.relation,
        phone=req.phone,
        email=req.email,
        isPrimary=req.isPrimary,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return {"success": True, "contact": {"id": contact.id, "name": contact.name}}


@router.delete("/me/emergency-contacts/{contact_id}")
def delete_emergency_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(EmergencyContact).filter(
        EmergencyContact.id == contact_id,
        EmergencyContact.userId == current_user.id,
    ).delete()
    db.commit()
    return {"success": True, "message": "Contact deleted"}


# ── GET USER STATS ────────────────────────────────────────────
@router.get("/me/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total_consultations = db.query(MedicalHistory).filter(MedicalHistory.userId == current_user.id).count()
    total_reports = db.query(Report).filter(Report.userId == current_user.id).count()
    total_prescriptions = db.query(Prescription).filter(
        Prescription.patientId == current_user.id, Prescription.status == "ACTIVE"
    ).count()

    return {
        "success": True,
        "stats": {
            "totalConsultations": total_consultations,
            "totalReports": total_reports,
            "totalPrescriptions": total_prescriptions,
        },
    }
