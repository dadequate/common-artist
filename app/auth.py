import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext

_SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_admin_password(password: str) -> bool:
    stored = os.environ.get("ADMIN_PASSWORD", "")
    if stored.startswith("$2b$"):
        return pwd_context.verify(password, stored)
    return password == stored


def create_admin_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": "admin", "exp": expire}, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_admin_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def require_admin(request: Request) -> str:
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER,
                            headers={"Location": "/admin/login"})
    sub = decode_admin_token(token)
    if sub != "admin":
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER,
                            headers={"Location": "/admin/login"})
    return sub
