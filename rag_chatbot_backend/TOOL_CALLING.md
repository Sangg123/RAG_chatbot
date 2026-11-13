# AI Tool Calling tra cứu đơn hàng

Tài liệu này mô tả phần mở rộng **Gemini function calling** của RAG Chatbot:
cho phép AI đọc dữ liệu đơn hàng có cấu trúc từ PostgreSQL thay vì nhồi
đơn hàng vào tài liệu RAG.

## 1. Vì sao cần tool calling?

RAG truyền thống phù hợp với kiến thức dạng văn bản (chính sách, hướng dẫn,
FAQ). Dữ liệu đơn hàng lại thay đổi liên tục và cần tra cứu chính xác theo khóa
(mã đơn hoặc số điện thoại). Nếu đưa đơn hàng vào vector store:

- Dữ liệu bị trùng lặp, lạc hậu mỗi khi đơn thay đổi trạng thái.
- Không đảm bảo tìm đúng đơn theo mã.
- AI có thể trả lời sai thông tin thanh toán/ngày giao.

Tool calling giải quyết bằng cách để AI quyết định **gọi hàm**, backend thực thi
SQL trên bảng `orders`, rồi gửi kết quả lại cho AI viết câu trả lời.

## 2. Kiến trúc

```
Người dùng
   │  "Đơn DH123 đang ở đâu?"
   ▼
FastAPI POST /conversations/{id}/messages (SSE)
   │
   ▼
order_intent.detect_order_intent()
   │  phát hiện mã DH + ngữ cảnh đơn hàng
   ▼
agent_service.stream_order_agent()
   │
   ├─ 1. Gemini + tool declarations
   │       tool_config = ANY (lookup_order)
   │       Gemini trả về function_call(name="lookup_order", args={"order_code":"DH123"})
   │
   ├─ 2. tool_service.execute_tool()
   │       backend tự gắn current_user.id từ JWT
   │       SELECT * FROM orders
   │       WHERE order_code = 'DH123' AND user_id = current_user.id
   │       SELECT * FROM order_items WHERE order_id = ...
   │
   ├─ 3. Gửi function_response(result) lại Gemini
   │       Gemini viết câu trả lời tiếng Việt từ dữ liệu thật
   │
   └─ 4. Stream token + lưu message_tool_calls
   ▼
Frontend hiển thị câu trả lời + chip "Đã tra cứu: Đơn DH123"
```

Điểm quan trọng: **AI không tự viết SQL**. AI chỉ chọn tool và truyền tham số;
backend kiểm soát câu query, chuẩn hóa mã đơn/SĐT, **luôn lọc theo user đang
đăng nhập** và che bớt PII.

## 3. Guardrail chống gọi tool sai

Chỉ bật tool đơn hàng khi câu hỏi thực sự liên quan đến đơn hàng. Nếu chữ `DH`
xuất hiện tình cờ, chatbot giữ nguyên luồng RAG tài liệu.

| Câu hỏi | Kết quả | Lý do |
|---|---|---|
| `Đơn DH123 đang ở đâu?` | Gọi `lookup_order` | Có mã đơn + từ khóa đơn hàng |
| `DH123` | Gọi `lookup_order` | Tin nhắn chỉ gồm mã đơn |
| `Mã đơn DH-123 giao chưa?` | Gọi `lookup_order` | Chuẩn hóa `DH-123` → `DH123` |
| `SĐT 0901234567 có đơn nào chưa giao?` | Gọi `list_orders_by_phone` | Có SĐT + ngữ cảnh đơn |
| `Sản phẩm DH có gì đặc biệt?` | Không gọi tool, dùng RAG | `DH` không phải mã đơn |
| `DH123 có gì đặc biệt?` | Không gọi tool, dùng RAG | Có mã nhưng thiếu ngữ cảnh đơn hàng |
| `Chính sách đổi trả thế nào?` | Không gọi tool, dùng RAG | Không liên quan đơn cụ thể |
| `Đơn hàng của tôi đâu rồi?` | Bật tool ở chế độ AUTO | Có ngữ cảnh đơn nhưng chưa có mã/SĐT; AI sẽ hỏi lại |

Guardrail nằm trong `app/services/order_intent.py`, có unit test tại
`tests/test_order_intent.py`.

## 3.1. Phân quyền đơn hàng (chống lộ thông tin khách khác)

Mỗi đơn hàng có cột `orders.user_id` tham chiếu `users.id`. Khi khách chat:

1. Backend lấy user từ JWT (`current_user`) ở endpoint chat.
2. Backend truyền `current_user.id` vào tool, **không cho AI truyền `user_id`**.
3. SQL luôn có điều kiện `orders.user_id = current_user.id`.
4. Nếu mã đơn/SĐT tồn tại nhưng thuộc người khác, tool trả `found=false` với
   thông báo chung; không trả tên, địa chỉ, sản phẩm, thanh toán, vận đơn.
5. Không phân biệt “không tồn tại” với “không thuộc tài khoản” để tránh dò mã
   đơn/SĐT.

Ví dụ:

