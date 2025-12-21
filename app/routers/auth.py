from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
from app.core.security import create_access_token
from app.services.image_service import imagekit
from imagekitio import ImageKit
import uuid
from datetime import timedelta
import os
import shutil
import tempfile
from starlette.concurrency import run_in_threadpool
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- REGISTER ---

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    # FIXED: Explicitly passing 'request' and 'name'
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={}
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
        request: Request,
        username: str = Form(...),
        display_name: str = Form(...),
        gender: str = Form(...),
        profile_pic: UploadFile = File(None),
        db: Session = Depends(get_db)
):
    # 1. Check if username exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Username already taken."}
        )

    # 2. Upload Image to ImageKit (if provided)

    pic_url = None
    temp_file_path = None

    if profile_pic and profile_pic.filename:
        try:
            suffix = os.path.splitext(profile_pic.filename)[1]

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                shutil.copyfileobj(profile_pic.file, temp_file)
                temp_file_path = temp_file.name

            def sync_upload():
                with open(temp_file_path, "rb") as f:
                    return imagekit.upload_file(
                        file=f,
                        file_name=f"{username}_{uuid.uuid4()}",
                        options=UploadFileRequestOptions(
                            folder="/chat_app_profiles/",
                            use_unique_file_name=True,
                            tags=['profile_pic-upload'],
                            is_private_file=False
                        )
                    )
                
            upload_response = await run_in_threadpool(sync_upload)

            if upload_response and hasattr(upload_response, 'url'):
                pic_url = upload_response.url
            else:
                print(f"Upload Warning: Response was {upload_response}")
        except Exception as e:
            print(f"Image Upload Failed: {e}")
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    # 3. Create User
    new_user = User(
        username=username,
        display_name=display_name,
        gender=gender,
        profile_pic=pic_url
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/login", status_code=303)


# --- LOGIN ---

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={}
    )


@router.post("/login")
async def login(
        request: Request,
        username: str = Form(...),
        db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Invalid username."}
        )
    
    # Create Access Token
    access_token_expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Login Success -> Set Cookie
    response = RedirectResponse(url="/chat", status_code=303)
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}",
        httponly=True 
    )
    return response


# --- LOGOUT ---
@router.get("/logout")
async def logout():
    """Logout user and clear authentication cookie"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("user_id")
    return response