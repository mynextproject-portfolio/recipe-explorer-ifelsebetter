"""
Authentication routes for Recipe Explorer.

Handles user registration, login, logout, profile retrieval,
and updates. Enforces secure cookies and CSRF token initialization.
"""

import secrets
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, field_validator
from typing import Optional, Dict
from app.models import User, UserCreate, UserLogin, UserProfileUpdate
from app.services.interfaces import RecipeStorageInterface, CacheInterface
from app.dependencies import get_storage, get_cache, get_current_user
from app.services.auth import hash_password, verify_password, create_access_token, verify_access_token
from app.services.metrics import auth_operations_total

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    profile_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v



def set_auth_cookies(response: Response, user_id: str, email: str, username: str) -> str:
    """Helper to generate JWT and set secure cookies on response."""
    # Generate JWT
    token = create_access_token(user_id=user_id, email=email, username=username)
    
    # Secure Session cookie holding the JWT
    # Secure=True is best, but since local dev might run on HTTP, we can set secure=True
    # as per production guidelines, FastAPI/Starlette handles it cleanly.
    response.set_cookie(
        key="__Secure-session",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/"
    )
    
    # CSRF cookie (not HttpOnly so frontend JS can read and send it in headers)
    csrf_token = secrets.token_hex(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        path="/"
    )
    return token


@router.post("/register", status_code=201)
def register(
    payload: RegisterRequest,
    response: Response,
    storage: RecipeStorageInterface = Depends(get_storage)
):
    try:
        # Check if username/email already exist
        if storage.get_user_by_username(payload.username):
            auth_operations_total.labels(action="register", status="failure").inc()
            raise HTTPException(status_code=400, detail="Username is already taken")
        if storage.get_user_by_email(payload.email):
            auth_operations_total.labels(action="register", status="failure").inc()
            raise HTTPException(status_code=400, detail="Email is already registered")

        hashed = hash_password(payload.password)
        user_create = UserCreate(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            profile_name=payload.profile_name
        )
        user = storage.create_user(user_create, hashed)
        
        # Log user in immediately
        set_auth_cookies(response, user.id, user.email, user.username)
        
        auth_operations_total.labels(action="register", status="success").inc()
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "profile_name": user.profile_name,
            "preferences": user.preferences
        }
    except HTTPException:
        raise
    except Exception as exc:
        auth_operations_total.labels(action="register", status="failure").inc()
        raise HTTPException(status_code=500, detail="Registration failed due to server error")


@router.post("/login")
def login(
    payload: UserLogin,
    response: Response,
    storage: RecipeStorageInterface = Depends(get_storage)
):
    user = storage.get_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        auth_operations_total.labels(action="login", status="failure").inc()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    set_auth_cookies(response, user.id, user.email, user.username)
    
    auth_operations_total.labels(action="login", status="success").inc()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "profile_name": user.profile_name,
        "preferences": user.preferences
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    cache: CacheInterface = Depends(get_cache)
):
    token = request.cookies.get("__Secure-session")
    if token:
        payload = verify_access_token(token)
        if payload and "jti" in payload:
            jti = payload["jti"]
            # Blacklist token JTI in Redis with a TTL matching token expiry
            exp = payload.get("exp", 0)
            import time
            now = int(time.time())
            ttl = max(1, exp - now)
            cache.set(f"blacklist:{jti}", "1", ttl_seconds=ttl)

    # Invalidate cookies
    response.set_cookie(
        key="__Secure-session",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
        max_age=0
    )
    response.set_cookie(
        key="csrf_token",
        value="",
        httponly=False,
        secure=True,
        samesite="lax",
        path="/",
        max_age=0
    )
    
    auth_operations_total.labels(action="logout", status="success").inc()
    return {"message": "Successfully logged out"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "profile_name": current_user.profile_name,
        "preferences": current_user.preferences
    }


@router.put("/profile")
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    storage: RecipeStorageInterface = Depends(get_storage)
):
    updated = storage.update_user_profile(
        user_id=current_user.id,
        profile_name=payload.profile_name,
        preferences=payload.preferences
    )
    if not updated:
        raise HTTPException(status_code=400, detail="Profile update failed")
        
    return {
        "id": updated.id,
        "username": updated.username,
        "email": updated.email,
        "profile_name": updated.profile_name,
        "preferences": updated.preferences
    }
