# RAG Chatbot Application

Đây là một ứng dụng chatbot sử dụng công nghệ Retrieval-Augmented Generation (RAG) với kiến trúc Monolyth, áp dụng mô hình MVC, bao gồm backend được xây dựng bằng FastAPI và frontend bằng Next.js.

## Triển khai miễn phí

Hướng dẫn deploy Vercel + Render + Neon + Gemini embedding (không cần chạy Ollama trên cloud):

- Xem [`DEPLOY_FREE.md`](DEPLOY_FREE.md).
- Local vẫn dùng Ollama mặc định (`EMBEDDING_PROVIDER=ollama`).
- Trên Render đặt `EMBEDDING_PROVIDER=gemini` và dùng `render.yaml` ở root repo.

## Cấu Trúc Dự Án

```
rag_chatbot/
├── rag_chatbot_backend/          # Backend API (FastAPI)
├── RAG_chatbot_frontend/         # Frontend (Next.js)
├── docker-compose.yml            # Cấu hình Docker Compose
├── .env                          # Biến môi trường
└── .env.example                  # Ví dụ biến môi trường
```

## Backend (FastAPI)

Backend được triển khai trong thư mục `rag_chatbot_backend` với các tính năng chính:

- API RESTful sử dụng FastAPI
- Xác thực người dùng (JWT)
- Truy xuất và tạo sinh phản hồi (RAG)
- Lưu trữ tài liệu trong PostgreSQL với pgvector
- Tích hợp với Ollama để chạy mô hình ngôn ngữ cục bộ
- Tích hợp với Google Gemini API
- **AI tool calling (Gemini function calling)** tra cứu đơn hàng có cấu trúc từ PostgreSQL
- Lưu audit log mỗi lần AI gọi tool vào bảng `message_tool_calls`
- Xử lý tải lên tài liệu

### Công nghệ sử dụng:
- FastAPI
- PostgreSQL với pgvector
- SQLAlchemy (async)
- Alembic (migrations)
- LangChain
- Google Generative AI
- Ollama
- Pydantic Settings
- JWT

### Cách chạy backend:
```bash
cd rag_chatbot_backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend (Next.js)

Frontend được triển khai trong thư mục `RAG_chatbot_frontend` với các tính năng chính:

- Giao diện người dùng hiện đại
- Trò chuyện real-time
- Quản lý tài liệu
- Cấu hình người dùng
- Đăng nhập/đăng xuất

### Công nghệ sử dụng:
- Next.js 13+ (App Router)
- React
- Tailwind CSS
- TypeScript

### Cách chạy frontend:
```bash
cd RAG_chatbot_frontend
npm install
npm run dev
```

## Docker Compose

Dự án hỗ trợ triển khai đầy đủ bằng Docker Compose với các service:
- PostgreSQL với pgvector (db)
- Ollama (ollama)
- Backend API (backend)
- Frontend (frontend)

### Cách chạy với Docker:
```bash
docker-compose up --build
```

## Cấu hình môi trường

Sao chép file `.env.example` thành `.env` và điền các giá trị cần thiết:

```
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=rag_chatbot

# JWT
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_CHAT_MODEL=gemini-3.5-flash
GEMINI_TITLE_MODEL=gemini-3.1-flash-lite
GEMINI_FALLBACK_MODELS=gemini-3.1-flash-lite

# Embeddings
# Local: ollama. Free cloud: gemini (no Ollama container needed).
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBED_MODEL=embeddinggemma
GEMINI_EMBED_MODEL=gemini-embedding-001
GEMINI_EMBED_DIM=1536
GEMINI_EMBED_BATCH_SIZE=50

# Tool calling
# Số tin nhắn gần nhất gửi kèm để AI hiểu câu hỏi nối tiếp.
CHAT_HISTORY_MAX_MESSAGES=8

# Upload / registration
# Render free: MAX_UPLOAD_MB=20, ALLOW_PUBLIC_REGISTRATION=false
MAX_UPLOAD_MB=20
ALLOW_PUBLIC_REGISTRATION=true

# Admin Seed
ADMIN_SEED_USER_ID=00000000-0000-0000-0000-000000000001
ADMIN_SEED_USERNAME=admin
ADMIN_SEED_EMAIL=admin@company.com
ADMIN_SEED_PASSWORD=admin123

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Backend
ENVIRONMENT=development
STORAGE_DIR=/app/storage/uploads

