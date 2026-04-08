"""Pydantic schemas for authentication endpoints."""
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"  # "admin" | "user"


class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None
