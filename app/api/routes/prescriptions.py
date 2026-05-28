from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Prescription, AuditLog

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


@router.get("")
def list_prescriptions(status: Optional[str] = None, page: int = 1, limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	query = db.query(Prescription).filter(Prescription.patientId == current_user.id)
	if status:
		query = query.filter(Prescription.status == status)
	total = query.count()
	prescriptions = query.order_by(Prescription.issuedDate.desc()).offset((page - 1) * limit).limit(limit).all()
	return {"success": True, "prescriptions": [{"id": p.id, "title": p.title, "diagnosis": p.diagnosis, "notes": p.notes, "status": p.status, "issuedDate": p.issuedDate.isoformat() if p.issuedDate else None, "expiryDate": p.expiryDate.isoformat() if p.expiryDate else None, "medicines": [{"id": m.id, "name": m.name, "dosage": m.dosage, "frequency": m.frequency, "timing": m.timing, "duration": m.duration, "instructions": m.instructions} for m in p.medicines]} for p in prescriptions], "total": total, "page": page, "totalPages": max(1, -(-total // limit))}


@router.get("/active")
def get_active_prescriptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	prescriptions = db.query(Prescription).filter(Prescription.patientId == current_user.id, Prescription.status == "ACTIVE").order_by(Prescription.issuedDate.desc()).all()
	return {"success": True, "prescriptions": [{"id": p.id, "title": p.title, "diagnosis": p.diagnosis, "status": p.status, "issuedDate": p.issuedDate.isoformat() if p.issuedDate else None, "medicines": [{"id": m.id, "name": m.name, "dosage": m.dosage, "frequency": m.frequency} for m in p.medicines]} for p in prescriptions]}


@router.get("/{prescription_id}")
def get_prescription(prescription_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	p = db.query(Prescription).filter(Prescription.id == prescription_id, Prescription.patientId == current_user.id).first()
	if not p:
		raise HTTPException(status_code=404, detail="Prescription not found")
	return {"success": True, "prescription": {"id": p.id, "title": p.title, "diagnosis": p.diagnosis, "notes": p.notes, "status": p.status, "issuedDate": p.issuedDate.isoformat() if p.issuedDate else None, "medicines": [{"id": m.id, "name": m.name, "dosage": m.dosage, "frequency": m.frequency, "timing": m.timing, "duration": m.duration, "instructions": m.instructions} for m in p.medicines]}}


@router.post("/{prescription_id}/share")
def share_prescription(prescription_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	p = db.query(Prescription).filter(Prescription.id == prescription_id, Prescription.patientId == current_user.id).first()
	if not p:
		raise HTTPException(status_code=404, detail="Prescription not found")
	db.add(AuditLog(userId=current_user.id, action="SHARE", resource="prescription", resourceId=p.id))
	db.commit()
	return {"success": True}