| Tài khoản đang đăng nhập | Câu hỏi | Kết quả |
|---|---|---|
| `nguyen.van.an` (chủ DH123) | `Đơn DH123 đang ở đâu?` | Trả dữ liệu DH123 |
| `nguyen.van.an` | `Đơn DH124 đang ở đâu?` | `found=false`, từ chối |
| `nguyen.van.an` | `SĐT 0901234567 có đơn nào chưa giao?` | Trả DH123 |
| `nguyen.van.an` | `SĐT 0912345678 có đơn nào chưa giao?` | `found=false`, từ chối |
| `tran.thi.binh` (chủ DH124) | `Đơn DH124 đang ở đâu?` | Trả dữ liệu DH124 |
| `admin` | `Đơn DH123 đang ở đâu?` | `found=false` (chat khách hàng không bypass quyền) |

Tài khoản demo (mật khẩu `password123`):

| Username | Sở hữu | SĐT |
|---|---|---|
| `nguyen.van.an` | `DH123` | `0901234567` |
| `tran.thi.binh` | `DH124` | `0912345678` |
| `le.hoang.cuong` | `DH125` | `0987654321` |
| `pham.thu.dung` | `DH126` | `0909876543` |
| `hoang.van.em` | `DH127` | `0934567890` |
| `vu.thi.lan` | `DH1001` | `0945678901` |

> Đây là tài khoản giả lập phục vụ demo. Khi triển khai thật phải xóa hoặc vô
> hiệu hóa các tài khoản này và đổi mật khẩu admin.

## 4. Hai tool

### `lookup_order`

- Input từ AI: `order_code` (string, bắt buộc). `user_id` do backend tự gắn.
- Backend chuẩn hóa: `dh 123`, `DH-123`, `123` → `DH123`.
- Chỉ trả dữ liệu nếu `orders.user_id = current_user.id`.
- Output: trạng thái, tên/địa chỉ khách, SĐT đã che, sản phẩm, số lượng,
  đơn giá, tổng tiền, phương thức thanh toán, đơn vị vận chuyển, mã vận đơn,
  ngày đặt, ngày giao dự kiến/ngày giao thực tế.
- Không tìm thấy hoặc không thuộc tài khoản → `found=false` + thông báo chung.

### `list_orders_by_phone`

- Input từ AI: `phone` (string, bắt buộc), `limit` (int, tùy chọn 1–10).
  `user_id` do backend tự gắn.
- Backend chuẩn hóa `+84 901 234 567` → `0901234567`.
- Chỉ trả đơn có `orders.user_id = current_user.id` và SĐT khớp.
- Output: tối đa 10 đơn gần nhất kèm trạng thái, tổng tiền, hãng vận chuyển,
  mã vận đơn, ngày giao.
- SĐT không thuộc tài khoản → `found=false`, không trả danh sách đơn.

Khai báo tool nằm trong `app/services/tool_service.py`.

## 5. Cơ sở dữ liệu

Ba bảng mới (migration `20261117_000005`):

| Bảng | Vai trò |
|---|---|
| `orders` | Thông tin đơn hàng; `user_id` FK → `users.id` |
| `order_items` | Sản phẩm trong đơn |
| `message_tool_calls` | Audit log tool name, arguments, result, status, duration_ms |

Migration `20261117_000006` bổ sung `orders.user_id`, index/FK, gắn 6 đơn mẫu
với đúng tài khoản demo và tạo các tài khoản khách hàng demo.

Đơn hàng mẫu:

| Mã | Trạng thái | SĐT | Tài khoản sở hữu |
|---|---|---|---|
| `DH123` | Đang giao hàng | `0901234567` | `nguyen.van.an` |
| `DH124` | Đã giao hàng | `0912345678` | `tran.thi.binh` |
| `DH125` | Chờ xác nhận | `0987654321` | `le.hoang.cuong` |
| `DH126` | Đã hủy | `0909876543` | `pham.thu.dung` |
| `DH127` | Đã xác nhận | `0934567890` | `hoang.van.em` |
| `DH1001` | Đang giao hàng | `0945678901` | `vu.thi.lan` |

## 6. API và SSE

`POST /api/v1/conversations/{id}/messages` trả về SSE:

```text
event: tool_call
data: {"id":"...","name":"lookup_order","arguments":{"order_code":"DH123"},"label":"Tra cứu đơn hàng DH123","status":"running"}

event: tool_result
data: {"id":"...","name":"lookup_order","status":"success","result":{"found":true,"order_code":"DH123",...},"error":null,"duration_ms":12}

event: token
data: Chào bạn, đơn hàng DH123 ...

event: done
data: [DONE]
```

Khi đơn không thuộc tài khoản, `tool_result` chỉ còn thông tin từ chối, không
có tên/địa chỉ/sản phẩm:

```json
{
  "found": false,
  "order_code": "DH124",
  "message": "Không tìm thấy đơn hàng này trong tài khoản đang đăng nhập..."
}
```

Lịch sử tool call sau khi reload:

```http
GET /api/v1/messages/{message_id}/tool-calls
```

