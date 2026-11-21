from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from google.genai.types import GenerateContentConfig
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import ChannelAccount, Conversation, Message, User
from app.services.rag_service import generate_chat_response

logger = logging.getLogger(__name__)

SUPPORT_MODE_BOT = "bot"
SUPPORT_MODE_WAITING = "waiting"
SUPPORT_MODE_HUMAN = "human"

HANDOFF_CUSTOMER_NOTICE = (
    "Mình đã chuyển cuộc trò chuyện này đến nhân viên hỗ trợ. "
    "Bạn đợi một chút nhé, nhân viên sẽ phản hồi bạn ngay khi có thể."
)

RETURN_TO_BOT_NOTICE = (
    "Nhân viên đã kết thúc phần hỗ trợ trực tiếp. "
    "Trợ lý AI sẽ tiếp tục phản hồi bạn từ tin nhắn tiếp theo."
)

_SUMMARY_MAX_CHARS = 8000
_TRANSCRIPT_MESSAGE_LIMIT = 60
_TRANSCRIPT_MESSAGE_CHARS = 700


def is_support_agent(user: User) -> bool:
    return user.role in {"staff", "admin"}


def can_view_conversation(user: User, conversation: Conversation) -> bool:
    """Quyền xem hội thoại ở chế độ hỗ trợ.

    - Admin: xem mọi hội thoại.
    - Staff: xem hàng đợi và hội thoại mình đang phụ trách.
    - Khách: chỉ xem hội thoại của chính mình.
    """

    if user.role == "admin":
        return True
    if user.role == "staff":
        if conversation.support_mode == SUPPORT_MODE_WAITING and conversation.resolved_at is None:
            return True
        return (
            conversation.support_mode == SUPPORT_MODE_HUMAN
            and conversation.assigned_staff_id == user.id
        )
    return conversation.user_id == user.id


async def _get_conversation_or_404(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> Conversation:
    conversation = await db.scalar(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


async def get_support_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    agent: User,
) -> Conversation:
    conversation = await _get_conversation_or_404(db, conversation_id)
    if agent.role == "admin":
        if conversation.handoff_at is None and conversation.support_mode == SUPPORT_MODE_BOT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation is not in support mode",
            )
        return conversation
    if agent.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    if not can_view_conversation(agent, conversation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    return conversation


async def _find_channel_account(
    db: AsyncSession,
    conversation: Conversation,
) -> ChannelAccount | None:
    if not conversation.external_chat_id:
        return None
    return await db.scalar(
        select(ChannelAccount)
        .where(
            ChannelAccount.channel == conversation.channel,
            ChannelAccount.external_chat_id == conversation.external_chat_id,
        )
        .order_by(ChannelAccount.created_at.desc())
        .limit(1)
    )


def _seconds_since(value: datetime | None) -> int:
    if value is None:
        return 0
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, int((now - value).total_seconds()))


def _preview(text: str | None, limit: int = 160) -> str | None:
    if not text:
        return None
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


async def build_support_conversation(
    db: AsyncSession,
    conversation: Conversation,
) -> dict[str, Any]:
    """Chuẩn bị dữ liệu cho danh sách/chi tiết ticket của staff."""

    customer = await db.get(User, conversation.user_id)
    account = await _find_channel_account(db, conversation)

    message_count = (
        await db.scalar(
            select(func.count(Message.id)).where(
                Message.conversation_id == conversation.id,
                Message.is_internal.is_(False),
            )
        )
        or 0
    )
    last_message = await db.scalar(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.is_internal.is_(False),
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )

    assigned_staff = None
    if conversation.assigned_staff_id:
        assigned_staff = await db.get(User, conversation.assigned_staff_id)

    display_name = (
        (account.display_name if account else None)
        or (customer.username if customer else None)
        or "Khách"
    )
    customer_is_linked = bool(
        customer and customer.role != "guest" and customer.is_active
    )

    return {
        "id": conversation.id,
        "title": conversation.title,
        "channel": conversation.channel,
        "external_chat_id": conversation.external_chat_id,
        "support_mode": conversation.support_mode,
        "handoff_reason": conversation.handoff_reason,
        "handoff_at": conversation.handoff_at,
        "resolved_at": conversation.resolved_at,
        "summary": conversation.summary,
        "summary_updated_at": conversation.summary_updated_at,
        "assigned_staff_id": conversation.assigned_staff_id,
        "assigned_staff_username": assigned_staff.username if assigned_staff else None,
        "customer_name": display_name,
        "customer_username": (
            customer.username
            if customer and customer.role != "guest"
            else None
        ),
        "customer_external_username": (
            account.external_username if account else None
        ),
        "customer_is_linked": customer_is_linked,
        "message_count": message_count,
        "last_message_preview": _preview(last_message.content if last_message else None),
        "last_message_at": last_message.created_at if last_message else None,
        "waiting_seconds": (
            _seconds_since(conversation.handoff_at)
            if conversation.support_mode == SUPPORT_MODE_WAITING
            and conversation.resolved_at is None
            else 0
        ),
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
    }


