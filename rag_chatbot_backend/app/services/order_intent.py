from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from app.services.order_service import normalize_order_code, normalize_phone


class OrderIntent(str, Enum):
    ORDER_CODE = "order_code"
    ORDER_PHONE = "order_phone"
    ORDER_GENERAL = "order_general"


@dataclass(frozen=True)
class OrderIntentResult:
    intent: OrderIntent | None
    order_code: str | None = None
    phone: str | None = None
    forced_tool: str | None = None
    reason: str = ""

    @property
    def is_order(self) -> bool:
        return self.intent is not None


ORDER_CODE_RE = re.compile(r"\bDH[\s._-]?\d{3,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?84|0)\d{9}(?!\d)")
_PHONE_SEPARATORS = re.compile(r"[\s.\-()]")

# Từ khóa đủ mạnh để kết luận người dùng đang nói về đơn hàng.
_STRONG_ORDER_KEYWORDS = (
    "don hang",
    "ma don",
    "don cua",
    "don dat",
    "don mua",
    "don kia",
    "don do",
    "don nay",
    "don ay",
    "don truoc",
    "don sau",
    "con don",
    "don vua",
    "huy don",
    "tra don",
    "xem don",
    "don dh",
    "giao hang",
    "van chuyen",
    "van don",
    "tracking",
    "ship",
    "shipper",
    "trang thai don",
    "dat hang",
    "thanh toan don",
    "nhan hang",
    "ngay giao",
    "du kien giao",
    "dang o dau",
    "toi dau",
    "giao chua",
    "chua giao",
    "giao den dau",
    "den dau roi",
    "nhan duoc chua",
    "bao gio giao",
    "order status",
    "my order",
    "order code",
    "track order",
    "where is my order",
    "delivery status",
    "shipping status",
    "payment status",
    "cancel order",
)

# Từ khóa chỉ dùng khi đã có mã đơn hoặc SĐT trong câu.
_CONTEXT_ORDER_KEYWORDS = (
    "kiem tra",
    "tra cuu",
    "giao",
    "don",
    "bao gio",
    "dang",
    "o dau",
    "chua",
    "order",
    "delivery",
    "shipping",
)

_STANDALONE_CODE_RE = re.compile(
    r"(?:ma\s+(?:don\s+)?)?dh\s*\d{3,}[?.!]*", re.IGNORECASE
)

# Khi câu hỏi đơn hàng kèm các chủ đề chính sách này, vẫn cần ngữ cảnh RAG.
_POLICY_KEYWORDS = (
    "doi tra",
    "hoan tien",
    "bao hanh",
    "chinh sach",
    "khuyen mai",
    "voucher",
    "hoa don",
    "xuat hoa don",
    "huy don",
    "doi dia chi",
    "giao lai",
    "kiem hang",
    "dong goi",
    "quy dinh",
    "thoi gian giao",
    "phi van chuyen",
    "phi ship",
)


def _strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def _normalize_text(text: str) -> str:
    return " ".join(_strip_accents(text).lower().split())


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords
    )


def is_policy_question(message: str) -> bool:
    """Câu hỏi đơn hàng có kèm chủ đề chính sách cần thêm ngữ cảnh RAG."""
    return _has_any(_normalize_text(message or ""), _POLICY_KEYWORDS)


def detect_order_intent(message: str) -> OrderIntentResult:
    """Phát hiện ý định tra cứu đơn hàng.

    Guardrail này chỉ quyết định có ép Gemini gọi tool hay không. Nó được
    thiết kế bảo thủ để tránh trường hợp chữ "DH" xuất hiện tình cờ.
    """
    raw = message or ""
    normalized = _normalize_text(raw)

    # Dùng bản bỏ dấu để bắt cả trường hợp gõ "đh123" thay vì "DH123".
    code_match = ORDER_CODE_RE.search(_strip_accents(raw))
    phone_match = PHONE_RE.search(_PHONE_SEPARATORS.sub("", raw))

    has_strong = _has_any(normalized, _STRONG_ORDER_KEYWORDS)
    has_context = has_strong or _has_any(normalized, _CONTEXT_ORDER_KEYWORDS)

    if code_match:
        order_code = normalize_order_code(code_match.group(0))
        standalone = bool(_STANDALONE_CODE_RE.fullmatch(normalized.strip()))
        if standalone or has_context:
            return OrderIntentResult(
                intent=OrderIntent.ORDER_CODE,
                order_code=order_code,
                forced_tool="lookup_order",
                reason="order_code_with_context",
            )
        return OrderIntentResult(
            intent=None,
            order_code=order_code,
            reason="code_without_order_context",
        )

    if phone_match:
        phone = normalize_phone(phone_match.group(0))
        if has_context:
            return OrderIntentResult(
                intent=OrderIntent.ORDER_PHONE,
                phone=phone,
                forced_tool="list_orders_by_phone",
                reason="phone_with_order_context",
            )
        return OrderIntentResult(
            intent=None,
            phone=phone,
            reason="phone_without_order_context",
        )

    if has_strong:
        return OrderIntentResult(
            intent=OrderIntent.ORDER_GENERAL,
            reason="order_context_without_code",
        )

    return OrderIntentResult(intent=None, reason="not_order_related")
