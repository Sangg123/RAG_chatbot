from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class EscalationSignal:
    """Tín hiệu cho thấy khách đang bức xúc hoặc cần người thật hỗ trợ."""

    reason: str
    matched: str


# Các cụm từ được so khớp sau khi bỏ dấu và chuyển về chữ thường. Nhờ vậy
# khách gõ "bực mình", "buc minh" hay "BỰC MÌNH" đều được nhận diện.
_EXPLICIT_HUMAN_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bgap\s+(?:nhan\s+vien|nguoi\s+that|tu\s+van\s+vien)\b",
        r"\bchuyen\s+(?:sang\s+)?nhan\s+vien\b",
        r"\bchuyen\s+cho\s+(?:nhan\s+vien|nguoi\s+that|ho\s+tro\s+vien)\b",
        r"\b(?:can|goi|ket\s+noi)\s+nhan\s+vien\b",
        r"\b(?:can|goi)\s+(?:nguoi|ho\s+tro\s+vien)\s+that\b",
        r"\bnhan\s+vien\s+(?:ho\s+tro|that|tu\s+van)\b",
        r"\bnoi\s+chuyen\s+voi\s+(?:nguoi|nhan\s+vien)\b",
        r"\b(?:chat|tro\s+chuyen)\s+voi\s+(?:nhan\s+vien|nguoi\s+that|tu\s+van\s+vien)\b",
        r"\bho\s+tro\s+truc\s+tiep\b",
        r"\b(?:gap|goi)\s+(?:support|ho\s+tro\s+vien)\b",
        r"\b(?:live\s+agent|real\s+person|human\s+agent)\b",
        r"\b(?:talk|speak)\s+to\s+(?:a\s+)?human\b",
    )
)

_ANGER_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bbuc\s*(?:minh|boi|xuc)?\b",
        r"\btuc\s*(?:gian|dien|minh)?\b",
        r"\bdien\s*(?:tiet|roi)?\b",
        r"\bgiang\s+(?:du|len|qua)\b",
        r"\bgian\s+(?:du|len|qua|roi)\b",
        r"\bkhong\s+thich\b",
        r"\bnoi\s+khong\s+duoc\b",
        r"\bchan\s*(?:qua|that|roi)?\b",
        r"\bvo\s+dung\b",
        r"\bvo\s+li\b",
        r"\bvo\s+ly\b",
        r"\b(?:do\s+)?ngu\b",
        r"\bngu\s+ngoc\b",
        r"\b(?:do\s+)?te\b",
        r"\bte\s+qua\b",
        r"\bkem\s*(?:qua|chat)?\b",
        r"\bthat\s+vong\b",
        r"\bkhong\s+hai\s+long\b",
        r"\bbat\s+binh\b",
        r"\bphan\s+nan\b",
        r"\bkhieu\s+nai\b",
        r"\blua\s+dao\b",
        r"\bbip\s+dao\b",
        r"\b(?:dm|dmm|dcm|vcl|wtf)\b",
        r"\b(?:fuck|shit|damn|stupid|useless|angry|furious|terrible|worst|ridiculous|scam)\b",
    )
)

_AI_COMPLAINT_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\btra\s+loi\s+(?:sai|khong\s+dung|vo\s+nghia|linh\s+tinh)\b",
        r"\bsai\s+roi\b",
        r"\bkhong\s+dung\s+(?:y|roi|thong\s+tin)\b",
        r"\bkhong\s+hieu\s+(?:gi|ca)\b",
        r"\bhoi\s+lai\b",
        r"\blap\s+lai\b",
        r"\bbot\s+(?:ngu|do|te)\b",
        r"\bkhong\s+ai\s+tra\s+loi\b",
        r"\bdoi\s+qua\s+lau\b",
        r"\bcho\s+qua\s+lau\b",
        r"\bcham\s+qua\b",
    )
)

_NEGATIVE_FEEDBACK_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bkhong\s+hieu\b",
        r"\bkhong\s+giup\s+ich\b",
        r"\bkhong\s+co\s+ich\b",
        r"\bsai\b",
        r"\bte\b",
        r"\bvo\s+dung\b",
        r"\bthat\s+vong\b",
    )
)

_EXCLAMATION_PATTERN = re.compile(r"[!?]{3,}")
_WORD_PATTERN = re.compile(r"[^\W\d_]+", re.UNICODE)


def _normalize(text: str) -> str:
    """Bỏ dấu tiếng Việt + lowercase để so khớp ổn định."""

    lowered = text.casefold()
    decomposed = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    # đ/Đ không bị NFD tách dấu nên cần thay riêng.
    without_marks = without_marks.replace("đ", "d")
    return " ".join(without_marks.split())


def _find_match(patterns: tuple[re.Pattern[str], ...], normalized: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(normalized)
        if match:
            return match.group(0)
    return None


def detect_escalation(text: str) -> EscalationSignal | None:
    """Phát hiện khách bức xúc từ nội dung tin nhắn.

    Trả về None nếu tin nhắn bình thường. Hàm thuần (không gọi DB/AI) nên có
    thể dùng chung cho Web, Telegram và kiểm thử nhanh.
    """

    cleaned = (text or "").strip()
    if not cleaned:
        return None

    normalized = _normalize(cleaned)

    matched = _find_match(_EXPLICIT_HUMAN_PATTERNS, normalized)
    if matched:
        return EscalationSignal(
            reason="Khách yêu cầu gặp nhân viên hỗ trợ",
            matched=matched,
        )

    matched = _find_match(_ANGER_PATTERNS, normalized)
    if matched:
        return EscalationSignal(
            reason="Khách dùng ngôn từ bức xúc/tiêu cực",
            matched=matched,
        )

    matched = _find_match(_AI_COMPLAINT_PATTERNS, normalized)
    if matched:
        return EscalationSignal(
            reason="Khách phản ánh AI trả lời chưa đúng",
            matched=matched,
        )

    # Viết hoa gần như toàn bộ + nhiều dấu câu là dấu hiệu mạnh của bực bội.
    letters = [char for char in cleaned if char.isalpha()]
    if letters:
        uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
        if uppercase_ratio >= 0.7 and _EXCLAMATION_PATTERN.search(cleaned):
            return EscalationSignal(
                reason="Khách viết hoa và dùng nhiều dấu câu",
                matched="UPPERCASE",
            )

    return None


def detect_negative_feedback(text: str | None) -> EscalationSignal | None:
    """Phát hiện phản hồi đánh giá tiêu cực (dùng kèm rating thấp)."""

    cleaned = (text or "").strip()
    if not cleaned:
        return None
    normalized = _normalize(cleaned)
    matched = _find_match(_NEGATIVE_FEEDBACK_PATTERNS, normalized)
    if not matched:
        return None
    return EscalationSignal(
        reason="Khách gửi phản hồi tiêu cực",
        matched=matched,
    )
