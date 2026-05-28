"""Upload service."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile


def resolve_upload_root(upload_dir: str) -> Path:
	root = Path(upload_dir).resolve()
	root.mkdir(parents=True, exist_ok=True)
	return root


def safe_relative_path(base_dir: Path, relative_path: str) -> Path:
	target = (base_dir / relative_path).resolve()
	if base_dir not in target.parents and target != base_dir:
		raise HTTPException(status_code=400, detail="Invalid upload path")
	return target


def list_directory(base_dir: Path, folder: str = "") -> list[dict[str, Any]]:
	target_dir = safe_relative_path(base_dir, folder) if folder else base_dir
	if not target_dir.exists() or not target_dir.is_dir():
		raise HTTPException(status_code=404, detail="Folder not found")

	items: list[dict[str, Any]] = []
	for entry in sorted(target_dir.iterdir(), key=lambda path: path.name.lower()):
		items.append(
			{
				"name": entry.name,
				"path": str(entry.relative_to(base_dir)).replace(os.sep, "/"),
				"isDirectory": entry.is_dir(),
				"size": entry.stat().st_size if entry.is_file() else None,
			}
		)
	return items


async def save_upload(base_dir: Path, file: UploadFile, folder: str = "") -> dict[str, Any]:
	target_dir = safe_relative_path(base_dir, folder) if folder else base_dir
	target_dir.mkdir(parents=True, exist_ok=True)

	filename = file.filename or "upload.bin"
	destination = (target_dir / filename).resolve()
	if base_dir not in destination.parents and destination != base_dir:
		raise HTTPException(status_code=400, detail="Invalid upload path")

	content = await file.read()
	destination.write_bytes(content)

	return {
		"name": filename,
		"path": destination.relative_to(base_dir).as_posix(),
		"size": len(content),
		"contentType": file.content_type,
	}


def delete_path(base_dir: Path, relative_path: str) -> Path:
	target = safe_relative_path(base_dir, relative_path)
	if not target.exists() or not target.is_file():
		raise HTTPException(status_code=404, detail="File not found")
	target.unlink()
	return target


class UploadService:
	"""Lightweight class wrapper to use with FastAPI dependencies."""

	def __init__(self, upload_dir: str | Path):
		self.root = resolve_upload_root(str(upload_dir))

	def resolve_root(self) -> Path:
		return self.root

	def list(self, folder: str = "") -> list[dict[str, Any]]:
		return list_directory(self.root, folder)

	async def save(self, file: UploadFile, folder: str = "") -> dict[str, Any]:
		return await save_upload(self.root, file, folder)

	def delete(self, relative_path: str) -> Path:
		return delete_path(self.root, relative_path)
