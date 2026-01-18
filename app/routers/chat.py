import json
import os
import tempfile
import uuid

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Request,
    UploadFile,
    File,
    status,
    HTTPException,
)
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from pydantic import BaseModel

from app.core.security import get_current_user
from app.db.models import Message, User, Contact, ChatPreference
from app.db.session import get_db
from app.services.image_service import imagekit, upload_chat_attachment_to_imagekit
from app.services.socket_manager import manager
from app.services.translation_service import translation_service

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# File Upload Configuration
# -----------------------------
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# -----------------------------
# Chat Dashboard (HTML)
# -----------------------------
@router.get("/chat", response_class=HTMLResponse)
async def chat_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Renders the main chat dashboard.
    Redirects unauthenticated users to login.
    """
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    contacts = db.query(Contact).filter(Contact.owner_id == user.id).all()

    # Token used by frontend to prevent stale socket reuse
    import secrets
    page_token = secrets.token_urlsafe(16)

    return templates.TemplateResponse(
        "chat/dashboard.html",
        {
            "request": request,
            "user": user,
            "contacts": contacts,
            "page_token": page_token,
        },
    )


# -----------------------------
# User Search
# -----------------------------
@router.get("/users/search")
async def search_users(query: str, request: Request, db: Session = Depends(get_db)):
    """
    Search users by username to start new chats.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)

    users = (
        db.query(User)
        .filter(User.username.contains(query), User.id != user.id)
        .limit(5)
        .all()
    )

    return [
        {
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "profile_pic": u.profile_pic,
            "is_online": manager.is_user_online(u.id),
        }
        for u in users
    ]


# -----------------------------
# Chat History (with Translation)
# -----------------------------
@router.get("/chat/history/{friend_id}")
async def get_chat_history(
        friend_id: int,
        request: Request,
        db: Session = Depends(get_db),
        limit: int = 20,
        offset: int = 0,
):
    """
    Fetch full chat history with language translation applied per preference.
    """
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)

    preference = db.query(ChatPreference).filter(
        ChatPreference.user_id == user.id,
        ChatPreference.friend_id == friend_id,
    ).first()

    preferred_lang = preference.preferred_language if preference else "en"

    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == friend_id),
                and_(Message.sender_id == friend_id, Message.receiver_id == user.id),
            )
        )
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    messages.reverse()

    response = []
    for msg in messages:
        data = {
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "content": msg.content,
            "original_content": msg.content,
            "media_url": msg.media_url,
            "media_type": msg.media_type,
            "status": msg.status,
            "timestamp": msg.timestamp.isoformat(),
            "is_translated": False,
            "original_language": msg.original_language or "en",
        }

        if msg.sender_id == friend_id and msg.original_language != preferred_lang:
            if msg.translated_content:
                data["content"] = msg.translated_content
            else:
                translated, _ = translation_service.translate(
                    msg.content,
                    preferred_lang,
                    msg.original_language,
                )
                data["content"] = translated
            data["is_translated"] = True

        response.append(data)

    return response


# -----------------------------
# User Online Status
# -----------------------------
@router.get("/user/status/{user_id}")
async def get_user_status(user_id: int):
    """Return real-time online status."""
    return {
        "user_id": user_id,
        "is_online": manager.is_user_online(user_id),
    }


