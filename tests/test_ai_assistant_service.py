from app.services.ai_service import ProjectAssistantService


def test_assistant_patient_kb_match():
    svc = ProjectAssistantService()
    res = svc.answer_query("How do I upload my report?", role="PATIENT", context={})
    assert res["source"] in {"knowledge-base", "fallback", "docs-retrieval"}
    assert isinstance(res["answer"], str)
    assert len(res["answer"]) > 0
    assert isinstance(res.get("actions"), list)


def test_assistant_empty_query_validation():
    svc = ProjectAssistantService()
    res = svc.answer_query("   ", role="PATIENT", context={})
    assert res["source"] == "validation"
    assert "provide your question" in res["answer"].lower()


def test_assistant_admin_role_prefix():
    svc = ProjectAssistantService()
    res = svc.answer_query("admin dashboard help", role="ADMIN", context={})
    assert "admin" in res["answer"].lower()


def test_assistant_suggests_endpoint_actions_for_reports():
    svc = ProjectAssistantService()
    res = svc.answer_query("How can I upload report file?", role="PATIENT", context={})
    actions = res.get("actions") or []
    assert any(a.get("endpoint") == "/api/reports/upload" for a in actions)


def test_assistant_suggests_endpoint_actions_for_appointments():
    svc = ProjectAssistantService()
    res = svc.answer_query("Need appointment scheduling help", role="PATIENT", context={})
    actions = res.get("actions") or []
    assert any(a.get("endpoint") == "/api/appointments" for a in actions)
