import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User, Doctor, OtpCode, RefreshToken, AuditLog, Notification
from app.security import (
    verify_password, get_password_hash,
    create_access_token, generate_refresh_token,
    generate_otp, get_otp_expiry,
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request Schemas ────────────────────────────────────────────
class RegisterRequest(BaseModel):
    fullName: str
    email: str
    password: str
    mobile: Optional[str] = None
    role: Optional[str] = "PATIENT"


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyOTPRequest(BaseModel):
    userId: str
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    userId: str
    otp: str
    newPassword: str


class LogoutRequest(BaseModel):
    refreshToken: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refreshToken: str


# ── REGISTER ──────────────────────────────────────────────────
@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.email == req.email.lower()) |
        (User.mobile == req.mobile if req.mobile else False)
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="User with this email or mobile already exists")

    hashed = get_password_hash(req.password)
    # Patients are directly ACTIVE, only doctors need verification
    is_doctor = req.role == "DOCTOR"
    user = User(
        fullName=req.fullName,
        email=req.email.lower(),
        mobile=req.mobile or None,
        passwordHash=hashed,
        role="DOCTOR" if is_doctor else "PATIENT",
        status="PENDING_VERIFICATION" if is_doctor else "ACTIVE",
    )
    db.add(user)
    db.flush()

    # Create doctor profile if registering as doctor
    if is_doctor:
        doctor = Doctor(
            userId=user.id,
            specialization="General Practice",
            licenseNumber=f"PENDING-{int(time.time() * 1000)}",
            verificationStatus="PENDING",
        )
        db.add(doctor)

    # Invalidate old OTPs
    db.query(OtpCode).filter(OtpCode.userId == user.id, OtpCode.isUsed == False).update({"isUsed": True})

    otp_code = generate_otp()
    otp = OtpCode(
        userId=user.id,
        code=otp_code,
        purpose="REGISTER",
        expiresAt=get_otp_expiry(10),
    )
    db.add(otp)

    # Audit log
    audit = AuditLog(userId=user.id, action="REGISTER", resource="user")
    db.add(audit)

    db.commit()

    print(f"[OTP] Registration OTP for {req.email}: {otp_code}")

    return {
        "success": True,
        "message": "Registration successful. Please verify with OTP.",
        "userId": user.id,
        "otpCode": otp_code,  # dev mode
    }


# ── LOGIN ─────────────────────────────────────────────────────
@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.email == req.email.lower()) | (User.mobile == req.email)
    ).first()

    if not user or not verify_password(req.password, user.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.status == "SUSPENDED":
        raise HTTPException(status_code=403, detail="Account suspended")

    # Invalidate old OTPs
    db.query(OtpCode).filter(OtpCode.userId == user.id, OtpCode.isUsed == False).update({"isUsed": True})

    otp_code = generate_otp()
    otp = OtpCode(
        userId=user.id,
        code=otp_code,
        purpose="LOGIN",
        expiresAt=get_otp_expiry(5),
    )
    db.add(otp)

    audit = AuditLog(userId=user.id, action="LOGIN_ATTEMPT")
    db.add(audit)

    db.commit()

    print(f"[OTP] Login OTP for {req.email}: {otp_code}")

    return {
        "success": True,
        "message": "OTP sent. Please verify to complete login.",
        "userId": user.id,
        "otpCode": otp_code,  # dev mode
    }


# ── VERIFY OTP ────────────────────────────────────────────────
@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = (
        db.query(OtpCode)
        .filter(
            OtpCode.userId == req.userId,
            OtpCode.isUsed == False,
            OtpCode.purpose.in_(["LOGIN", "REGISTER"]),
            OtpCode.expiresAt > datetime.utcnow(),
        )
        .order_by(OtpCode.createdAt.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Please request a new one.")

    if otp_record.attempts >= 5:
        otp_record.isUsed = True
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")

    if otp_record.code != req.otp:
        otp_record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Mark used
    otp_record.isUsed = True

    # Activate user
    user = db.query(User).filter(User.id == req.userId).first()
    user.status = "ACTIVE"

    # Generate tokens
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token_value = generate_refresh_token()

    rt = RefreshToken(
        userId=user.id,
        token=refresh_token_value,
        expiresAt=datetime.utcnow() + timedelta(days=7),
    )
    db.add(rt)

    audit = AuditLog(userId=user.id, action="LOGIN_SUCCESS")
    db.add(audit)

    db.commit()

    return {
        "success": True,
        "message": "Authentication successful",
        "accessToken": access_token,
        "refreshToken": refresh_token_value,
        "user": {
            "id": user.id,
            "email": user.email,
            "fullName": user.fullName,
            "role": user.role,
        },
    }


# ── REFRESH TOKEN ─────────────────────────────────────────────
@router.post("/refresh-token")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    record = db.query(RefreshToken).filter(RefreshToken.token == req.refreshToken).first()

    if not record or record.isRevoked or record.expiresAt < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate
    record.isRevoked = True
    user = db.query(User).filter(User.id == record.userId).first()

    new_access = create_access_token(user.id, user.email, user.role)
    new_refresh = generate_refresh_token()

    new_rt = RefreshToken(
        userId=user.id,
        token=new_refresh,
        expiresAt=datetime.utcnow() + timedelta(days=7),
    )
    db.add(new_rt)
    db.commit()

    return {
        "success": True,
        "accessToken": new_access,
        "refreshToken": new_refresh,
    }


# ── LOGOUT ────────────────────────────────────────────────────
@router.post("/logout")
def logout(
    req: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.refreshToken:
        db.query(RefreshToken).filter(
            RefreshToken.token == req.refreshToken,
            RefreshToken.userId == current_user.id,
        ).update({"isRevoked": True})

    audit = AuditLog(userId=current_user.id, action="LOGOUT")
    db.add(audit)
    db.commit()

    return {"success": True, "message": "Logged out successfully"}


# ── FORGOT PASSWORD ───────────────────────────────────────────
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.email == req.email.lower()) | (User.mobile == req.email)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User with this email or mobile number does not exist")

    # Invalidate old reset OTPs
    db.query(OtpCode).filter(
        OtpCode.userId == user.id, OtpCode.purpose == "RESET_PASSWORD", OtpCode.isUsed == False
    ).update({"isUsed": True})

    otp_code = generate_otp()
    otp = OtpCode(
        userId=user.id,
        code=otp_code,
        purpose="RESET_PASSWORD",
        expiresAt=get_otp_expiry(10),
    )
    db.add(otp)
    db.commit()

    print(f"[OTP] Reset Password OTP for {user.email}: {otp_code}")

    return {
        "success": True,
        "message": "OTP sent. Please verify to reset your password.",
        "userId": user.id,
        "otpCode": otp_code,
    }


# ── RESET PASSWORD ────────────────────────────────────────────
@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.newPassword) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    otp_record = (
        db.query(OtpCode)
        .filter(
            OtpCode.userId == req.userId,
            OtpCode.isUsed == False,
            OtpCode.purpose == "RESET_PASSWORD",
            OtpCode.expiresAt > datetime.utcnow(),
        )
        .order_by(OtpCode.createdAt.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Please request a new one.")

    if otp_record.attempts >= 5:
        otp_record.isUsed = True
        db.commit()
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")

    if otp_record.code != req.otp:
        otp_record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_record.isUsed = True

    hashed = get_password_hash(req.newPassword)
    db.query(User).filter(User.id == req.userId).update({
        "passwordHash": hashed,
        "passwordRaw": None,
    })

    audit = AuditLog(userId=req.userId, action="PASSWORD_RESET")
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": "Password reset successful. You can now login with your new password.",
    }
