from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Request,
    UploadFile,
    File,
    Form,
    status,
    HTTPException
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.db.models import Message, User, Contact
from app.services.socket_manager import manager
from app.core.security import get_current_user 
from app.services.image_service import imagekit

import json
from datetime import datetime
import os
import shutil
import tempfile
import uuid


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# File upload configuration
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_DOCUMENT_EXTENSIONS
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# HTML Route: Render the Chat Dashboard
@router.get("/chat", response_class=HTMLResponse)
async def chat_dashboard(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Fetch user's contacts to display in the sidebar
    contacts = db.query(Contact).filter(Contact.owner_id == user.id).all()
    
    return templates.TemplateResponse("chat/dashboard.html", {
        "request": request, 
        "user": user, 
        "contacts": contacts
    })

# ------ API ROUTES -----

@router.get("/users/search")
async def search_users(query: str, request: Request, db: Session = Depends(get_db)):
    """Search for users by username to start a new chat"""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    
    users = db.query(User).filter(
        User.username.contains(query),
        User.id != user.id
    ).limit(5).all()

    return [{
        "id": u.id,
        "username": u.username,
        "display_name": u.display_name,
        "profile_pic": u.profile_pic,
        "is_online": manager.is_user_online(u.id)  # Check real-time status
    } for u in users]

@router.get("/chat/history/{friend_id}")
async def get_chat_history(
    friend_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """Get previous messages"""
    user = await get_current_user(request, db)
    if not user:
        return []

    # Fetch messages between Me and Friend (ordered by time)
    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == friend_id),
            and_(Message.sender_id == friend_id, Message.receiver_id == user.id)
        )
    ).order_by(Message.timestamp.asc()).all()
    
    # Return as dict for JSON serialization
    return [{
        "id": msg.id,
        "sender_id": msg.sender_id,
        "receiver_id": msg.receiver_id,
        "content": msg.content,
        "media_url": msg.media_url,
        "media_type": msg.media_type,
        "status": msg.status,
        "timestamp": msg.timestamp.isoformat()
    } for msg in messages]


@router.get("/user/status/{user_id}")
async def get_user_status(user_id: int):
    """Get real-time online status of a user"""
    return {
        "user_id": user_id,
        "is_online": manager.is_user_online(user_id)
    }


# WebSocket Route (The Real-Time Link)
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int, db: Session = Depends(get_db)):
    # Connect the websocket first
    await manager.connect(websocket, client_id)
    
    # CRITICAL: Only set user online if this is their FIRST connection
    was_offline = not manager.is_user_online(client_id, exclude_websocket=websocket)
    
    if was_offline:
        user = db.query(User).filter(User.id == client_id).first()
        if user:
            user.is_online = True
            db.commit()

        # Notify all friends that this user just came online
        online_payload = {
            "type": "user_status",
            "user_id": client_id,
            "status": "online"
        }
        
        # Get all people who should be notified
        await notify_contacts_about_status(client_id, online_payload, db)

    pending_messages = db.query(Message).filter(
        Message.receiver_id == client_id,
        Message.status == "sent"
    ).all()

    if pending_messages:
        for msg in pending_messages:
            msg.status = 'delivered'
            await manager.send_personal_message({
                "type": "status_update",
                "message_id": msg.id,
                "status": "delivered"
            }, msg.sender_id)

        db.commit()

    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)

            # Type 1: Regular Message
            if 'receiver_id' in msg_data and msg_data.get('type') != 'typing':
                receiver_id = int(msg_data['receiver_id'])
                content = msg_data.get('content', '')
                media_url = msg_data.get('media_url', None)
                media_type = msg_data.get('media_type', 'text')

                # Ensure contact relationship exists
                existing_contact = db.query(Contact).filter(
                    Contact.owner_id == client_id, 
                    Contact.contact_id == receiver_id
                ).first()

                if not existing_contact:
                    new_contact = Contact(owner_id=client_id, contact_id=receiver_id)
                    db.add(new_contact)

                    reverse_contact = Contact(owner_id=receiver_id, contact_id=client_id)
                    db.add(reverse_contact)
                    db.commit()

                # Determine initial status based on receiver's online state
                is_receiver_online = manager.is_user_online(receiver_id)
                status = "delivered" if is_receiver_online else "sent"

                # Save message to database
                new_msg = Message(
                    sender_id=client_id,
                    receiver_id=receiver_id,
                    content=content,
                    media_url=media_url,
                    media_type=media_type,
                    status=status
                )
                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)

                # Prepare response payload
                response = {
                    "type": "message",
                    "id": new_msg.id,
                    "content": new_msg.content,
                    "media_url": new_msg.media_url,
                    "media_type": new_msg.media_type,
                    "sender_id": client_id,
                    "receiver_id": receiver_id,
                    "timestamp": new_msg.timestamp.isoformat(),
                    "status": status
                }

                # Send to receiver (if online)
                if is_receiver_online:
                    await manager.send_personal_message(response, receiver_id)
                
                # Send confirmation back to sender
                await manager.send_personal_message(response, client_id)

            # Type 2: Read Receipt
            elif msg_data.get('type') == 'read_receipt':
                msg_id = msg_data['message_id']
                sender_id = msg_data['sender_id']

                # Update message status in database
                msg_to_update = db.query(Message).filter(Message.id == msg_id).first()
                if msg_to_update and msg_to_update.status != "read":
                    msg_to_update.status = "read"
                    db.commit()

                    # Notify the sender about read status
                    await manager.send_personal_message({
                        "type": "status_update",
                        "message_id": msg_id,
                        "status": "read"
                    }, sender_id)

            # Type 3: Delivered Receipt
            elif msg_data.get('type') == 'delivered_receipt':
                msg_id = msg_data['message_id']
                sender_id = msg_data['sender_id']

                # Update message status
                msg_to_update = db.query(Message).filter(Message.id == msg_id).first()
                if msg_to_update and msg_to_update.status == "sent":
                    msg_to_update.status = "delivered"
                    db.commit()

                    # Notify sender
                    await manager.send_personal_message({
                        "type": "status_update",
                        "message_id": msg_id,
                        "status": "delivered"
                    }, sender_id)
            
            # Type 4: Ping to check connection
            elif msg_data.get('type') == 'ping':
                await websocket.send_json({"type": "pong"})

            elif msg_data.get('type') == 'typing':
                receiver_id = int(msg_data['receiver_id'])

                await manager.send_personal_message({
                    'type': 'typing',
                    'sender_id': client_id,
                }, receiver_id)
            
    except WebSocketDisconnect:
        # Disconnect this specific websocket
        manager.disconnect(websocket, client_id)
        
        # CRITICAL: Only mark user offline if ALL their connections are closed
        still_online = manager.is_user_online(client_id)
        
        if not still_online:
            user = db.query(User).filter(User.id == client_id).first()
            if user:
                user.is_online = False
                db.commit()

            # Notify all contacts that user is now offline
            offline_payload = {
                "type": "user_status", 
                "user_id": client_id, 
                "status": "offline"
            }
            
            await notify_contacts_about_status(client_id, offline_payload, db)
    
    except Exception as e:
        print(f"❌ WebSocket Error for user {client_id}: {e}")
        manager.disconnect(websocket, client_id)


