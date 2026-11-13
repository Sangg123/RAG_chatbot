# Tích hợp đa kênh Telegram

Tài liệu này giải thích cách dự án được mở rộng từ **chatbot web** thành
**chatbot đa kênh**: cùng một lõi RAG + tra cứu đơn hàng, nhưng khách có thể
nhắn qua Web hoặc Telegram.

## 1. Kiến trúc

```
Khách Telegram
      │  (chat 1-1)
      ▼
Telegram Bot API
      │  webhook (production)  /  getUpdates long-polling (local)
      ▼
app/channels/telegram.py          ← adapter: parse update, gửi tin, typing...
      │
      ▼
app/services/channel_service.py   ← identity + conversation + command
      │
      ▼
app/services/chat_service.py      ← LÕI DÙNG CHUNG: RAG + tool calling
      │
      ├── rag_service.py            (pgvector + Gemini)
      ├── agent_service.py          (function calling)
      └── order_service.py          (đơn hàng, kiểm tra chủ sở hữu)
      │
      ▼
PostgreSQL
```

Điểm quan trọng: **Telegram không có logic AI riêng**. Kênh ngoài chỉ chịu
trách nhiệm:

1. Nhận payload riêng của kênh và chuyển thành `IncomingMessage`.
2. Gọi `handle_incoming_message()`.
3. Gửi nội dung trả về qua API của kênh.

Nhờ vậy sau này thêm Zalo/WhatsApp chỉ cần viết adapter mới, không sửa RAG,
prompt hay tool tra cứu đơn.

## 2. Những thành phần đã thêm

| File | Vai trò |
|---|---|
| `app/channels/base.py` | `IncomingMessage` chuẩn hóa + `parse_command` |
| `app/channels/telegram.py` | Telegram Bot API client, parse update, chia tin nhắn dài, typing indicator |
| `app/models/channel_account.py` | Bảng ánh xạ danh tính kênh ngoài ↔ user nội bộ |
| `app/services/channel_service.py` | Tạo/định danh khách, chọn hội thoại, xử lý lệnh, gọi lõi chat |
| `app/services/telegram_service.py` | Xử lý update, long-polling, gửi lỗi thân thiện |
| `app/api/v1/channels.py` | Webhook `POST /api/v1/channels/telegram/webhook` |
| `alembic/versions/20261120_000007_add_multi_channel.py` | Migration bảng `channel_accounts` + cột kênh cho `conversations` |
| `scripts/telegram_polling.py` | Chạy bot local bằng long polling |
| `scripts/telegram_webhook.py` | Đăng ký/xóa webhook production |
| `tests/test_telegram_channel.py` | Unit test parse update, command, chia tin nhắn |

### Thay đổi DB

`channel_accounts`:

| Cột | Ý nghĩa |
|---|---|
| `channel` | `telegram`, `zalo`, ... |
| `external_user_id` | ID người dùng phía kênh (Telegram user id) |
| `external_chat_id` | ID cuộc chat (với chat 1-1 thường trùng user id) |
| `user_id` | FK tới `users.id` |
| `display_name`, `external_username` | Tên/username để hiển thị |

Ràng buộc `UNIQUE(channel, external_user_id)` đảm bảo một tài khoản Telegram
chỉ ánh xạ tới một user nội bộ.

`conversations` thêm:

- `channel`: `web` (mặc định) hoặc `telegram`.
- `external_chat_id`: id chat phía kênh, dùng để tìm lại hội thoại đang mở.

## 3. Cài đặt

### Bước 1 — Tạo bot

1. Mở Telegram, tìm `@BotFather`.
2. Gửi `/newbot`, đặt tên và username (phải kết thúc bằng `bot`).
3. Lưu **bot token** dạng `123456789:AA...`.

Không cần bật privacy mode cho chat 1-1. Bot chỉ hỗ trợ chat riêng để tránh lộ
dữ liệu đơn hàng trong nhóm.

### Bước 2 — Cấu hình `.env`

Tùy cách chạy:

- **Chạy backend trực tiếp** (`uvicorn app.main:app` trong
  `rag_chatbot_backend`): thêm vào `rag_chatbot_backend/.env`.
- **Chạy Docker Compose**: thêm vào `.env` ở thư mục gốc (file compose đọc
  biến từ đây).
- **Render**: đặt trong Dashboard → Environment.

Nội dung cần thêm:

```env
TELEGRAM_BOT_TOKEN=123456789:AA...
TELEGRAM_WEBHOOK_SECRET=mot-chuoi-ngau-nhien-dai
```

