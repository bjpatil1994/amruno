from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List 

class UserCreate(BaseModel):
    full_name: str
    mobile_number: str
    password: str
    gender: str 

class UserOut(BaseModel):
    id: int
    full_name: str
    mobile_number: str
    gender: str 

    class Config:
        from_attributes = True

class MessageOut(BaseModel):
    id: int
    sender_mobile: str
    recipient_mobile: str
    content: Optional[str] = None
    timestamp: datetime
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    
    # ✅ FIX: Is_read ko MessageOut mein add kiya
    is_read: bool = False

    class Config:
        from_attributes = True

# ✅ FIX: ChatPartnerOut class mein unread_count add kiya
class ChatPartnerOut(UserOut):
    last_message: Optional[str] = None
    last_message_timestamp: Optional[str] = None
    unread_count: int = 0  # <-- Naya field