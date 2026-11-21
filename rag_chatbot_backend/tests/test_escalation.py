import pytest

from app.services.escalation_service import (
    detect_escalation,
    detect_negative_feedback,
)


@pytest.mark.parametrize(
    ("text", "expected_fragment"),
    [
        ("Shop trả lời sai rồi, bực mình quá!", "buc minh"),
        ("Tôi rất bực bội vì chờ lâu", "buc boi"),
        ("dịch vụ quá tệ!!!", "te"),
        ("chán quá, không ai trả lời", "chan"),
        ("TÔI MUỐN GẶP NHÂN VIÊN", "gap nhan vien"),
        ("cho tôi nói chuyện với người thật", "noi chuyen voi nguoi"),
        ("chuyển cho nhân viên hỗ trợ", "chuyen cho nhan vien"),
        ("gọi support giúp tôi", "goi support"),
        ("this is useless, I want a human", "useless"),
        ("BỰC MÌNH QUÁ!!!!", "buc minh"),
    ],
)
def test_detects_frustration_or_human_request(text, expected_fragment):
    signal = detect_escalation(text)
    assert signal is not None
    assert expected_fragment in signal.matched


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Chính sách đổi trả thế nào?",
        "Tôi muốn hỏi về đơn hàng ORD-123",
        "Thời gian giao hàng bao lâu?",
        "Cảm ơn shop, mình đã nhận được hàng.",
        "Hướng dẫn bảo hành giúp mình",
    ],
)
def test_normal_messages_are_not_escalated(text):
    assert detect_escalation(text) is None


def test_uppercase_with_many_exclamation_marks_is_escalation():
    signal = detect_escalation("TÔI ĐANG RẤT CẦN GIẢI THÍCH!!!!")
    assert signal is not None
    assert signal.matched == "UPPERCASE"


def test_negative_feedback_detection():
    signal = detect_negative_feedback("Câu trả lời sai và vô dụng")
    assert signal is not None
    assert "phản hồi tiêu cực" in signal.reason


def test_negative_feedback_ignores_empty_text():
    assert detect_negative_feedback(None) is None
    assert detect_negative_feedback("   ") is None
