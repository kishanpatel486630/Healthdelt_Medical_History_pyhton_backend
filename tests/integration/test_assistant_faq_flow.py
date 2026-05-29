from tests.integration.helpers import register_and_verify


def test_admin_can_create_and_list_faqs(client):
    admin = register_and_verify(
        client,
        full_name="FAQ Admin",
        email="faq.admin@example.com",
        password="adminpass123",
        role="ADMIN",
    )
    headers = {"Authorization": f"Bearer {admin['access_token']}"}

    create_resp = client.post(
        "/api/assistant/faqs",
        headers=headers,
        json={
            "question": "How do I upload a report?",
            "answer": "Use the reports upload endpoint.",
            "role": "PATIENT",
            "tags": ["reports", "upload"],
            "priority": 10,
            "isActive": True,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json()["success"] is True

    list_resp = client.get("/api/assistant/faqs", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    body = list_resp.json()
    assert body["success"] is True
    assert any(faq["question"] == "How do I upload a report?" for faq in body["faqs"])


def test_assistant_uses_faq_source(client):
    admin = register_and_verify(
        client,
        full_name="FAQ Admin 2",
        email="faq.admin2@example.com",
        password="adminpass123",
        role="ADMIN",
    )
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}
    client.post(
        "/api/assistant/faqs",
        headers=admin_headers,
        json={
            "question": "How do I upload a report?",
            "answer": "Use the reports upload endpoint and attach the file.",
            "role": "PATIENT",
            "tags": ["reports", "upload"],
            "priority": 10,
            "isActive": True,
        },
    )

    patient = register_and_verify(
        client,
        full_name="FAQ Patient",
        email="faq.patient@example.com",
        password="patientpass123",
        role="PATIENT",
    )
    patient_headers = {"Authorization": f"Bearer {patient['access_token']}"}

    query_resp = client.post(
        "/api/assistant/query",
        headers=patient_headers,
        json={"query": "How do I upload a report?", "context": {}},
    )
    assert query_resp.status_code == 200, query_resp.text
    body = query_resp.json()
    assert body["assistant"]["source"] == "faq"
    assert "reports upload endpoint" in body["assistant"]["answer"].lower()
