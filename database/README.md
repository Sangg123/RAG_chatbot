# Database RAG Chatbot

Thư mục này chứa SQL để tạo và nạp dữ liệu mẫu cho database `rag_chatbot` trên PostgreSQL/pgAdmin.

## Cấu trúc database (7 bảng)

| Bảng | Mô tả |
|---|---|
| `users` | Tài khoản đăng nhập, phân quyền admin/user, token_version |
| `knowledge_bases` | Kho tri thức |
| `documents` | Tài liệu thuộc kho tri thức |
| `document_chunks` | Các đoạn văn bản + embedding vector (768 chiều) |
| `conversations` | Hội thoại của người dùng |
| `messages` | Tin nhắn USER/BOT, đánh giá và phản hồi |
| `message_citations` | Trích dẫn chunk cho câu trả lời của BOT |

Quan hệ khóa ngoại:

```
users 1─n conversations 1─n messages 1─n message_citations
knowledge_bases 1─n documents 1─n document_chunks 1─n message_citations
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
```

## Tài khoản mẫu

| Username | Mật khẩu | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `nguyen.van.an` và các user còn lại | `password123` | user |

Mật khẩu đã được băm bằng bcrypt đúng định dạng backend đang dùng.

## Lưu ý

- `CREATE EXTENSION IF NOT EXISTS vector;` cần quyền superuser và server phải cài pgvector. Nếu dùng Docker của dự án (`pgvector/pgvector:pg16`) thì đã có sẵn.
- Nếu database đã có bảng từ Alembic, chỉ cần chạy `02_seed_data.sql`. Các lệnh insert đều có `ON CONFLICT (id) DO NOTHING` nên chạy lại không bị lỗi trùng khóa.
- Nếu muốn xóa sạch làm lại: chạy `00_reset_database.sql` rồi chạy lại file 01 và 02.
- Embedding trong file seed là vector giả lập 768 chiều, chỉ để hiển thị/kiểm thử. Muốn RAG tìm kiếm ngữ nghĩa thật, hãy upload tài liệu qua API để backend gọi Ollama (`embeddinggemma`) tạo embedding thật.
- File `01_create_tables.sql` có ghi revision `20260411_000004` vào `alembic_version`, giúp backend chạy `alembic upgrade head` mà không báo lỗi bảng đã tồn tại.

## Chạy nhanh bằng psql (nếu có)

```bash
psql -U postgres -d rag_chatbot -f database/01_create_tables.sql
psql -U postgres -d rag_chatbot -f database/02_seed_data.sql
```