Frontend hiển thị một chip dưới câu trả lời của bot. Bấm vào chip để xem
arguments/result/status/duration phục vụ demo kỹ thuật.

## 7. Cách chạy

### Cập nhật database

```bash
cd rag_chatbot_backend
alembic upgrade head
```

Lệnh này tạo bảng, seed 6 đơn hàng mẫu, gắn chủ sở hữu và tạo tài khoản demo.
Với database mới hoàn toàn có thể chạy `database/01_create_tables.sql` +
`database/02_seed_data.sql`.

### Unit test guardrail

```bash
cd rag_chatbot_backend
python -m unittest tests.test_order_intent -v
```

### Test end-to-end

```bash
# Terminal 1
cd rag_chatbot_backend
uvicorn app.main:app --reload

# Terminal 2
cd rag_chatbot_backend
python scripts/test_tool_calling.py
```

Script đăng nhập hai tài khoản demo và kiểm tra:

- Chủ `DH123` tra cứu được đơn của mình, tool call được lưu DB.
- Chủ `DH123` hỏi `DH124` của người khác → `found=false`, không lộ PII.
- Chủ `DH123` tra cứu đúng SĐT của mình → có đơn.
- Chủ `DH123` hỏi SĐT của người khác → `found=false`.
- Đăng nhập `tran.thi.binh` → tra cứu được `DH124`.
- Guardrail: `Sản phẩm DH có gì đặc biệt?` không gọi tool.

Script tự xóa conversation test sau khi chạy (trừ khi dùng
`--keep-conversations`).

## 8. Kịch bản demo 5 phút

1. Đăng nhập `nguyen.van.an` / `password123`, hỏi `Đơn DH123 đang ở đâu?`.
2. Chỉ vào chip **Đã tra cứu: Đơn DH123**, mở chi tiết để thấy
   `function_call` + kết quả SQL.
3. Vẫn tài khoản đó, hỏi `Đơn DH124 đang ở đâu?` → chatbot từ chối vì DH124
   thuộc `tran.thi.binh`, không lộ tên/địa chỉ/sản phẩm.
4. Đăng nhập `tran.thi.binh` / `password123`, hỏi `Đơn DH124 đang ở đâu?` →
   tra cứu được đơn của chính mình.
5. Hỏi `SĐT 0901234567 có đơn nào chưa giao?` khi đang là `nguyen.van.an` để
   demo tool thứ hai; thử SĐT `0912345678` để thấy bị từ chối.
6. Hỏi `Sản phẩm DH có gì đặc biệt?` để chứng minh guardrail: không gọi tool,
   chatbot trả lời bằng RAG tài liệu.
7. Reload trang, mở lại hội thoại: chip tool call vẫn còn nhờ dữ liệu trong
   `message_tool_calls`.

## 9. Câu hỏi bảo vệ gợi ý

- **Vì sao không đưa đơn hàng vào RAG?** Vì đơn hàng là dữ liệu có cấu trúc,
  thay đổi liên tục; tool calling đảm bảo tra cứu đúng theo khóa và luôn là dữ
  liệu hiện tại.
- **AI có tự viết SQL không?** Không. AI chỉ sinh `function_call` với tham số;
  backend dùng ORM/SQL cố định, có chuẩn hóa và kiểm tra đầu vào.
- **Làm sao tránh AI gọi tool bừa?** Có guardrail ý định: chỉ bật tool khi có
  mã đơn/SĐT kèm ngữ cảnh đơn hàng; trường hợp mơ hồ dùng RAG.
- **Làm sao chống lộ đơn của khách khác?** Mỗi đơn có `user_id`; backend tự
  gắn user từ JWT vào truy vấn, AI không được truyền `user_id`. Đơn/SĐT của
  người khác trả `found=false` và không kèm PII.
- **Nếu AI bị prompt injection bảo “bỏ qua kiểm tra quyền” thì sao?** Tool
  không có tham số `user_id` và không có tool “lấy tất cả đơn”, nên model không
  thể thay đổi phạm vi truy vấn.
- **Tool call có được lưu không?** Có, bảng `message_tool_calls` lưu
  arguments/result/status/duration để audit và hiển thị lại sau reload.
- **Nếu Gemini không gọi tool dù đã ép?** Có fallback thực thi tool trực tiếp
  theo mã/SĐT guardrail đã phát hiện, sau đó vẫn để Gemini viết câu trả lời.

## 10. Hạn chế và hướng phát triển

- Chưa có tool ghi dữ liệu (hủy đơn, đổi địa chỉ) vì cần xác thực danh tính.
- Tài khoản demo có mật khẩu công khai; phải xóa/vô hiệu hóa khi triển khai thật.
- Chưa có OTP/2FA cho các thao tác xem thông tin nhạy cảm; hiện dựa vào đăng
  nhập tài khoản và kiểm tra `user_id`.
- Có thể bổ sung tool `check_stock`, `create_return_request`, `track_shipment`.
- Có thể thêm evaluation tự động cho độ chính xác tool selection và phân quyền.
