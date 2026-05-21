import secrets
import random
import string
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt

from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt directly — compatible with bcryptjs from Node.js."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt — compatible with bcryptjs from Node.js."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Match Node.js: jwt.sign({ id, email, role }, ACCESS_SECRET, { expiresIn: '15m' })"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "id": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_ACCESS_SECRET, algorithm=settings.ALGORITHM)


def generate_refresh_token() -> str:
    """Match Node.js: crypto.randomBytes(40).toString('hex')"""
    return secrets.token_hex(40)


def generate_otp(length: int = 4) -> str:
    """Generate a numeric OTP code."""
    return "".join(random.choices(string.digits, k=length))


def get_otp_expiry(minutes: int = 5) -> datetime:
    """Return a datetime `minutes` from now."""
    return datetime.utcnow() + timedelta(minutes=minutes)
