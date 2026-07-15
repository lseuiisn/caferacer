from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser
from app.core.config import get_settings

router = APIRouter(prefix="/uploads", tags=["uploads"])
settings = get_settings()
CONTENT_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(
    _: CurrentUser,
    file: UploadFile = File(...),
) -> dict[str, str]:
    extension = CONTENT_EXTENSIONS.get(file.content_type or "")
    if extension is None:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are allowed")
    content = await file.read(settings.max_image_bytes + 1)
    if len(content) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="Image is too large")
    media_root = Path(settings.media_root).resolve()
    media_root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    (media_root / filename).write_bytes(content)
    return {"url": f"{settings.media_base_url.rstrip('/')}/{filename}"}
