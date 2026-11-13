from __future__ import annotations

import asyncio
import logging
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, verify_password
from app.channels.base import IncomingMessage, parse_command
from app.models import ChannelAccount, Conversation, User
from app.schemas.message import MAX_MESSAGE_LENGTH, MessageCreate
from app.services.chat_service import stream_rag_answer


logger = logging.getLogger(__name__)

_FALLBACK_ANSWER = (
    "Xin lỗi, mình chưa thể tạo câu trả lời lúc này. "
    "Bạn vui lòng thử lại sau ít phút nhé."
)
_SAFE_IDENTIFIER = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class ChannelContext:
    account: ChannelAccount
    user: User

    @property
    def is_linked(self) -> bool:
        return self.user.role != "guest" and self.user.is_active


def _safe_identifier(value: str) -> str:
    cleaned = _SAFE_IDENTIFIER.sub("_", value).strip("._-")
    return (cleaned or "unknown")[:60]


async def _find_account(
    db: AsyncSession,
    incoming: IncomingMessage,
) -> ChannelAccount | None:
    return await db.scalar(
        select(ChannelAccount).where(
            ChannelAccount.channel == incoming.channel,
            ChannelAccount.external_user_id == incoming.external_user_id,
        )
    )


async def _create_guest_user(
    db: AsyncSession,
    incoming: IncomingMessage,
) -> User:
    """Tạo user nội bộ cho khách chưa liên kết tài khoản web.

    Guest bị đặt is_active=False để không thể đăng nhập web. Khi khách dùng
    /link, channel_account sẽ được trỏ sang user thật và hội thoại được
    chuyển theo.
    """

    safe_id = _safe_identifier(incoming.external_user_id)
    username = f"{incoming.channel}_{safe_id}"[:100]
    email = f"{incoming.channel}.{safe_id}@channels.example.com"[:255]

    # Trường hợp dữ liệu cũ bị tạo dở: tránh đụng unique constraint.
    existing = await db.scalar(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if existing is not None:
        suffix = uuid.uuid4().hex[:8]
        username = f"{username[:80]}_{suffix}"
        email = f"{incoming.channel}.{safe_id}.{suffix}@channels.example.com"[:255]

    password_hash = await asyncio.to_thread(
        hash_password,
        secrets.token_urlsafe(32),
    )
    user = User(
        username=username,
        email=email,
        hashed_password=password_hash,
        role="guest",
        is_active=False,
    )
    db.add(user)
    await db.flush()
    return user


async def get_or_create_channel_account(
    db: AsyncSession,
    incoming: IncomingMessage,
) -> ChannelAccount:
    account = await _find_account(db, incoming)
    if account is not None:
        changed = False
        if incoming.display_name and account.display_name != incoming.display_name:
            account.display_name = incoming.display_name
            changed = True
        if (
            incoming.external_username is not None
            and account.external_username != incoming.external_username
        ):
            account.external_username = incoming.external_username
            changed = True
        if account.external_chat_id != incoming.external_chat_id:
            account.external_chat_id = incoming.external_chat_id
            changed = True
        if changed:
            account.updated_at = datetime.now(timezone.utc)
            await db.commit()
        return account

    try:
        user = await _create_guest_user(db, incoming)
        account = ChannelAccount(
            channel=incoming.channel,
            external_user_id=incoming.external_user_id,
            external_chat_id=incoming.external_chat_id,
            user_id=user.id,
            display_name=incoming.display_name,
            external_username=incoming.external_username,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return account
    except IntegrityError:
        # Hai update đồng thời cho cùng một chat (webhook retry...).
        await db.rollback()
        account = await _find_account(db, incoming)
        if account is None:
            raise
        return account


async def _get_account_user(db: AsyncSession, account: ChannelAccount) -> User:
    user = await db.scalar(select(User).where(User.id == account.user_id))
    if user is None:
        raise RuntimeError(f"Channel account {account.id} points to a missing user")
    return user


async def _create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    incoming: IncomingMessage,
) -> Conversation:
    conversation = Conversation(
        user_id=user_id,
        title="New conversation",
        channel=incoming.channel,
        external_chat_id=incoming.external_chat_id,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def _get_active_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    incoming: IncomingMessage,
) -> Conversation:
    conversation = await db.scalar(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.channel == incoming.channel,
            Conversation.external_chat_id == incoming.external_chat_id,
        )
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    if conversation is not None:
        return conversation
    return await _create_conversation(db, user_id, incoming)


async def handle_incoming_message(
    db: AsyncSession,
    incoming: IncomingMessage,
) -> str:
    """Xử lý một tin nhắn kênh ngoài và trả về nội dung cần gửi lại.

    Hàm này không biết gì về Telegram HTTP API; nhờ vậy có thể tái sử dụng cho
    Zalo/WhatsApp bằng cách viết adapter mới.
    """

    if not incoming.is_private:
        return (
            "Mình chỉ hỗ trợ chat riêng 1-1 để bảo vệ thông tin đơn hàng. "
            "Bạn hãy nhắn trực tiếp cho bot nhé."
        )

    account = await get_or_create_channel_account(db, incoming)
    user = await _get_account_user(db, account)
    context = ChannelContext(account=account, user=user)

    parsed = parse_command(incoming.text)
    if parsed is not None:
        command, args = parsed
        return await _handle_command(db, incoming, context, command, args)

    text = incoming.text.strip()
    if not text:
        return "Bạn hãy nhập câu hỏi hoặc gõ /help để xem hướng dẫn."
    if len(text) > MAX_MESSAGE_LENGTH:
        return (
            f"Tin nhắn quá dài (tối đa {MAX_MESSAGE_LENGTH} ký tự). "
            "Bạn rút gọn rồi gửi lại giúp mình nhé."
        )

    conversation = await _get_active_conversation(db, user.id, incoming)
    return await _answer_question(db, conversation, text, user)


async def _answer_question(
    db: AsyncSession,
    conversation: Conversation,
    text: str,
    user: User,
) -> str:
    tokens: list[str] = []
    try:
        async for event in stream_rag_answer(
            db,
            conversation.id,
            MessageCreate(content=text),
            user,
        ):
            if event.event == "token":
                tokens.append(str(event.data))
    except Exception:  # noqa: BLE001 - lỗi AI không được làm sập webhook
        logger.exception(
            "Channel chat failed for conversation %s",
            conversation.id,
        )
        await db.rollback()
        return _FALLBACK_ANSWER

    answer = "".join(tokens).strip()
    return answer or _FALLBACK_ANSWER


async def _handle_command(
    db: AsyncSession,
    incoming: IncomingMessage,
    context: ChannelContext,
    command: str,
    args: str,
) -> str:
    if command in {"/start", "/help"}:
        return _help_text(context)

    if command == "/new":
        await _create_conversation(db, context.user.id, incoming)
        return "✅ Đã bắt đầu hội thoại mới. Bạn hỏi tiếp nhé."

    if command == "/link":
        return await _link_account(db, incoming, context, args)

    if command == "/unlink":
        return await _unlink_account(db, context)

    if command == "/id":
        return (
            f"🆔 Kênh: {incoming.channel}\n"
            f"ID người dùng trên kênh: {incoming.external_user_id}\n"
            f"ID chat: {incoming.external_chat_id}\n"
            f"Tài khoản nội bộ: {context.user.username}\n"
            f"Trạng thái: {'đã liên kết' if context.is_linked else 'chưa liên kết'}"
        )

    return "Mình chưa hỗ trợ lệnh này. Gõ /help để xem các lệnh nhé."


def _help_text(context: ChannelContext) -> str:
    if context.is_linked:
        account_line = (
            f"Bạn đang liên kết với tài khoản: {context.user.username}"
        )
    else:
        account_line = (
            "Bạn chưa liên kết tài khoản web. Dùng "
            "/link <username> <password> để tra cứu đơn hàng của chính mình."
        )

    return (
        f"👋 Xin chào {context.account.display_name or 'bạn'}!\n"
        "Mình là trợ lý hỗ trợ khách hàng, có thể:\n"
        "• Trả lời câu hỏi về sản phẩm, chính sách, đổi trả, vận chuyển\n"
        "• Tra cứu đơn hàng khi bạn gửi mã đơn hoặc số điện thoại\n\n"
        f"{account_line}\n\n"
        "Lệnh:\n"
        "/new – bắt đầu hội thoại mới\n"
        "/link – liên kết tài khoản web\n"
        "/unlink – hủy liên kết\n"
        "/id – xem thông tin kênh\n"
        "/help – xem hướng dẫn"
    )


async def _link_account(
    db: AsyncSession,
    incoming: IncomingMessage,
    context: ChannelContext,
    args: str,
) -> str:
    parts = args.split(maxsplit=1)
    if len(parts) != 2:
        return (
            "Cú pháp: /link <tên đăng nhập> <mật khẩu>\n"
            "Ví dụ: /link nguyen.van.an password123"
        )

    identifier, password = parts[0].strip(), parts[1]
    target = await db.scalar(
        select(User).where(
            or_(User.username == identifier, User.email == identifier)
        )
    )
    if target is None or not target.is_active:
        return "❌ Không tìm thấy tài khoản đang hoạt động với thông tin này."

    try:
        valid = await asyncio.to_thread(
            verify_password,
            password,
            target.hashed_password,
        )
    except ValueError:
        valid = False

    if not valid:
        return "❌ Sai tên đăng nhập hoặc mật khẩu. Bạn thử lại nhé."

    if context.account.user_id == target.id:
        return f"✅ Kênh này đã liên kết với tài khoản {target.username} rồi."

    previous_user = context.user
    context.account.user_id = target.id
    context.account.updated_at = datetime.now(timezone.utc)

    # Chỉ chuyển hội thoại của guest sang user thật. Nếu kênh đang liên kết
    # với một tài khoản thật khác, giữ nguyên lịch sử của tài khoản cũ.
    if previous_user.role == "guest":
        await db.execute(
            update(Conversation)
            .where(
                Conversation.user_id == previous_user.id,
                Conversation.channel == incoming.channel,
                Conversation.external_chat_id == incoming.external_chat_id,
            )
            .values(user_id=target.id)
        )

    await db.commit()
    return (
        f"✅ Đã liên kết kênh với tài khoản {target.username}.\n"
        "Từ giờ bạn có thể tra cứu đơn hàng của mình ngay trong chat."
    )


async def _unlink_account(
    db: AsyncSession,
    context: ChannelContext,
) -> str:
    if not context.is_linked:
        return "Kênh này chưa liên kết với tài khoản web nào."

    await db.delete(context.account)
    await db.commit()
    return (
        "🔓 Đã hủy liên kết. Lịch sử hội thoại vẫn được lưu trong tài khoản web.\n"
        "Các tin nhắn tiếp theo sẽ được xử lý như khách chưa đăng nhập."
    )
