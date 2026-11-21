from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None = None
    channel: str = "web"
    external_chat_id: str | None = None
    support_mode: str = "bot"
    assigned_staff_id: UUID | None = None
    handoff_reason: str | None = None
    handoff_at: datetime | None = None
    summary: str | None = None
    summary_updated_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None
    message_count: int = 0

    model_config = {"from_attributes": True}
