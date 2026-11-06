#!/usr/bin/env python3
"""Kiểm thử tự động TC15, TC18, TC19 cho RAG Chatbot Backend.

Cách chạy (backend đang chạy ở http://127.0.0.1:8000):

    python scripts/test_tc15_18_19.py

Có thể đổi địa chỉ backend:

    python scripts/test_tc15_18_19.py --base-url http://localhost:8000

Script chỉ dùng thư viện chuẩn của Python, không cần cài thêm package.

TC15: gửi câu hỏi dài N-1, N, N+1 ký tự.
      N được đọc trực tiếp từ OpenAPI schema (MessageCreate.content.maxLength).
TC18: user thường gọi GET /api/v1/stats -> phải trả 403.
TC19: user_b đọc messages trong conversation của user_a -> phải trả 403.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------

def _build_request(
    method: str,
    url: str,
    token: str | None = None,
    payload: dict | None = None,
    accept: str = "application/json",
) -> urllib.request.Request:
    data = None
    headers = {"Accept": accept}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def _parse_body(raw: bytes):
    text = raw.decode("utf-8", "replace")
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def json_call(
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    payload: dict | None = None,
    timeout: int = 30,
) -> tuple[int, object]:
    """Gọi API và đọc toàn bộ body JSON."""
    url = f"{base_url}{path}"
    req = _build_request(method, url, token=token, payload=payload)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, _parse_body(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _parse_body(exc.read())
    except Exception as exc:  # noqa: BLE001 - hiển thị lỗi rõ ràng cho người chạy test
        raise RuntimeError(f"Không gọi được {method} {url}: {exc}") from exc


def sse_call(
    base_url: str,
    path: str,
    token: str,
    payload: dict,
    timeout: int = 60,
    hold_seconds: float = 0.0,
) -> tuple[int, object]:
    """Gửi request SSE.

    - Nếu bị từ chối (422/403/...), đọc body JSON và trả về.
    - Nếu được chấp nhận (200), giữ kết nối thêm `hold_seconds` giây rồi đóng.
      Chỉ cần status 200 để xác nhận request đã vượt qua validation.
    """
    url = f"{base_url}{path}"
    req = _build_request(
        "POST",
        url,
        token=token,
        payload=payload,
        accept="text/event-stream",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return exc.code, _parse_body(exc.read())
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Không gọi được POST {url}: {exc}") from exc

    try:
        if hold_seconds > 0:
            time.sleep(hold_seconds)
        return resp.status, None
    finally:
        resp.close()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

@dataclass
class TestUser:
    id: str
    username: str
    password: str
    token: str


@dataclass
class Results:
    items: list[tuple[str, str, str]] = field(default_factory=list)

    def add(self, tc: str, status: str, detail: str) -> None:
        self.items.append((tc, status, detail))
        print(f"  [{status}] {tc}: {detail}")

    def passed(self) -> bool:
        return all(status != "FAIL" for _, status, _ in self.items)


def register_user(base_url: str, prefix: str) -> TestUser:
    suffix = uuid.uuid4().hex[:10]
    username = f"{prefix}_{suffix}"
    password = "Test123456!"
    status, body = json_call(
        base_url,
        "POST",
        "/api/v1/auth/register",
        payload={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    if status != 201 or not isinstance(body, dict):
        raise RuntimeError(f"Đăng ký user {username} thất bại: {status} {body}")
    return TestUser(
        id=str(body["user"]["id"]),
        username=username,
        password=password,
        token=body["access_token"],
    )


def login(base_url: str, username: str, password: str) -> str | None:
    status, body = json_call(
        base_url,
        "POST",
        "/api/v1/auth/login",
        payload={"username": username, "password": password},
    )
    if status == 200 and isinstance(body, dict):
        return body.get("access_token")
    return None


def create_conversation(base_url: str, user: TestUser, title: str) -> str:
    status, body = json_call(
        base_url,
        "POST",
        "/api/v1/conversations",
        token=user.token,
        payload={"title": title},
    )
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"Tạo conversation thất bại: {status} {body}")
    return str(body["id"])


def delete_conversation(base_url: str, user: TestUser, conversation_id: str) -> None:
    json_call(
        base_url,
        "DELETE",
        f"/api/v1/conversations/{conversation_id}",
        token=user.token,
    )


def list_messages(base_url: str, user: TestUser, conversation_id: str) -> tuple[int, object]:
    return json_call(
        base_url,
        "GET",
        f"/api/v1/conversations/{conversation_id}/messages",
        token=user.token,
    )


def wait_for_message(
    base_url: str,
    user: TestUser,
    conversation_id: str,
    marker: str,
    timeout_seconds: int = 20,
) -> dict | None:
    """Chờ message chứa marker được lưu vào DB (user message được lưu trước khi gọi LLM)."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status, body = list_messages(base_url, user, conversation_id)
        if status == 200 and isinstance(body, list):
            for message in body:
                if marker in (message.get("content") or ""):
                    return message
        time.sleep(1)
    return None


