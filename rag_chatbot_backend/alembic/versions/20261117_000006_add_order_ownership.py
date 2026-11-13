"""add order ownership scoping

Revision ID: 20261117_000006
Revises: 20261117_000005
Create Date: 2026-11-17

Mỗi đơn hàng phải thuộc một user. Tool tra cứu chỉ được trả dữ liệu khi
orders.user_id trùng với user đang đăng nhập. Migration này cũng tạo các tài
khoản khách hàng demo để test tính năng phân quyền.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261117_000006"
down_revision = "20261117_000005"
branch_labels = None
depends_on = None


# Mật khẩu demo là "password123" (cùng hash với các user seed trong file SQL).
DEMO_PASSWORD_HASH = (
    "$2b$12$029RT/kJDFB7YC8MhdKogelrma4lDmICJOm3kLI1i4yAvLbbVHtQ2"
)

# (id, username, email, order_code)
DEMO_USERS = (
    (
        "11111111-1111-1111-1111-111111111001",
        "nguyen.van.an",
        "an.nguyen@company.com",
        "DH123",
    ),
    (
        "11111111-1111-1111-1111-111111111002",
        "tran.thi.binh",
        "binh.tran@company.com",
        "DH124",
    ),
    (
        "11111111-1111-1111-1111-111111111003",
        "le.hoang.cuong",
        "cuong.le@company.com",
        "DH125",
    ),
    (
        "11111111-1111-1111-1111-111111111010",
        "pham.thu.dung",
        "dung.pham@company.com",
        "DH126",
    ),
    (
        "11111111-1111-1111-1111-111111111011",
        "hoang.van.em",
        "em.hoang@company.com",
        "DH127",
    ),
    (
        "11111111-1111-1111-1111-111111111012",
        "vu.thi.lan",
        "lan.vu@company.com",
        "DH1001",
    ),
)


def _ensure_demo_user(bind, user_id: str, username: str, email: str) -> str:
    """Tạo user demo nếu chưa có, trả về UUID thực tế trong DB."""
    bind.execute(
        sa.text(
            """
            INSERT INTO users (
                id, username, email, hashed_password, role,
                is_active, token_version, created_at
            )
            VALUES (
                :id, :username, :email, :hashed_password, 'user',
                TRUE, 0, now()
            )
            ON CONFLICT (username) DO NOTHING
            """
        ),
        {
            "id": user_id,
            "username": username,
            "email": email,
            "hashed_password": DEMO_PASSWORD_HASH,
        },
    )
    return str(
        bind.execute(
            sa.text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).scalar_one()
    )


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    bind = op.get_bind()
    for user_id, username, email, order_code in DEMO_USERS:
        actual_user_id = _ensure_demo_user(bind, user_id, username, email)
        bind.execute(
            sa.text(
                "UPDATE orders SET user_id = :user_id WHERE order_code = :order_code"
            ),
            {"user_id": actual_user_id, "order_code": order_code},
        )

    remaining = bind.execute(
        sa.text("SELECT COUNT(*) FROM orders WHERE user_id IS NULL")
    ).scalar_one()
    if remaining:
        raise RuntimeError(
            f"Còn {remaining} đơn hàng chưa có chủ sở hữu. "
            "Hãy gán orders.user_id trước khi chạy migration này."
        )

    op.alter_column("orders", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_orders_user_id_users",
        "orders",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_orders_user_id"),
        "orders",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_constraint(
        "fk_orders_user_id_users",
        "orders",
        type_="foreignkey",
    )
    op.drop_column("orders", "user_id")
