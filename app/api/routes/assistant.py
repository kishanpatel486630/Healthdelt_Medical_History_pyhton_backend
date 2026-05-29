import json
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_ai_service, get_current_user, require_role
from app.models import AssistantQueryLog, FaqEntry, User
from app.services.ai_service import AiService


router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AssistantQueryRequest(BaseModel):
    query: str
    context: Optional[dict[str, Any]] = None


@router.post("/query")
def query_assistant(
    req: AssistantQueryRequest,
    current_user: User = Depends(get_current_user),
    ai_service: AiService = Depends(get_ai_service),
    db: Session = Depends(get_db),
):
    result = ai_service.answer_project_query(req.query, current_user.role, req.context or {}, db=db)
    log = AssistantQueryLog(
        userId=current_user.id,
        role=current_user.role,
        query=req.query,
        queryContext=json.dumps(req.context or {}),
        answer=result.get("answer") or "",
        answerSource=result.get("source"),
        confidence=result.get("confidence"),
        actions=json.dumps(result.get("actions") or []),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {
        "success": True,
        "role": current_user.role,
        "queryLogId": log.id,
        "assistant": result,
    }


class AssistantFeedbackRequest(BaseModel):
    queryLogId: str
    helpful: bool
    feedback: Optional[str] = None


@router.post("/feedback")
def assistant_feedback(
    req: AssistantFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(AssistantQueryLog)
        .filter(AssistantQueryLog.id == req.queryLogId, AssistantQueryLog.userId == current_user.id)
        .first()
    )
    if not row:
        return {"success": False, "message": "Query log not found"}
    row.helpful = req.helpful
    row.feedback = req.feedback
    db.commit()
    return {"success": True, "message": "Feedback recorded"}


class FaqEntryRequest(BaseModel):
    question: str
    answer: str
    role: str = "PATIENT"
    tags: Optional[list[str]] = None
    priority: int = 0
    isActive: bool = True


@router.get("/faqs")
def list_faqs(
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    rows = db.query(FaqEntry).order_by(FaqEntry.priority.desc(), FaqEntry.createdAt.desc()).all()
    return {
        "success": True,
        "faqs": [
            {
                "id": row.id,
                "question": row.question,
                "answer": row.answer,
                "role": row.role,
                "tags": (row.tags.split(",") if row.tags else []),
                "priority": row.priority,
                "isActive": row.isActive,
            }
            for row in rows
        ],
    }


@router.post("/faqs")
def create_faq(
    req: FaqEntryRequest,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    row = FaqEntry(
        question=req.question,
        answer=req.answer,
        role=req.role.upper(),
        tags=",".join(req.tags or []),
        priority=req.priority,
        isActive=req.isActive,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "success": True,
        "faq": {
            "id": row.id,
            "question": row.question,
            "answer": row.answer,
            "role": row.role,
            "tags": req.tags or [],
            "priority": row.priority,
            "isActive": row.isActive,
        },
    }


# ---------------- Admin review endpoints ----------------


class AdminQueryFilter(BaseModel):
    unresolved: bool = True
    page: int = 1
    limit: int = 50


@router.get("/admin/queries")
def admin_list_queries(
    unresolved: bool = True,
    page: int = 1,
    limit: int = 50,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    q = db.query(AssistantQueryLog).order_by(AssistantQueryLog.createdAt.desc())
    if unresolved:
        q = q.filter(AssistantQueryLog.helpful == None)
    total = q.count()
    rows = q.offset((page - 1) * limit).limit(limit).all()
    return {
        "success": True,
        "total": total,
        "page": page,
        "limit": limit,
        "queries": [
            {
                "id": r.id,
                "userId": r.userId,
                "role": r.role,
                "query": r.query,
                "answer": r.answer,
                "answerSource": r.answerSource,
                "confidence": r.confidence,
                "helpful": r.helpful,
                "feedback": r.feedback,
                "createdAt": r.createdAt.isoformat() if r.createdAt else None,
            }
            for r in rows
        ],
    }


class PromoteRequest(BaseModel):
    queryLogId: str
    question: Optional[str] = None
    answer: str
    role: str = "PATIENT"
    tags: Optional[list[str]] = None
    priority: int = 0


@router.post("/admin/promote")
def admin_promote_query(
    req: PromoteRequest,
    current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    row = db.query(AssistantQueryLog).filter(AssistantQueryLog.id == req.queryLogId).first()
    if not row:
        return {"success": False, "message": "Query log not found"}
    # create FAQ entry
    faq = FaqEntry(
        question=(req.question or row.query),
        answer=req.answer,
        role=req.role.upper(),
        tags=",".join(req.tags or []),
        priority=req.priority,
        isActive=True,
    )
    db.add(faq)
    # mark query as helpful and add feedback
    row.helpful = True
    row.feedback = f"Promoted to FAQ ({faq.id}) by {current_user.id}"
    db.commit()
    db.refresh(faq)
    return {"success": True, "faqId": faq.id, "queryLogId": row.id}
