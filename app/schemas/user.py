from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# Shared user properties
class UserBase(BaseModel):
    username: str
    display_name: str
    gender: Optional[str] = None


# Schema used during user registration
class UserCreate(UserBase):
    # Profile picture is handled via UploadFile, not here
    pass


# Schema returned to frontend
class UserOut(UserBase):
    id: int
    profile_pic: Optional[str] = None
    is_online: bool

    class Config:
        # Enables ORM-to-schema conversion
        from_attributes = True


# Schema used for showing contacts
class ContactShow(BaseModel):
    id: int
    contact: UserOut
    added_at: str

    class Config:
        from_attributes = True
