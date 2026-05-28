from tests.integration.helpers import register_and_verify, seed_doctor_profile


def test_doctor_create_and_list_prescriptions(client, db_session_factory):
    doctor = register_and_verify(
        client,
        full_name="Dr. Prescribe",
        email="dr.prescribe@example.com",
        password="doctorpass123",
        role="DOCTOR",
    )
    patient = register_and_verify(
        client,
        full_name="Patient Rx",
        email="patient.rx@example.com",
        password="patientpass123",
        role="PATIENT",
    )

    seed_doctor_profile(db_session_factory, doctor["user_id"], specialization="Internal Medicine")

    headers = {"Authorization": f"Bearer {doctor['access_token']}"}

    create_resp = client.post(
        "/api/doctors/me/prescriptions",
        headers=headers,
        json={
            "patientId": patient["user_id"],
            "title": "Diabetes Follow-up",
            "diagnosis": "Type 2 Diabetes",
            "notes": "Continue current regimen",
            "medicines": [
                {
                    "name": "Metformin",
                    "dosage": "500mg",
                    "frequency": "BID",
                    "timing": "After meals",
                    "duration": "30 days",
                    "instructions": "Take with water",
                }
            ],
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    create_body = create_resp.json()
    assert create_body["success"] is True

    list_resp = client.get("/api/doctors/me/prescriptions", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    list_body = list_resp.json()
    assert list_body["success"] is True
    assert any(p["title"] == "Diabetes Follow-up" for p in list_body["prescriptions"])
