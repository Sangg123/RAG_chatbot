from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_current_admin,
    get_current_support_agent,
    get_db,
)
from app.models import User
from app.schemas.message import MessageResponse
from app.schemas.support import (
    AssignStaffRequest,
    SupportActionResponse,
    SupportConversationDetail,
    SupportConversationResponse,
    SupportMessageCreate,
    SupportMessageResult,
    SupportStaffOption,
    SupportStatsResponse,
)
from app.services.handoff_service import (
    assign_conversation,
    build_support_conversation,
    claim_conversation,
    get_support_conversation_detail,
    get_support_stats,
    list_staff_options,
    list_support_conversations,
    refresh_conversation_summary,
    return_conversation_to_bot,
    send_support_message,
)

router = APIRouter(prefix="/support", tags=["support"])


def _action_response(conversation) -> SupportActionResponse:
    return SupportActionResponse(
        support_mode=conversation.support_mode,
        assigned_staff_id=conversation.assigned_staff_id,
        resolved_at=conversation.resolved_at,
    )


@router.get("/conversations", response_model=list[SupportConversationResponse])
async def list_support_conversations_endpoint(
    scope: Literal["waiting", "mine", "active", "closed", "all"] | None = Query(
        default=None
    ),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    effective_scope = scope or ("all" if agent.role == "admin" else "waiting")
    return await list_support_conversations(
        db,
        agent,
        scope=effective_scope,
        search=search,
    )


@router.get("/stats", response_model=SupportStatsResponse)
async def support_stats_endpoint(
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    return await get_support_stats(db, agent)


@router.get("/staff", response_model=list[SupportStaffOption])
async def list_support_staff_endpoint(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    return await list_staff_options(db)


@router.get(
    "/conversations/{conversation_id}",
    response_model=SupportConversationDetail,
)
async def get_support_conversation_endpoint(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    return await get_support_conversation_detail(db, conversation_id, agent)


@router.post(
    "/conversations/{conversation_id}/claim",
    response_model=SupportActionResponse,
)
async def claim_support_conversation_endpoint(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    conversation = await claim_conversation(db, conversation_id, agent)
    return _action_response(conversation)


@router.post(
    "/conversations/{conversation_id}/assign",
    response_model=SupportActionResponse,
)
async def assign_support_conversation_endpoint(
    conversation_id: uuid.UUID,
    payload: AssignStaffRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    conversation = await assign_conversation(
        db,
        conversation_id,
        admin,
        payload.staff_id,
    )
    return _action_response(conversation)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SupportMessageResult,
)
async def send_support_message_endpoint(
    conversation_id: uuid.UUID,
    payload: SupportMessageCreate,
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    message, delivered, warning = await send_support_message(
        db,
        conversation_id,
        agent,
        payload.content,
        payload.is_internal,
    )
    return SupportMessageResult(
        delivered=delivered,
        warning=warning,
        message=MessageResponse.model_validate(message),
    )


@router.post(
    "/conversations/{conversation_id}/summary",
    response_model=SupportConversationResponse,
)
async def refresh_support_summary_endpoint(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    conversation = await refresh_conversation_summary(db, conversation_id, agent)
    return await build_support_conversation(db, conversation)


@router.post(
    "/conversations/{conversation_id}/return-to-bot",
    response_model=SupportActionResponse,
)
async def return_support_conversation_endpoint(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    agent: User = Depends(get_current_support_agent),
):
    conversation = await return_conversation_to_bot(db, conversation_id, agent)
    return _action_response(conversation)
