"""add human handoff support

Revision ID: 20261121_000008
Revises: 20261120_000007
Create Date: 2026-11-21

Chuyển hội thoại từ AI sang nhân viên thật:

- conversations.support_mode: "bot" | "waiting" | "human"
- conversations.assigned_staff_id: nhân viên đang phụ trách
- conversations.handoff_reason / handoff_at: lý do và thời điểm chuyển giao
- conversations.summary / summary_updated_at: tóm tắt hội thoại cho nhân viên
- conversations.resolved_at: thời điểm kết thúc hỗ trợ
- messages.sender_id: nhân viên gửi tin (sender_type = "STAFF")
- messages.is_internal: ghi chú nội bộ, không gửi khách
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261121_000008"
down_revision = "20261120_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "support_mode",
            sa.String(length=16),
            server_default="bot",
            nullable=False,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "assigned_staff_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("handoff_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "handoff_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "summary_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_conversations_assigned_staff_id_users",
        "conversations",
        "users",
        ["assigned_staff_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_support_mode",
        "conversations",
        ["support_mode"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_assigned_staff_id",
        "conversations",
        ["assigned_staff_id"],
        unique=False,
    )

    op.add_column(
        "messages",
        sa.Column(
            "sender_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "messages",
        sa.Column(
            "is_internal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_messages_sender_id_users",
        "messages",
        "users",
        ["sender_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_messages_sender_id",
        "messages",
        ["sender_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_messages_sender_id", table_name="messages")
    op.drop_constraint(
        "fk_messages_sender_id_users",
        "messages",
        type_="foreignkey",
    )
    op.drop_column("messages", "is_internal")
    op.drop_column("messages", "sender_id")

    op.drop_index(
        "ix_conversations_assigned_staff_id",
        table_name="conversations",
    )
    op.drop_index(
        "ix_conversations_support_mode",
        table_name="conversations",
    )
    op.drop_constraint(
        "fk_conversations_assigned_staff_id_users",
        "conversations",
        type_="foreignkey",
    )
    op.drop_column("conversations", "resolved_at")
    op.drop_column("conversations", "summary_updated_at")
    op.drop_column("conversations", "summary")
    op.drop_column("conversations", "handoff_at")
    op.drop_column("conversations", "handoff_reason")
    op.drop_column("conversations", "assigned_staff_id")
    op.drop_column("conversations", "support_mode")
