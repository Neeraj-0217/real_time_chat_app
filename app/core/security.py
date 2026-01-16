from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User

from datetime import datetime, timedelta, timezone
from typing import Optional


# -----------------------------
# Password Hashing Configuration
# -----------------------------
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
)

# Prevents denial-of-service via extremely large passwords
MAX_PASSWORD_LENGTH = 1024


# -----------------------------
# OAuth2 / JWT Configuration
# -----------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# -----------------------------
# Password Utilities
# -----------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare plain password with stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password using Argon2."""
    if len(password.encode("utf-8")) > MAX_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail="Password too long")
    return pwd_context.hash(password)


# -----------------------------
# JWT Token Utilities
# -----------------------------
def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token.

    `data` usually contains {"sub": username}
    """
    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc) + timedelta(minutes=15)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# -----------------------------
# Authentication Dependencies
# -----------------------------
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Retrieves the currently authenticated user from JWT.

    Token is checked in:
    1. Cookies (browser flow)
    2. Authorization header (API / Swagger flow)

    Returns None if unauthenticated.
    """
    token = request.cookies.get("access_token")

    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        return None

    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        username: str = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    return db.query(User).filter(User.username == username).first()


async def get_current_active_user(
    user: User = Depends(get_current_user),
):
    """
    Enforces authentication.
    Raises 401 if user is not logged in.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
