import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    Conversation,
    Message,
    MessageCitation,
    MessageToolCall,
    User,
)
from app.schemas.message import MessageCreate
from app.services.agent_service import stream_order_agent
from app.services.order_intent import detect_order_intent, is_policy_question
from app.services.rag_service import (
    build_context_prompt,
    embed_query,
    find_similar_chunks,
    generate_conversation_title,
    stream_chat_answer,
)

settings = get_settings()
logger = logging.getLogger(__name__)

_DEFAULT_CONVERSATION_TITLES = {
    "new conversation",
    "hội thoại mới",
    "hoi thoai moi",
}

_EMPTY_ANSWER_FALLBACK = (
    "Xin lỗi, mình chưa thể tạo câu trả lời lúc này. "
    "Bạn vui lòng thử lại sau ít phút nhé."
)


@dataclass
class ChatEvent:
    """Sự kiện nội bộ được map thành SSE ở tầng API."""

    event: str
    data: str | dict


def _is_default_title(title: str | None) -> bool:
    if title is None:
        return True
    normalized = " ".join(title.strip().lower().split())
    return not normalized or normalized in _DEFAULT_CONVERSATION_TITLES


def _fallback_title_from_message(content: str) -> str:
    cleaned = " ".join(content.strip().split())
    if not cleaned:
        return "New conversation"
    words = cleaned.split()
    title = " ".join(words[:8])
    return title[:255]


async def _load_recent_history(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int,
) -> list[tuple[str, str]]:
    if limit <= 0:
        return []

    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list((await db.scalars(stmt)).all())
    rows.reverse()
    return [(message.sender_type, message.content) for message in rows]


def _record_tool_event(
    tool_calls: dict[str, dict],
    event_name: str,
    data: dict,
) -> None:
    call_id = str(data.get("id") or "")
    if not call_id:
        return

    record = tool_calls.setdefault(
        call_id,
        {
            "id": call_id,
            "name": data.get("name", ""),
            "arguments": {},
            "status": "running",
        },
    )
    record.update(data)
    if event_name == "tool_call":
        record["status"] = "running"


async def create_conversation(db: AsyncSession, user_id: uuid.UUID, title: str | None) -> dict:
    conv = Conversation(
        user_id=user_id,
        title=title or "New conversation",
        channel="web",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return {
        "id": conv.id,
        "user_id": conv.user_id,
        "title": conv.title,
        "channel": conv.channel,
        "external_chat_id": conv.external_chat_id,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "message_count": 0,
    }


async def delete_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    current_user: User,
) -> None:
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if current_user.role != "admin" and conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    await db.delete(conv)
    await db.commit()


async def list_conversations(db: AsyncSession, current_user: User, include_all: bool = False) -> list[dict]:
    stmt = (
        select(Conversation, func.count(Message.id).label("message_count"))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.id)
        .order_by(Conversation.created_at.desc())
    )
    if include_all and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    if not include_all:
        stmt = stmt.where(Conversation.user_id == current_user.id)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": conv.id,
            "user_id": conv.user_id,
            "title": conv.title,
            "channel": conv.channel,
            "external_chat_id": conv.external_chat_id,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "message_count": count,
        }
        for conv, count in rows
    ]


async def list_messages(db: AsyncSession, conversation_id: uuid.UUID, current_user: User) -> list[Message]:
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if current_user.role != "admin" and conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    return result.scalars().all()


