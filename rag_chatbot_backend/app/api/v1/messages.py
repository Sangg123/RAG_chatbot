import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_current_user, get_db
from app.models import (
    Conversation,
    Document,
    DocumentChunk,
    Message,
    MessageCitation,
    MessageToolCall,
    User,
)
from app.schemas.message import (
    MessageCitationResponse,
    MessageCreate,
    MessageFeedbackUpdate,
    MessageToolCallResponse,
)
from app.services.chat_service import stream_rag_answer
from app.services.escalation_service import detect_negative_feedback
from app.services.handoff_service import (
    SUPPORT_MODE_BOT,
    can_view_conversation,
    trigger_handoff,
)


router = APIRouter(tags=["messages"])
logger = logging.getLogger(__name__)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    async def event_generator():
        try:
            async for event in stream_rag_answer(db, conversation_id, payload, current_user):
                if event.event == "token":
                    yield {"event": "token", "data": event.data}
                else:
                    yield {
                        "event": event.event,
                        "data": json.dumps(event.data, ensure_ascii=False),
                    }
            yield {"event": "done", "data": "[DONE]"}
        except Exception as exc:
            logger.exception("Chat stream failed for conversation %s", conversation_id)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(exc)}),
            }

    return EventSourceResponse(event_generator())


@router.get("/messages/{message_id}/citations", response_model=list[MessageCitationResponse])
async def get_message_citations(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = await db.scalar(select(Message).where(Message.id == message_id))
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    conversation = await db.scalar(select(Conversation).where(Conversation.id == message.conversation_id))
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if not can_view_conversation(current_user, conversation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(
        select(MessageCitation, DocumentChunk, Document)
        .join(DocumentChunk, MessageCitation.chunk_id == DocumentChunk.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(MessageCitation.message_id == message_id)
    )
    rows = result.all()
    return [
        MessageCitationResponse(
            id=citation.id,
            message_id=citation.message_id,
            chunk_id=citation.chunk_id,
            relevance_score=citation.relevance_score,
            chunk_content=chunk.content,
            document_name=document.filename,
        )
        for citation, chunk, document in rows
    ]


@router.get(
    "/messages/{message_id}/tool-calls",
    response_model=list[MessageToolCallResponse],
)
async def get_message_tool_calls(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = await db.scalar(select(Message).where(Message.id == message_id))
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    conversation = await db.scalar(select(Conversation).where(Conversation.id == message.conversation_id))
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if not can_view_conversation(current_user, conversation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    result = await db.execute(
        select(MessageToolCall)
        .where(MessageToolCall.message_id == message_id)
        .order_by(MessageToolCall.created_at.asc())
    )
    return result.scalars().all()


@router.patch("/messages/{message_id}/feedback")
async def update_message_feedback(
    message_id: uuid.UUID,
    payload: MessageFeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = await db.scalar(select(Message).where(Message.id == message_id))
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    conversation = await db.scalar(select(Conversation).where(Conversation.id == message.conversation_id))
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if not can_view_conversation(current_user, conversation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    message.rating = payload.rating
    message.feedback_text = payload.feedback_text

    handoff = False
    support_mode = conversation.support_mode
    if conversation.support_mode == SUPPORT_MODE_BOT:
        negative_feedback = detect_negative_feedback(payload.feedback_text)
        rating_signal = payload.rating is not None and payload.rating <= 2
        if rating_signal or negative_feedback is not None:
            reason = (
                f"Khách đánh giá {payload.rating}/5 sao"
                if rating_signal
                else (negative_feedback.reason if negative_feedback else "Khách phản hồi tiêu cực")
            )
            handoff = await trigger_handoff(db, conversation, reason)
            if handoff:
                support_mode = conversation.support_mode
    if not handoff:
        await db.commit()

    return {
        "ok": True,
        "handoff": handoff,
        "support_mode": support_mode,
    }
