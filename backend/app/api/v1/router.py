from fastapi import APIRouter

from app.api.v1 import auth, bp_records, chat, ocr, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(ocr.router)
api_router.include_router(bp_records.router)
api_router.include_router(chat.router)
