"""Подключение маршрутов модулей к версии API v1."""

from fastapi import APIRouter

from linguabot.modules.assessment.router import router as assessment_router
from linguabot.modules.auth.router import router as auth_router
from linguabot.modules.dialogues.router import router as dialogues_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(dialogues_router, prefix="/dialogues", tags=["dialogues"])
api_router.include_router(
    assessment_router, prefix="/assessment", tags=["assessment"]
)
