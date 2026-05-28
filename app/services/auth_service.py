"""Auth service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog, OtpCode, RefreshToken, User
from app.security import (
	create_access_token,
	generate_otp,
	generate_refresh_token,
	get_otp_expiry,
	get_password_hash,
	verify_password,
)


def normalize_identifier(value: str) -> str:
	return value.strip().lower()


def utc_now_naive() -> datetime:
	"""Return current UTC timestamp without tzinfo for naive DB datetime comparisons."""
	return datetime.now(UTC).replace(tzinfo=None)


def get_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
	normalized = normalize_identifier(identifier)
	return (
		db.query(User)
		.filter((User.email == normalized) | (User.mobile == identifier.strip()))
		.first()
	)


def create_user_account(
	db: Session,
	full_name: str,
	email: str,
	password: str,
	mobile: str | None = None,
	role: str = "PATIENT",
) -> User:
	user = User(
		fullName=full_name,
		email=normalize_identifier(email),
		mobile=mobile or None,
		passwordHash=get_password_hash(password),
		role=role,
		status="ACTIVE" if role != "DOCTOR" else "PENDING_VERIFICATION",
	)
	db.add(user)
	db.flush()
	return user


def mark_otp_used(db: Session, user_id: str, purpose: str | None = None) -> None:
	query = db.query(OtpCode).filter(OtpCode.userId == user_id, OtpCode.isUsed == False)  # noqa: E712
	if purpose:
		query = query.filter(OtpCode.purpose == purpose)
	query.update({"isUsed": True})


def create_otp(db: Session, user_id: str, purpose: str, ttl_minutes: int) -> str:
	code = generate_otp()
	db.add(
		OtpCode(
			userId=user_id,
			code=code,
			purpose=purpose,
			expiresAt=get_otp_expiry(ttl_minutes),
		)
	)
	return code


def validate_password(password: str, hashed_password: str) -> bool:
	return verify_password(password, hashed_password)


def issue_tokens(db: Session, user: User, refresh_days: int = 7) -> tuple[str, str]:
	access_token = create_access_token(user.id, user.email, user.role)
	refresh_token = generate_refresh_token()
	db.add(
		RefreshToken(
			userId=user.id,
			token=refresh_token,
			expiresAt=datetime.now(UTC) + timedelta(days=refresh_days),
		)
	)
	return access_token, refresh_token


def revoke_refresh_tokens(db: Session, user_id: str) -> None:
	db.query(RefreshToken).filter(RefreshToken.userId == user_id).update({"isRevoked": True})


def write_audit(db: Session, user_id: str | None, action: str, resource: str | None = None, resource_id: str | None = None) -> None:
	db.add(AuditLog(userId=user_id, action=action, resource=resource, resourceId=resource_id))


def build_auth_response(user: User, access_token: str, refresh_token: str) -> dict:
	return {
		"success": True,
		"accessToken": access_token,
		"refreshToken": refresh_token,
		"user": {
			"id": user.id,
			"email": user.email,
			"fullName": user.fullName,
			"role": user.role,
		},
	}


class AuthService:
	"""Class wrapper for authentication helpers to be used as a DI service."""

	def register(self, db: Session, fullName: str, email: str, password: str, mobile: str | None = None, role: str = "PATIENT") -> dict:
		existing = db.query(User).filter((User.email == email.lower()) | (User.mobile == mobile if mobile else False)).first()
		if existing:
			raise ValueError("User exists")
		user = create_user_account(db, fullName, email, password, mobile, role)
		# mark previous otps used
		mark_otp_used(db, user.id)
		otp = create_otp(db, user.id, "REGISTER", 10)
		write_audit(db, user.id, "REGISTER", "user")
		db.commit()
		return {"userId": user.id, "otpCode": otp}

	def login_request_otp(self, db: Session, identifier: str) -> dict:
		user = get_user_by_identifier(db, identifier)
		if not user:
			raise LookupError("User not found")
		mark_otp_used(db, user.id)
		otp = create_otp(db, user.id, "LOGIN", 5)
		write_audit(db, user.id, "LOGIN_ATTEMPT")
		db.commit()
		return {"userId": user.id, "otpCode": otp}

	def verify_otp_and_issue(self, db: Session, user_id: str, otp_value: str) -> dict:
		# this replicates the route logic: validate otp, set user active, issue tokens

		otp_record = (
			db.query(OtpCode)
			.filter(
				OtpCode.userId == user_id,
				OtpCode.isUsed == False,
				OtpCode.purpose.in_(["LOGIN", "REGISTER"]),
				OtpCode.expiresAt > datetime.now(UTC),
			)
			.order_by(OtpCode.createdAt.desc())
			.first()
		)

		if not otp_record:
			raise ValueError("OTP expired or not found")

		if otp_record.attempts >= 5:
			otp_record.isUsed = True
			db.commit()
			raise ValueError("Too many attempts")

		if otp_record.code != otp_value:
			otp_record.attempts += 1
			db.commit()
			raise ValueError("Invalid OTP")

		otp_record.isUsed = True
		user = db.query(User).filter(User.id == user_id).first()
		user.status = "ACTIVE"

		access_token, refresh_token = issue_tokens(db, user)
		write_audit(db, user.id, "LOGIN_SUCCESS")
		db.commit()
		return build_auth_response(user, access_token, refresh_token)

	def refresh(self, db: Session, refresh_token_value: str) -> dict:
		record = db.query(RefreshToken).filter(RefreshToken.token == refresh_token_value).first()
		if not record or record.isRevoked or record.expiresAt < utc_now_naive():
			raise LookupError("Invalid or expired refresh token")
		record.isRevoked = True
		user = db.query(User).filter(User.id == record.userId).first()
		new_access = create_access_token(user.id, user.email, user.role)
		new_refresh = generate_refresh_token()
		new_rt = RefreshToken(userId=user.id, token=new_refresh, expiresAt=datetime.now(UTC) + timedelta(days=7))
		db.add(new_rt)
		db.commit()
		return {"accessToken": new_access, "refreshToken": new_refresh}

	def logout(self, db: Session, user: User, refresh_token_value: str | None = None) -> dict:
		if refresh_token_value:
			db.query(RefreshToken).filter(RefreshToken.token == refresh_token_value, RefreshToken.userId == user.id).update({"isRevoked": True})
		write_audit(db, user.id, "LOGOUT")
		db.commit()
		return {"success": True}

	def revoke_tokens(self, db: Session, user_id: str) -> None:
		"""Revoke all refresh tokens for a user and write an audit entry."""
		revoke_refresh_tokens(db, user_id)
		write_audit(db, user_id, "REVOKE_TOKENS")
		db.commit()
