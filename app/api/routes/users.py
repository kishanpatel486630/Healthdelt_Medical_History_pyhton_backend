from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_auth_service, get_user_service
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.models import User, MedicalHistory, Report, Prescription, EmergencyContact, AuditLog, RefreshToken
from app.security import verify_password, get_password_hash

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    profile = user_service.get_profile(db, current_user)
    return {"success": True, "user": profile}


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
def update_profile(req: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    updated = user_service.update_profile(db, current_user, req.model_dump(exclude_unset=True))
    return {"success": True, "message": "Profile updated", "user": updated}


class ChangePasswordRequest(BaseModel):
	currentPassword: str
	newPassword: str


@router.put("/me/password")
def change_password(
	req: ChangePasswordRequest,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db),
	auth_service: AuthService = Depends(get_auth_service),
):
	if not verify_password(req.currentPassword, current_user.passwordHash):
		raise HTTPException(status_code=400, detail="Current password is incorrect")
	current_user.passwordHash = get_password_hash(req.newPassword)
	# Revoke all refresh tokens via AuthService
	auth_service.revoke_tokens(db, current_user.id)
	db.add(AuditLog(userId=current_user.id, action="PASSWORD_CHANGE", resource="user"))
	db.commit()
	return {"success": True, "message": "Password changed. Please log in again on other devices."}


@router.get("/me/emergency-contacts")
def get_emergency_contacts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    contacts = user_service.list_emergency_contacts(db, current_user)
    return {"success": True, "contacts": contacts}


class AddContactRequest(BaseModel):
	name: str
	relation: str
	phone: str
	email: Optional[str] = None
	isPrimary: Optional[bool] = False


@router.post("/me/emergency-contacts", status_code=201)
def add_emergency_contact(req: AddContactRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    contact = user_service.add_emergency_contact(db, current_user, req.model_dump())
    return {"success": True, "contact": contact}


@router.delete("/me/emergency-contacts/{contact_id}")
def delete_emergency_contact(contact_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    user_service.delete_emergency_contact(db, current_user, contact_id)
    return {"success": True, "message": "Contact deleted"}


@router.get("/me/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), user_service: UserService = Depends(get_user_service)):
    stats = user_service.get_stats(db, current_user)
    return {"success": True, "stats": stats}
