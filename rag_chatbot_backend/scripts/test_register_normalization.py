import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Cau hinh gia lap chi dung cho unit test
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db"
)

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "unit-test-only-not-for-production-0123456789"
)

os.environ.setdefault(
    "GEMINI_API_KEY",
    "unit-test-placeholder"
)

from fastapi import HTTPException

from app.api.v1 import auth as auth_api
from app.schemas.user import RegisterRequest


class TestRegisterNormalization(unittest.IsolatedAsyncioTestCase):

    def create_mock_db(self, existing=None):
        db = MagicMock()
        db.scalar = AsyncMock(return_value=existing)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    async def test_normalize_username_and_email(self):
        """Kiểm tra chuẩn hóa username và email khi đăng ký."""

        db = self.create_mock_db()

        payload = RegisterRequest(
            username="  testuser  ",
            email="TEST@EXAMPLE.COM",
            password="TestPassword123!"
        )

        with patch.object(
            auth_api, "hash_password", return_value="hashed_test"
        ), patch.object(
            auth_api, "_build_auth_response", return_value={"ok": True}
        ):
            result = await auth_api.register(payload, db)

        # Kiểm tra dữ liệu được lưu
        user = db.add.call_args.args[0]

        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")

        # Kiểm tra dữ liệu dùng để tìm tài khoản trùng
        query = db.scalar.await_args.args[0]
        values = list(query.compile().params.values())

        self.assertIn("testuser", values)
        self.assertIn("test@example.com", values)

        db.commit.assert_awaited_once()

        self.assertEqual(result, {"ok": True})

    async def test_duplicate_account(self):
        """Kiểm tra phát hiện tài khoản trùng sau chuẩn hóa."""

        db = self.create_mock_db(existing=object())

        payload = RegisterRequest(
            username="  testuser  ",
            email="TEST@EXAMPLE.COM",
            password="TestPassword123!"
        )

        with self.assertRaises(HTTPException) as context:
            await auth_api.register(payload, db)

        # Phiên bản Backend hiện tại trả về HTTP 400
        self.assertEqual(context.exception.status_code, 400)

        # Kiểm tra truy vấn dùng dữ liệu đã chuẩn hóa
        query = db.scalar.await_args.args[0]
        values = list(query.compile().params.values())

        self.assertIn("testuser", values)
        self.assertIn("test@example.com", values)

        # Không tạo tài khoản khi phát hiện trùng
        db.add.assert_not_called()
        db.commit.assert_not_awaited()
    async def test_reject_short_username_after_trimming(self):
        """Từ chối username quá ngắn sau khi loại bỏ khoảng trắng."""

        db = self.create_mock_db()

        payload = RegisterRequest(
            username="  ab  ",
            email="shortusername@example.com",
            password="TestPassword123!"
        )

        with self.assertRaises(HTTPException) as context:
            await auth_api.register(payload, db)

        self.assertEqual(context.exception.status_code, 422)

        db.scalar.assert_not_awaited()
        db.add.assert_not_called()
        db.commit.assert_not_awaited()




if __name__ == "__main__":

    unittest.main()