async def list_support_conversations(
    db: AsyncSession,
    agent: User,
    scope: str,
    search: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    allowed_scopes = {"waiting", "mine", "active", "closed", "all"}
    if scope not in allowed_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scope",
        )
    if scope in {"active", "closed", "all"} and agent.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    stmt = select(Conversation)
    if scope == "waiting":
        stmt = stmt.where(
            Conversation.support_mode == SUPPORT_MODE_WAITING,
            Conversation.resolved_at.is_(None),
        )
    elif scope == "mine":
        stmt = stmt.where(
            Conversation.support_mode == SUPPORT_MODE_HUMAN,
            Conversation.assigned_staff_id == agent.id,
            Conversation.resolved_at.is_(None),
        )
    elif scope == "active":
        stmt = stmt.where(
            Conversation.support_mode == SUPPORT_MODE_HUMAN,
            Conversation.resolved_at.is_(None),
        )
    elif scope == "closed":
        stmt = stmt.where(Conversation.resolved_at.is_not(None))
    else:  # all (admin)
        stmt = stmt.where(Conversation.handoff_at.is_not(None))

    stmt = stmt.order_by(
        func.coalesce(Conversation.updated_at, Conversation.created_at).desc()
    ).limit(max(1, min(limit, 300)))

    conversations = list((await db.scalars(stmt)).all())
    items = [await build_support_conversation(db, conv) for conv in conversations]

    if search:
        needle = search.strip().casefold()
        if needle:
            items = [
                item
                for item in items
                if needle in (item["title"] or "").casefold()
                or needle in (item["customer_name"] or "").casefold()
                or needle in (item["customer_username"] or "").casefold()
                or needle in (item["customer_external_username"] or "").casefold()
                or needle in (item["last_message_preview"] or "").casefold()
            ]
    return items


async def get_support_conversation_detail(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    agent: User,
) -> dict[str, Any]:
    conversation = await get_support_conversation(db, conversation_id, agent)
    data = await build_support_conversation(db, conversation)
    messages = list(
        (
            await db.scalars(
                select(Message)
                .options(selectinload(Message.sender))
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.asc())
            )
        ).all()
    )
    data["messages"] = messages
    return data


async def trigger_handoff(
    db: AsyncSession,
    conversation: Conversation,
    reason: str,
) -> bool:
    """Đưa hội thoại vào hàng đợi nhân viên. Trả False nếu đã chuyển rồi."""

    if conversation.support_mode != SUPPORT_MODE_BOT:
        return False

    conversation_id = conversation.id
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.support_mode == SUPPORT_MODE_BOT,
        )
        .values(
            support_mode=SUPPORT_MODE_WAITING,
            assigned_staff_id=None,
            handoff_reason=reason,
            handoff_at=now,
            resolved_at=None,
            summary=None,
            summary_updated_at=None,
            updated_at=now,
        )
        .returning(Conversation.id)
    )
    if result.scalar_one_or_none() is None:
        return False

    await db.commit()
    await db.refresh(conversation)
    schedule_summary_generation(conversation_id)
    logger.info(
        "Conversation %s handed off to staff: %s",
        conversation_id,
        reason,
    )
    return True


