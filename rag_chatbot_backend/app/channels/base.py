from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class IncomingMessage:
    """Tin nhắn đã chuẩn hóa từ một kênh bất kỳ (Telegram, Zalo, web...).

    Adapter của từng kênh chịu trách nhiệm chuyển payload riêng của kênh đó
    thành cấu trúc này. Lõi chatbot (RAG + tool calling) chỉ làm việc với
    IncomingMessage, nên thêm kênh mới không phải sửa lại logic AI.
    """

    channel: str
    external_user_id: str
    external_chat_id: str
    text: str
    display_name: str | None = None
    external_username: str | None = None
    is_private: bool = True


@runtime_checkable
class ChannelAdapter(Protocol):
    """Giao diện tối thiểu mà một adapter kênh mới cần triển khai."""

    channel_name: str

    async def send_text(self, external_chat_id: str, text: str) -> None:
        ...


def parse_command(text: str) -> tuple[str, str] | None:
    """Tách lệnh Telegram: /help@ShopBot args -> ("/help", "args")."""
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None

    head, _, rest = stripped.partition(" ")
    command = head.split("@", 1)[0].lower()
    return command, rest.strip()
