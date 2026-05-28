"""QR service."""

from __future__ import annotations

from io import BytesIO
import json
from typing import Any

import qrcode
from fastapi.responses import StreamingResponse


def build_qr_response(payload: Any, title: str) -> StreamingResponse:
	"""Return a PNG QR code response for any JSON-serializable payload."""

	img = qrcode.make(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
	buffer = BytesIO()
	img.save(buffer, format="PNG")
	buffer.seek(0)
	return StreamingResponse(
		buffer,
		media_type="image/png",
		headers={"Content-Disposition": f'inline; filename="{title}.png"'},
	)


def build_patient_payload(patient: Any) -> dict[str, Any]:
	return {
		"type": "patient",
		"patientId": patient.id,
		"fullName": patient.fullName,
		"generatedAt": patient.createdAt.isoformat() if getattr(patient, "createdAt", None) else None,
	}


def build_medical_record_payload(record: Any) -> dict[str, Any]:
	return {
		"type": "medical-record",
		"recordId": record.id,
		"patientId": record.userId,
		"title": record.title,
	}


def build_prescription_payload(prescription: Any) -> dict[str, Any]:
	return {
		"type": "prescription",
		"prescriptionId": prescription.id,
		"patientId": prescription.patientId,
		"title": prescription.title,
	}


class QrService:
	"""Class wrapper for QR helper functions to support DI and mocking."""

	def build_qr_response(self, payload: Any, title: str) -> StreamingResponse:
		return build_qr_response(payload, title)

	def build_patient_payload(self, patient: Any) -> dict[str, Any]:
		return build_patient_payload(patient)

	def build_medical_record_payload(self, record: Any) -> dict[str, Any]:
		return build_medical_record_payload(record)

	def build_prescription_payload(self, prescription: Any) -> dict[str, Any]:
		return build_prescription_payload(prescription)
