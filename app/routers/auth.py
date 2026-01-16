from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Form,
    UploadFile,
    File,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user,
)
from app.services.image_service import imagekit, upload_dp_to_imagekit

import uuid
import os
import shutil
import tempfile
from datetime import timedelta
from starlette.concurrency import run_in_threadpool
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ------------------------
# Register
# ------------------------

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render user registration page."""
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={},
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(...),
    gender: str = Form(...),
    profile_pic: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    # 1. Validate username
    if len(username) < 3:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Username must be at least 3 characters."},
        )

    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Username already taken."},
        )

    # 2. Validate password
    if len(password) < 6:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Password must be at least 6 characters."},
        )

    if len(password) > 100:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Password too long (max 100 characters)."},
        )

    # 3. Hash password
    try:
        hashed_password = get_password_hash(password)
    except Exception:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Password processing failed. Please try again."},
        )

    # 4. Upload profile picture (optional)
    image_url = None
    if profile_pic and profile_pic.filename:
        if not profile_pic.content_type or not profile_pic.content_type.startswith("image/"):
            raise HTTPException(400, detail="File must be an image")

        profile_pic.file.seek(0, 2)
        file_size = profile_pic.file.tell()
        profile_pic.file.seek(0)

        if file_size > 5 * 1024 * 1024:
            raise HTTPException(400, detail="Image too large (max 5MB)")

        image_url = await upload_dp_to_imagekit(
            profile_pic,
            folder="chat_app_profiles",
        )

    # 5. Create user
    new_user = User(
        username=username,
        password=hashed_password,
        display_name=display_name,
        gender=gender,
        profile_pic=image_url,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 6. Auto-login after registration
    expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    token = create_access_token({"sub": new_user.username}, expires)

    response = RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
        secure=False,
        samesite="lax",
    )
    return response


# ------------------------
# Login
# ------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Invalid username or password."},
        )

    expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    token = create_access_token({"sub": user.username}, expires)

    response = RedirectResponse(url="/chat", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        max_age=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
        secure=False,
        samesite="lax",
    )
    return response


# ------------------------
# Auth Verification
# ------------------------

@router.get("/auth/verify")
async def verify_user(request: Request, db: Session = Depends(get_db)):
    """Verify currently authenticated user."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "profile_pic": user.profile_pic,
    }


# ------------------------
# Logout
# ------------------------

@router.get("/logout")
async def logout():
    """Clear auth cookie and logout user."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response
