from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db_session
from app.db.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserRead])
def list_users(
    db=Depends(get_db_session),
    _: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    service = UserService(db)
    return service.list(limit=limit, offset=offset)


@router.post("/", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    db=Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    service = UserService(db)
    return service.create(payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db=Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    service = UserService(db)
    return service.get(user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db=Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    service = UserService(db)
    return service.update(user_id, payload)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db=Depends(get_db_session),
    _: User = Depends(get_current_user),
):
    service = UserService(db)
    service.delete(user_id)


