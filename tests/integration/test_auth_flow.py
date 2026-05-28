def test_register_verify_and_get_profile(client):
    # Register a new user
    email = "inttest@example.com"
    password = "testpass123"
    resp = client.post("/api/auth/register", json={
        "fullName": "Integration Tester",
        "email": email,
        "password": password,
        "role": "PATIENT",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    user_id = body["userId"]
    otp_code = body["otpCode"]

    # Verify OTP and receive tokens
    resp = client.post("/api/auth/verify-otp", json={"userId": user_id, "otp": otp_code})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    access = body["accessToken"]

    # Use access token to call protected endpoint
    headers = {"Authorization": f"Bearer {access}"}
    resp = client.get("/api/users/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["user"]["email"] == email