def get_message_max_length(base_url: str) -> int:
    """Đọc N từ OpenAPI schema do FastAPI sinh ra."""
    status, spec = json_call(base_url, "GET", "/openapi.json", timeout=20)
    if status != 200 or not isinstance(spec, dict):
        raise RuntimeError(f"Không đọc được /openapi.json: {status}")

    try:
        content_schema = spec["components"]["schemas"]["MessageCreate"]["properties"]["content"]
    except KeyError as exc:
        raise RuntimeError("Không tìm thấy MessageCreate.content trong OpenAPI schema") from exc

    max_length = content_schema.get("maxLength")
    if not isinstance(max_length, int):
        raise RuntimeError(
            "MessageCreate.content chưa có maxLength trong OpenAPI schema. "
            "Hãy thêm Field(max_length=...) vào app/schemas/message.py và rebuild backend."
        )
    return max_length


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_tc15(base_url: str, user: TestUser, results: Results) -> None:
    print("\n[TC15] Độ dài câu hỏi tối đa")
    conversation_id: str | None = None
    try:
        max_length = get_message_max_length(base_url)
        print(f"  N = {max_length} (đọc từ OpenAPI schema)")

        conversation_id = create_conversation(base_url, user, "TC15 - max length")

        # Đếm số message trước khi gửi câu hỏi vượt giới hạn.
        status, before = list_messages(base_url, user, conversation_id)
        if status != 200 or not isinstance(before, list):
            raise RuntimeError(f"Không đọc được messages ban đầu: {status} {before}")
        before_count = len(before)

        # N+1: phải bị từ chối 422, body phải nói rõ giới hạn.
        status_n_plus_1, body_n_plus_1 = sse_call(
            base_url,
            f"/api/v1/conversations/{conversation_id}/messages",
            user.token,
            {"content": "x" * (max_length + 1)},
        )
        if status_n_plus_1 != 422:
            raise AssertionError(
                f"N+1 phải trả 422 nhưng nhận {status_n_plus_1}: {body_n_plus_1}"
            )
        rejection_text = json.dumps(body_n_plus_1, ensure_ascii=False)
        if str(max_length) not in rejection_text:
            raise AssertionError(
                f"Thông báo 422 không nêu giới hạn {max_length}: {rejection_text}"
            )

        # Đảm bảo message vượt giới hạn không được lưu.
        status, after = list_messages(base_url, user, conversation_id)
        if status != 200 or not isinstance(after, list):
            raise RuntimeError(f"Không đọc được messages sau khi gửi N+1: {status} {after}")
        if len(after) != before_count:
            raise AssertionError(
                f"Message N+1 vẫn bị lưu: trước={before_count}, sau={len(after)}"
            )

        # N và N-1: phải được chấp nhận (HTTP 200, SSE stream mở).
        # Đóng kết nối ngay sau khi nhận header để test chỉ tập trung vào validation.
        status_n, body_n = sse_call(
            base_url,
            f"/api/v1/conversations/{conversation_id}/messages",
            user.token,
            {"content": "x" * max_length},
            hold_seconds=0.3,
        )
        if status_n != 200:
            raise AssertionError(f"N phải được chấp nhận (200) nhưng nhận {status_n}: {body_n}")

        status_n_minus_1, body_n_minus_1 = sse_call(
            base_url,
            f"/api/v1/conversations/{conversation_id}/messages",
            user.token,
            {"content": "x" * (max_length - 1)},
            hold_seconds=0.3,
        )
        if status_n_minus_1 != 200:
            raise AssertionError(
                f"N-1 phải được chấp nhận (200) nhưng nhận {status_n_minus_1}: {body_n_minus_1}"
            )

        results.add(
            "TC15",
            "PASS",
            f"N={max_length}: N-1={status_n_minus_1}, N={status_n}, "
            f"N+1={status_n_plus_1} (bị từ chối, không lưu message)",
        )
    except Exception as exc:  # noqa: BLE001
        results.add("TC15", "FAIL", str(exc))
    finally:
        if conversation_id:
            delete_conversation(base_url, user, conversation_id)


