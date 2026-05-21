import os
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Report, AuditLog

router = APIRouter(prefix="/api/reports", tags=["reports"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "reports")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("")
def list_reports(
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Report).filter(Report.userId == current_user.id)
    if type:
        query = query.filter(Report.reportType == type)

    total = query.count()
    reports = query.order_by(Report.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "success": True,
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "reportType": r.reportType,
                "fileUrl": r.fileUrl,
                "fileSize": r.fileSize,
                "mimeType": r.mimeType,
                "category": r.category,
                "notes": r.notes,
                "labName": r.labName,
                "reportDate": r.reportDate.isoformat() if r.reportDate else None,
                "createdAt": r.createdAt.isoformat() if r.createdAt else None,
            }
            for r in reports
        ],
        "total": total,
        "page": page,
        "totalPages": max(1, -(-total // limit)),
    }


@router.get("/{report_id}")
def get_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.userId == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "success": True,
        "report": {
            "id": report.id,
            "name": report.name,
            "reportType": report.reportType,
            "fileUrl": report.fileUrl,
        },
    }


@router.post("/upload", status_code=201)
async def upload_report(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    reportType: Optional[str] = Form("OTHER"),
    category: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    labName: Optional[str] = Form(None),
    reportDate: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    unique_suffix = f"{int(time.time())}-{int(time.time() * 1000) % 1000000}"
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{unique_suffix}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    from datetime import datetime

    report = Report(
        userId=current_user.id,
        name=name or file.filename,
        reportType=reportType or "OTHER",
        fileUrl=f"/uploads/reports/{filename}",
        fileSize=f"{len(content) / 1024:.1f} KB",
        mimeType=file.content_type,
        category=category,
        notes=notes,
        labName=labName,
        reportDate=datetime.fromisoformat(reportDate) if reportDate else datetime.utcnow(),
    )
    db.add(report)

    audit = AuditLog(userId=current_user.id, action="UPLOAD", resource="report", resourceId=report.id)
    db.add(audit)

    db.commit()
    db.refresh(report)

    return {"success": True, "report": {"id": report.id, "name": report.name, "fileUrl": report.fileUrl}}


@router.delete("/{report_id}")
def delete_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Report).filter(Report.id == report_id, Report.userId == current_user.id).delete()
    db.commit()
    return {"success": True, "message": "Report deleted"}


@router.post("/{report_id}/share")
def share_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id, Report.userId == current_user.id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    audit = AuditLog(userId=current_user.id, action="SHARE", resource="report", resourceId=report.id)
    db.add(audit)
    db.commit()
    return {"success": True}
