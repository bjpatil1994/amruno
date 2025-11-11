from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean # ✅ Boolean import kiya
from sqlalchemy.sql import func 
from database import Base

class User(Base):
    # ... (User class same) ...
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    mobile_number = Column(String(15), unique=True, index=True)
    hashed_password = Column(String(255))
    gender = Column(String(10)) 

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    sender_mobile = Column(String(15), ForeignKey("users.mobile_number"))
    recipient_mobile = Column(String(15), ForeignKey("users.mobile_number"))
    
    content = Column(String(1000), nullable=True) 
    image_url = Column(String(500), nullable=True) 
    audio_url = Column(String(500), nullable=True) 
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # ✅ FIX YAHAN HAI: Naya Column Add Kiya
    is_read = Column(Boolean, default=False)