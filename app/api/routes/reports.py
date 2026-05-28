import os
import time
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user, get_upload_service
from app.models import User, Report, AuditLog
from app.services.upload_service import UploadService

router = APIRouter(prefix="/api/reports", tags=["reports"])



@router.get("")
def list_reports(type: Optional[str] = None, page: int = 1, limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	query = db.query(Report).filter(Report.userId == current_user.id)
	if type:
		query = query.filter(Report.reportType == type)
	total = query.count()
	reports = query.order_by(Report.createdAt.desc()).offset((page - 1) * limit).limit(limit).all()
	return {"success": True, "reports": [{"id": r.id, "name": r.name, "reportType": r.reportType, "fileUrl": r.fileUrl, "fileSize": r.fileSize, "mimeType": r.mimeType, "category": r.category, "notes": r.notes, "labName": r.labName, "reportDate": r.reportDate.isoformat() if r.reportDate else None, "createdAt": r.createdAt.isoformat() if r.createdAt else None} for r in reports], "total": total, "page": page, "totalPages": max(1, -(-total // limit))}


@router.get("/{report_id}")
def get_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
	report = db.query(Report).filter(Report.id == report_id, Report.userId == current_user.id).first()
	if not report:
		raise HTTPException(status_code=404, detail="Report not found")
	return {"success": True, "report": {"id": report.id, "name": report.name, "reportType": report.reportType, "fileUrl": report.fileUrl}}


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
	upload_service: UploadService = Depends(get_upload_service),
):
	# Save file under 'reports' folder using upload service
	info = await upload_service.save(file, folder="reports")
	report = Report(
		userId=current_user.id,
		name=name or file.filename,
		reportType=reportType or "OTHER",
		fileUrl=f"/uploads/{info['path']}",
		fileSize=f"{info['size'] / 1024:.1f} KB",
		mimeType=info.get("contentType"),
		category=category,
		notes=notes,
		labName=labName,
		reportDate=datetime.fromisoformat(reportDate) if reportDate else datetime.now(UTC),
	)
	db.add(report)
	db.add(AuditLog(userId=current_user.id, action="UPLOAD", resource="report", resourceId=report.id))
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
	db.add(AuditLog(userId=current_user.id, action="SHARE", resource="report", resourceId=report.id))
	db.commit()
	return {"success": True}
