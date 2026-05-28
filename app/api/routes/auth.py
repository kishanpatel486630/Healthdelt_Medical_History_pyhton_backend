import time
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User, Doctor, OtpCode, RefreshToken, AuditLog
from app.dependencies import get_current_user, get_auth_service
from app.services.auth_service import AuthService
from app.security import verify_password, get_password_hash

router = APIRouter(prefix="/api/auth", tags=["auth"])


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


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
	try:
		res = auth_service.register(db, req.fullName, req.email, req.password, req.mobile, req.role)
	except ValueError:
		raise HTTPException(status_code=409, detail="User with this email or mobile already exists")
	return {"success": True, "message": "Registration successful. Please verify with OTP.", "userId": res["userId"], "otpCode": res["otpCode"]}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
	try:
		res = auth_service.login_request_otp(db, req.email)
	except LookupError:
		raise HTTPException(status_code=401, detail="Invalid credentials")
	return {"success": True, "message": "OTP sent. Please verify to complete login.", "userId": res["userId"], "otpCode": res["otpCode"]}


@router.post("/verify-otp")
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
	try:
		return auth_service.verify_otp_and_issue(db, req.userId, req.otp)
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh-token")
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db), auth_service: AuthService = Depends(get_auth_service)):
	try:
		res = auth_service.refresh(db, req.refreshToken)
	except LookupError:
		raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
	return {"success": True, **res}


@router.post("/logout")
def logout(
	req: LogoutRequest,
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db),
	auth_service: AuthService = Depends(get_auth_service),
):
	auth_service.logout(db, current_user, req.refreshToken)
	return {"success": True, "message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
	user = db.query(User).filter(
		(User.email == req.email.lower()) | (User.mobile == req.email)
	).first()

	if not user:
		raise HTTPException(status_code=404, detail="User with this email or mobile number does not exist")

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
			OtpCode.expiresAt > datetime.now(UTC),
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
