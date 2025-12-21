from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# 1. Shared Properties (Base)
class MessageBase(BaseModel):
    content: Optional[str] = None
    media_url: Optional[str] = None
    media_type: str = "text" 

# 2. Input: What the frontend sends via WebSocket
class MessageCreate(MessageBase):
    receiver_id: int 

# 3. Output: What the frontend receives to display
class MessageOut(MessageBase):
    id: int
    sender_id: int
    receiver_id: int
    timestamp: datetime
    status: str # sent, delivered, read

    class Config:
        from_attributes = True