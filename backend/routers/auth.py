"""
Auth router — login, register (admin only), and /me endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from models.user import User
from schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from services.security import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    require_admin,
)

router = APIRouter()


# ── POST /auth/login ──────────────────────────────────────────────────────── #
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_username = payload.username.lower()
    user = db.query(User).filter(func.lower(User.username) == normalized_username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun tidak aktif. Hubungi administrator.",
        )

    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
    )


# ── POST /auth/register (admin only) ─────────────────────────────────────── #
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    payload.username = payload.username.lower()
    if db.query(User).filter(func.lower(User.username) == payload.username).first():
        raise HTTPException(status_code=400, detail="Username sudah digunakan")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email sudah digunakan")
    if payload.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role harus 'admin' atau 'user'")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── GET /auth/me ──────────────────────────────────────────────────────────── #
@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
