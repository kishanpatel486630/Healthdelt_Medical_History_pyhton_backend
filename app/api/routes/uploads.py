from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.dependencies import get_current_user
from app.models import User
from app.services.upload_service import (
    delete_path,
    list_directory,
    resolve_upload_root,
    safe_relative_path,
    save_upload,
)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

BASE_UPLOAD_DIR = resolve_upload_root(settings.UPLOAD_DIR)


@router.get("")
def list_uploads(folder: str = "", current_user: User = Depends(get_current_user)):
	return {"success": True, "folder": folder, "items": list_directory(BASE_UPLOAD_DIR, folder)}


@router.post("")
async def upload_file(file: UploadFile = File(...), folder: str = Query(""), current_user: User = Depends(get_current_user)):
	return {"success": True, "file": await save_upload(BASE_UPLOAD_DIR, file, folder)}


@router.get("/{file_path:path}")
def download_file(file_path: str, current_user: User = Depends(get_current_user)):
	target = safe_relative_path(BASE_UPLOAD_DIR, file_path)
	if not target.exists() or not target.is_file():
		raise HTTPException(status_code=404, detail="File not found")
	return FileResponse(target)


@router.delete("/{file_path:path}")
def delete_file(file_path: str, current_user: User = Depends(get_current_user)):
	delete_path(BASE_UPLOAD_DIR, file_path)
	return {"success": True, "message": "File deleted"}
