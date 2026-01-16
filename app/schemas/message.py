from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# Shared fields between different message schemas
class MessageBase(BaseModel):
    content: Optional[str] = None
    media_url: Optional[str] = None
    media_type: str = "text"  # text | image | pdf


# Schema used when sending a message (WebSocket input)
class MessageCreate(MessageBase):
    receiver_id: int


# Schema returned to frontend for displaying messages
class MessageOut(MessageBase):
    id: int
    sender_id: int
    receiver_id: int
    timestamp: datetime
    status: str  # sent | delivered | read

    class Config:
        # Allows returning SQLAlchemy objects directly
        from_attributes = True
