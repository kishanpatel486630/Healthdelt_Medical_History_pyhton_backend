from tests.integration.helpers import register_and_verify


def test_admin_can_list_and_promote_queries(client):
    admin = register_and_verify(
        client,
        full_name="Admin Reviewer",
        email="admin.reviewer@example.com",
        password="adminpass123",
        role="ADMIN",
    )
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    patient = register_and_verify(
        client,
        full_name="Query Patient",
        email="query.patient@example.com",
        password="patientpass123",
        role="PATIENT",
    )
    patient_headers = {"Authorization": f"Bearer {patient['access_token']}"}

    # Patient submits a query
    q = "How do I change my appointment time?"
    resp = client.post("/api/assistant/query", headers=patient_headers, json={"query": q, "context": {}})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    query_log_id = body["queryLogId"]

    # Admin lists unresolved queries
    list_resp = client.get("/api/assistant/admin/queries", headers=admin_headers)
    assert list_resp.status_code == 200, list_resp.text
    lb = list_resp.json()
    assert lb["success"] is True
    assert any(item["id"] == query_log_id for item in lb["queries"])

    # Admin promotes the query to a FAQ
    promote_payload = {
        "queryLogId": query_log_id,
        "question": "How to change appointment time?",
        "answer": "Use the appointments endpoint to update the slot.",
        "role": "PATIENT",
        "tags": ["appointments", "reschedule"],
        "priority": 5,
    }
    prom = client.post("/api/assistant/admin/promote", headers=admin_headers, json=promote_payload)
    assert prom.status_code == 200, prom.text
    pb = prom.json()
    assert pb["success"] is True
    faq_id = pb.get("faqId")
    assert faq_id is not None

    # Ensure FAQ exists in list
    faqs = client.get("/api/assistant/faqs", headers=admin_headers)
    assert faqs.status_code == 200, faqs.text
    fb = faqs.json()
    assert any(f["id"] == faq_id for f in fb["faqs"])