# Ports
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

## API Endpoints

Backend cung cấp các endpoint API chính (tiền tố `/api/v1`):

- `POST /auth/register` - Đăng ký người dùng
- `POST /auth/login` - Đăng nhập
- `POST /auth/refresh` - Làm mới token
- `GET /auth/me` - Lấy thông tin người dùng hiện tại
- `POST /documents/upload` - Tải lên tài liệu
- `GET /documents` - Lấy danh sách tài liệu
- `DELETE /documents/{id}` - Xóa tài liệu
- `POST /conversations` - Tạo hội thoại
- `POST /conversations/{id}/messages` - Gửi tin nhắn, trả về SSE
- `GET /conversations/{id}/messages` - Lấy lịch sử tin nhắn
- `GET /messages/{id}/citations` - Lấy trích dẫn RAG của câu trả lời
- `GET /messages/{id}/tool-calls` - Lấy các tool call AI đã thực hiện
- `GET /health` - Kiểm tra tình trạng hệ thống

### SSE events của chat

`POST /conversations/{id}/messages` trả về `text/event-stream` với các event:

| Event | Ý nghĩa |
|---|---|
| `token` | Một phần nội dung câu trả lời |
| `tool_call` | AI vừa quyết định gọi tool (JSON: id, name, arguments, label) |
| `tool_result` | Kết quả tool từ PostgreSQL (JSON: id, status, result, duration_ms) |
| `done` | Kết thúc stream |
| `error` | Có lỗi xảy ra |

## AI Tool Calling tra cứu đơn hàng

Ngoài RAG trên tài liệu, chatbot còn dùng **Gemini native function calling** để đọc dữ liệu đơn hàng có cấu trúc từ PostgreSQL.

### Hai tool đang có

| Tool | Khi nào dùng | Dữ liệu trả về |
|---|---|---|
| `lookup_order` | Khách hỏi một đơn cụ thể, ví dụ `Đơn DH123 đang ở đâu?` | Trạng thái, sản phẩm, thanh toán, vận đơn, ngày giao dự kiến — **chỉ đơn thuộc tài khoản đang đăng nhập** |
| `list_orders_by_phone` | Khách cho SĐT và hỏi các đơn của mình | Danh sách đơn gần nhất kèm trạng thái/tổng tiền — **chỉ đơn thuộc tài khoản đang đăng nhập** |

### Luồng xử lý

```
Câu hỏi khách
   │
   ├─ Guardrail phát hiện ý định đơn hàng (mã DH + ngữ cảnh, hoặc SĐT + ngữ cảnh)
   │      │
   │      ├─ Có: backend lấy current_user.id từ JWT
   │      │        gọi Gemini kèm tool declarations (ép đúng tool nếu rõ ý định)
   │      │        Gemini trả function_call
   │      │        Backend query PostgreSQL với user_id = current_user.id
   │      │        Gửi function_response lại Gemini
   │      │        Gemini viết câu trả lời cuối, stream về UI
   │      │
   │      └─ Không: giữ nguyên luồng RAG tài liệu như cũ
   │
   └─ Lưu message + tool call vào DB, frontend hiển thị chip "Đã tra cứu..."
```

Guardrail được thiết kế bảo thủ:

- `Đơn DH123 đang ở đâu?` → ép gọi `lookup_order`.
- `DH123` (chỉ gõ mã) → ép gọi `lookup_order`.
- `SĐT 0901234567 có đơn nào chưa giao?` → ép gọi `list_orders_by_phone`.
- `Sản phẩm DH có gì đặc biệt?` → **không** gọi tool, dùng RAG bình thường.
- `DH123 có gì đặc biệt?` → không đủ ngữ cảnh đơn hàng, dùng RAG bình thường.

### Phân quyền đơn hàng

Mỗi đơn hàng có `orders.user_id` trỏ tới tài khoản sở hữu. Khi tra cứu:

