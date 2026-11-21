import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.services import handoff_service


class _UpdateResult:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id

    def scalar_one_or_none(self):
        return self.conversation_id


class _FakeSession:
    def __init__(self, conversation_id):
        self.conversation_id = conversation_id
        self.statement = None
        self.committed = False

    async def execute(self, statement):
        self.statement = statement
        return _UpdateResult(self.conversation_id)

    async def commit(self):
        self.committed = True

    async def refresh(self, conversation):
        conversation.support_mode = handoff_service.SUPPORT_MODE_WAITING
        conversation.resolved_at = None


def test_handoff_reopens_resolved_conversation(monkeypatch):
    conversation_id = uuid.uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        support_mode=handoff_service.SUPPORT_MODE_BOT,
        resolved_at=datetime.now(timezone.utc),
    )
    db = _FakeSession(conversation_id)
    monkeypatch.setattr(
        handoff_service,
        "schedule_summary_generation",
        lambda _: None,
    )

    changed = asyncio.run(
        handoff_service.trigger_handoff(db, conversation, "Khách yêu cầu gặp nhân viên")
    )

    assert changed
    assert db.committed
    assert conversation.support_mode == handoff_service.SUPPORT_MODE_WAITING
    assert conversation.resolved_at is None
    where_sql = str(db.statement.whereclause.compile(dialect=postgresql.dialect()))
    assert "resolved_at" not in where_sql
