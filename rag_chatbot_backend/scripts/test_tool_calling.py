#!/usr/bin/env python3
"""Kiểm thử end-to-end AI tool calling và phân quyền đơn hàng.

Cách chạy (backend đang chạy ở http://127.0.0.1:8000):

    python scripts/test_tool_calling.py

Script dùng các tài khoản demo do migration tạo:
- nguyen.van.an / password123  -> sở hữu DH123, SĐT 0901234567
- tran.thi.binh / password123 -> sở hữu DH124, SĐT 0912345678

Các kịch bản kiểm tra:
1. Chủ đơn hỏi DH123 -> tool lookup_order trả found=true.
2. Chủ đơn hỏi DH124 của người khác -> tool trả found=false, không lộ PII.
3. Chủ đơn hỏi SĐT của mình -> tool list_orders_by_phone trả found=true.
4. Chủ đơn hỏi SĐT của người khác -> tool trả found=false.
5. Đăng nhập đúng chủ DH124 -> tra cứu được DH124.
6. Guardrail: câu có chữ "DH" nhưng không phải tra cứu đơn -> không gọi tool.

Mặc định script xóa các conversation tạo ra khi test để giữ DB sạch.
Giữ lại để xem trên UI:

    python scripts/test_tool_calling.py --keep-conversations
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def request_json(
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    payload: dict | None = None,
    timeout: int = 60,
) -> tuple[int, object]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
            return response.status, json.loads(body) if body.strip() else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(body) if body.strip() else None
        except json.JSONDecodeError:
            parsed = body
        return exc.code, parsed


def login(base_url: str, username: str, password: str) -> tuple[str, dict]:
    status, data = request_json(
        base_url,
        "POST",
        "/auth/login",
        payload={"username": username, "password": password},
    )
    if status == 200 and isinstance(data, dict):
        return str(data["access_token"]), data["user"]

    raise RuntimeError(
        f"Không đăng nhập được {username} (HTTP {status}): {data}. "
        "Hãy chạy `alembic upgrade head` để tạo tài khoản demo, "
        "hoặc kiểm tra lại username/password."
    )


@dataclass
class StreamResult:
    tokens: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    done: bool = False

    @property
    def answer(self) -> str:
        return "".join(self.tokens).strip()


def stream_chat(
    base_url: str,
    token: str,
    conversation_id: str,
    content: str,
    timeout: int = 240,
) -> StreamResult:
    request = urllib.request.Request(
        f"{base_url}/conversations/{conversation_id}/messages",
        data=json.dumps({"content": content}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    result = StreamResult()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        event_name = "message"
        data_lines: list[str] = []

        for raw_line in response:
            line = raw_line.decode("utf-8", "replace").rstrip("\r\n")

            if line == "":
                if data_lines:
                    data = "\n".join(data_lines)
                    if event_name == "token":
                        result.tokens.append(data)
                    elif event_name == "tool_call":
                        result.tool_calls.append(json.loads(data))
                    elif event_name == "tool_result":
                        result.tool_results.append(json.loads(data))
                    elif event_name == "error":
                        result.errors.append(data)
                    elif event_name == "done":
                        result.done = True
                event_name = "message"
                data_lines = []
                if result.done:
                    break
                continue

            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                value = line[len("data:") :]
                if value.startswith(" "):
                    value = value[1:]
                data_lines.append(value)

    return result


def create_conversation(base_url: str, token: str, title: str) -> str:
    status, data = request_json(
        base_url,
        "POST",
        "/conversations",
        token=token,
        payload={"title": title},
    )
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(f"Không tạo được conversation (HTTP {status}): {data}")
    return str(data["id"])


def delete_conversation(base_url: str, token: str, conversation_id: str) -> None:
    status, _ = request_json(
        base_url,
        "DELETE",
        f"/conversations/{conversation_id}",
        token=token,
    )
    if status not in (200, 204):
        print(
            f"[cleanup] Không xóa được conversation {conversation_id} "
            f"(HTTP {status})",
            file=sys.stderr,
        )


def last_bot_message(base_url: str, token: str, conversation_id: str) -> dict:
    status, data = request_json(
        base_url,
        "GET",
        f"/conversations/{conversation_id}/messages",
        token=token,
    )
    if status != 200 or not isinstance(data, list):
        raise RuntimeError(f"Không đọc được messages (HTTP {status}): {data}")
    for message in reversed(data):
        if message.get("sender_type") == "BOT":
            return message
    raise RuntimeError("Không tìm thấy message BOT sau khi chat")


def persisted_tool_calls(base_url: str, token: str, message_id: str) -> list[dict]:
    status, data = request_json(
        base_url,
        "GET",
        f"/messages/{message_id}/tool-calls",
        token=token,
    )
    if status != 200 or not isinstance(data, list):
        raise RuntimeError(
            f"Không đọc được tool calls đã lưu (HTTP {status}): {data}"
        )
    return data


def print_stream(label: str, result: StreamResult) -> None:
    for call in result.tool_calls:
        print(
            f"[{label}] tool_call: {call.get('name')} "
            f"{json.dumps(call.get('arguments'), ensure_ascii=False)}"
        )
    for item in result.tool_results:
        payload = item.get("result") or {}
        found = payload.get("found")
        print(
            f"[{label}] tool_result: {item.get('name')} "
            f"status={item.get('status')} found={found} "
            f"duration={item.get('duration_ms')}ms"
        )
    if result.answer:
        print(f"[{label}] answer: {result.answer[:500]}")
    for error in result.errors:
        print(f"[{label}] ERROR: {error}")


def assert_no_errors(label: str, result: StreamResult) -> None:
    if result.errors:
        raise AssertionError(f"{label}: SSE trả lỗi: {result.errors}")
    if not result.done:
        raise AssertionError(f"{label}: không nhận được event done")
    if not result.answer:
        raise AssertionError(f"{label}: không có nội dung trả lời")


def _tool_result(result: StreamResult, name: str) -> dict:
    for item in result.tool_results:
        if item.get("name") == name:
            return item
    raise AssertionError(f"Không thấy tool_result {name}")


def _ask(
    base_url: str,
    token: str,
    conversation_id: str,
    question: str,
    label: str,
) -> StreamResult:
    print(f"\n=== {label}: {question} ===")
    result = stream_chat(base_url, token, conversation_id, question)
    print_stream(label, result)
    assert_no_errors(label, result)
    return result


def test_allowed_order(
    base_url: str,
    token: str,
    order_code: str,
) -> str:
    conversation_id = create_conversation(
        base_url, token, f"Test quyền xem đơn {order_code}"
    )
    result = _ask(
        base_url,
        token,
        conversation_id,
        f"Đơn {order_code} đang ở đâu?",
        "owner-order",
    )

    names = [call.get("name") for call in result.tool_calls]
    if "lookup_order" not in names:
        raise AssertionError(
            f"owner-order: không thấy tool_call lookup_order (nhận được {names})"
        )

    item = _tool_result(result, "lookup_order")
    payload = item.get("result") or {}
    if item.get("status") != "success" or payload.get("found") is not True:
        raise AssertionError(
            "owner-order: chủ đơn phải tra cứu được đơn của mình"
        )

    bot_message = last_bot_message(base_url, token, conversation_id)
    saved = persisted_tool_calls(base_url, token, str(bot_message["id"]))
    print(f"[owner-order] persisted tool calls: {len(saved)}")
    if not any(item.get("tool_name") == "lookup_order" for item in saved):
        raise AssertionError(
            "owner-order: tool call lookup_order chưa được lưu vào message_tool_calls"
        )
    return conversation_id


def test_denied_order(
    base_url: str,
    token: str,
    other_order_code: str,
    forbidden_texts: list[str],
) -> str:
    conversation_id = create_conversation(
        base_url, token, f"Test từ chối đơn {other_order_code}"
    )
    result = _ask(
        base_url,
        token,
        conversation_id,
        f"Đơn {other_order_code} đang ở đâu?",
        "denied-order",
    )

    names = [call.get("name") for call in result.tool_calls]
    if "lookup_order" not in names:
        raise AssertionError(
            f"denied-order: không thấy tool_call lookup_order (nhận được {names})"
        )

    item = _tool_result(result, "lookup_order")
    payload = item.get("result") or {}
    if item.get("status") != "success" or payload.get("found") is not False:
        raise AssertionError(
            "denied-order: đơn của người khác phải trả found=false"
        )

    forbidden_keys = {
        "customer_name",
        "customer_phone_masked",
        "shipping_address",
        "items",
        "item_count",
        "subtotal",
        "total_amount",
        "payment_status",
        "tracking_code",
        "ordered_at",
        "delivered_at",
        "carrier",
    }
    leaked_keys = forbidden_keys.intersection(payload.keys())
    if leaked_keys:
        raise AssertionError(
            f"denied-order: kết quả bị từ chối vẫn lộ dữ liệu: {sorted(leaked_keys)}"
        )

    answer_lower = result.answer.lower()
    refusal_phrases = (
        "không tìm thấy",
        "không thuộc",
        "không có quyền",
        "đăng nhập đúng",
        "không tồn tại",
    )
    if not any(phrase in answer_lower for phrase in refusal_phrases):
        raise AssertionError(
            "denied-order: câu trả lời không thể hiện việc từ chối tra cứu"
        )

    for text in forbidden_texts:
        if text and text.lower() in answer_lower:
            raise AssertionError(
                f"denied-order: câu trả lời bị lộ thông tin '{text}'"
            )

    print("[denied-order] OK: đã từ chối và không lộ dữ liệu.")
    return conversation_id


def test_allowed_phone(
    base_url: str,
    token: str,
    phone: str,
) -> str:
    conversation_id = create_conversation(
        base_url, token, "Test quyền xem đơn theo SĐT"
    )
    result = _ask(
        base_url,
        token,
        conversation_id,
        f"SĐT {phone} có đơn nào chưa giao?",
        "owner-phone",
    )

    names = [call.get("name") for call in result.tool_calls]
    if "list_orders_by_phone" not in names:
        raise AssertionError(
            "owner-phone: không thấy tool_call list_orders_by_phone "
            f"(nhận được {names})"
        )

    item = _tool_result(result, "list_orders_by_phone")
    payload = item.get("result") or {}
    if (
        item.get("status") != "success"
        or payload.get("found") is not True
        or int(payload.get("count") or 0) < 1
    ):
        raise AssertionError(
            "owner-phone: chủ đơn phải tra cứu được đơn theo SĐT của mình"
        )
    return conversation_id


def test_denied_phone(
    base_url: str,
    token: str,
    other_phone: str,
) -> str:
    conversation_id = create_conversation(
        base_url, token, "Test từ chối tra cứu SĐT người khác"
    )
    result = _ask(
        base_url,
        token,
        conversation_id,
        f"SĐT {other_phone} có đơn nào chưa giao?",
        "denied-phone",
    )

    names = [call.get("name") for call in result.tool_calls]
    if "list_orders_by_phone" not in names:
        raise AssertionError(
            "denied-phone: không thấy tool_call list_orders_by_phone "
            f"(nhận được {names})"
        )

    item = _tool_result(result, "list_orders_by_phone")
    payload = item.get("result") or {}
    if item.get("status") != "success" or payload.get("found") is not False:
        raise AssertionError(
            "denied-phone: SĐT của người khác phải trả found=false"
        )
    if "orders" in payload:
        raise AssertionError(
            "denied-phone: kết quả bị từ chối vẫn chứa danh sách đơn"
        )

    answer_lower = result.answer.lower()
    refusal_phrases = (
        "không tìm thấy",
        "không thuộc",
        "không có quyền",
        "đăng nhập đúng",
        "không tồn tại",
    )
    if not any(phrase in answer_lower for phrase in refusal_phrases):
        raise AssertionError(
            "denied-phone: câu trả lời không thể hiện việc từ chối tra cứu"
        )
    print("[denied-phone] OK: đã từ chối và không lộ danh sách đơn.")
    return conversation_id


def test_other_owner(
    base_url: str,
    other_token: str,
    other_order_code: str,
) -> str:
    conversation_id = create_conversation(
        base_url, other_token, f"Test chủ đơn {other_order_code}"
    )
    result = _ask(
        base_url,
        other_token,
        conversation_id,
        f"Đơn {other_order_code} đang ở đâu?",
        "other-owner",
    )

    item = _tool_result(result, "lookup_order")
    payload = item.get("result") or {}
    if item.get("status") != "success" or payload.get("found") is not True:
        raise AssertionError(
            "other-owner: đăng nhập đúng chủ đơn phải tra cứu được đơn"
        )
    print("[other-owner] OK: đúng chủ sở hữu tra cứu được đơn.")
    return conversation_id


def test_guardrail(base_url: str, token: str) -> str:
    conversation_id = create_conversation(base_url, token, "Test guardrail DH")
    result = _ask(
        base_url,
        token,
        conversation_id,
        "Sản phẩm DH có gì đặc biệt?",
        "guardrail",
    )

    if result.tool_calls:
        raise AssertionError(
            "guardrail: chữ DH xuất hiện tình cờ nhưng AI vẫn gọi tool: "
            f"{[call.get('name') for call in result.tool_calls]}"
        )
    print("[guardrail] OK: không gọi tool đơn hàng.")
    return conversation_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test end-to-end AI tool calling và phân quyền đơn hàng"
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000/api/v1",
        help="Base URL của API (mặc định: http://127.0.0.1:8000/api/v1)",
    )
    parser.add_argument(
        "--owner-username",
        default="nguyen.van.an",
        help="Tài khoản chủ đơn demo",
    )
    parser.add_argument(
        "--owner-password",
        default="password123",
        help="Mật khẩu tài khoản chủ đơn",
    )
    parser.add_argument(
        "--other-username",
        default="tran.thi.binh",
        help="Tài khoản của người khác",
    )
    parser.add_argument(
        "--other-password",
        default="password123",
        help="Mật khẩu tài khoản người khác",
    )
    parser.add_argument(
        "--order-code",
        default="DH123",
        help="Mã đơn thuộc tài khoản chủ",
    )
    parser.add_argument(
        "--other-order-code",
        default="DH124",
        help="Mã đơn thuộc tài khoản người khác",
    )
    parser.add_argument(
        "--phone",
        default="0901234567",
        help="SĐT thuộc tài khoản chủ",
    )
    parser.add_argument(
        "--other-phone",
        default="0912345678",
        help="SĐT thuộc tài khoản người khác",
    )
    parser.add_argument(
        "--forbidden-text",
        default="Trần Thị Bình,Đà Nẵng",
        help="Chuỗi không được xuất hiện trong câu trả lời bị từ chối",
    )
    parser.add_argument(
        "--skip-guardrail",
        action="store_true",
        help="Bỏ qua test chữ DH xuất hiện tình cờ",
    )
    parser.add_argument(
        "--keep-conversations",
        action="store_true",
        help="Không xóa conversation tạo ra khi test",
    )
    args = parser.parse_args()

    forbidden_texts = [
        item.strip() for item in args.forbidden_text.split(",") if item.strip()
    ]

    print(f"Backend: {args.base_url}")
    owner_token, owner = login(
        args.base_url, args.owner_username, args.owner_password
    )
    other_token, other = login(
        args.base_url, args.other_username, args.other_password
    )
    print(f"Owner: {owner.get('username')} ({owner.get('role')})")
    print(f"Other: {other.get('username')} ({other.get('role')})")

    created: list[tuple[str, str]] = []
    try:
        created.append(
            (
                owner_token,
                test_allowed_order(args.base_url, owner_token, args.order_code),
            )
        )
        created.append(
            (
                owner_token,
                test_denied_order(
                    args.base_url,
                    owner_token,
                    args.other_order_code,
                    forbidden_texts,
                ),
            )
        )
        created.append(
            (
                owner_token,
                test_allowed_phone(args.base_url, owner_token, args.phone),
            )
        )
        created.append(
            (
                owner_token,
                test_denied_phone(args.base_url, owner_token, args.other_phone),
            )
        )
        created.append(
            (
                other_token,
                test_other_owner(
                    args.base_url,
                    other_token,
                    args.other_order_code,
                ),
            )
        )
        if not args.skip_guardrail:
            created.append(
                (
                    owner_token,
                    test_guardrail(args.base_url, owner_token),
                )
            )
    finally:
        if args.keep_conversations:
            print("\n[cleanup] Giữ lại các conversation để xem trên UI.")
        else:
            for token, conversation_id in created:
                delete_conversation(args.base_url, token, conversation_id)
            print(f"\n[cleanup] Đã xóa {len(created)} conversation test.")

    print("\nTẤT CẢ TEST TOOL CALLING + PHÂN QUYỀN ĐỀU PASS.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"\nTEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001 - script test in lỗi rõ ràng
        print(f"\nTEST ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
