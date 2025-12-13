import logging
import json
import time
from pathlib import Path
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


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


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db=Depends(get_db_session)):
    # region agent log (debug-mode)
    email = getattr(payload, "email", "")
    email_hash = sha256(email.encode("utf-8")).hexdigest()[:12] if isinstance(email, str) else None
    _debug_log(
        "D",
        "app/api/v1/routes_auth.py:login",
        "/auth/login called",
        {"emailHash12": email_hash, "emailLen": len(email) if isinstance(email, str) else None},
    )
    # endregion agent log (debug-mode)
    auth_service = AuthService(db)
    user = auth_service.authenticate(payload.email, payload.password)
    return auth_service.issue_token(user)


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: UserCreate, db=Depends(get_db_session)):
    try:
        auth_service = AuthService(db)
        user = auth_service.register_user(payload)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error during user registration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


