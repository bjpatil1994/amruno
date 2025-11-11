from fastapi import FastAPI, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, File, UploadFile
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_, and_, distinct, func, desc # ✅ FIX: desc ko import kiya
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import models
import schemas
import security
from database import engine, SessionLocal, Base 
import json 
from connection_manager import manager 

# --- NAYE IMPORTS ---
import shutil
from pathlib import Path
import uuid
from fastapi.staticfiles import StaticFiles
from datetime import datetime
# --- YAHAA TAK ---

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- CORS Settings ---
# Aapki purani origins list ko comment kar diya hai
# origins = [
#     "http://localhost:8081",
#     "http://localhost",
#     "http://192.168.31.182:8081", 
#     "http://192.168.31.182"
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # ✅ FIX: Sabko allow kiya (Development ke liye)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- CORS End ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    mobile_number = security.verify_token(token, credentials_exception)
    user = db.query(models.User).filter(models.User.mobile_number == mobile_number).first()
    return user

@app.get("/")
def read_root():
    return {"message": "Amruno Backend Running 🚀"}

@app.post("/register", response_model=schemas.UserOut)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.mobile_number == user.mobile_number).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Mobile number already registered")
    hashed_password = security.hash_password(user.password)
    new_user = models.User(
        full_name=user.full_name,
        mobile_number=user.mobile_number,
        hashed_password=hashed_password,
        gender=user.gender
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login")
async def login_for_access_token(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    mobile_number = data.get("mobile_number")
    password = data.get("password")
    if not mobile_number or not password:
        raise HTTPException(status_code=400, detail="Missing mobile number or password")
    user = db.query(models.User).filter(models.User.mobile_number == mobile_number).first()
    if not user or not security.verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect mobile number or password")
    access_token = security.create_access_token({"sub": user.mobile_number})
    # ✅ FIX: Login response mein user_mobile bhi bhej rahe hain
    return {"access_token": access_token, "token_type": "bearer", "user_mobile": user.mobile_number}

@app.get("/users", response_model=List[schemas.UserOut])
def read_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    users = db.query(models.User).filter(models.User.mobile_number != current_user.mobile_number).all()
    return users

# --- ✅ NAYA FUNCTION: /users/me (App ko user ka mobile number dega) ---
@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- ✅ FIX: get_chat_history Order Fix ---
@app.get("/chat/{recipient_mobile}", response_model=List[schemas.MessageOut])
def get_chat_history(
    recipient_mobile: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    my_mobile = current_user.mobile_number
    messages = db.query(models.Message).filter(
        or_(
            and_(models.Message.sender_mobile == my_mobile, models.Message.recipient_mobile == recipient_mobile),
            and_(models.Message.sender_mobile == recipient_mobile, models.Message.recipient_mobile == my_mobile)
        )
    ).order_by(desc(models.Message.timestamp)).all() # ✅ FIX: Descending order kiya
    return messages


# --- FINAL get_my_chats endpoint (Unread Count + Last Message) ---
@app.get("/my-chats", response_model=List[schemas.ChatPartnerOut])
def get_my_chats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    my_mobile = current_user.mobile_number

    sent_to_mobiles = db.query(distinct(models.Message.recipient_mobile)).filter(
        models.Message.sender_mobile == my_mobile
    ).all()
    received_from_mobiles = db.query(distinct(models.Message.sender_mobile)).filter(
        models.Message.recipient_mobile == my_mobile
    ).all()
    
    all_chat_partners_mobiles = {row[0] for row in sent_to_mobiles} | {row[0] for row in received_from_mobiles}
    
    if not all_chat_partners_mobiles:
        return []

    chat_partners = db.query(models.User).filter(
        models.User.mobile_number.in_(all_chat_partners_mobiles)
    ).all()
    
    chat_partners_with_last_msg = []
    
    for partner in chat_partners:
        partner_mobile = partner.mobile_number
        
        last_msg = (
            db.query(models.Message)
            .filter(
                or_(
                    and_(models.Message.sender_mobile == my_mobile, models.Message.recipient_mobile == partner_mobile),
                    and_(models.Message.sender_mobile == partner_mobile, models.Message.recipient_mobile == my_mobile)
                )
            )
            .order_by(models.Message.timestamp.desc()) # ✅ FIX: Yahaan bhi desc() use kiya
            .first()
        )
        
        unread_count = db.query(models.Message).filter(
            models.Message.sender_mobile == partner_mobile,
            models.Message.recipient_mobile == my_mobile,
            models.Message.is_read == False
        ).count()
        
        partner_data = schemas.UserOut.from_orm(partner).dict()
        partner_data["unread_count"] = unread_count
        
        if last_msg:
            if last_msg.content:
                partner_data["last_message"] = last_msg.content
            elif last_msg.image_url:
                partner_data["last_message"] = "📷 Image"
            elif last_msg.audio_url:
                partner_data["last_message"] = "🎙️ Audio"
            else:
                partner_data["last_message"] = None
            
            partner_data["last_message_timestamp"] = last_msg.timestamp.isoformat()
        else:
            partner_data["last_message"] = None
            partner_data["last_message_timestamp"] = None
        
        chat_partners_with_last_msg.append(partner_data)
    
    chat_partners_with_last_msg.sort(
        key=lambda x: x["last_message_timestamp"] or '1970-01-01T00:00:00', 
        reverse=True
    )
            
    return chat_partners_with_last_msg


# --- API ENDPOINT: Read Messages ---
@app.post("/read-messages/{sender_mobile}")
def read_messages(
    sender_mobile: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    my_mobile = current_user.mobile_number

    db.query(models.Message).filter(
        models.Message.sender_mobile == sender_mobile,
        models.Message.recipient_mobile == my_mobile,
        models.Message.is_read == False
    ).update(
        {models.Message.is_read: True}, 
        synchronize_session=False
    )
    db.commit()
    return {"message": f"All messages from {sender_mobile} marked as read"}


@app.post("/upload-file")
async def create_upload_file(
    file: UploadFile = File(...), 
    current_user: models.User = Depends(get_current_user)
):
    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()
    file_url = f"http://192.168.31.182:8000/uploads/{unique_filename}"
    return {"url": file_url}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    
    await manager.connect(websocket, client_id)
    print(f"User {client_id} connected.")
    
    online_users = [user_id for user_id in manager.active_connections if user_id != client_id]
    await manager.send_personal_message(
        json.dumps({"type": "presence", "users": online_users}),
        client_id
    )
    await manager.broadcast_to_others(
        json.dumps({"type": "status", "user_id": client_id, "status": "online"}),
        client_id
    )
    
    db = SessionLocal() # ✅ FIX: Naya database session banaya
    try:
        while True:
            data = await websocket.receive_json()
            
            message_content: Optional[str] = None
            image_url: Optional[str] = None
            audio_url: Optional[str] = None
            
            recipient_id = data['recipient_id']

            if data.get('type') == 'chat_text':
                message_content = data['message']
            elif data.get('type') == 'chat_image':
                image_url = data['url']
            elif data.get('type') == 'chat_audio':
                audio_url = data['url']
            elif data.get('type') == 'typing':
                payload = { "type": "typing", "sender_id": client_id }
                await manager.send_personal_message(json.dumps(payload), recipient_id)
                continue 
            
            new_msg = models.Message(
                sender_mobile=client_id,
                recipient_mobile=recipient_id,
                content=message_content,
                image_url=image_url,
                audio_url=audio_url,
                is_read=False 
            )

            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)
            
            payload = {
                "type": "chat", 
                "id": str(new_msg.id), 
                "sender_mobile": new_msg.sender_mobile,
                "recipient_mobile": new_msg.recipient_mobile,
                "message": new_msg.content, # ✅ FIX: 'message' aur 'content' dono bhej rahe hain
                "content": new_msg.content,
                "image_url": new_msg.image_url,
                "audio_url": new_msg.audio_url,
                "timestamp": new_msg.timestamp.isoformat(),
                "is_read": new_msg.is_read
            }
            json_payload = json.dumps(payload)
            
            await manager.send_personal_message(json_payload, recipient_id)
            await manager.send_personal_message(json_payload, client_id)
            print(f"Message from {client_id} to {recipient_id} saved and sent.")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"User {client_id} disconnected.")
        await manager.broadcast_to_others(
            json.dumps({"type": "status", "user_id": client_id, "status": "offline"}),
            client_id
        )
    finally:
        db.close()