- `TELEGRAM_BOT_TOKEN`: bắt buộc để bật kênh Telegram.
- `TELEGRAM_WEBHOOK_SECRET`: bắt buộc khi `ENVIRONMENT=production`. Dùng
  `openssl rand -hex 32` hoặc một chuỗi ngẫu nhiên tương đương.

Nếu dùng Docker, các biến này đã được truyền vào service `backend` trong
`docker-compose.yml`.

### Bước 3 — Chạy migration

```bash
cd rag_chatbot_backend
alembic upgrade head
```

Nếu đang dùng Docker:

```bash
docker compose up -d db ollama
docker compose run --rm backend alembic upgrade head
```

### Bước 4 — Chạy local bằng polling

```bash
cd rag_chatbot_backend
python scripts/telegram_polling.py
```

Script sẽ:

1. Gọi `deleteWebhook` để tắt webhook cũ.
2. Đăng ký menu lệnh với Telegram.
3. Gọi `getUpdates` liên tục và trả lời từng tin nhắn.

Nếu backend chạy bằng Docker:

```bash
docker compose run --rm backend python scripts/telegram_polling.py
```

> Chỉ chạy **một trong hai**: polling hoặc webhook. Chạy cả hai với cùng bot
> token sẽ gây lỗi `409 Conflict`.

### Bước 5 — Production bằng webhook (Render)

Backend cần URL HTTPS công khai. Render đã cấp sẵn.

1. Trên Render, đặt `TELEGRAM_BOT_TOKEN` và `TELEGRAM_WEBHOOK_SECRET`.
2. Đặt cùng secret trong `.env` local (script đọc secret từ đây).
3. Đăng ký webhook:

```bash
cd rag_chatbot_backend
python scripts/telegram_webhook.py \
  --url https://<backend-cua-ban>/api/v1/channels/telegram/webhook
```

4. Kiểm tra:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Kết quả mong đợi có `"url"` đúng và `"last_error_message"` không có.

Webhook được bảo vệ bằng header `X-Telegram-Bot-Api-Secret-Token`. Backend từ
chối request nếu secret không khớp. Ở production, nếu chưa đặt secret, endpoint
trả `503` thay vì chạy không bảo vệ.

Muốn quay lại polling:

```bash
python scripts/telegram_webhook.py --delete
```

## 4. Luồng định danh và lệnh

### Khách mới

Lần đầu nhắn tin, hệ thống tự tạo:

- Một `users` row role `guest`, `is_active=false` (không thể đăng nhập web).
- Một `channel_accounts` row trỏ tới user đó.
- Một `conversations` row với `channel='telegram'`.

Khách chưa liên kết vẫn hỏi được FAQ/chính sách bằng RAG, nhưng **không tra
cứu được đơn hàng** vì chưa có chủ sở hữu.

### Liên kết tài khoản web

```text
/link nguyen.van.an password123
```

- Xác thực bằng username/email + mật khẩu của tài khoản web.
- `channel_accounts.user_id` được trỏ sang user thật.
- Hội thoại Telegram của guest được chuyển sang user thật.
- Từ đó tool `lookup_order` / `list_orders_by_phone` dùng đúng `user_id`, nên
  khách chỉ thấy đơn của chính mình.

> **Lưu ý bảo mật:** mật khẩu gửi qua `/link` sẽ nằm trong lịch sử chat
> Telegram. Khi demo, nên dùng tài khoản demo riêng và hướng dẫn khách
> `/unlink` sau khi dùng xong. Giải pháp lâu dài là mã liên kết một lần (OTP)
> như nêu ở mục 7.

### Các lệnh

| Lệnh | Chức năng |
|---|---|
| `/start`, `/help` | Chào mừng + hướng dẫn |
| `/new` | Tạo hội thoại mới |
| `/link <username> <password>` | Liên kết tài khoản web |
| `/unlink` | Hủy liên kết |
| `/id` | Xem Telegram id, chat id, tài khoản nội bộ |

## 5. Kịch bản demo trước hội đồng

Chuẩn bị:

- Backend chạy, đã upload tài liệu chính sách vào knowledge base.
- Tài khoản demo `nguyen.van.an / password123` (sở hữu `DH123`).

Thực hiện:

1. Mở bot, gửi `/start`.
2. Hỏi một câu chính sách, ví dụ: *"Chính sách đổi trả trong bao nhiêu ngày?"*
   → câu trả lời lấy từ RAG.
3. Hỏi *"Đơn DH123 đang ở đâu?"* khi chưa liên kết
   → bot báo không tìm thấy đơn thuộc tài khoản hiện tại.
