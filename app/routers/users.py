from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Request,
)
from sqlalchemy.orm import Session

from app.core.security import get_current_user, get_password_hash
from app.db.models import User
from app.db.session import get_db
from app.services.image_service import upload_dp_to_imagekit

router = APIRouter()


@router.patch("/users/me")
async def update_user_profile(
    request: Request,
    display_name: str = Form(...),
    password: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """
    Update logged-in user's profile.
    Supports text fields and profile image upload.
    """
    # Re-fetch user to ensure valid authentication
    current_user = await get_current_user(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Update display name
    if display_name.strip():
        current_user.display_name = display_name.strip()

    # Update password if provided
    if password and password.strip():
        current_user.password = get_password_hash(password)

    # Update avatar if provided
    if avatar and avatar.filename:
        if not avatar.content_type or not avatar.content_type.startswith("image/"):
            raise HTTPException(400, detail="File must be an image")

        avatar.file.seek(0, 2)
        file_size = avatar.file.tell()
        avatar.file.seek(0)

        if file_size > 5 * 1024 * 1024:
            raise HTTPException(400, detail="Image too large (max 5MB)")

        image_url = await upload_dp_to_imagekit(
            avatar,
            folder="chat_app_profiles",
        )
        current_user.profile_pic = image_url

    # Persist changes
    try:
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Failed to save profile changes")

    return {
        "message": "Profile updated successfully",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "display_name": current_user.display_name,
            "profile_pic": current_user.profile_pic,
        },
    }
