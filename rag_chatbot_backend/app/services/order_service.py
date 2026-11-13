from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Order, OrderItem


ORDER_STATUS_LABELS = {
    "PENDING": "Chờ xác nhận",
    "CONFIRMED": "Đã xác nhận",
    "PACKING": "Đang đóng gói",
    "SHIPPING": "Đang giao hàng",
    "DELIVERED": "Đã giao hàng",
    "CANCELLED": "Đã hủy",
    "RETURNED": "Đã trả hàng",
}

PAYMENT_STATUS_LABELS = {
    "UNPAID": "Chưa thanh toán",
    "PAID": "Đã thanh toán",
    "REFUNDED": "Đã hoàn tiền",
}

_ORDER_CODE_SEPARATORS = re.compile(r"[\s._-]+")
_NON_DIGITS = re.compile(r"\D")


def normalize_order_code(value: str | None) -> str:
    """Chuẩn hóa mã đơn: 'dh 123' / 'DH-123' -> 'DH123'."""
    cleaned = _ORDER_CODE_SEPARATORS.sub("", str(value or "")).upper()
    if cleaned.isdigit():
        cleaned = f"DH{cleaned}"
    return cleaned


def normalize_phone(value: str | None) -> str:
    """Chuẩn hóa SĐT Việt Nam: '+84 901 234 567' -> '0901234567'."""
    digits = _NON_DIGITS.sub("", str(value or ""))
    if digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits


def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r"0\d{9}", phone))


def mask_phone(phone: str | None) -> str:
    digits = _NON_DIGITS.sub("", str(phone or ""))
    if len(digits) < 4:
        return "******"
    return f"******{digits[-4:]}"


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _money(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _serialize_item(item: OrderItem) -> dict:
    unit_price = _money(item.unit_price)
    return {
        "product_name": item.product_name,
        "quantity": item.quantity,
        "unit_price": unit_price,
        "line_total": round(unit_price * item.quantity, 2),
    }


def serialize_order(order: Order) -> dict:
    items = [_serialize_item(item) for item in order.items]
    return {
        "found": True,
        "order_code": order.order_code,
        "status": order.status,
        "status_label": ORDER_STATUS_LABELS.get(order.status, order.status),
        "customer_name": order.customer_name,
        "customer_phone_masked": mask_phone(order.customer_phone),
        "shipping_address": order.shipping_address,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "payment_status_label": PAYMENT_STATUS_LABELS.get(
            order.payment_status or "", order.payment_status
        ),
        "items": items,
        "item_count": len(items),
        "subtotal": _money(order.subtotal),
        "shipping_fee": _money(order.shipping_fee),
        "total_amount": _money(order.total_amount),
        "currency": "VND",
        "carrier": order.carrier,
        "tracking_code": order.tracking_code,
        "ordered_at": _iso(order.ordered_at),
        "estimated_delivery": _iso(order.estimated_delivery),
        "delivered_at": _iso(order.delivered_at),
        "note": order.note,
    }


def _serialize_order_summary(order: Order) -> dict:
    return {
        "order_code": order.order_code,
        "status": order.status,
        "status_label": ORDER_STATUS_LABELS.get(order.status, order.status),
        "total_amount": _money(order.total_amount),
        "currency": "VND",
        "item_count": len(order.items),
        "carrier": order.carrier,
        "tracking_code": order.tracking_code,
        "ordered_at": _iso(order.ordered_at),
        "estimated_delivery": _iso(order.estimated_delivery),
        "delivered_at": _iso(order.delivered_at),
    }


def _lookup_not_found(order_code: str | None) -> dict:
    """Kết quả chung khi không tìm thấy đơn hoặc đơn không thuộc user.

    Không phân biệt "không tồn tại" với "thuộc người khác" để tránh lộ việc
    mã đơn/SĐT có tồn tại trong hệ thống hay không.
    """
    return {
        "found": False,
        "order_code": order_code,
        "message": (
            "Không tìm thấy đơn hàng này trong tài khoản đang đăng nhập. "
            "Vui lòng kiểm tra lại mã đơn hoặc đăng nhập đúng tài khoản."
        ),
    }


async def lookup_order(
    db: AsyncSession,
    order_code: str | None,
    *,
    user_id: uuid.UUID,
) -> dict:
    """Tra cứu đơn theo mã, chỉ trong phạm vi tài khoản đang đăng nhập."""
    normalized = normalize_order_code(order_code)
    if not normalized:
        return {
            "found": False,
            "order_code": None,
            "message": "Mã đơn hàng không hợp lệ. Vui lòng cung cấp mã như DH123.",
        }

    if not user_id:
        return _lookup_not_found(normalized)

    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.order_code == normalized,
            Order.user_id == user_id,
        )
    )
    order = await db.scalar(stmt)

    if not order:
        return _lookup_not_found(normalized)

    return serialize_order(order)


async def list_orders_by_phone(
    db: AsyncSession,
    phone: str | None,
    *,
    user_id: uuid.UUID,
    limit: int = 5,
) -> dict:
    """Liệt kê đơn của SĐT, chỉ trong phạm vi tài khoản đang đăng nhập."""
    normalized = normalize_phone(phone)
    if not is_valid_phone(normalized):
        return {
            "found": False,
            "phone_masked": mask_phone(normalized),
            "message": "Số điện thoại không hợp lệ. Vui lòng cung cấp SĐT 10 số.",
        }

    if not user_id:
        return {
            "found": False,
            "phone_masked": mask_phone(normalized),
            "message": (
                "Không tìm thấy đơn hàng nào thuộc tài khoản đang đăng nhập "
                "gắn với số điện thoại này."
            ),
        }

    try:
        limit_value = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        limit_value = 5

    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.user_id == user_id,
            Order.customer_phone == normalized,
        )
        .order_by(Order.ordered_at.desc())
        .limit(limit_value)
    )
    orders = list((await db.scalars(stmt)).all())

    if not orders:
        return {
            "found": False,
            "phone_masked": mask_phone(normalized),
            "message": (
                "Không tìm thấy đơn hàng nào thuộc tài khoản đang đăng nhập "
                "gắn với số điện thoại này."
            ),
        }

    return {
        "found": True,
        "phone_masked": mask_phone(normalized),
        "count": len(orders),
        "orders": [_serialize_order_summary(order) for order in orders],
    }
