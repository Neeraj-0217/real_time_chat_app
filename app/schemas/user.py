from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Base schema (shared properties)
class UserBase(BaseModel):
    username: str
    display_name: str
    gender: Optional[str] = None

# Schema for creating a user (Register)
class UserCreate(UserBase):
    pass
    # Profile pic is handled as UploadFile, not Pydantic

# Schema for reading user data (returning to frontend)
class UserOut(UserBase):
    id: int
    username: str
    display_name: str
    profile_pic: Optional[str] = None
    # created_at: datetime
    is_online: bool

    class Config:
        from_attributes = True


class ContactShow(BaseModel):
    id: int
    contact: UserOut
    added_at: str

    class Config:
        from_attributes = True