4. Gửi `/link nguyen.van.an password123`.
5. Hỏi lại *"Đơn DH123 đang ở đâu?"*
   → bot gọi `lookup_order`, trả đúng trạng thái/sản phẩm/vận đơn.
6. Hỏi *"SĐT 0901234567 có đơn nào chưa giao?"*
   → bot gọi `list_orders_by_phone`.
7. Gửi `/new`, hỏi tiếp một câu FAQ.
8. Vào Admin → **Lịch sử hội thoại**, lọc kênh **Telegram**
   → thấy hội thoại vừa chat, có badge kênh.
9. (Tùy chọn) Kiểm tra DB:

```sql
SELECT id, channel, external_chat_id, title
FROM conversations
ORDER BY created_at DESC
LIMIT 5;

SELECT channel, external_user_id, user_id, display_name
FROM channel_accounts;
```

## 6. Kiểm thử

Unit test không cần DB/Gemini:

```bash
cd rag_chatbot_backend
python -m unittest tests.test_telegram_channel -v
```

Các test kiểm tra:

- Parse tin nhắn text/private, bỏ qua sticker và edited message.
- Tách lệnh `/help@BotName`.
- Chia câu trả lời dài dưới giới hạn Telegram.
- Chat nhóm bị đánh dấu `is_private=false` và bị từ chối.

Kiểm thử webhook thủ công (không khuyến khích vì sẽ gọi Gemini thật):

```bash
curl -X POST "http://localhost:8000/api/v1/channels/telegram/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: <secret>" \
  -d '{"update_id":1,"message":{"message_id":1,"from":{"id":1,"first_name":"Test"},"chat":{"id":1,"type":"private"},"text":"/help"}}'
```

## 7. Bảo mật và giới hạn

Đã có:

- Webhook secret bắt buộc ở production.
- Chỉ hỗ trợ chat 1-1; tin nhắn nhóm bị từ chối.
- Guest user bị vô hiệu hóa đăng nhập web.
- `/link` yêu cầu đúng mật khẩu tài khoản web.
- Tool đơn hàng vẫn giới hạn theo `current_user.id`; Telegram không bypass.
- Token bot không xuất hiện trong log lỗi mạng.

Chưa có (nên nêu là hướng phát triển nếu bị hỏi):

- Rate limiting theo chat id để chống spam.
- OTP/mã liên kết một lần thay vì gõ mật khẩu trong chat.
- Hàng đợi (Celery/RQ) cho webhook thay vì `BackgroundTasks`.
- Lưu `update_id` đã xử lý để chống trùng khi retry.
- Hỗ trợ ảnh, voice, file.
- Mã hóa/che PII trong log.

## 8. Mở rộng thêm kênh Zalo/WhatsApp

Ví dụ thêm Zalo OA:

1. Viết `app/channels/zalo.py`:
   - Xác thực chữ ký webhook.
   - Chuyển payload Zalo thành `IncomingMessage(channel="zalo", ...)`.
   - Viết hàm gửi tin qua Zalo OA API.
2. Thêm route `POST /api/v1/channels/zalo/webhook`.
3. Route gọi:

```python
async with AsyncSessionLocal() as db:
    reply = await handle_incoming_message(db, incoming)
await zalo_client.send_text(incoming.external_chat_id, reply)
```

Không cần sửa `chat_service.py`, prompt, RAG hay tool đơn hàng.

## 9. Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `409 Conflict` khi polling | Bot đang có webhook. Chạy `python scripts/telegram_webhook.py --delete` rồi polling lại. |
| Webhook trả `403` | `TELEGRAM_WEBHOOK_SECRET` trên Render khác secret lúc gọi `setWebhook`. Đặt lại cùng giá trị và đăng ký lại webhook. |
| Webhook trả `503` | Chưa có `TELEGRAM_BOT_TOKEN`, hoặc production chưa có secret. |
| Bot không trả lời | Xem log backend; kiểm tra token, migration, Gemini quota, DB. |
| `relation "channel_accounts" does not exist` | Chưa chạy `alembic upgrade head`. |
| Bot trả lời chậm | Lần đầu có thể gọi Gemini tạo tiêu đề + embedding; kiểm tra Ollama/Gemini. |
| Trả lời dài bị cắt | Đã tự chia thành nhiều tin nhắn dưới 4000 ký tự. |
| Không tra cứu được đơn | Chưa `/link`, hoặc đơn không thuộc tài khoản đã liên kết. Đây là hành vi bảo mật đúng. |
