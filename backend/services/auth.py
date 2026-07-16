from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from config import settings


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt. We encode to bytes and enforce bcrypt's
    72-byte limit explicitly (bytes beyond 72 are ignored by the algorithm)."""
    pwd_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt()  # random salt per password
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Re-hash the attempt and compare against the stored hash. One-way."""
    pwd_bytes = plain.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))


def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None