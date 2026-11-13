import unittest

from app.services.order_intent import (
    OrderIntent,
    detect_order_intent,
    is_policy_question,
)
from app.services.order_service import normalize_order_code, normalize_phone


class OrderIntentTests(unittest.TestCase):
    def assert_intent(self, message: str, intent: OrderIntent | None):
        result = detect_order_intent(message)
        self.assertEqual(result.intent, intent, msg=message)
        return result

    def test_order_code_with_context(self):
        result = self.assert_intent(
            "Đơn DH123 đang ở đâu?", OrderIntent.ORDER_CODE
        )
        self.assertEqual(result.order_code, "DH123")
        self.assertEqual(result.forced_tool, "lookup_order")

    def test_standalone_order_code(self):
        result = self.assert_intent("DH123", OrderIntent.ORDER_CODE)
        self.assertEqual(result.order_code, "DH123")
        self.assertEqual(result.forced_tool, "lookup_order")

    def test_order_code_with_separators(self):
        result = self.assert_intent("Mã đơn DH-123 giao chưa?", OrderIntent.ORDER_CODE)
        self.assertEqual(result.order_code, "DH123")

    def test_order_code_typed_with_vietnamese_d(self):
        result = self.assert_intent("Đơn đh123 đang ở đâu?", OrderIntent.ORDER_CODE)
        self.assertEqual(result.order_code, "DH123")

    def test_order_code_not_found_still_forces_tool(self):
        result = self.assert_intent("DH999 giao chưa?", OrderIntent.ORDER_CODE)
        self.assertEqual(result.order_code, "DH999")
        self.assertEqual(result.forced_tool, "lookup_order")

    def test_code_without_order_context_does_not_force(self):
        result = self.assert_intent("DH123 có gì đặc biệt?", None)
        self.assertEqual(result.reason, "code_without_order_context")

    def test_product_name_with_dh_does_not_force(self):
        result = self.assert_intent("Sản phẩm DH có gì đặc biệt?", None)
        self.assertEqual(result.reason, "not_order_related")

    def test_policy_question_is_not_order(self):
        self.assert_intent("Chính sách đổi trả thế nào?", None)

    def test_english_ticket_status_is_not_order(self):
        self.assert_intent("What is the status of my support ticket?", None)

    def test_english_order_question(self):
        self.assert_intent("Where is my order?", OrderIntent.ORDER_GENERAL)

    def test_phone_with_order_context(self):
        result = self.assert_intent(
            "SĐT 0901234567 có đơn nào chưa giao?", OrderIntent.ORDER_PHONE
        )
        self.assertEqual(result.phone, "0901234567")
        self.assertEqual(result.forced_tool, "list_orders_by_phone")

    def test_phone_without_order_context_does_not_force(self):
        self.assert_intent("0901234567", None)

    def test_order_general_without_code(self):
        result = self.assert_intent(
            "Đơn hàng của tôi đâu rồi?", OrderIntent.ORDER_GENERAL
        )
        self.assertIsNone(result.forced_tool)

    def test_order_follow_up_reference(self):
        result = self.assert_intent(
            "Thế còn đơn kia thì sao?", OrderIntent.ORDER_GENERAL
        )
        self.assertIsNone(result.forced_tool)

    def test_order_code_with_return_policy_context(self):
        self.assert_intent(
            "Đơn DH123 có được đổi trả không?", OrderIntent.ORDER_CODE
        )

    def test_policy_question_detection(self):
        self.assertTrue(
            is_policy_question("Đơn DH123 có được đổi trả không?")
        )
        self.assertFalse(is_policy_question("Đơn DH123 đang ở đâu?"))


class NormalizeTests(unittest.TestCase):
    def test_normalize_order_code(self):
        self.assertEqual(normalize_order_code(" dh 123 "), "DH123")
        self.assertEqual(normalize_order_code("DH-123"), "DH123")
        self.assertEqual(normalize_order_code("123"), "DH123")

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+84 901 234 567"), "0901234567")
        self.assertEqual(normalize_phone("090-123-4567"), "0901234567")


if __name__ == "__main__":
    unittest.main()
