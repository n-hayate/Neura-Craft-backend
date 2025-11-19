from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings


settings = get_settings()
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",  # bcryptのバージョンを明示的に指定
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Hashing password: '{password}' (len: {len(password)})")
    
    # bcryptは72バイトを超えるパスワードをハッシュ化できないため、制限する
    try:
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # 72バイトを超える場合は切り詰める
            password = password_bytes[:72].decode('utf-8', errors='ignore')
        return pwd_context.hash(password)
    except Exception as e:
        # エラーが発生した場合、より詳細な情報をログに記録
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Password hashing error: {e}, password length: {len(password.encode('utf-8'))}")
        raise


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if isinstance(subject, int):
        to_encode = {"sub": str(subject)}
    else:
        to_encode = {"sub": subject}

    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


