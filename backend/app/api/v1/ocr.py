from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services import ocr_service
from app.services.ocr.extractor import FieldCandidate, OCRFields

router = APIRouter(prefix="/ocr", tags=["ocr"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_BYTES = 8 * 1024 * 1024
STORAGE_ROOT = Path("storage/images")


class FieldCandidateOut(BaseModel):
    label: str
    value: int
    confidence: float


class OCRFieldsOut(BaseModel):
    systolic: int | None = None
    diastolic: int | None = None
    heart_rate: int | None = None


class OCRBpResponse(BaseModel):
    image_id: str
    raw_text: str
    candidates: list[FieldCandidateOut]
    fields: OCRFieldsOut


def _ext_from_content_type(ct: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(ct, ".bin")


@router.post("/bp", response_model=OCRBpResponse)
async def ocr_blood_pressure(
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported image type",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="image too large",
        )

    image_id = uuid.uuid4().hex
    ext = _ext_from_content_type(file.content_type)
    user_dir = STORAGE_ROOT / str(current.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dst = user_dir / f"{image_id}{ext}"
    dst.write_bytes(data)

    try:
        result = ocr_service.recognize(data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("ocr recognize failed: {}", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ocr failed")

    return OCRBpResponse(
        image_id=image_id,
        raw_text=result.raw_text,
        candidates=[FieldCandidateOut(**c.__dict__) for c in result.candidates],
        fields=OCRFieldsOut(**result.fields.to_dict()),
    )
