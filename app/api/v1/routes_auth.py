import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db=Depends(get_db_session)):
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


