from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User

from datetime import datetime, timedelta
from typing import Optional
   

# 1. Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Token Configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Password Functions ---

def verify_password(plain_password, hashed_password):
    """Checks if the typed password matches the stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Converts a plain password into a secure hash."""
    return pwd_context.hash(password)

# --- Token Creation ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a JWT Token string."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    
    # Create the encoded JWT string
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 1. Try to get token from cookie first
    token = request.cookies.get("access_token")

    # 2. If no cookie, try the Authorization header (API flow)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        print("DEBUG: No token found in cookie or header")
        return None
    
    if token.startswith("Bearer "):
        token = token.split(" ")[1]
    
    try: 
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError as e:
        print(f"DEBUG: JWT Decode Error: {e}")
        return None
    
    # Get user from DB
    user = db.query(User).filter(User.username == username).first()
    return user