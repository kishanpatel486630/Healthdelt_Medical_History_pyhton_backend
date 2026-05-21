import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# CORE USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "User"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    mobile = Column(String, unique=True, index=True, nullable=True)
    passwordHash = Column(String, nullable=False)
    passwordRaw = Column(String, nullable=True)
    fullName = Column(String, nullable=False)
    role = Column(String, default="PATIENT", nullable=False)
    status = Column(String, default="ACTIVE", nullable=False)
    avatar = Column(String, nullable=True)

    bloodGroup = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)
    chronicDisease = Column(Text, nullable=True)
    dateOfBirth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    weight = Column(String, nullable=True)
    height = Column(String, nullable=True)
    insuranceId = Column(String, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")
    medical_histories = relationship("MedicalHistory", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    prescriptions_received = relationship("Prescription", back_populates="patient", cascade="all, delete-orphan")
    appointments_as_patient = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    otp_codes = relationship("OtpCode", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    emergency_contacts = relationship("EmergencyContact", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class Doctor(Base):
    __tablename__ = "Doctor"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), unique=True, nullable=False)
    specialization = Column(String, nullable=False)
    subSpecialization = Column(String, nullable=True)
    qualifications = Column(String, nullable=True)
    licenseNumber = Column(String, unique=True, nullable=False)
    registrationNumber = Column(String, nullable=True)
    hospital = Column(String, nullable=True)
    clinicName = Column(String, nullable=True)
    clinicAddress = Column(String, nullable=True)
    experienceYears = Column(Integer, default=0)
    previousExperience = Column(Text, nullable=True)
    consultationFee = Column(Float, nullable=True)
    languages = Column(String, nullable=True)
    workingHours = Column(Text, nullable=True)
    availableDays = Column(Text, nullable=True)
    availableSlots = Column(Text, nullable=True)
    verificationStatus = Column(String, default="PENDING")
    rejectionReason = Column(String, nullable=True)

    rating = Column(Float, default=0)
    reviewCount = Column(Integer, default=0)
    bio = Column(Text, nullable=True)
    image = Column(String, nullable=True)
    documents = Column(Text, nullable=True)

    securityPin = Column(String, nullable=True)
    secretCode = Column(String, nullable=True)
    prescriptionFormat = Column(Text, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="doctor_profile")
    prescriptions_issued = relationship("Prescription", back_populates="doctor")
    appointments_as_doctor = relationship("Appointment", back_populates="doctor")
    medical_histories = relationship("MedicalHistory", back_populates="doctor")


# ═══════════════════════════════════════════════════════════════
# MEDICAL DATA
# ═══════════════════════════════════════════════════════════════

class MedicalHistory(Base):
    __tablename__ = "MedicalHistory"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    doctorId = Column(String, ForeignKey("Doctor.id"), nullable=True)
    title = Column(String, nullable=False)
    diagnosis = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    visitType = Column(String, default="CONSULTATION")
    status = Column(String, default="COMPLETED")
    visitDate = Column(DateTime, nullable=False)
    symptoms = Column(Text, nullable=True)
    vitals = Column(Text, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="medical_histories")
    doctor = relationship("Doctor", back_populates="medical_histories")


class Report(Base):
    __tablename__ = "Report"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    reportType = Column(String, nullable=False)
    fileUrl = Column(String, nullable=False)
    fileSize = Column(String, nullable=True)
    mimeType = Column(String, nullable=True)
    category = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    labName = Column(String, nullable=True)
    reportDate = Column(DateTime, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="reports")


class Prescription(Base):
    __tablename__ = "Prescription"

    id = Column(String, primary_key=True, default=generate_uuid)
    patientId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    doctorId = Column(String, ForeignKey("Doctor.id"), nullable=False)
    title = Column(String, nullable=False)
    diagnosis = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="ACTIVE")
    issuedDate = Column(DateTime, default=datetime.utcnow)
    expiryDate = Column(DateTime, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", back_populates="prescriptions_received")
    doctor = relationship("Doctor", back_populates="prescriptions_issued")
    medicines = relationship("Medicine", back_populates="prescription", cascade="all, delete-orphan")


class Medicine(Base):
    __tablename__ = "Medicine"

    id = Column(String, primary_key=True, default=generate_uuid)
    prescriptionId = Column(String, ForeignKey("Prescription.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    timing = Column(String, nullable=True)
    duration = Column(String, nullable=True)
    instructions = Column(Text, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)

    prescription = relationship("Prescription", back_populates="medicines")


class Appointment(Base):
    __tablename__ = "Appointment"

    id = Column(String, primary_key=True, default=generate_uuid)
    patientId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    doctorId = Column(String, ForeignKey("Doctor.id"), nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, default="IN_PERSON")
    status = Column(String, default="CONFIRMED")
    date = Column(DateTime, nullable=False)
    startTime = Column(String, nullable=False)
    endTime = Column(String, nullable=True)
    location = Column(String, nullable=True)
    meetingUrl = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", back_populates="appointments_as_patient")
    doctor = relationship("Doctor", back_populates="appointments_as_doctor")


# ═══════════════════════════════════════════════════════════════
# SYSTEM & SECURITY
# ═══════════════════════════════════════════════════════════════

class Notification(Base):
    __tablename__ = "Notification"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False)
    isRead = Column(Boolean, default=False)
    actionUrl = Column(String, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class OtpCode(Base):
    __tablename__ = "OtpCode"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    code = Column(String, nullable=False)
    purpose = Column(String, default="LOGIN")
    expiresAt = Column(DateTime, nullable=False)
    isUsed = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)

    createdAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="otp_codes")


class RefreshToken(Base):
    __tablename__ = "RefreshToken"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    deviceInfo = Column(String, nullable=True)
    ipAddress = Column(String, nullable=True)
    expiresAt = Column(DateTime, nullable=False)
    isRevoked = Column(Boolean, default=False)

    createdAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class EmergencyContact(Base):
    __tablename__ = "EmergencyContact"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    relation = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=True)
    isPrimary = Column(Boolean, default=False)

    createdAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="emergency_contacts")


class AuditLog(Base):
    __tablename__ = "AuditLog"

    id = Column(String, primary_key=True, default=generate_uuid)
    userId = Column(String, ForeignKey("User.id"), nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=True)
    resourceId = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    ipAddress = Column(String, nullable=True)
    userAgent = Column(String, nullable=True)

    createdAt = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


# ═══════════════════════════════════════════════════════════════
# MASTERS MANAGEMENT
# ═══════════════════════════════════════════════════════════════

class MasterMedicine(Base):
    __tablename__ = "MasterMedicine"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    genericName = Column(String, nullable=True)
    dosageTypes = Column(String, nullable=True)
    strength = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    instructions = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)


class MasterLabTest(Base):
    __tablename__ = "MasterLabTest"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    referenceRange = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)


class MasterDisease(Base):
    __tablename__ = "MasterDisease"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    icdCode = Column(String, nullable=True)
    symptoms = Column(String, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)


class MasterTemplate(Base):
    __tablename__ = "MasterTemplate"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    medicines = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)


class MasterCategory(Base):
    __tablename__ = "MasterCategory"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)
