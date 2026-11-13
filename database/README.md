# Database RAG Chatbot

Thư mục này chứa SQL để tạo và nạp dữ liệu mẫu cho database `rag_chatbot` trên PostgreSQL/pgAdmin.

## Cấu trúc database (10 bảng)

| Bảng | Mô tả |
|---|---|
| `users` | Tài khoản đăng nhập, phân quyền admin/user, token_version |
| `knowledge_bases` | Kho tri thức |
| `documents` | Tài liệu thuộc kho tri thức |
| `document_chunks` | Các đoạn văn bản + embedding vector (768 chiều) |
| `conversations` | Hội thoại của người dùng |
| `messages` | Tin nhắn USER/BOT, đánh giá và phản hồi |
| `message_citations` | Trích dẫn chunk cho câu trả lời của BOT |
| `orders` | Đơn hàng có cấu trúc để AI tra cứu; mỗi đơn thuộc một `user_id` |
| `order_items` | Sản phẩm trong từng đơn hàng |
| `message_tool_calls` | Audit log mỗi lần AI gọi tool (arguments/result JSONB) |

Quan hệ khóa ngoại:

```
users 1─n conversations 1─n messages 1─n message_citations
knowledge_bases 1─n documents 1─n document_chunks 1─n message_citations
messages 1─n message_tool_calls
users 1─n orders 1─n order_items
```

## Thứ tự chạy trên pgAdmin

1. Chuột phải database `rag_chatbot` → **Query Tool**.
2. Mở file `01_create_tables.sql` → **Execute** (F5).
3. Mở file `02_seed_data.sql` → **Execute** (F5).
4. Kiểm tra bằng câu query ở cuối file seed hoặc:

```sql
SELECT * FROM users;
SELECT * FROM knowledge_bases;
SELECT * FROM documents;
SELECT * FROM document_chunks LIMIT 5;
SELECT * FROM conversations;
SELECT * FROM messages;
SELECT * FROM message_citations;
SELECT * FROM orders;
SELECT * FROM order_items;
SELECT * FROM message_tool_calls;
```

## Đơn hàng mẫu để test tool calling

| Mã đơn | Trạng thái | SĐT | Tài khoản sở hữu | Tổng tiền |
|---|---|---|---|---|
| `DH123` | Đang giao hàng | `0901234567` | `nguyen.van.an` | 887.000đ |
| `DH124` | Đã giao hàng | `0912345678` | `tran.thi.binh` | 529.000đ |
| `DH125` | Chờ xác nhận | `0987654321` | `le.hoang.cuong` | 1.298.000đ |
| `DH126` | Đã hủy | `0909876543` | `pham.thu.dung` | 279.000đ |
| `DH127` | Đã xác nhận | `0934567890` | `hoang.van.em` | 489.000đ |
| `DH1001` | Đang giao hàng | `0945678901` | `vu.thi.lan` | 703.000đ |

Mỗi đơn hàng chỉ được tra cứu bởi tài khoản sở hữu. Ví dụ đăng nhập
`nguyen.van.an`, hỏi `Đơn DH123 đang ở đâu?` sẽ có dữ liệu; hỏi
`Đơn DH124 đang ở đâu?` sẽ nhận thông báo không tìm thấy đơn thuộc tài khoản
đang đăng nhập. Đây là kiểm tra phân quyền ở backend, không phụ thuộc vào AI.
Muốn xem đơn DH124, đăng nhập `tran.thi.binh`.

Thử hỏi chatbot: `Đơn DH123 đang ở đâu?` hoặc
`SĐT 0901234567 có đơn nào chưa giao?`.

## Tài khoản mẫu

| Username | Mật khẩu | Role | Ghi chú |
|---|---|---|---|
| `admin` | `admin123` | admin | Quản trị |
| `nguyen.van.an` | `password123` | user | Sở hữu `DH123` |
| `tran.thi.binh` | `password123` | user | Sở hữu `DH124` |
| `le.hoang.cuong` | `password123` | user | Sở hữu `DH125` |
| `pham.thu.dung` | `password123` | user | Sở hữu `DH126` |
| `hoang.van.em` | `password123` | user | Sở hữu `DH127` |
| `vu.thi.lan` | `password123` | user | Sở hữu `DH1001` |

Mật khẩu đã được băm bằng bcrypt đúng định dạng backend đang dùng.

> Đây là tài khoản demo với mật khẩu công khai. Khi triển khai thật, phải xóa
> hoặc vô hiệu hóa các tài khoản demo và đổi mật khẩu admin. Có thể vô hiệu hóa
> mà vẫn giữ đơn hàng để audit bằng lệnh:
>
> ```sql
> UPDATE users SET is_active = FALSE
> WHERE username IN (
>     'nguyen.van.an', 'tran.thi.binh', 'le.hoang.cuong',
>     'pham.thu.dung', 'hoang.van.em', 'vu.thi.lan'
> );
> ```

## Lưu ý

- `CREATE EXTENSION IF NOT EXISTS vector;` cần quyền superuser và server phải cài pgvector. Nếu dùng Docker của dự án (`pgvector/pgvector:pg16`) thì đã có sẵn.
- Nếu database đã có bảng từ Alembic, chỉ cần chạy `02_seed_data.sql`. Các lệnh insert user/knowledge base dùng `ON CONFLICT (id) DO NOTHING`; riêng `orders` dùng `ON CONFLICT (order_code) DO UPDATE SET user_id = EXCLUDED.user_id` để gắn lại chủ sở hữu khi chạy lại seed.
- Nếu muốn xóa sạch làm lại: chạy `00_reset_database.sql` rồi chạy lại file 01 và 02.
- Embedding trong file seed là vector giả lập 768 chiều, chỉ để hiển thị/kiểm thử. Muốn RAG tìm kiếm ngữ nghĩa thật, hãy upload tài liệu qua API để backend gọi Ollama (`embeddinggemma`) tạo embedding thật.
- File `01_create_tables.sql` có ghi revision `20261117_000006` vào `alembic_version`, giúp backend chạy `alembic upgrade head` mà không báo lỗi bảng đã tồn tại.
- Với database đang chạy Alembic (kể cả Neon), chỉ cần chạy `alembic upgrade head`: migration tạo 3 bảng mới, seed 6 đơn hàng mẫu, sau đó migration `20261117_000006` gắn `orders.user_id` và tạo tài khoản demo. Không cần chạy lại toàn bộ file 01/02.

## Chạy nhanh bằng psql (nếu có)

```bash
psql -U postgres -d rag_chatbot -f database/01_create_tables.sql
psql -U postgres -d rag_chatbot -f database/02_seed_data.sql
```
