from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Any, AsyncIterator

import httpx

from app.channels.base import IncomingMessage


logger = logging.getLogger(__name__)

TELEGRAM_TEXT_LIMIT = 4000
_TYPING_INTERVAL_SECONDS = 4.5

TELEGRAM_BOT_COMMANDS: list[dict[str, str]] = [
    {"command": "start", "description": "Bắt đầu trò chuyện"},
    {"command": "new", "description": "Bắt đầu hội thoại mới"},
    {"command": "link", "description": "Liên kết tài khoản web"},
    {"command": "unlink", "description": "Hủy liên kết tài khoản"},
    {"command": "id", "description": "Xem thông tin kênh"},
    {"command": "help", "description": "Xem hướng dẫn"},
]


class TelegramAPIError(RuntimeError):
    """Lỗi trả về từ Telegram Bot API."""

    def __init__(self, method: str, description: str) -> None:
        self.method = method
        self.description = description
        super().__init__(f"Telegram {method} failed: {description}")


class TelegramClient:
    """Client nhỏ cho Telegram Bot API, dùng httpx có sẵn của dự án.

    Không cần thêm thư viện như aiogram/python-telegram-bot; đổi lại ta chủ
    động kiểm soát timeout, retry và cách map update sang IncomingMessage.
    """

    def __init__(self, token: str, *, timeout: float = 60.0) -> None:
        # Không dùng base_url của httpx vì đường dẫn "/method" có thể ghi đè
        # phần "/bot<token>" trên base URL.
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    async def __aenter__(self) -> "TelegramClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, **params: Any) -> Any:
        try:
            response = await self._client.post(
                f"{self._base_url}/{method}",
                json=params,
            )
        except httpx.HTTPError:
            # Không đưa URL vào message vì URL chứa bot token.
            raise TelegramAPIError(method, "network error") from None

        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}

        if response.status_code >= 400 or not payload.get("ok"):
            description = str(payload.get("description") or "unknown error")
            raise TelegramAPIError(method, description)

        return payload.get("result")

    async def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout: int = 30,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            params["offset"] = offset
        result = await self._call("getUpdates", **params)
        return list(result or [])

    async def delete_webhook(self, *, drop_pending_updates: bool = False) -> Any:
        return await self._call(
            "deleteWebhook",
            drop_pending_updates=drop_pending_updates,
        )

    async def set_webhook(
        self,
        url: str,
        *,
        secret_token: str | None = None,
        drop_pending_updates: bool | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "url": url,
            "allowed_updates": ["message"],
        }
        if secret_token:
            params["secret_token"] = secret_token
        if drop_pending_updates is not None:
            params["drop_pending_updates"] = drop_pending_updates
        return await self._call("setWebhook", **params)

    async def set_my_commands(self, commands: list[dict[str, str]]) -> Any:
        return await self._call("setMyCommands", commands=commands)

    async def send_message(self, chat_id: str | int, text: str) -> None:
        for chunk in split_telegram_text(text):
            await self._call(
                "sendMessage",
                chat_id=chat_id,
                text=chunk,
                disable_web_page_preview=True,
            )

    async def send_typing(self, chat_id: str | int) -> None:
        await self._call("sendChatAction", chat_id=chat_id, action="typing")

    @asynccontextmanager
    async def typing(self, chat_id: str | int) -> AsyncIterator[None]:
        """Giữ trạng thái 'đang nhập...' trong suốt thời gian xử lý.

        Telegram chỉ hiển thị typing khoảng 5 giây, nên phải gửi lặp lại.
        """

        stop = asyncio.Event()

        async def keep_typing() -> None:
            while not stop.is_set():
                try:
                    await self.send_typing(chat_id)
                except TelegramAPIError:
                    logger.debug("Could not send Telegram typing indicator")
                try:
                    await asyncio.wait_for(
                        stop.wait(),
                        timeout=_TYPING_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    continue

        task = asyncio.create_task(keep_typing())
        try:
            yield
        finally:
            stop.set()
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def parse_update(update: dict[str, Any]) -> IncomingMessage | None:
    """Chuyển một Telegram Update thành IncomingMessage.

    Chỉ nhận tin nhắn văn bản mới. Bỏ qua edited_message để tránh bot trả lời
    hai lần khi người dùng sửa tin.
    """

    message = update.get("message")
    if not isinstance(message, dict):
        return None

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = sender.get("id") or chat_id
    if chat_id is None or user_id is None:
        return None

    first_name = str(sender.get("first_name") or "").strip()
    last_name = str(sender.get("last_name") or "").strip()
    display_name = " ".join(part for part in (first_name, last_name) if part)
    if not display_name:
        display_name = str(sender.get("username") or user_id)

    username = sender.get("username")
    return IncomingMessage(
        channel="telegram",
        external_user_id=str(user_id),
        external_chat_id=str(chat_id),
        text=text.strip(),
        display_name=display_name[:255],
        external_username=str(username)[:255] if username else None,
        is_private=chat.get("type") == "private",
    )


def split_telegram_text(
    text: str,
    *,
    limit: int = TELEGRAM_TEXT_LIMIT,
) -> list[str]:
    """Chia câu trả lời dài thành nhiều tin nhắn dưới giới hạn của Telegram.

    Giới hạn thật của Telegram là 4096 ký tự; mặc định 4000 để dư chỗ cho
    emoji/UTF-16. Ưu tiên cắt ở newline, sau đó ở khoảng trắng.
    """

    cleaned = (text or "").strip()
    if not cleaned:
        return []

    safe_limit = max(1, min(limit, 4096))
    chunks: list[str] = []
    remaining = cleaned

    while len(remaining) > safe_limit:
        cut = remaining.rfind("\n", 0, safe_limit)
        if cut < safe_limit // 2:
            cut = remaining.rfind(" ", 0, safe_limit)
        if cut < safe_limit // 2:
            cut = safe_limit

        chunk = remaining[:cut].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[cut:].lstrip()

    if remaining:
        chunks.append(remaining)
    return chunks