async def notify_contacts_about_status(user_id: int, payload: dict, db: Session):
    """
    Notify all contacts (bidirectional) about a user's status change.
    This ensures both people who added this user AND people this user added get notified.
    """
    # Get contacts where user_id is the owner (people I added)
    my_contacts = db.query(Contact).filter(Contact.owner_id == user_id).all()
    
    # Get contacts where user_id is the contact (people who added me)
    reverse_contacts = db.query(Contact).filter(Contact.contact_id == user_id).all()
    
    # Create a set to avoid duplicate notifications
    notify_users = set()
    
    for contact in my_contacts:
        notify_users.add(contact.contact_id)
    
    for contact in reverse_contacts:
        notify_users.add(contact.owner_id)
    
    # Send notification to all relevant users
    for friend_id in notify_users:
        if friend_id != user_id:  # Don't notify self
            await manager.send_personal_message(payload, friend_id)

@router.post("/chat/upload")
async def upload_attachment(
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):
    # Validate extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Determine media type
    media_type = "text"
    target_folder = "/chat_others/"

    if file_ext in ALLOWED_IMAGE_EXTENSIONS:
        media_type = "image"
        target_folder = "/chat_images/"
    elif file_ext in ALLOWED_DOCUMENT_EXTENSIONS:
        media_type = "document"
        target_folder = "/chat_documents/"

    # Read file and validate size
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 5MB."
        )
    await file.seek(0)

    temp_file_path = None
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # Upload to ImageKit
        def sync_upload():
            with open(temp_file_path, "rb") as f:
                return imagekit.upload_file(
                    file=f,
                    file_name=f"chat_{user.username}_{uuid.uuid4()}",
                    options=UploadFileRequestOptions(
                        folder=target_folder,
                        is_private_file=False,
                        use_unique_file_name=True,
                        tags=['chat-attachment', media_type]
                    )
                )
            
        upload_response = await run_in_threadpool(sync_upload)

        # Handle Response
        if upload_response and hasattr(upload_response, "url"):
            return {
                "url": upload_response.url,
                "type": media_type,
                "filename": file.filename,
                "size": file_size
            }
        else:
            print(f"ImageKit Error: {upload_response}")
            raise HTTPException(status_code=500, detail="Upload failed")
    except HTTPException as he:
        raise he   
    except Exception as e:
        print(f"Attachment Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Server error during upload.")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

@router.get("/debug/connections")
async def debug_connections(request: Request, db: Session = Depends(get_db)):
    """Debug endpoint to see connection statistics"""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    
    stats = manager.get_stats()
    
    # Get database status for comparison
    online_users_db = db.query(User).filter(User.is_online == True).all()
    online_users_db_ids = [u.id for u in online_users_db]
    
    return {
        "websocket_stats": stats,
        "database_online_users": online_users_db_ids,
        "discrepancy": {
            "in_db_not_in_ws": [uid for uid in online_users_db_ids if uid not in stats['users']],
            "in_ws_not_in_db": [uid for uid in stats['users'] if uid not in online_users_db_ids]
        }
    }


@router.post("/debug/fix-online-status")
async def fix_online_status(request: Request, db: Session = Depends(get_db)):
    """Manually sync database online status with actual connections"""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)
    
    online_user_ids = manager.get_online_users()
    
    # Set all users to offline first
    db.query(User).update({User.is_online: False})
    
    # Set only connected users to online
    if online_user_ids:
        db.query(User).filter(User.id.in_(online_user_ids)).update(
            {User.is_online: True}, 
            synchronize_session=False
        )
    
    db.commit()
    
    return {
        "message": "Online status synchronized",
        "online_users": online_user_ids
    }