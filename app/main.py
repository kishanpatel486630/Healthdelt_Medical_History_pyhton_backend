import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.config import settings
from app.api.routes import (
    auth, users, doctors, doctor_me,
    history, appointments, prescriptions,
    reports, notifications, admin, patients, medical_records, qr, uploads,
)

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Healthdelt API (Python/FastAPI)")

# CORS — allow frontend origins
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://healthdelt-tracker.vercel.app",
    "https://healthdelt-tracker-lidpw925x-kishan-parvadiyas-projects.vercel.app",
]

if settings.CLIENT_URL:
    if "," in settings.CLIENT_URL:
        origins.extend([o.strip() for o in settings.CLIENT_URL.split(",") if o.strip()])
    else:
        origins.append(settings.CLIENT_URL.strip())

unique_origins = []
for origin in origins:
    if origin not in unique_origins:
        unique_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=unique_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(doctors.router)
app.include_router(doctor_me.router)
app.include_router(patients.router)
app.include_router(medical_records.router)
app.include_router(history.router)
app.include_router(appointments.router)
app.include_router(prescriptions.router)
app.include_router(reports.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(qr.router)
app.include_router(uploads.router)

# Serve uploaded files
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "Healthdelt Python API is running"}


# ── Error handler to match Node.js format ─────────────────────
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": str(exc.errors()[0]["msg"]) if exc.errors() else "Validation error"},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )
