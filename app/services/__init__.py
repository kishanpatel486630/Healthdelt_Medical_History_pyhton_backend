"""Services package."""

from .ai_service import suggest_follow_up_flags, suggest_patient_questions, summarize_record, summarize_text
from .auth_service import (
	build_auth_response,
	create_otp,
	create_user_account,
	get_user_by_identifier,
	issue_tokens,
	mark_otp_used,
	normalize_identifier,
	revoke_refresh_tokens,
	validate_password,
	write_audit,
)
from .doctor_service import (
	allow_security_pin,
	build_doctor_id_card,
	get_doctor_patient_ids,
	build_doctor_stats,
	build_patient_history,
	build_patient_overview,
	build_prescription_template,
	create_link_notification,
	get_doctor_profile,
	list_master_data,
	serialize_doctor_profile,
	update_doctor_profile,
	update_prescription_template,
)
from .patient_service import (
	build_patient_detail,
	build_patient_summary,
	filter_patients,
	get_doctor_profile as get_patient_doctor_profile,
	get_patient_ids_for_doctor,
	link_patient_record,
	require_doctor_or_admin,
)
from .pdf_service import build_text_lines, render_simple_pdf, render_text_pdf_bytes
from .qr_service import (
	build_medical_record_payload,
	build_patient_payload,
	build_prescription_payload,
	build_qr_response,
)
from .upload_service import delete_path, list_directory, resolve_upload_root, safe_relative_path, save_upload

__all__ = [
	# auth
	"build_auth_response",
	"create_otp",
	"create_user_account",
	"get_user_by_identifier",
	"issue_tokens",
	"mark_otp_used",
	"normalize_identifier",
	"revoke_refresh_tokens",
	"validate_password",
	"write_audit",
	# doctor
	"allow_security_pin",
	"build_doctor_id_card",
	"get_doctor_patient_ids",
	"build_doctor_stats",
	"build_patient_history",
	"build_patient_overview",
	"build_prescription_template",
	"create_link_notification",
	"get_doctor_profile",
	"list_master_data",
	"serialize_doctor_profile",
	"update_doctor_profile",
	"update_prescription_template",
	# patient
	"build_patient_detail",
	"build_patient_summary",
	"filter_patients",
	"get_patient_ids_for_doctor",
	"get_patient_doctor_profile",
	"link_patient_record",
	"require_doctor_or_admin",
	# pdf
	"build_text_lines",
	"render_simple_pdf",
	"render_text_pdf_bytes",
	# qr
	"build_medical_record_payload",
	"build_patient_payload",
	"build_prescription_payload",
	"build_qr_response",
	# upload
	"delete_path",
	"list_directory",
	"resolve_upload_root",
	"safe_relative_path",
	"save_upload",
	# ai
	"suggest_follow_up_flags",
	"suggest_patient_questions",
	"summarize_record",
	"summarize_text",
]
