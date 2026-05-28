from tests.integration.helpers import register_and_verify, seed_doctor_profile


def test_doctor_link_patient_and_list_patients(client, db_session_factory):
    doctor = register_and_verify(
        client,
        full_name="Dr. Integrate",
        email="doctor.flow@example.com",
        password="doctorpass123",
        role="DOCTOR",
    )
    patient = register_and_verify(
        client,
        full_name="Patient Integrate",
        email="patient.flow@example.com",
        password="patientpass123",
        role="PATIENT",
    )

    doctor_headers = {"Authorization": f"Bearer {doctor['access_token']}"}

    # Seed a minimal doctor profile required by doctor-only endpoints.
    seed_doctor_profile(db_session_factory, doctor["user_id"])

    link_resp = client.post(
        "/api/doctors/me/patients/link",
        headers=doctor_headers,
        json={"patientId": patient["user_id"]},
    )
    assert link_resp.status_code == 200, link_resp.text
    assert link_resp.json()["success"] is True

    patients_resp = client.get("/api/doctors/me/patients", headers=doctor_headers)
    assert patients_resp.status_code == 200, patients_resp.text
    body = patients_resp.json()
    assert body["success"] is True
    assert any(p["id"] == patient["user_id"] for p in body["patients"])