# -----------------------------
# WebSocket Endpoint
# -----------------------------
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: int,
    db: Session = Depends(get_db),
):
    """
    Core real-time WebSocket handler.
    Handles messaging, receipts, typing, translation and presence.
    """
    await manager.connect(websocket, client_id)

    was_offline = not manager.is_user_online(client_id, exclude_websocket=websocket)

    user = db.query(User).filter(User.id == client_id).first()
    if not user:
        await websocket.close()
        return

    if was_offline:
        user.is_online = True
        db.commit()
        await notify_contacts_about_status(
            client_id,
            {"type": "user_status", "user_id": client_id, "status": "online"},
            db,
        )

    # Deliver pending messages
    pending = db.query(Message).filter(
        Message.receiver_id == client_id,
        Message.status == "sent",
    ).all()

    for msg in pending:
        msg.status = "delivered"
        await manager.send_personal_message(
            {"type": "status_update", "message_id": msg.id, "status": "delivered"},
            msg.sender_id,
        )
    db.commit()

    try:
        while True:
            payload = json.loads(await websocket.receive_text())

            # ---- Regular Message ----
            if "content" in payload and payload.get("type") != "typing":
                receiver_id = int(payload["receiver_id"])
                content = payload.get("content", "")
                media_url = payload.get("media_url")
                media_type = payload.get("media_type", "text")

                detected_lang = translation_service.detect_language(content)

                pref = db.query(ChatPreference).filter(
                    ChatPreference.user_id == receiver_id,
                    ChatPreference.friend_id == client_id,
                ).first()

                receiver_lang = pref.preferred_language if pref else "en"

                translated = None
                is_translated = False

                if detected_lang != receiver_lang:
                    translated, _ = translation_service.translate(
                        content, receiver_lang, detected_lang
                    )
                    is_translated = True

                # Ensure contacts exist (bidirectional)
                if not db.query(Contact).filter(
                    Contact.owner_id == client_id,
                    Contact.contact_id == receiver_id,
                ).first():
                    db.add(Contact(owner_id=client_id, contact_id=receiver_id))
                    db.add(Contact(owner_id=receiver_id, contact_id=client_id))
                    db.commit()

                online = manager.is_user_online(receiver_id)
                status_value = "delivered" if online else "sent"

                message = Message(
                    sender_id=client_id,
                    receiver_id=receiver_id,
                    content=content,
                    original_language=detected_lang,
                    translated_content=translated,
                    is_translated=is_translated,
                    media_url=media_url,
                    media_type=media_type,
                    status=status_value,
                )

                db.add(message)
                db.commit()
                db.refresh(message)

                if online:
                    await manager.send_personal_message(
                        {
                            "type": "message",
                            "id": message.id,
                            "content": translated if is_translated else content,
                            "original_content": content,
                            "is_translated": is_translated,
                            "original_language": detected_lang,
                            "media_url": media_url,
                            "media_type": media_type,
                            "sender_id": client_id,
                            "receiver_id": receiver_id,
                            "timestamp": message.timestamp.isoformat(),
                            "status": status_value,
                        },
                        receiver_id,
                    )

                await manager.send_personal_message(
                    {
                        "type": "message",
                        "id": message.id,
                        "content": content,
                        "original_content": content,
                        "is_translated": False,
                        "original_language": detected_lang,
                        "media_url": media_url,
                        "media_type": media_type,
                        "sender_id": client_id,
                        "receiver_id": receiver_id,
                        "timestamp": message.timestamp.isoformat(),
                        "status": status_value,
                    },
                    client_id,
                )

            # ---- Read Receipt ----
            elif payload.get("type") == "read_receipt":
                msg = db.query(Message).filter(Message.id == payload["message_id"]).first()
                if msg and msg.status != "read":
                    msg.status = "read"
                    db.commit()
                    await manager.send_personal_message(
                        {"type": "status_update", "message_id": msg.id, "status": "read"},
                        payload["sender_id"],
                    )

            # ---- Delivered Receipt ----
            elif payload.get("type") == "delivered_receipt":
                msg = db.query(Message).filter(Message.id == payload["message_id"]).first()
                if msg and msg.status == "sent":
                    msg.status = "delivered"
                    db.commit()
                    await manager.send_personal_message(
                        {"type": "status_update", "message_id": msg.id, "status": "delivered"},
                        payload["sender_id"],
                    )

            # ---- Typing Indicator ----
            elif payload.get("type") == "typing":
                await manager.send_personal_message(
                    {"type": "typing", "sender_id": client_id},
                    int(payload["receiver_id"]),
                )

            # ---- Ping ----
            elif payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)

        if not manager.is_user_online(client_id):
            user.is_online = False
            db.commit()
            await notify_contacts_about_status(
                client_id,
                {"type": "user_status", "user_id": client_id, "status": "offline"},
                db,
            )


# -----------------------------
# Notify Contacts of Status
# -----------------------------
async def notify_contacts_about_status(user_id: int, payload: dict, db: Session):
    """
    Notify all related contacts (both directions) about status change.
    """
    notify_users = set()

    for c in db.query(Contact).filter(Contact.owner_id == user_id).all():
        notify_users.add(c.contact_id)

    for c in db.query(Contact).filter(Contact.contact_id == user_id).all():
        notify_users.add(c.owner_id)

    for friend_id in notify_users:
        if friend_id != user_id:
            await manager.send_personal_message(payload, friend_id)


# -----------------------------
# Attachment Upload
# -----------------------------
@router.post("/chat/upload")
async def upload_attachment(file: UploadFile = File(...), user=Depends(get_current_user)):
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    await file.seek(0)  # Reset file pointer so service can read it again.

    result = await upload_chat_attachment_to_imagekit(
        file=file,
        uploader_username=user.username,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Upload failed")

    return {
        "url": result["url"],
        "type": result["media_type"],
        "filename": result["filename"],
        "size": file_size,
    }


# -----------------------------
# Language Preference
# -----------------------------
class LanguagePreferenceRequest(BaseModel):
    friend_id: int
    language: str


@router.post("/chat/language-preference")
async def set_chat_language_preference(
    req: LanguagePreferenceRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)

    if req.language not in translation_service.SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Language not supported")

    pref = db.query(ChatPreference).filter(
        ChatPreference.user_id == user.id,
        ChatPreference.friend_id == req.friend_id,
    ).first()

    if pref:
        pref.preferred_language = req.language
    else:
        db.add(ChatPreference(
            user_id=user.id,
            friend_id=req.friend_id,
            preferred_language=req.language,
        ))

    db.commit()
    return {"message": "Language updated", "language": req.language}


@router.get("/chat/language-preference/{friend_id}")
async def get_chat_language_preference(friend_id: int, request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)

    pref = db.query(ChatPreference).filter(
        ChatPreference.user_id == user.id,
        ChatPreference.friend_id == friend_id,
    ).first()

    return {
        "friend_id": friend_id,
        "preferred_language": pref.preferred_language if pref else "en",
        "available_languages": translation_service.SUPPORTED_LANGUAGES,
    }


# -----------------------------
# Debug Utilities
# -----------------------------
@router.get("/debug/connections")
async def debug_connections(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)

    stats = manager.get_stats()
    db_online = [u.id for u in db.query(User).filter(User.is_online == True).all()]

    return {
        "websocket": stats,
        "database": db_online,
    }


@router.post("/debug/fix-online-status")
async def fix_online_status(request: Request, db: Session = Depends(get_db)):
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401)

    online_ids = manager.get_online_users()
    db.query(User).update({User.is_online: False})

    if online_ids:
        db.query(User).filter(User.id.in_(online_ids)).update(
            {User.is_online: True},
            synchronize_session=False,
        )

    db.commit()
    return {"message": "Online status synced", "online_users": online_ids}
