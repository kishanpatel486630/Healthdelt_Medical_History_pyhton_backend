"""AI service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from urllib import request as urlrequest

from collections.abc import Iterable
from typing import Any

from app.config import settings
from app.models import FaqEntry


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

	def answer_project_query(self, query: str, role: str, context: dict[str, Any] | None = None, db: Any | None = None) -> dict[str, Any]:
		assistant = ProjectAssistantService()
		# Forward DB session when provided for FAQ resolution and logging-aware lookups
		return assistant.answer_query(query=query, role=role, context=context, db=db)


@dataclass
class KnowledgeItem:
	title: str
	keywords: tuple[str, ...]
	answer: str
	roles: tuple[str, ...] = ("PATIENT", "DOCTOR", "ADMIN")


@dataclass
class DocChunk:
	path: str
	title: str
	content: str


@dataclass
class FaqMatch:
	id: str
	question: str
	answer: str
	role: str
	score: float


class ProjectAssistantService:
	"""Role-aware helper agent for project support queries."""
	_docs_cache: list[DocChunk] | None = None

	def __init__(self) -> None:
		self.knowledge: list[KnowledgeItem] = [
			KnowledgeItem(
				title="How login works",
				keywords=("login", "otp", "verify", "auth", "signin"),
				answer="Use email/mobile with password on login, then verify OTP to receive access and refresh tokens.",
			),
			KnowledgeItem(
				title="Upload reports",
				keywords=("upload", "report", "file", "lab", "documents"),
				answer="Use report upload endpoints to attach lab or clinical files. Uploaded files are stored in uploads and tracked in Report records.",
			),
			KnowledgeItem(
				title="Doctor links patient",
				keywords=("link patient", "doctor", "patients", "practice"),
				answer="Doctor can link a patient from doctor-me endpoint. This creates linkage history and notification to the patient.",
				roles=("DOCTOR", "ADMIN"),
			),
			KnowledgeItem(
				title="Create prescription",
				keywords=("prescription", "medicine", "dosage", "create"),
				answer="Doctor can create a prescription with diagnosis, notes, and medicines. Patients can view active prescriptions linked to their account.",
				roles=("DOCTOR", "PATIENT", "ADMIN"),
			),
			KnowledgeItem(
				title="Admin access",
				keywords=("admin", "suspend", "manage", "users", "dashboard"),
				answer="Admins can manage users and operations endpoints; they should use role-protected routes and audit-sensitive actions.",
				roles=("ADMIN",),
			),
		]
		if ProjectAssistantService._docs_cache is None:
			ProjectAssistantService._docs_cache = self._load_docs_index()

	def answer_query(self, query: str, role: str, context: dict[str, Any] | None = None, db: Any | None = None) -> dict[str, Any]:
		clean_query = " ".join((query or "").split()).strip()
		if not clean_query:
			return {
				"answer": "Please provide your question so I can help.",
				"source": "validation",
				"confidence": 0.0,
			}

		role_upper = (role or "PATIENT").upper()
		actions = self._suggest_actions(clean_query, role_upper)
		faq_match = self._best_faq_match(db, clean_query, role_upper)
		if faq_match:
			return {
				"answer": self._role_prefix(role_upper) + " " + faq_match.answer,
				"source": "faq",
				"confidence": round(faq_match.score, 2),
				"actions": actions,
				"faqId": faq_match.id,
			}

		doc_match = self._best_doc_match(clean_query)
		if doc_match:
			doc, score = doc_match
			answer = (
				f"{self._role_prefix(role_upper)} Based on project docs ({doc.title}, {doc.path}): "
				f"{summarize_text(doc.content, 360)}"
			)
			return {
				"answer": answer,
				"source": "docs-retrieval",
				"confidence": round(score, 2),
				"actions": actions,
			}

		best = self._best_match(clean_query, role_upper)
		if best:
			item, score = best
			answer = self._role_prefix(role_upper) + " " + item.answer
			if self._needs_safety_note(clean_query):
				answer += " For medical emergencies, contact local emergency services immediately."
			return {
				"answer": answer,
				"source": "knowledge-base",
				"confidence": round(score, 2),
				"actions": actions,
			}

		# Optional LLM fallback if key is configured
		if settings.OPENAI_API_KEY:
			llm = self._llm_answer(clean_query, role_upper, context or {})
			if llm:
				return {
					"answer": llm,
					"source": "llm",
					"confidence": 0.65,
					"actions": actions,
				}

		return {
			"answer": self._fallback_answer(role_upper),
			"source": "fallback",
			"confidence": 0.3,
			"actions": actions,
		}

	def _load_docs_index(self) -> list[DocChunk]:
		root = Path(__file__).resolve().parents[2]
		docs_dir = root / "docs"
		chunks: list[DocChunk] = []
		if not docs_dir.exists():
			return chunks
		for path in docs_dir.rglob("*.md"):
			try:
				text = path.read_text(encoding="utf-8", errors="ignore")
				lines = [line.strip() for line in text.splitlines() if line.strip()]
				title = lines[0].lstrip("# ") if lines else path.name
				chunks.append(
					DocChunk(
						path=str(path.relative_to(root)).replace("\\", "/"),
						title=title,
						content=text,
					)
				)
			except Exception:
				continue
		return chunks

	def _best_doc_match(self, query: str) -> tuple[DocChunk, float] | None:
		query_lower = query.lower()
		best: DocChunk | None = None
		best_score = 0.0
		for chunk in ProjectAssistantService._docs_cache or []:
			title_score = SequenceMatcher(a=query_lower, b=chunk.title.lower()).ratio()
			text_score = SequenceMatcher(a=query_lower, b=chunk.content[:600].lower()).ratio()
			keyword_hits = sum(1 for token in query_lower.split() if len(token) > 2 and token in chunk.content.lower())
			score = max(title_score, text_score) + min(keyword_hits * 0.05, 0.4)
			if score > best_score:
				best_score = score
				best = chunk
		if best and best_score >= 0.5:
			return best, best_score
		return None

	def _best_faq_match(self, db: Any | None, query: str, role: str) -> FaqMatch | None:
		if db is None:
			return None
		query_lower = query.lower()
		best: FaqMatch | None = None
		best_score = 0.0
		rows = (
			db.query(FaqEntry)
			.filter(FaqEntry.isActive == True)  # noqa: E712
			.filter((FaqEntry.role == role) | (FaqEntry.role == "ALL"))
			.all()
		)
		for row in rows:
			tags = (row.tags or "").lower()
			question_score = SequenceMatcher(a=query_lower, b=row.question.lower()).ratio()
			answer_score = SequenceMatcher(a=query_lower, b=row.answer.lower()[:500]).ratio()
			tag_score = 0.0
			for token in query_lower.split():
				if len(token) > 2 and token in tags:
					tag_score += 0.05
			score = max(question_score, answer_score) + min(tag_score, 0.3)
			if score > best_score:
				best_score = score
				best = FaqMatch(id=row.id, question=row.question, answer=row.answer, role=row.role, score=score)
		if best and best_score >= 0.45:
			return best
		return None

	def _suggest_actions(self, query: str, role: str) -> list[dict[str, str]]:
		q = query.lower()
		actions: list[dict[str, str]] = []
		if any(token in q for token in ("appointment", "book", "schedule", "reschedule")):
			actions.append(
				{
					"label": "Open appointments endpoint",
					"method": "GET",
					"endpoint": "/api/appointments",
					"hint": "Use this to list appointments and verify scheduling data.",
				}
			)
		if any(token in q for token in ("report", "upload", "lab", "file")):
			actions.append(
				{
					"label": "Upload a report",
					"method": "POST",
					"endpoint": "/api/reports/upload",
					"hint": "Attach report file and metadata like reportType, category, and labName.",
				}
			)
		if role in {"DOCTOR", "ADMIN"} and any(token in q for token in ("patient", "link", "assign")):
			actions.append(
				{
					"label": "Link patient to doctor",
					"method": "POST",
					"endpoint": "/api/doctors/me/patients/link",
					"hint": "Provide patientId in payload.",
				}
			)
		if role == "DOCTOR" and any(token in q for token in ("prescription", "medicine", "dosage")):
			actions.append(
				{
					"label": "Create prescription",
					"method": "POST",
					"endpoint": "/api/doctors/me/prescriptions",
					"hint": "Include patientId, title, diagnosis, notes, and medicines.",
				}
			)
		return actions

	def _best_match(self, query: str, role: str) -> tuple[KnowledgeItem, float] | None:
		query_lower = query.lower()
		best_item = None
		best_score = 0.0
		for item in self.knowledge:
			if role not in item.roles:
				continue
			keyword_score = max((1.0 if kw in query_lower else 0.0 for kw in item.keywords), default=0.0)
			title_score = SequenceMatcher(a=query_lower, b=item.title.lower()).ratio()
			score = max(keyword_score, title_score)
			if score > best_score:
				best_score = score
				best_item = item
		if best_item and best_score >= 0.45:
			return best_item, best_score
		return None

	def _role_prefix(self, role: str) -> str:
		if role == "DOCTOR":
			return "Doctor support:" 
		if role == "ADMIN":
			return "Admin support:"
		return "Patient support:"

	def _needs_safety_note(self, query: str) -> bool:
		text = query.lower()
		return any(token in text for token in ("emergency", "severe pain", "heart", "stroke", "suicidal", "bleeding"))

	def _fallback_answer(self, role: str) -> str:
		base = {
			"PATIENT": "I can help with login, reports, prescriptions, appointments, and profile questions.",
			"DOCTOR": "I can help with patient linking, prescriptions, reports, and doctor profile workflows.",
			"ADMIN": "I can help with user management, role-based access, and operational workflows.",
		}.get(role, "I can help with project workflows and troubleshooting.")
		return f"{base} Please ask a specific question like: 'How do I upload a report?'"

	def _llm_answer(self, query: str, role: str, context: dict[str, Any]) -> str | None:
		try:
			system_prompt = self._build_role_prompt(role)
			payload = {
				"model": settings.AI_ASSISTANT_MODEL,
				"messages": [
					{
						"role": "system",
						"content": system_prompt,
					},
					{
						"role": "user",
						"content": f"Role: {role}\nContext: {json.dumps(context)}\nQuestion: {query}",
					},
				],
				"temperature": 0.2,
			}
			req = urlrequest.Request(
				"https://api.openai.com/v1/chat/completions",
				data=json.dumps(payload).encode("utf-8"),
				headers={
					"Authorization": f"Bearer {settings.OPENAI_API_KEY}",
					"Content-Type": "application/json",
				},
				method="POST",
			)
			with urlrequest.urlopen(req, timeout=15) as response:
				body = json.loads(response.read().decode("utf-8"))
				choices = body.get("choices") or []
				if not choices:
					return None
				message = choices[0].get("message") or {}
				content = message.get("content")
				if isinstance(content, str):
					return content.strip()
				return None
		except Exception:
			return None

	def _build_role_prompt(self, role: str) -> str:
		base = (
			"You are a healthcare project support assistant. Give practical, safe, concise guidance. "
			"Do not diagnose disease. For emergency-like queries, advise contacting emergency services."
		)
		if role == "DOCTOR":
			return base + " Focus on clinical workflow support: patient linkage, prescriptions, records, and reports."
		if role == "ADMIN":
			return base + " Focus on operations and governance: role access, auditing, policy-safe process guidance."
		return base + " Focus on patient self-service: login help, reports, appointments, profile, and prescriptions."
