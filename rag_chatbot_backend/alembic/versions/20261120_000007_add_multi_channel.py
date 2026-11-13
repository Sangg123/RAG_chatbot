"""add multi-channel support (Telegram first)

Revision ID: 20261120_000007
Revises: 20261117_000006
Create Date: 2026-11-20

Thêm lớp danh tính kênh ngoài và đánh dấu hội thoại đến từ kênh nào:

- channel_accounts: ánh xạ (channel, external_user_id) -> users.id
- conversations.channel: "web" (mặc định) hoặc "telegram", "zalo"...
- conversations.external_chat_id: id chat/thread phía kênh ngoài
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261120_000007"
down_revision = "20261117_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "channel",
            sa.String(length=32),
            server_default="web",
            nullable=False,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("external_chat_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_conversations_channel_external_chat",
        "conversations",
        ["channel", "external_chat_id"],
        unique=False,
    )

    op.create_table(
        "channel_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("external_user_id", sa.String(length=128), nullable=False),
        sa.Column("external_chat_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("external_username", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "channel",
            "external_user_id",
            name="uq_channel_accounts_channel_external_user",
        ),
    )
    op.create_index(
        op.f("ix_channel_accounts_channel"),
        "channel_accounts",
        ["channel"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_accounts_external_user_id"),
        "channel_accounts",
        ["external_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_accounts_external_chat_id"),
        "channel_accounts",
        ["external_chat_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_channel_accounts_user_id"),
        "channel_accounts",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_channel_accounts_user_id"), table_name="channel_accounts")
    op.drop_index(
        op.f("ix_channel_accounts_external_chat_id"),
        table_name="channel_accounts",
    )
    op.drop_index(
        op.f("ix_channel_accounts_external_user_id"),
        table_name="channel_accounts",
    )
    op.drop_index(op.f("ix_channel_accounts_channel"), table_name="channel_accounts")
    op.drop_table("channel_accounts")

    op.drop_index(
        "ix_conversations_channel_external_chat",
        table_name="conversations",
    )
    op.drop_column("conversations", "external_chat_id")
    op.drop_column("conversations", "channel")
