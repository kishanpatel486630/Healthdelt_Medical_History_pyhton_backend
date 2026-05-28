def register_and_verify(client, *, full_name: str, email: str, password: str, role: str = "PATIENT"):
    reg = client.post(
        "/api/auth/register",
        json={
            "fullName": full_name,
            "email": email,
            "password": password,
            "role": role,
        },
    )
    assert reg.status_code == 200, reg.text
    reg_body = reg.json()

    verify = client.post(
        "/api/auth/verify-otp",
        json={"userId": reg_body["userId"], "otp": reg_body["otpCode"]},
    )
    assert verify.status_code == 200, verify.text
    verify_body = verify.json()

    return {
        "user_id": reg_body["userId"],
        "access_token": verify_body["accessToken"],
        "refresh_token": verify_body.get("refreshToken"),
    }


def seed_doctor_profile(db_session_factory, user_id: str, *, specialization: str = "General Practice"):
    from app.models import Doctor

    db = db_session_factory()
    try:
        db.add(
            Doctor(
                userId=user_id,
                specialization=specialization,
                licenseNumber=f"INT-LIC-{user_id[:8]}",
                verificationStatus="VERIFIED",
            )
        )
        db.commit()
    finally:
        db.close()
