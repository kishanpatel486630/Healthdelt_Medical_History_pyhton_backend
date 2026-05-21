from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/history")
def get_history():
    return {"records": []}

@router.get("/prescriptions/active")
def get_prescriptions():
    return {"prescriptions": []}

@router.get("/appointments")
def get_appointments():
    return {"appointments": []}

@router.get("/doctors/me/stats")
def get_doctor_stats():
    return {"stats": {"totalPatients": 0, "todayPatients": 0, "pendingAppointments": 0}}

@router.get("/doctors/me/patients")
def get_doctor_patients():
    return {"patients": []}
