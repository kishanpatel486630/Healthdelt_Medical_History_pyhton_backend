from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.config import settings
from app.services.upload_service import UploadService
from app.services.patient_service import PatientService
from app.services.doctor_service import DoctorService
from app.services.pdf_service import PdfService
from app.services.ai_service import AiService
from app.services.user_service import UserService
from app.services.qr_service import QrService


def get_upload_service():
    return UploadService(settings.UPLOAD_DIR)


def get_patient_service():
    return PatientService()


def get_auth_service():
    from app.services.auth_service import AuthService

    return AuthService()


def get_doctor_service():
    return DoctorService()


def get_pdf_service():
    return PdfService()


def get_ai_service():
    return AiService()


def get_user_service():
    return UserService()


def get_qr_service():
    return QrService()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.JWT_ACCESS_SECRET, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    if user.status == "SUSPENDED":
        raise HTTPException(status_code=403, detail="Account suspended")

    return user


def require_role(*roles: str):
    """Dependency factory that checks the current user's role."""

    def check(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return check
