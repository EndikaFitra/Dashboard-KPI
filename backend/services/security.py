"""
Security service — JWT encoding/decoding + bcrypt password hashing.
Provides FastAPI Depends for current user and admin guard.
"""
import os
import bcrypt
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from models.user import User

# ── Config ─────────────────────────────────────────────────────────────────── #
SECRET_KEY  = os.getenv("JWT_SECRET",         "kpi-analytics-secret-change-me")
ALGORITHM   = os.getenv("JWT_ALGORITHM",      "HS256")
EXPIRE_MIN  = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# ── OAuth2 scheme ───────────────────────────────────────────────────────────── #
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ── bcrypt helpers ─────────────────────────────────────────────────────────── #
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT helpers ─────────────────────────────────────────────────────────────── #
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ── FastAPI Dependencies ─────────────────────────────────────────────────────── #
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate JWT and return the authenticated User object."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if user is None:
        raise credentials_exc
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Guard — raises 403 if the authenticated user is not an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
