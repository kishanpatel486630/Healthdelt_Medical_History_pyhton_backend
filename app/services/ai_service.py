"""AI service."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def summarize_text(text: str, max_length: int = 240) -> str:
	cleaned = " ".join(text.split())
	if len(cleaned) <= max_length:
		return cleaned
	return cleaned[: max_length - 3].rstrip() + "..."


def summarize_record(record: dict[str, Any]) -> dict[str, Any]:
	symptoms = record.get("symptoms") or ""
	diagnosis = record.get("diagnosis") or ""
	notes = record.get("notes") or ""
	summary_parts = [part for part in [diagnosis, symptoms, notes] if part]
	summary = summarize_text(". ".join(summary_parts), 220) if summary_parts else "No clinical notes provided."
	return {
		"summary": summary,
		"highlights": [
			value
			for value in [record.get("title"), record.get("visitType"), record.get("status")]
			if value
		],
	}


def suggest_follow_up_flags(records: Iterable[dict[str, Any]]) -> list[str]:
	flags: list[str] = []
	for record in records:
		status = (record.get("status") or "").upper()
		visit_type = (record.get("visitType") or "").upper()
		if status in {"PENDING", "UNDER_REVIEW"}:
			flags.append(f"Review pending record: {record.get('title', 'Untitled')}")
		if visit_type == "FOLLOW_UP":
			flags.append(f"Follow-up visit noted: {record.get('title', 'Untitled')}")
	return flags


def suggest_patient_questions(condition: str | None, symptoms: str | None) -> list[str]:
	prompts = []
	if condition:
		prompts.append(f"How long have you experienced {condition.lower()}?")
	if symptoms:
		prompts.append(f"Which symptom is most severe: {summarize_text(symptoms, 80)}?")
	prompts.extend([
		"Any recent medication changes?",
		"Have you noticed any new triggers or patterns?",
	])
	return prompts


class AiService:
	"""Class wrapper for AI helpers to enable DI and testing."""

	def summarize_text(self, text: str, max_length: int = 240) -> str:
		return summarize_text(text, max_length)

	def summarize_record(self, record: dict[str, Any]) -> dict[str, Any]:
		return summarize_record(record)

	def suggest_follow_up_flags(self, records: Iterable[dict[str, Any]]) -> list[str]:
		return suggest_follow_up_flags(records)

	def suggest_patient_questions(self, condition: str | None, symptoms: str | None) -> list[str]:
		return suggest_patient_questions(condition, symptoms)
