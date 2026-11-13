from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.channels.telegram import (
    TELEGRAM_BOT_COMMANDS,
    TelegramAPIError,
    TelegramClient,
    parse_update,
)
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.channel_service import handle_incoming_message


logger = logging.getLogger(__name__)

_ERROR_REPLY = (
    "Xin lỗi, hệ thống đang gặp sự cố. "
    "Bạn vui lòng thử lại sau ít phút nhé."
)


async def process_telegram_update(
    update: dict[str, Any],
    bot: TelegramClient | None = None,
) -> None:
    """Xử lý một Update. Có thể tái sử dụng cho webhook và polling."""

    settings = get_settings()
    if not settings.telegram_bot_token:
        return

    incoming = parse_update(update)
    if incoming is None:
        return

    owns_client = bot is None
    if bot is None:
        bot = TelegramClient(settings.telegram_bot_token)

    try:
        async with bot.typing(incoming.external_chat_id):
            try:
                async with AsyncSessionLocal() as db:
                    reply = await handle_incoming_message(db, incoming)
            except Exception:  # noqa: BLE001 - luôn trả lời khách thay vì im lặng
                logger.exception(
                    "Telegram update %s failed",
                    update.get("update_id"),
                )
                reply = _ERROR_REPLY

        try:
            await bot.send_message(incoming.external_chat_id, reply)
        except TelegramAPIError:
            logger.exception(
                "Could not send Telegram reply to chat %s",
                incoming.external_chat_id,
            )
    finally:
        if owns_client:
            await bot.aclose()


async def run_polling() -> None:
    """Long polling cho local development.

    Production nên dùng webhook để Render free có thể ngủ khi không có traffic.
    Không chạy polling và webhook cùng lúc với một bot token.
    """

    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit(
            "Chưa cấu hình TELEGRAM_BOT_TOKEN trong .env. "
            "Tạo bot với @BotFather rồi dán token vào."
        )

    if settings.environment == "production":
        logger.warning(
            "Đang chạy Telegram polling với ENVIRONMENT=production. "
            "Nên dùng webhook thay vì polling trên môi trường thật."
        )

    bot = TelegramClient(token, timeout=60.0)
    offset: int | None = None
    try:
        try:
            await bot.delete_webhook(drop_pending_updates=False)
        except TelegramAPIError:
            logger.warning(
                "Không xóa được webhook cũ; vẫn tiếp tục polling",
                exc_info=True,
            )

        try:
            await bot.set_my_commands(TELEGRAM_BOT_COMMANDS)
        except TelegramAPIError:
            logger.warning("Không đăng ký được command menu", exc_info=True)

        logger.info("Telegram polling đã khởi động")
        while True:
            try:
                updates = await bot.get_updates(offset=offset, timeout=30)
            except asyncio.CancelledError:
                raise
            except TelegramAPIError:
                logger.warning(
                    "getUpdates lỗi; thử lại sau 3 giây",
                    exc_info=True,
                )
                await asyncio.sleep(3)
                continue

            for update in updates:
                try:
                    next_offset = int(update.get("update_id", 0)) + 1
                except (TypeError, ValueError):
                    continue
                await process_telegram_update(update, bot=bot)
                # Chỉ tăng offset sau khi xử lý xong để không mất update nếu lỗi.
                offset = next_offset
    finally:
        await bot.aclose()
