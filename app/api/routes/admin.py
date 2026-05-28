from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Report, AuditLog, Prescription, Appointment, MedicalHistory

router = APIRouter(prefix="/api/admin", tags=["admin"])


def check_admin(current_user: User = Depends(get_current_user)):
	if current_user.role not in ("ADMIN", "DOCTOR"):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
	return current_user


@router.get("/users")
def list_users(skip: int = 0, limit: int = 50, page: int = 1, role: Optional[str] = None, search: Optional[str] = None, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	if page > 0:
		skip = (page - 1) * limit
	query = db.query(User)
	if role:
		query = query.filter(User.role == role)
	if search:
		lower_search = f"%{search.lower()}%"
		query = query.filter((User.fullName.ilike(lower_search)) | (User.email.ilike(lower_search)) | (User.mobile.ilike(lower_search)))
	total = query.count()
	users = query.offset(skip).limit(limit).all()
	return {"success": True, "total": total, "skip": skip, "limit": limit, "page": page, "users": [{"id": u.id, "email": u.email, "fullName": u.fullName, "role": u.role, "status": u.status, "mobile": u.mobile, "createdAt": u.createdAt.isoformat() if u.createdAt else None} for u in users]}


@router.get("/users/{user_id}")
def get_user_details(user_id: str, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	total_reports = db.query(Report).filter(Report.userId == user_id).count()
	total_prescriptions = db.query(Prescription).filter(Prescription.patientId == user_id).count()
	total_appointments = db.query(Appointment).filter(Appointment.patientId == user_id).count()
	total_histories = db.query(MedicalHistory).filter(MedicalHistory.userId == user_id).count()
	return {"success": True, "user": {"id": user.id, "email": user.email, "fullName": user.fullName, "role": user.role, "status": user.status, "mobile": user.mobile, "avatar": user.avatar, "bloodGroup": user.bloodGroup, "gender": user.gender, "createdAt": user.createdAt.isoformat() if user.createdAt else None, "updatedAt": user.updatedAt.isoformat() if user.updatedAt else None, "stats": {"totalReports": total_reports, "totalPrescriptions": total_prescriptions, "totalAppointments": total_appointments, "totalMedicalHistories": total_histories}}}


@router.get("/reports")
def list_reports(skip: int = 0, limit: int = 50, user_id: Optional[str] = None, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	query = db.query(Report)
	if user_id:
		query = query.filter(Report.userId == user_id)
	total = query.count()
	reports = query.offset(skip).limit(limit).all()
	return {"success": True, "total": total, "skip": skip, "limit": limit, "reports": [{"id": r.id, "userId": r.userId, "name": r.name, "reportType": r.reportType, "category": r.category, "labName": r.labName, "reportDate": r.reportDate.isoformat() if r.reportDate else None, "createdAt": r.createdAt.isoformat() if r.createdAt else None, "fileUrl": r.fileUrl, "fileSize": r.fileSize} for r in reports]}


@router.get("/stats")
def get_system_stats(current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	return {"success": True, "stats": {"users": {"total": db.query(User).count(), "patients": db.query(User).filter(User.role == "PATIENT").count(), "doctors": db.query(User).filter(User.role == "DOCTOR").count(), "active": db.query(User).filter(User.status == "ACTIVE").count(), "suspended": db.query(User).filter(User.status == "SUSPENDED").count()}, "data": {"totalReports": db.query(Report).count(), "totalPrescriptions": db.query(Prescription).count(), "totalAppointments": db.query(Appointment).count(), "totalMedicalHistories": db.query(MedicalHistory).count()}}}


@router.get("/audit-logs")
def get_audit_logs(skip: int = 0, limit: int = 100, user_id: Optional[str] = None, action: Optional[str] = None, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	query = db.query(AuditLog)
	if user_id:
		query = query.filter(AuditLog.userId == user_id)
	if action:
		query = query.filter(AuditLog.action == action)
	total = query.count()
	logs = query.order_by(AuditLog.createdAt.desc()).offset(skip).limit(limit).all()
	return {"success": True, "total": total, "skip": skip, "limit": limit, "logs": [{"id": log.id, "userId": log.userId, "action": log.action, "resource": log.resource, "resourceId": log.resourceId, "details": log.details, "createdAt": log.createdAt.isoformat() if log.createdAt else None} for log in logs]}


class UpdateUserStatusRequest(BaseModel):
	status: str


@router.put("/users/{user_id}/status")
def update_user_status(user_id: str, req: UpdateUserStatusRequest, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	if user.id == current_user.id and req.status == "SUSPENDED":
		raise HTTPException(status_code=400, detail="Cannot suspend your own account")
	old_status = user.status
	user.status = req.status
	db.add(AuditLog(userId=current_user.id, action="UPDATE_USER_STATUS", resource="user", resourceId=user_id, details=f"Changed from {old_status} to {req.status}"))
	db.commit()
	return {"success": True, "message": f"User status updated to {req.status}"}


@router.put("/users/{user_id}/suspend")
def suspend_user(user_id: str, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	if user.id == current_user.id:
		raise HTTPException(status_code=400, detail="Cannot suspend your own account")
	user.status = "SUSPENDED"
	db.add(AuditLog(userId=current_user.id, action="SUSPEND_USER", resource="user", resourceId=user_id))
	db.commit()
	return {"success": True, "message": f"User {user_id} suspended"}


@router.put("/users/{user_id}/unsuspend")
def unsuspend_user(user_id: str, current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
	user = db.query(User).filter(User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	user.status = "ACTIVE"
	db.add(AuditLog(userId=current_user.id, action="UNSUSPEND_USER", resource="user", resourceId=user_id))
	db.commit()
	return {"success": True, "message": f"User {user_id} unsuspended"}
