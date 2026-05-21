from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, MedicalHistory, AuditLog

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(MedicalHistory).filter(MedicalHistory.userId == current_user.id)
    if type:
        query = query.filter(MedicalHistory.visitType == type)

    total = query.count()
    records = query.order_by(MedicalHistory.visitDate.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "success": True,
        "records": [
            {
                "id": r.id,
                "title": r.title,
                "diagnosis": r.diagnosis,
                "notes": r.notes,
                "visitType": r.visitType,
                "status": r.status,
                "visitDate": r.visitDate.isoformat() if r.visitDate else None,
                "symptoms": r.symptoms,
                "vitals": r.vitals,
                "createdAt": r.createdAt.isoformat() if r.createdAt else None,
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "totalPages": max(1, -(-total // limit)),
    }


@router.get("/{record_id}")
def get_history(record_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(MedicalHistory).filter(
        MedicalHistory.id == record_id, MedicalHistory.userId == current_user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return {
        "success": True,
        "record": {
            "id": record.id,
            "title": record.title,
            "diagnosis": record.diagnosis,
            "notes": record.notes,
            "visitType": record.visitType,
            "status": record.status,
            "visitDate": record.visitDate.isoformat() if record.visitDate else None,
            "symptoms": record.symptoms,
            "vitals": record.vitals,
        },
    }


class CreateHistoryRequest(BaseModel):
    title: str
    visitDate: str
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
    visitType: Optional[str] = "CONSULTATION"
    symptoms: Optional[str] = None
    vitals: Optional[str] = None
    doctorId: Optional[str] = None


@router.post("", status_code=201)
def create_history(req: CreateHistoryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = MedicalHistory(
        userId=current_user.id,
        doctorId=req.doctorId,
        title=req.title,
        diagnosis=req.diagnosis,
        notes=req.notes,
        visitType=req.visitType,
        visitDate=datetime.fromisoformat(req.visitDate),
        symptoms=req.symptoms,
        vitals=req.vitals,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "record": {"id": record.id, "title": record.title}}


@router.put("/{record_id}")
def update_history(record_id: str, req: CreateHistoryRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(MedicalHistory).filter(
        MedicalHistory.id == record_id, MedicalHistory.userId == current_user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "visitDate" and value:
            setattr(record, field, datetime.fromisoformat(value))
        else:
            setattr(record, field, value)

    db.commit()
    return {"success": True, "record": {"id": record.id}}


@router.delete("/{record_id}")
def delete_history(record_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(MedicalHistory).filter(
        MedicalHistory.id == record_id, MedicalHistory.userId == current_user.id
    ).delete()
    db.commit()
    return {"success": True, "message": "Record deleted"}