def test_tc18(
    base_url: str,
    normal_user: TestUser,
    admin_username: str,
    admin_password: str,
    results: Results,
) -> None:
    print("\n[TC18] User thường gọi API admin (GET /api/v1/stats)")
    try:
        status, body = json_call(
            base_url,
            "GET",
            "/api/v1/stats",
            token=normal_user.token,
        )
        if status != 403:
            raise AssertionError(f"Phải trả 403 nhưng nhận {status}: {body}")

        body_text = json.dumps(body, ensure_ascii=False)
        leaked_fields = [
            field
            for field in (
                "total_users",
                "total_knowledge_bases",
                "total_documents",
                "total_conversations",
                "total_messages",
            )
            if field in body_text
        ]
        if leaked_fields:
            raise AssertionError(f"Response 403 làm lộ dữ liệu thống kê: {leaked_fields}")

        detail = body.get("detail") if isinstance(body, dict) else None
        if not detail:
            raise AssertionError(f"Response 403 không có thông báo rõ ràng: {body}")

        admin_note = "admin: không kiểm tra (đăng nhập admin thất bại)"
        admin_token = login(base_url, admin_username, admin_password)
        if admin_token:
            admin_status, admin_body = json_call(
                base_url,
                "GET",
                "/api/v1/stats",
                token=admin_token,
            )
            if admin_status != 200 or not isinstance(admin_body, dict):
                raise AssertionError(
                    f"Admin gọi /stats phải trả 200 nhưng nhận {admin_status}: {admin_body}"
                )
            missing = [
                field
                for field in ("total_users", "total_knowledge_bases", "total_documents")
                if field not in admin_body
            ]
            if missing:
                raise AssertionError(f"Admin /stats thiếu field: {missing}")
            admin_note = "admin: gọi /stats = 200 (đối chứng)"

        results.add(
            "TC18",
            "PASS",
            f"user thường nhận 403, không lộ field thống kê; {admin_note}",
        )
    except Exception as exc:  # noqa: BLE001
        results.add("TC18", "FAIL", str(exc))


