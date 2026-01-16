import tempfile
import uuid
import os
import shutil

from fastapi import UploadFile, HTTPException
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from starlette.concurrency import run_in_threadpool

from app.core.config import settings


# -----------------------------
# ImageKit Client
# -----------------------------
imagekit = ImageKit(
    private_key=settings.IMAGEKIT_PRIVATE_KEY,
    public_key=settings.IMAGEKIT_PUBLIC_KEY,
    url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
)


# -----------------------------
# Shared Helpers
# -----------------------------
def _validate_extension(filename: str, allowed: set) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed)}",
        )
    return ext


async def _upload_via_tempfile(
    file: UploadFile,
    filename: str,
    folder: str,
    tags: list,
) -> str:
    """
    Core upload logic used by all helpers.
    """
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = tmp.name

        def sync_upload():
            with open(temp_path, "rb") as f:
                return imagekit.upload_file(
                    file=f,
                    file_name=filename,
                    options=UploadFileRequestOptions(
                        folder=f"/{folder}/",
                        use_unique_file_name=True,
                        is_private_file=False,
                        tags=tags,
                    ),
                )

        response = await run_in_threadpool(sync_upload)

        if not response or not hasattr(response, "url"):
            raise Exception("Invalid ImageKit response")

        return response.url

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}",
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


# -----------------------------
# Profile Picture Upload
# -----------------------------
async def upload_dp_to_imagekit(
    file: UploadFile,
    folder: str = "chat_app_profiles",
) -> str:
    """
    Upload profile picture (DP).
    """
    allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
    ext = _validate_extension(file.filename, allowed_extensions)

    filename = f"profile_{uuid.uuid4()}.{ext}"

    return await _upload_via_tempfile(
        file=file,
        filename=filename,
        folder=folder,
        tags=["profile_picture"],
    )


# -----------------------------
# Chat Attachment Upload
# -----------------------------
async def upload_chat_attachment_to_imagekit(
    file: UploadFile,
    uploader_username: str,
) -> dict:
    """
    Upload chat image/document.
    Returns metadata needed by chat system.
    """
    image_ext = {"jpg", "jpeg", "png", "gif", "webp"}
    doc_ext = {"pdf", "doc", "docx", "txt"}
    allowed = image_ext | doc_ext

    ext = _validate_extension(file.filename, allowed)

    if ext in image_ext:
        media_type = "image"
        folder = "chat_images"
    else:
        media_type = "document"
        folder = "chat_documents"

    filename = f"chat_{uploader_username}_{uuid.uuid4()}.{ext}"

    url = await _upload_via_tempfile(
        file=file,
        filename=filename,
        folder=folder,
        tags=["chat_attachment", media_type],
    )

    return {
        "url": url,
        "media_type": media_type,
        "filename": file.filename,
    }
