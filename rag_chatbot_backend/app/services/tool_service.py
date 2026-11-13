from __future__ import annotations

import uuid

from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order_intent import OrderIntentResult
from app.services.order_service import list_orders_by_phone, lookup_order


class ToolExecutionError(Exception):
    pass


def build_tools() -> list[types.Tool]:
    lookup_order_decl = types.FunctionDeclaration(
        name="lookup_order",
        description=(
            "Tra cứu thông tin chi tiết của một đơn hàng trong cơ sở dữ liệu "
            "theo mã đơn, chỉ trong phạm vi tài khoản đang đăng nhập. Dùng khi "
            "khách hỏi trạng thái, sản phẩm, thanh toán, vận chuyển, ngày giao "
            "hoặc muốn kiểm tra một đơn cụ thể. Đơn của người khác sẽ trả về "
            "found=false."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "order_code": types.Schema(
                    type=types.Type.STRING,
                    description="Mã đơn hàng cần tra cứu, ví dụ DH123.",
                )
            },
            required=["order_code"],
        ),
    )

    list_orders_decl = types.FunctionDeclaration(
        name="list_orders_by_phone",
        description=(
            "Liệt kê các đơn hàng gần đây theo số điện thoại, chỉ trong phạm vi "
            "tài khoản đang đăng nhập. Dùng khi khách cung cấp SĐT và hỏi các "
            "đơn hàng của mình. SĐT của người khác sẽ trả về found=false."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "phone": types.Schema(
                    type=types.Type.STRING,
                    description="Số điện thoại Việt Nam, ví dụ 0901234567.",
                ),
                "limit": types.Schema(
                    type=types.Type.INTEGER,
                    description="Số đơn tối đa cần lấy (1-10), mặc định 5.",
                ),
            },
            required=["phone"],
        ),
    )

    return [
        types.Tool(function_declarations=[lookup_order_decl, list_orders_decl])
    ]


def build_forced_tool_config(intent: OrderIntentResult) -> types.ToolConfig | None:
    if not intent.forced_tool:
        return None
    return types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode=types.FunctionCallingConfigMode.ANY,
            allowed_function_names=[intent.forced_tool],
        )
    )


def tool_call_label(name: str, arguments: dict | None) -> str:
    args = arguments or {}
    if name == "lookup_order":
        return f"Tra cứu đơn hàng {args.get('order_code', '')}".strip()
    if name == "list_orders_by_phone":
        return f"Tra cứu đơn theo SĐT {args.get('phone', '')}".strip()
    return name


async def execute_tool(
    db: AsyncSession,
    name: str,
    arguments: dict | None,
    *,
    current_user_id: uuid.UUID,
) -> dict:
    """Thực thi tool với user_id do backend cung cấp, không lấy từ AI."""
    args = arguments or {}

    if name == "lookup_order":
        return await lookup_order(
            db,
            args.get("order_code"),
            user_id=current_user_id,
        )

    if name == "list_orders_by_phone":
        return await list_orders_by_phone(
            db,
            args.get("phone"),
            user_id=current_user_id,
            limit=args.get("limit", 5),
        )

    raise ToolExecutionError(f"Công cụ không tồn tại: {name}")
