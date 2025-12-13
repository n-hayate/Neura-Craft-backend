from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import json
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserCreate


settings = get_settings()


# region agent log (debug-mode)
_DEBUG_LOG_PATH = Path(r"d:\UserDATA\DN30665\Desktop\Techファイル\step4_NC\.cursor\debug.log")
def _debug_log(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    try:
        payload = {
            "sessionId": "debug-session",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
# endregion agent log (debug-mode)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, email: str, password: str) -> User:
        user = self.db.query(User).filter(User.email == email).first()
        # region agent log (debug-mode)
        _debug_log(
            "D",
            "app/services/auth_service.py:authenticate",
            "authenticate checked user/password",
            {"userFound": bool(user), "passwordLen": len(password) if isinstance(password, str) else None},
        )
        # endregion agent log (debug-mode)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        return user

    def register_user(self, payload: UserCreate) -> User:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Registering user: {payload.email}")

        existing = self.db.query(User).filter(User.email == payload.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=get_password_hash(payload.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def issue_token(self, user: User) -> Token:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        token = create_access_token(subject=str(user.id), expires_delta=expires_delta)
        return Token(access_token=token)


