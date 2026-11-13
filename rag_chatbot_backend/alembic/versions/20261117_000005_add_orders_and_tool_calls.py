"""add orders, order items and tool call logs

Revision ID: 20261117_000005
Revises: 20260411_000004
Create Date: 2026-11-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261117_000005"
down_revision = "20260411_000004"
branch_labels = None
depends_on = None


SEED_ORDERS_SQL = """
INSERT INTO orders (
    id, order_code, customer_name, customer_phone, shipping_address,
    status, payment_method, payment_status, subtotal, shipping_fee,
    total_amount, carrier, tracking_code, ordered_at, estimated_delivery,
    delivered_at, note, created_at, updated_at
)
VALUES
    (
        '11111111-1111-4111-8111-111111111111', 'DH123',
        'Nguyễn Văn An', '0901234567',
        '123 Nguyễn Trãi, Quận 1, TP. Hồ Chí Minh',
        'SHIPPING', 'COD', 'UNPAID', 857000, 30000, 887000,
        'GHN', 'GHN123456789',
        now() - interval '2 days', now() + interval '1 day', NULL,
        'Giao trong giờ hành chính', now(), now()
    ),
    (
        '11111111-1111-4111-8111-111111111112', 'DH124',
        'Trần Thị Bình', '0912345678',
        '45 Lê Lợi, Hải Châu, Đà Nẵng',
        'DELIVERED', 'COD', 'PAID', 529000, 0, 529000,
        'Viettel Post', 'VTP987654321',
        now() - interval '5 days', now() - interval '2 days',
        now() - interval '1 day', NULL, now(), now()
    ),
    (
        '11111111-1111-4111-8111-111111111113', 'DH125',
        'Lê Minh Cường', '0987654321',
        '78 Trần Duy Hưng, Cầu Giấy, Hà Nội',
        'PENDING', 'BANK_TRANSFER', 'UNPAID', 1298000, 0, 1298000,
        NULL, NULL, now() - interval '2 hours',
        now() + interval '3 days', NULL, NULL, now(), now()
    ),
    (
        '11111111-1111-4111-8111-111111111114', 'DH126',
        'Phạm Thu Dung', '0909876543',
        '12 Phan Đình Phùng, Ba Đình, Hà Nội',
        'CANCELLED', 'COD', 'UNPAID', 249000, 30000, 279000,
        NULL, NULL, now() - interval '3 days', NULL, NULL,
        'Khách hủy do đổi ý', now(), now()
    ),
    (
        '11111111-1111-4111-8111-111111111115', 'DH127',
        'Hoàng Văn Em', '0934567890',
        '99 Võ Văn Ngân, Thủ Đức, TP. Hồ Chí Minh',
        'CONFIRMED', 'COD', 'UNPAID', 459000, 30000, 489000,
        'GHTK', 'GHTK456789123',
        now() - interval '1 day', now() + interval '2 days', NULL,
        NULL, now(), now()
    ),
    (
        '11111111-1111-4111-8111-111111111116', 'DH1001',
        'Vũ Thị Lan', '0945678901',
        '56 Hùng Vương, Ninh Kiều, Cần Thơ',
        'SHIPPING', 'BANK_TRANSFER', 'PAID', 678000, 25000, 703000,
        'Viettel Post', 'VTP112233445',
        now() - interval '1 day', now() + interval '1 day', NULL,
        NULL, now(), now()
    )
ON CONFLICT (order_code) DO NOTHING;
"""

_SEED_ORDER_ITEM_ROWS = (
    ("22222222-2222-4222-8222-222222220001", "DH123", "Áo thun cotton", 2, 199000),
    ("22222222-2222-4222-8222-222222220002", "DH123", "Quần jean slim", 1, 459000),
    ("22222222-2222-4222-8222-222222220003", "DH124", "Tai nghe Bluetooth", 1, 529000),
    ("22222222-2222-4222-8222-222222220004", "DH125", "Bàn phím cơ", 1, 899000),
    ("22222222-2222-4222-8222-222222220005", "DH125", "Chuột không dây", 1, 399000),
    ("22222222-2222-4222-8222-222222220006", "DH126", "Áo khoác gió", 1, 249000),
    ("22222222-2222-4222-8222-222222220007", "DH127", "Giày sneaker", 1, 459000),
    ("22222222-2222-4222-8222-222222220008", "DH1001", "Balo laptop", 1, 399000),
    ("22222222-2222-4222-8222-222222220009", "DH1001", "Ví da", 1, 279000),
)

SEED_ORDER_ITEM_STATEMENTS = tuple(
    f"""
INSERT INTO order_items (id, order_id, product_name, quantity, unit_price)
SELECT '{item_id}', o.id, '{product_name}', {quantity}, {unit_price}
FROM orders o WHERE o.order_code = '{order_code}'
ON CONFLICT (id) DO NOTHING
""".strip()
    for item_id, order_code, product_name, quantity, unit_price in _SEED_ORDER_ITEM_ROWS
)


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_code", sa.String(length=32), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_method", sa.String(length=32), nullable=True),
        sa.Column("payment_status", sa.String(length=32), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("shipping_fee", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("carrier", sa.String(length=100), nullable=True),
        sa.Column("tracking_code", sa.String(length=100), nullable=True),
        sa.Column(
            "ordered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("estimated_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_order_code"), "orders", ["order_code"], unique=True)
    op.create_index(op.f("ix_orders_customer_phone"), "orders", ["customer_phone"], unique=False)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)

    op.create_table(
        "message_tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_message_tool_calls_message_id"),
        "message_tool_calls",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_tool_calls_tool_name"),
        "message_tool_calls",
        ["tool_name"],
        unique=False,
    )

    op.execute(SEED_ORDERS_SQL)
    for statement in SEED_ORDER_ITEM_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.drop_index(op.f("ix_message_tool_calls_tool_name"), table_name="message_tool_calls")
    op.drop_index(op.f("ix_message_tool_calls_message_id"), table_name="message_tool_calls")
    op.drop_table("message_tool_calls")

    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_customer_phone"), table_name="orders")
    op.drop_index(op.f("ix_orders_order_code"), table_name="orders")
    op.drop_table("orders")