async def stream_rag_answer(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User,
) -> AsyncIterator[ChatEvent]:
    conv = await db.scalar(select(Conversation).where(Conversation.id == conversation_id))
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if current_user.role != "admin" and conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    has_default_title = _is_default_title(conv.title)
    intent = detect_order_intent(payload.content)
    logger.info(
        "Chat intent conversation=%s intent=%s forced_tool=%s reason=%s",
        conversation_id,
        intent.intent,
        intent.forced_tool,
        intent.reason,
    )

    history: list[tuple[str, str]] = []
    if intent.is_order:
        history = await _load_recent_history(
            db,
            conversation_id,
            settings.chat_history_max_messages,
        )

    user_message = Message(
        conversation_id=conversation_id,
        sender_type="USER",
        content=payload.content,
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    # Tra cứu đơn trực tiếp không cần embedding tài liệu. Chỉ retrieval khi
    # câu hỏi không phải đơn hàng hoặc đơn hàng có kèm chủ đề chính sách.
    needs_document_context = intent.intent is None or is_policy_question(
        payload.content
    )

    chunks_with_scores = []
    if needs_document_context:
        try:
            query_embedding = await asyncio.to_thread(embed_query, payload.content)
            chunks_with_scores = await find_similar_chunks(
                db=db,
                query_embedding=query_embedding,
                top_k=settings.top_k_chunks,
            )
        except Exception:  # noqa: BLE001 - tool đơn hàng vẫn phải chạy khi RAG lỗi
            logger.exception(
                "RAG retrieval failed for conversation %s; continuing without context",
                conversation_id,
            )
    else:
        logger.info(
            "Skipping RAG retrieval for direct order lookup conversation=%s",
            conversation_id,
        )

    bot_tokens: list[str] = []
    tool_calls_by_id: dict[str, dict] = {}

    if intent.is_order:
        async for event in stream_order_agent(
            db=db,
            question=payload.content,
            context_chunks=[chunk.content for chunk, _ in chunks_with_scores],
            history=history,
            intent=intent,
            current_user_id=current_user.id,
        ):
            if event.event == "token":
                token = str(event.data.get("text", ""))
                if token:
                    bot_tokens.append(token)
                    yield ChatEvent("token", token)
            else:
                _record_tool_event(tool_calls_by_id, event.event, event.data)
                yield ChatEvent(event.event, event.data)
    else:
        prompt = build_context_prompt(
            payload.content,
            [chunk.content for chunk, _ in chunks_with_scores],
        )
        async for token in stream_chat_answer(prompt):
            bot_tokens.append(token)
            yield ChatEvent("token", token)

    if not bot_tokens:
        bot_tokens.append(_EMPTY_ANSWER_FALLBACK)
        yield ChatEvent("token", _EMPTY_ANSWER_FALLBACK)

    bot_message = Message(
        conversation_id=conversation_id,
        sender_type="BOT",
        content="".join(bot_tokens).strip(),
    )
    db.add(bot_message)

    if has_default_title:
        try:
            generated_title = await asyncio.to_thread(
                generate_conversation_title,
                payload.content,
            )
            if generated_title and not _is_default_title(generated_title):
                conv.title = generated_title
            else:
                conv.title = _fallback_title_from_message(payload.content)
        except Exception:
            conv.title = _fallback_title_from_message(payload.content)

    conv.updated_at = datetime.now(timezone.utc)
    await db.flush()

    for tool_call in tool_calls_by_id.values():
        try:
            call_id = uuid.UUID(str(tool_call["id"]))
        except (ValueError, TypeError, KeyError):
            call_id = uuid.uuid4()

        db.add(
            MessageToolCall(
                id=call_id,
                message_id=bot_message.id,
                tool_name=str(tool_call.get("name") or ""),
                arguments=tool_call.get("arguments") or {},
                result=tool_call.get("result"),
                status=str(tool_call.get("status") or "success"),
                error_message=tool_call.get("error"),
                duration_ms=tool_call.get("duration_ms"),
            )
        )

    # Câu trả lời lấy từ DB đơn hàng thì không gắn citation tài liệu RAG,
    # tránh hiển thị nguồn không liên quan trong UI.
    if not tool_calls_by_id:
        for chunk, score in chunks_with_scores:
            db.add(
                MessageCitation(
                    message_id=bot_message.id,
                    chunk_id=chunk.id,
                    relevance_score=score,
                )
            )

    await db.commit()
