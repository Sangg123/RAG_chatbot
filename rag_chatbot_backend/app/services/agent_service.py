from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import AsyncIterator, Sequence

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_intent import OrderIntentResult
from app.services.rag_service import generate_chat_response, stream_chat_contents
from app.services.tool_service import (
    build_forced_tool_config,
    build_tools,
    execute_tool,
    tool_call_label,
)


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Bạn là trợ lý chăm sóc khách hàng của một doanh nghiệp bán lẻ trực tuyến.

Bạn có các công cụ tra cứu đơn hàng trong cơ sở dữ liệu:
- lookup_order: tra cứu một đơn hàng theo mã đơn.
- list_orders_by_phone: liệt kê các đơn hàng gần đây theo số điện thoại.

Quy tắc bắt buộc:
1. Bạn chỉ được tra cứu đơn hàng thuộc tài khoản đang đăng nhập. Không bao giờ hướng dẫn khách tra cứu đơn của người khác, không yêu cầu mật khẩu/OTP.
2. Khi khách hỏi về một đơn hàng cụ thể hoặc cung cấp mã đơn, phải gọi lookup_order trước khi trả lời. Không được bịa thông tin đơn hàng.
3. Khi khách cung cấp số điện thoại và hỏi các đơn hàng của mình, gọi list_orders_by_phone.
4. Nếu tool trả về found=false, trả lời rằng không tìm thấy đơn thuộc tài khoản đang đăng nhập và đề nghị khách kiểm tra lại mã đơn/SĐT hoặc đăng nhập đúng tài khoản. Không suy đoán, không xác nhận đơn có tồn tại ở tài khoản khác.
5. Nếu câu hỏi không liên quan đơn hàng, trả lời dựa trên ngữ cảnh tài liệu được cung cấp. Nếu ngữ cảnh không đủ, nói rõ là chưa có đủ thông tin.
6. Trả lời bằng tiếng Việt, ngắn gọn, thân thiện. Không hiển thị JSON thô hay tên hàm kỹ thuật cho khách.
"""


@dataclass
class AgentEvent:
    event: str
    data: dict


def _build_contents(
    question: str,
    context_chunks: Sequence[str],
    history: Sequence[tuple[str, str]],
) -> list[types.Content]:
    contents: list[types.Content] = []

    for sender_type, content in history:
        text = (content or "").strip()
        if not text:
            continue
        role = "user" if sender_type == "USER" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=text)])
        )

    if context_chunks:
        context = "\n\n".join(
            f"[Tài liệu {index + 1}]\n{chunk}"
            for index, chunk in enumerate(context_chunks)
        )
    else:
        context = "(Không có đoạn tài liệu nội bộ nào liên quan.)"

    prompt = (
        f"Ngữ cảnh tài liệu tham khảo:\n{context}\n\n"
        f"Câu hỏi của khách:\n{question}\n\n"
        "Hãy trả lời câu hỏi trên. Nếu cần tra cứu đơn hàng, hãy gọi công cụ "
        "trước khi trả lời."
    )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    )
    return contents


def _build_config(intent: OrderIntentResult) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=build_tools(),
        temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        tool_config=build_forced_tool_config(intent),
    )


def _final_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    )


def _synthetic_function_call(
    intent: OrderIntentResult,
) -> types.FunctionCall | None:
    if intent.forced_tool == "lookup_order" and intent.order_code:
        return types.FunctionCall(
            name="lookup_order", args={"order_code": intent.order_code}
        )
    if intent.forced_tool == "list_orders_by_phone" and intent.phone:
        return types.FunctionCall(
            name="list_orders_by_phone", args={"phone": intent.phone}
        )
    return None


async def stream_order_agent(
    db: AsyncSession,
    question: str,
    context_chunks: Sequence[str],
    history: Sequence[tuple[str, str]],
    intent: OrderIntentResult,
    current_user_id: uuid.UUID,
) -> AsyncIterator[AgentEvent]:
    """Chạy một lượt function calling rồi stream câu trả lời cuối.

    Luồng:
      1. Gọi Gemini kèm tool declarations (ép gọi nếu guardrail yêu cầu).
      2. Nếu có function_call: query PostgreSQL và gửi function_response lại.
      3. Gọi Gemini lần cuối không kèm tool và stream câu trả lời.
    """
    contents = _build_contents(question, context_chunks, history)
    response = await generate_chat_response(contents, _build_config(intent))
    function_calls = list(response.function_calls or [])

    if not function_calls:
        synthetic = _synthetic_function_call(intent)
        if synthetic is None:
            text = (response.text or "").strip()
            if text:
                yield AgentEvent("token", {"text": text})
            return

        # Guardrail đã xác định rõ đây là tra cứu đơn nhưng model không gọi
        # tool (hiếm). Thực hiện fallback để không bỏ sót yêu cầu của khách.
        logger.warning(
            "Gemini did not call %s despite forced tool config; using fallback",
            intent.forced_tool,
        )
        function_calls = [synthetic]
        contents.append(
            types.Content(
                role="model",
                parts=[types.Part(function_call=synthetic)],
            )
        )
    else:
        if not response.candidates or not response.candidates[0].content:
            raise RuntimeError("Gemini returned a function call without content")
        contents.append(response.candidates[0].content)

    function_response_parts: list[types.Part] = []

    for function_call in function_calls:
        call_id = str(uuid.uuid4())
        name = function_call.name or ""
        arguments = dict(function_call.args or {})

        # Nếu Gemini bỏ sót tham số đã được guardrail xác định, điền lại để
        # tool vẫn tra đúng đơn thay vì trả lỗi "mã không hợp lệ".
        if (
            intent.forced_tool == "lookup_order"
            and name == "lookup_order"
            and not arguments.get("order_code")
            and intent.order_code
        ):
            arguments["order_code"] = intent.order_code
        if (
            intent.forced_tool == "list_orders_by_phone"
            and name == "list_orders_by_phone"
            and not arguments.get("phone")
            and intent.phone
        ):
            arguments["phone"] = intent.phone

        yield AgentEvent(
            "tool_call",
            {
                "id": call_id,
                "name": name,
                "arguments": arguments,
                "label": tool_call_label(name, arguments),
                "status": "running",
            },
        )

        started_at = time.perf_counter()
        status = "success"
        error_message: str | None = None
        try:
            result = await execute_tool(
                db,
                name,
                arguments,
                current_user_id=current_user_id,
            )
        except Exception as exc:  # noqa: BLE001 - trả lỗi cho model thay vì crash
            status = "error"
            error_message = str(exc)
            result = {"error": error_message}
            logger.exception("Tool %s failed", name)

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        yield AgentEvent(
            "tool_result",
            {
                "id": call_id,
                "name": name,
                "status": status,
                "result": result,
                "error": error_message,
                "duration_ms": duration_ms,
            },
        )

        function_response_parts.append(
            types.Part.from_function_response(name=name, response=result)
        )

    contents.append(
        types.Content(role="user", parts=function_response_parts)
    )

    final_text_parts: list[str] = []
    async for token in stream_chat_contents(contents, _final_config()):
        final_text_parts.append(token)
        yield AgentEvent("token", {"text": token})

    if not final_text_parts:
        yield AgentEvent(
            "token",
            {
                "text": (
                    "Xin lỗi, mình chưa thể tạo câu trả lời lúc này. "
                    "Bạn vui lòng thử lại sau ít phút nhé."
                )
            },
        )
