from tests.integration.helpers import register_and_verify


def test_patient_qr_authorization_rules(client):
    patient_a = register_and_verify(
        client,
        full_name="Patient A",
        email="qr.patient.a@example.com",
        password="patientApass123",
        role="PATIENT",
    )
    patient_b = register_and_verify(
        client,
        full_name="Patient B",
        email="qr.patient.b@example.com",
        password="patientBpass123",
        role="PATIENT",
    )
    doctor = register_and_verify(
        client,
        full_name="Doctor QR",
        email="qr.doctor@example.com",
        password="doctorQRpass123",
        role="DOCTOR",
    )

    patient_a_headers = {"Authorization": f"Bearer {patient_a['access_token']}"}
    patient_b_headers = {"Authorization": f"Bearer {patient_b['access_token']}"}
    doctor_headers = {"Authorization": f"Bearer {doctor['access_token']}"}

    own_qr = client.get(f"/api/qr/patient/{patient_a['user_id']}", headers=patient_a_headers)
    assert own_qr.status_code == 200, own_qr.text
    assert own_qr.headers.get("content-type", "").startswith("image/png")

    forbidden_qr = client.get(f"/api/qr/patient/{patient_a['user_id']}", headers=patient_b_headers)
    assert forbidden_qr.status_code == 403, forbidden_qr.text

    doctor_qr = client.get(f"/api/qr/patient/{patient_a['user_id']}", headers=doctor_headers)
    assert doctor_qr.status_code == 200, doctor_qr.text
    assert doctor_qr.headers.get("content-type", "").startswith("image/png")