- Backend tự gắn `current_user.id` vào câu SQL; AI **không** được truyền `user_id`.
- Đơn của người khác trả `found=false` với thông báo chung, không lộ tên, địa chỉ, sản phẩm, thanh toán hay vận đơn.
- Không phân biệt “không tồn tại” với “không thuộc tài khoản” để tránh dò mã đơn/SĐT.
- Tài khoản admin cũng không bypass quyền trong chat khách hàng.

Tài khoản demo dùng để thử (mật khẩu `password123`):

| Username | Sở hữu | SĐT |
|---|---|---|
| `nguyen.van.an` | `DH123` | `0901234567` |
| `tran.thi.binh` | `DH124` | `0912345678` |
| `le.hoang.cuong` | `DH125` | `0987654321` |
| `pham.thu.dung` | `DH126` | `0909876543` |
| `hoang.van.em` | `DH127` | `0934567890` |
| `vu.thi.lan` | `DH1001` | `0945678901` |

> Đây là tài khoản demo với mật khẩu công khai. Khi triển khai thật phải xóa hoặc vô hiệu hóa các tài khoản này và đổi mật khẩu admin.

### Bảng dữ liệu mới

- `orders`: thông tin đơn hàng, có `user_id` xác định chủ sở hữu.
- `order_items`: sản phẩm trong đơn.
- `message_tool_calls`: audit log tool name, arguments, result, status, duration_ms.

Migration: `20261117_000005_add_orders_and_tool_calls.py` tạo bảng và seed đơn;
`20261117_000006_add_order_ownership.py` thêm `orders.user_id`, gắn 6 đơn mẫu
với đúng tài khoản demo và tạo tài khoản demo.
Dữ liệu mẫu: `DH123`, `DH124`, `DH125`, `DH126`, `DH127`, `DH1001`.
Chi tiết kiến trúc và kịch bản demo: [`rag_chatbot_backend/TOOL_CALLING.md`](rag_chatbot_backend/TOOL_CALLING.md).

## Kiểm thử

Hướng dẫn kiểm thử TC15, TC18, TC19 (giới hạn độ dài câu hỏi, phân quyền admin, truy cập hội thoại của người khác):

```bash
cd rag_chatbot_backend
python scripts/test_tc15_18_19.py
```

Kiểm thử end-to-end AI tool calling + phân quyền đơn hàng (cần backend đang chạy,
Gemini API key và migration `20261117_000006`):

```bash
cd rag_chatbot_backend
python scripts/test_tool_calling.py
```

Script dùng hai tài khoản demo `nguyen.van.an` và `tran.thi.binh` để kiểm tra
chủ đơn tra cứu được đơn của mình, còn người khác biết mã đơn/SĐT thì bị từ chối
và không lộ dữ liệu. Mặc định script xóa conversation test sau khi chạy.

Unit test guardrail không cần DB/API:

```bash
cd rag_chatbot_backend
python -m unittest tests.test_order_intent -v
```

Chi tiết và cách test thủ công bằng Postman/curl: xem [`rag_chatbot_backend/TESTING_TC15_TC18_TC19.md`](rag_chatbot_backend/TESTING_TC15_TC18_TC19.md).

## Đóng góp

1. Fork repository này
2. Tạo nhánh tính năng mới (`git checkout -b feature/amazing-feature`)
3. Commit thay đổi của bạn (`git commit -m 'Add some amazing-feature'`)
4. Push lên nhánh (`git push origin feature/amazing-feature`)
5. Mở Pull Request

## Giấy phép

Dự án này được phân phối sotto giấy phép MIT. Xem file `LICENSE` để biết thêm chi tiết.

## Liên hệ

Nếu bạn có bất kỳ câu hỏi nào, vui lòng mở một issue trong repository này.

# Cách xem DB tại thư mục gốc RAG_chatbot-main
    docker compose exec db psql -U postgres -d rag_chatbot
Hoặc dùng tên container trực tiếp:
    docker exec -it rag_chatbot-main-db-1 psql -U postgres -d rag_chatbot
Trong psql, vài lệnh hay dùng:
\dt                          -- xem danh sách bảng
\d users                     -- xem cấu trúc bảng users
\d+ users                    -- xem chi tiết hơn
SELECT * FROM users;         -- xem toàn bộ user
\x                           -- bật chế độ hiển thị dọc cho dễ đọc
\q                           -- thoát