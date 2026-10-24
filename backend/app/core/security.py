import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

pwd_hasher = PasswordHash.recommended()
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_hasher.verify(password, password_hash)


def create_access_token(*, user_id: UUID, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "jti": uuid4().hex,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def new_refresh_token() -> str:
    return uuid4().hex + uuid4().hex


def refresh_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
