from tests.integration.helpers import register_and_verify


def test_refresh_and_logout_flow(client):
    auth = register_and_verify(
        client,
        full_name="Refresh User",
        email="refresh.user@example.com",
        password="refreshpass123",
        role="PATIENT",
    )

    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    refresh_resp = client.post(
        "/api/auth/refresh-token",
        json={"refreshToken": auth["refresh_token"]},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    refresh_body = refresh_resp.json()
    assert refresh_body["success"] is True
    new_refresh = refresh_body["refreshToken"]

    logout_resp = client.post(
        "/api/auth/logout",
        headers=headers,
        json={"refreshToken": new_refresh},
    )
    assert logout_resp.status_code == 200, logout_resp.text
    assert logout_resp.json()["success"] is True

    # Logged-out refresh token should no longer be valid.
    post_logout_refresh = client.post(
        "/api/auth/refresh-token",
        json={"refreshToken": new_refresh},
    )
    assert post_logout_refresh.status_code == 401, post_logout_refresh.text
