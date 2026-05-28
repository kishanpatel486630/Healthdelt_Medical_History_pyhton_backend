from app.services.qr_service import build_patient_payload


class Dummy:
    def __init__(self):
        self.id = "p1"
        self.fullName = "Alice"
        self.createdAt = None


def test_build_patient_payload():
    d = Dummy()
    payload = build_patient_payload(d)
    assert payload["type"] == "patient"
    assert payload["patientId"] == "p1"