def test_tc19(
    base_url: str,
    user_a: TestUser,
    user_b: TestUser,
    results: Results,
) -> None:
    print("\n[TC19] User B truy cập hội thoại của user A")
    conversation_id: str | None = None
    try:
        conversation_id = create_conversation(base_url, user_a, "TC19 - private conversation")

        # Tạo một message thật trong hội thoại của user_a.
        marker = f"TC19_SECRET_{uuid.uuid4().hex}"
        status_send, body_send = sse_call(
            base_url,
            f"/api/v1/conversations/{conversation_id}/messages",
            user_a.token,
            {"content": marker},
            hold_seconds=4.0,
        )
        if status_send != 200:
            raise AssertionError(
                f"User A gửi message phải trả 200 nhưng nhận {status_send}: {body_send}"
            )

        message = wait_for_message(base_url, user_a, conversation_id, marker, timeout_seconds=20)
        if message is None:
            raise AssertionError(
                "Không thấy message của user_a được lưu sau khi gửi. "
                "Kiểm tra backend/DB trước khi chạy lại test."
            )

        # Đối chứng: chủ sở hữu đọc được.
        status_owner, body_owner = list_messages(base_url, user_a, conversation_id)
        if status_owner != 200 or not isinstance(body_owner, list):
            raise AssertionError(
                f"User A phải đọc được messages (200) nhưng nhận {status_owner}: {body_owner}"
            )

        # user_b phải bị chặn 403.
        status_other, body_other = list_messages(base_url, user_b, conversation_id)
        if status_other != 403:
            raise AssertionError(
                f"User B phải nhận 403 nhưng nhận {status_other}: {body_other}"
            )

        body_text = json.dumps(body_other, ensure_ascii=False)
        if marker in body_text:
            raise AssertionError("Response 403 làm lộ nội dung message của user A")
        if '"content"' in body_text or '"sender_type"' in body_text:
            raise AssertionError("Response 403 làm lộ cấu trúc message của user A")

        detail = body_other.get("detail") if isinstance(body_other, dict) else None
        if not detail:
            raise AssertionError(f"Response 403 không có thông báo rõ ràng: {body_other}")

        results.add(
            "TC19",
            "PASS",
            "User A đọc được hội thoại của mình (200); "
            "User B nhận 403, không lộ nội dung message",
        )
    except Exception as exc:  # noqa: BLE001
        results.add("TC19", "FAIL", str(exc))
    finally:
        if conversation_id:
            delete_conversation(base_url, user_a, conversation_id)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Test TC15, TC18, TC19 cho RAG Chatbot Backend.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Địa chỉ backend (mặc định: http://127.0.0.1:8000)",
    )
    parser.add_argument("--admin-username", default="admin", help="Username admin (mặc định: admin)")
    parser.add_argument("--admin-password", default="admin123", help="Password admin (mặc định: admin123)")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = Results()

    print(f"Backend: {base_url}")
    try:
        health_status, health_body = json_call(base_url, "GET", "/health", timeout=10)
        if health_status != 200:
            raise RuntimeError(f"Health check thất bại: {health_status} {health_body}")
    except Exception as exc:  # noqa: BLE001
        print(f"Không kết nối được backend: {exc}", file=sys.stderr)
        return 2

    print("Tạo user test...")
    user_a: TestUser | None = None
    user_b: TestUser | None = None
    try:
        user_a = register_user(base_url, "tc_user_a")
        user_b = register_user(base_url, "tc_user_b")
        print(f"  user_a = {user_a.username}")
        print(f"  user_b = {user_b.username}")
    except Exception as exc:  # noqa: BLE001
        print(f"Không tạo được user test: {exc}", file=sys.stderr)
        return 2

    test_tc15(base_url, user_a, results)
    test_tc18(base_url, user_b, args.admin_username, args.admin_password, results)
    test_tc19(base_url, user_a, user_b, results)

    # Dọn dẹp user test nếu đăng nhập được admin (xóa user sẽ cascade conversations).
    admin_token = login(base_url, args.admin_username, args.admin_password)
    if admin_token:
        for user in (user_a, user_b):
            json_call(
                base_url,
                "DELETE",
                f"/api/v1/users/{user.id}",
                token=admin_token,
            )
        print("\nĐã dọn dẹp user test.")
    else:
        print(
            f"\nKhông đăng nhập được admin ({args.admin_username}) nên giữ lại user test: "
            f"{user_a.username}, {user_b.username}"
        )

    print("\n===== KẾT QUẢ =====")
    for tc, status, detail in results.items:
        print(f"{tc}: {status} - {detail}")

    if results.passed():
        print("\nTẤT CẢ TEST CASE ĐỀU PASS.")
        return 0

    print("\nCÓ TEST CASE FAIL. Xem chi tiết phía trên.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
