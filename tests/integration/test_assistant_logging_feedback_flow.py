from tests.integration.helpers import register_and_verify


def test_assistant_query_logging_and_feedback(client):
    auth = register_and_verify(
        client,
        full_name="Assistant User",
        email="assistant.user@example.com",
        password="assistantpass123",
        role="PATIENT",
    )
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    query_resp = client.post(
        "/api/assistant/query",
        headers=headers,
        json={"query": "How do I upload report?", "context": {"area": "reports"}},
    )
    assert query_resp.status_code == 200, query_resp.text
    query_body = query_resp.json()
    assert query_body["success"] is True
    assert query_body.get("queryLogId")
    assert isinstance(query_body.get("assistant", {}).get("answer"), str)

    feedback_resp = client.post(
        "/api/assistant/feedback",
        headers=headers,
        json={
            "queryLogId": query_body["queryLogId"],
            "helpful": True,
            "feedback": "Very useful",
        },
    )
    assert feedback_resp.status_code == 200, feedback_resp.text
    feedback_body = feedback_resp.json()
    assert feedback_body["success"] is True
