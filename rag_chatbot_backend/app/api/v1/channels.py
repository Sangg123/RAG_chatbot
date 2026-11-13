from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from app.config import get_settings
from app.services.telegram_service import process_telegram_update


router = APIRouter(prefix="/channels", tags=["channels"])
logger = logging.getLogger(__name__)


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, bool]:
    """Nhận update từ Telegram rồi xử lý nền.

    Trả 200 ngay để Telegram không retry khi Gemini trả lời chậm. Việc gọi
    RAG/tool được đẩy sang BackgroundTasks của FastAPI.
    """

    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram channel is not configured",
        )

    if settings.telegram_webhook_secret:
        received = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token",
            "",
        )
        if not secrets.compare_digest(
            received.encode("utf-8"),
            settings.telegram_webhook_secret.encode("utf-8"),
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Telegram webhook secret",
            )
    elif settings.environment != "development":
        # Không cho phép webhook không có secret ở production.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TELEGRAM_WEBHOOK_SECRET is required",
        )

    try:
        update: Any = await request.json()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    if not isinstance(update, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid update payload",
        )

    background_tasks.add_task(process_telegram_update, update)
    return {"ok": True}
