import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChannelAccount(Base):
    """Liên kết danh tính trên kênh ngoài (Telegram, Zalo...) với user nội bộ.

    Mỗi cặp (channel, external_user_id) chỉ ánh xạ tới một user. Nhờ vậy cùng
    một khách có thể chat web và Telegram mà vẫn dùng chung lịch sử/đơn hàng
    sau khi liên kết tài khoản.
    """

    __tablename__ = "channel_accounts"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "external_user_id",
            name="uq_channel_accounts_channel_external_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_user_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    external_chat_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