def schedule_summary_generation(conversation_id: uuid.UUID) -> None:
    """Tạo tóm tắt ở nền để không làm chậm phản hồi cho khách."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.warning(
            "No running event loop; cannot schedule summary for %s",
            conversation_id,
        )
        return

    task = loop.create_task(_summary_task(conversation_id))
    task.add_done_callback(_log_summary_task_error)


def _log_summary_task_error(task: asyncio.Task) -> None:
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error(
            "Background handoff summary failed",
            exc_info=(type(error), error, error.__traceback__),
        )


async def _summary_task(conversation_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        try:
            conversation = await _get_conversation_or_404(db, conversation_id)
            await generate_conversation_summary(db, conversation)
            await db.commit()
        except Exception:  # noqa: BLE001 - tóm tắt không được làm hỏng handoff
            await db.rollback()
            logger.exception(
                "Could not generate handoff summary for conversation %s",
                conversation_id,
            )


def _role_label(sender_type: str) -> str:
    return {
        "USER": "Khách",
        "BOT": "Bot AI",
        "STAFF": "Nhân viên",
        "SYSTEM": "Hệ thống",
    }.get((sender_type or "").upper(), sender_type)


def _build_transcript(messages: list[Message]) -> str:
    visible = [message for message in messages if not message.is_internal]
    if len(visible) > _TRANSCRIPT_MESSAGE_LIMIT:
        visible = visible[-_TRANSCRIPT_MESSAGE_LIMIT:]
        prefix = "… (các tin nhắn trước đó đã được lược bớt)\n"
    else:
        prefix = ""

    lines: list[str] = []
    for message in visible:
        content = " ".join((message.content or "").split())
        if len(content) > _TRANSCRIPT_MESSAGE_CHARS:
            content = content[:_TRANSCRIPT_MESSAGE_CHARS].rstrip() + "…"
        lines.append(f"{_role_label(message.sender_type)}: {content}")
    return prefix + "\n".join(lines)


def _fallback_summary(
    conversation: Conversation,
    customer_name: str,
    messages: list[Message],
) -> str:
    customer_messages = [
        message.content
        for message in messages
        if message.sender_type.upper() == "USER" and not message.is_internal
    ][-3:]
    bot_messages = [
        message.content
        for message in messages
        if message.sender_type.upper() == "BOT" and not message.is_internal
    ][-1:]

    lines = [f"- Khách hàng: {customer_name}"]
    if conversation.handoff_reason:
        lines.append(f"- Lý do chuyển giao: {conversation.handoff_reason}")
    if customer_messages:
        lines.append(
            "- Nội dung khách vừa phản ánh: "
            + " | ".join(_preview(text, 220) or "" for text in customer_messages)
        )
    if bot_messages:
        lines.append(
            "- Câu trả lời gần nhất của AI: "
            + (_preview(bot_messages[-1], 260) or "")
        )
    lines.append(
        "- Nhân viên nên đọc lại lịch sử, xác nhận vấn đề và phản hồi khách."
    )
    lines.append("(Tóm tắt tự động tạm thời do AI chưa sẵn sàng.)")
    return "\n".join(lines)


async def generate_conversation_summary(
    db: AsyncSession,
    conversation: Conversation,
) -> str:
    """Tạo tóm tắt hội thoại cho nhân viên bằng Gemini, có fallback."""

    customer = await db.get(User, conversation.user_id)
    account = await _find_channel_account(db, conversation)
    customer_name = (
        (account.display_name if account else None)
        or (customer.username if customer else None)
        or "Khách"
    )

    messages = list(
        (
            await db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.asc())
            )
        ).all()
    )
    transcript = _build_transcript(messages)

    if not transcript.strip():
        summary = f"- Khách hàng: {customer_name}\n- Chưa có nội dung hội thoại để tóm tắt."
        conversation.summary = summary
        conversation.summary_updated_at = datetime.now(timezone.utc)
        return summary

    account_line = "chưa liên kết tài khoản web"
    if customer and customer.role != "guest" and customer.is_active:
        account_line = f"đã liên kết tài khoản {customer.username}"
    if account and account.external_username:
        account_line += f", username kênh: @{account.external_username}"

    prompt = (
        "Bạn là điều phối viên chăm sóc khách hàng. Hãy tóm tắt cuộc hội thoại "
        "dưới đây để nhân viên có thể tiếp quản ngay mà không cần đọc hết lịch sử.\n\n"
        "Thông tin khách:\n"
        f"- Tên hiển thị: {customer_name}\n"
        f"- Kênh: {conversation.channel}\n"
        f"- Tài khoản: {account_line}\n"
        f"- Lý do chuyển giao: {conversation.handoff_reason or 'Khách cần hỗ trợ'}\n\n"
        "Cuộc hội thoại:\n"
        f"{transcript}\n\n"
        "Yêu cầu:\n"
        "- Viết bằng tiếng Việt, 4-8 gạch đầu dòng ngắn gọn.\n"
        "- Nêu rõ vấn đề/chủ đề khách đang cần giải quyết.\n"
        "- Nêu cảm xúc hoặc lý do khách bức xúc (nếu có).\n"
        "- Tóm tắt những gì AI đã trả lời, đặc biệt là thông tin đơn hàng, "
        "chính sách hoặc cam kết đã đưa ra.\n"
        "- Nêu thông tin còn thiếu hoặc việc nhân viên nên làm tiếp theo.\n"
        "- Không bịa thông tin không có trong hội thoại.\n"
        "- Chỉ trả về nội dung tóm tắt, không mở đầu bằng lời chào."
    )

    try:
        response = await generate_chat_response(
            prompt,
            config=GenerateContentConfig(temperature=0.2),
        )
        summary = (response.text or "").strip()
    except Exception:  # noqa: BLE001 - luôn có tóm tắt dự phòng
        logger.exception(
            "Gemini summary failed for conversation %s",
            conversation.id,
        )
        summary = ""

    if not summary:
        summary = _fallback_summary(conversation, customer_name, messages)

    conversation.summary = summary[:_SUMMARY_MAX_CHARS]
    conversation.summary_updated_at = datetime.now(timezone.utc)
    await db.flush()
    return conversation.summary


async def refresh_conversation_summary(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    agent: User,
) -> Conversation:
    conversation = await get_support_conversation(db, conversation_id, agent)
    await generate_conversation_summary(db, conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def claim_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    agent: User,
) -> Conversation:
    conversation = await get_support_conversation(db, conversation_id, agent)
    if conversation.resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation is already closed",
        )
    if conversation.support_mode == SUPPORT_MODE_HUMAN:
        if conversation.assigned_staff_id == agent.id:
            return conversation
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation was already claimed by another staff member",
        )
    if conversation.support_mode != SUPPORT_MODE_WAITING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation is not waiting for staff",
        )

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.support_mode == SUPPORT_MODE_WAITING,
            Conversation.resolved_at.is_(None),
        )
        .values(
            support_mode=SUPPORT_MODE_HUMAN,
            assigned_staff_id=agent.id,
            updated_at=now,
        )
        .returning(Conversation.id)
    )
    if result.scalar_one_or_none() is None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation was already claimed by another staff member",
        )

    await db.commit()
    await db.refresh(conversation)

    if not conversation.summary:
        schedule_summary_generation(conversation.id)
    return conversation


async def assign_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    admin: User,
    staff_id: uuid.UUID | None,
) -> Conversation:
    if admin.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    conversation = await get_support_conversation(db, conversation_id, admin)
    if conversation.resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation is already closed",
        )

    now = datetime.now(timezone.utc)
    if staff_id is None:
        conversation.support_mode = SUPPORT_MODE_WAITING
        conversation.assigned_staff_id = None
        if conversation.handoff_at is None:
            conversation.handoff_at = now
            conversation.handoff_reason = conversation.handoff_reason or "Admin chuyển cho bàn hỗ trợ"
    else:
        staff = await db.get(User, staff_id)
        if (
            staff is None
            or not staff.is_active
            or staff.role not in {"staff", "admin"}
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid staff account",
            )
        conversation.support_mode = SUPPORT_MODE_HUMAN
        conversation.assigned_staff_id = staff.id

    conversation.updated_at = now
    await db.commit()
    await db.refresh(conversation)

    if not conversation.summary:
        schedule_summary_generation(conversation.id)
    return conversation


async def _send_telegram_text(
    conversation: Conversation,
    text: str,
) -> tuple[bool, str | None]:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return False, "Chưa cấu hình TELEGRAM_BOT_TOKEN trên server."
    if not conversation.external_chat_id:
        return False, "Hội thoại Telegram thiếu external_chat_id."

    # Import muộn để tránh vòng import giữa service và channel adapter.
    from app.channels.telegram import TelegramAPIError, TelegramClient

    bot = TelegramClient(settings.telegram_bot_token)
    try:
        await bot.send_message(conversation.external_chat_id, text)
        return True, None
    except TelegramAPIError as exc:
        logger.exception(
            "Could not deliver staff message to Telegram chat %s",
            conversation.external_chat_id,
        )
        return False, str(exc)
    finally:
        await bot.aclose()


async def send_support_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    agent: User,
    content: str,
    is_internal: bool,
) -> tuple[Message, bool, str | None]:
    conversation = await get_support_conversation(db, conversation_id, agent)
    if conversation.resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation is already closed",
        )
    if conversation.support_mode != SUPPORT_MODE_HUMAN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hãy nhận hội thoại trước khi trả lời khách.",
        )
    if agent.role != "admin" and conversation.assigned_staff_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conversation is assigned to another staff member",
        )

    text = content.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content is required",
        )

    delivered = True
    warning: str | None = None
    if not is_internal and conversation.channel == "telegram":
        delivered, warning = await _send_telegram_text(conversation, text)
        if not delivered:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=warning or "Không gửi được tin nhắn qua Telegram.",
            )

    now = datetime.now(timezone.utc)
    message = Message(
        conversation_id=conversation.id,
        sender_type="STAFF",
        sender_id=agent.id,
        is_internal=is_internal,
        content=text,
    )
    message.sender = agent
    db.add(message)
    conversation.updated_at = now
    await db.commit()
    await db.refresh(message)
    await db.refresh(agent)
    message.sender = agent
    return message, delivered, warning


async def return_conversation_to_bot(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    agent: User,
) -> Conversation:
    conversation = await get_support_conversation(db, conversation_id, agent)
    if conversation.resolved_at is not None:
        return conversation
    if agent.role != "admin" and (
        conversation.support_mode != SUPPORT_MODE_HUMAN
        or conversation.assigned_staff_id != agent.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phụ trách hội thoại này",
        )

    now = datetime.now(timezone.utc)
    conversation.support_mode = SUPPORT_MODE_BOT
    conversation.assigned_staff_id = None
    conversation.resolved_at = now
    conversation.updated_at = now

    notice = Message(
        conversation_id=conversation.id,
        sender_type="SYSTEM",
        content=RETURN_TO_BOT_NOTICE,
    )
    db.add(notice)
    await db.commit()
    await db.refresh(conversation)

    if conversation.channel == "telegram":
        delivered, warning = await _send_telegram_text(conversation, RETURN_TO_BOT_NOTICE)
        if not delivered:
            logger.warning(
                "Could not send return-to-bot notice to Telegram conversation %s: %s",
                conversation.id,
                warning,
            )
    return conversation


async def get_support_stats(db: AsyncSession, agent: User) -> dict[str, int]:
    waiting = (
        await db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.support_mode == SUPPORT_MODE_WAITING,
                Conversation.resolved_at.is_(None),
            )
        )
        or 0
    )
    assigned_to_me = (
        await db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.support_mode == SUPPORT_MODE_HUMAN,
                Conversation.assigned_staff_id == agent.id,
                Conversation.resolved_at.is_(None),
            )
        )
        or 0
    )
    active = (
        await db.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.support_mode == SUPPORT_MODE_HUMAN,
                Conversation.resolved_at.is_(None),
            )
        )
        or 0
    )
    return {
        "waiting_count": int(waiting),
        "assigned_to_me": int(assigned_to_me),
        "active_count": int(active),
    }


async def list_staff_options(db: AsyncSession) -> list[dict[str, Any]]:
    active_counts = (
        select(
            Conversation.assigned_staff_id.label("staff_id"),
            func.count(Conversation.id).label("active_count"),
        )
        .where(
            Conversation.support_mode == SUPPORT_MODE_HUMAN,
            Conversation.resolved_at.is_(None),
            Conversation.assigned_staff_id.is_not(None),
        )
        .group_by(Conversation.assigned_staff_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(User, func.coalesce(active_counts.c.active_count, 0))
            .outerjoin(active_counts, active_counts.c.staff_id == User.id)
            .where(User.role == "staff", User.is_active.is_(True))
            .order_by(User.username.asc())
        )
    ).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "active_count": int(count or 0),
        }
        for user, count in rows
    ]
