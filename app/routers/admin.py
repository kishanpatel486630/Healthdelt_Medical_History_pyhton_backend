from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Report, AuditLog, Prescription, Appointment, MedicalHistory

router = APIRouter(prefix="/api/admin", tags=["admin"])


def check_admin(current_user: User = Depends(get_current_user)):
    """Verify user is an admin."""
    if current_user.role not in ("ADMIN", "DOCTOR"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ── LIST ALL USERS ───────────────────────────────────────────
@router.get("/users")
def list_users(
    skip: int = 0,
    limit: int = 50,
    page: int = 1,
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """List all users with optional role filter and pagination."""
    # Support both page-based and offset-based pagination
    if page > 0:
        skip = (page - 1) * limit
    
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    if search:
        lower_search = f"%{search.lower()}%"
        query = query.filter(
            (User.fullName.ilike(lower_search)) |
            (User.email.ilike(lower_search)) |
            (User.mobile.ilike(lower_search))
        )
    
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "page": page,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "fullName": u.fullName,
                "role": u.role,
                "status": u.status,
                "mobile": u.mobile,
                "createdAt": u.createdAt.isoformat() if u.createdAt else None,
            }
            for u in users
        ],
    }


# ── GET USER DETAILS ─────────────────────────────────────────
@router.get("/users/{user_id}")
def get_user_details(
    user_id: str,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """Get detailed info about a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Count related records
    total_reports = db.query(Report).filter(Report.userId == user_id).count()
    total_prescriptions = db.query(Prescription).filter(Prescription.patientId == user_id).count()
    total_appointments = db.query(Appointment).filter(Appointment.patientId == user_id).count()
    total_histories = db.query(MedicalHistory).filter(MedicalHistory.userId == user_id).count()
    
    return {
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "fullName": user.fullName,
            "role": user.role,
            "status": user.status,
            "mobile": user.mobile,
            "avatar": user.avatar,
            "bloodGroup": user.bloodGroup,
            "gender": user.gender,
            "createdAt": user.createdAt.isoformat() if user.createdAt else None,
            "updatedAt": user.updatedAt.isoformat() if user.updatedAt else None,
            "stats": {
                "totalReports": total_reports,
                "totalPrescriptions": total_prescriptions,
                "totalAppointments": total_appointments,
                "totalMedicalHistories": total_histories,
            },
        },
    }


# ── LIST ALL REPORTS ────────────────────────────────────────
@router.get("/reports")
def list_reports(
    skip: int = 0,
    limit: int = 50,
    user_id: Optional[str] = None,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """List all reports with optional user filter."""
    query = db.query(Report)
    
    if user_id:
        query = query.filter(Report.userId == user_id)
    
    total = query.count()
    reports = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "reports": [
            {
                "id": r.id,
                "userId": r.userId,
                "name": r.name,
                "reportType": r.reportType,
                "category": r.category,
                "labName": r.labName,
                "reportDate": r.reportDate.isoformat() if r.reportDate else None,
                "createdAt": r.createdAt.isoformat() if r.createdAt else None,
                "fileUrl": r.fileUrl,
                "fileSize": r.fileSize,
            }
            for r in reports
        ],
    }


# ── SYSTEM STATISTICS ────────────────────────────────────────
@router.get("/stats")
def get_system_stats(
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """Get system-wide statistics."""
    total_users = db.query(User).count()
    total_patients = db.query(User).filter(User.role == "PATIENT").count()
    total_doctors = db.query(User).filter(User.role == "DOCTOR").count()
    total_reports = db.query(Report).count()
    total_prescriptions = db.query(Prescription).count()
    total_appointments = db.query(Appointment).count()
    total_medical_histories = db.query(MedicalHistory).count()
    
    active_users = db.query(User).filter(User.status == "ACTIVE").count()
    suspended_users = db.query(User).filter(User.status == "SUSPENDED").count()
    
    return {
        "success": True,
        "stats": {
            "users": {
                "total": total_users,
                "patients": total_patients,
                "doctors": total_doctors,
                "active": active_users,
                "suspended": suspended_users,
            },
            "data": {
                "totalReports": total_reports,
                "totalPrescriptions": total_prescriptions,
                "totalAppointments": total_appointments,
                "totalMedicalHistories": total_medical_histories,
            },
        },
    }


# ── AUDIT LOGS ───────────────────────────────────────────────
@router.get("/audit-logs")
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """Get audit logs with optional filters."""
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.userId == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    
    total = query.count()
    logs = query.order_by(AuditLog.createdAt.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "userId": log.userId,
                "action": log.action,
                "resource": log.resource,
                "resourceId": log.resourceId,
                "details": log.details,
                "createdAt": log.createdAt.isoformat() if log.createdAt else None,
            }
            for log in logs
        ],
    }


# ── UPDATE USER STATUS ───────────────────────────────────────
class UpdateUserStatusRequest(BaseModel):
    status: str


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    req: UpdateUserStatusRequest,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """Update a user's status (ACTIVE, SUSPENDED, etc.)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id and req.status == "SUSPENDED":
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")
    
    old_status = user.status
    user.status = req.status
    audit = AuditLog(
        userId=current_user.id,
        action=f"UPDATE_USER_STATUS",
        resource="user",
        resourceId=user_id,
        details=f"Changed from {old_status} to {req.status}",
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"User status updated to {req.status}"}


# ── SUSPEND/UNSUSPEND USER ───────────────────────────────────
@router.put("/users/{user_id}/suspend")
def suspend_user(
    user_id: str,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """Suspend a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own account")
    
    user.status = "SUSPENDED"
    audit = AuditLog(
        userId=current_user.id,
        action="SUSPEND_USER",
        resource="user",
        resourceId=user_id,
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"User {user_id} suspended"}


@router.put("/users/{user_id}/unsuspend")
def unsuspend_user(
    user_id: str,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db),
):
    """Unsuspend a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "ACTIVE"
    audit = AuditLog(
        userId=current_user.id,
        action="UNSUSPEND_USER",
        resource="user",
        resourceId=user_id,
    )
    db.add(audit)
    db.commit()
    
    return {"success": True, "message": f"User {user_id} unsuspended"}
