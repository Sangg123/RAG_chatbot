from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse, MAX_MESSAGE_LENGTH


class SupportConversationResponse(BaseModel):
    id: UUID
    title: str | None = None
    channel: str
    external_chat_id: str | None = None
    support_mode: str
    handoff_reason: str | None = None
    handoff_at: datetime | None = None
    resolved_at: datetime | None = None
    summary: str | None = None
    summary_updated_at: datetime | None = None
    assigned_staff_id: UUID | None = None
    assigned_staff_username: str | None = None
    customer_name: str
    customer_username: str | None = None
    customer_external_username: str | None = None
    customer_is_linked: bool = False
    message_count: int = 0
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    waiting_seconds: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class SupportConversationDetail(SupportConversationResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class SupportMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    is_internal: bool = False


class SupportMessageResult(BaseModel):
    ok: bool = True
    delivered: bool = True
    warning: str | None = None
    message: MessageResponse | None = None


class SupportActionResponse(BaseModel):
    ok: bool = True
    support_mode: str
    assigned_staff_id: UUID | None = None
    resolved_at: datetime | None = None


class SupportStatsResponse(BaseModel):
    waiting_count: int = 0
    assigned_to_me: int = 0
    active_count: int = 0


class SupportStaffOption(BaseModel):
    id: UUID
    username: str
    email: str
    active_count: int = 0


class AssignStaffRequest(BaseModel):
    staff_id: UUID | None = None
