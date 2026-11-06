# Hướng dẫn kiểm thử TC15, TC18, TC19

## 1. Giới hạn độ dài câu hỏi (N)

Giới hạn được khai báo trong `app/schemas/message.py`:

```python
MAX_MESSAGE_LENGTH = 2000

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
```

- **N = 2000 ký tự**.
- FastAPI tự sinh `maxLength: 2000` trong `/openapi.json`.
- Nếu muốn đổi N, chỉ cần sửa `MAX_MESSAGE_LENGTH` rồi rebuild backend.

## 2. Chạy test tự động

Từ thư mục `rag_chatbot_backend`:

```powershell
python scripts/test_tc15_18_19.py
```

Nếu backend chạy ở địa chỉ khác:

```powershell
python scripts/test_tc15_18_19.py --base-url http://localhost:8000
```

Script sẽ:

1. Tạo 2 user test (`user_a`, `user_b`) bằng API register.
2. **TC15**: đọc N từ OpenAPI, gửi câu hỏi dài N-1, N, N+1.
3. **TC18**: dùng token user thường gọi `GET /api/v1/stats`.
4. **TC19**: user_b đọc messages trong conversation của user_a.
5. Xóa user test sau khi chạy xong (nếu đăng nhập được admin).

Kết quả mong đợi:

```text
TC15: PASS - N=2000: N-1=200, N=200, N+1=422 (bị từ chối, không lưu message)
TC18: PASS - user thường nhận 403, không lộ field thống kê; admin: gọi /stats = 200 (đối chứng)
TC19: PASS - User A đọc được hội thoại của mình (200); User B nhận 403, không lộ nội dung message
```

> Lưu ý: sau khi sửa code backend, phải rebuild container thì thay đổi mới có hiệu lực:
>
> ```powershell
> cd <thư mục gốc RAG_chatbot-main>
> docker compose up -d --build backend
> ```

## 3. Test thủ công bằng PowerShell / curl

### Bước 0: Tạo 2 user và lấy token

```powershell
$base = "http://127.0.0.1:8000/api/v1"
$suffix = Get-Random

$bodyA = @{
    username = "tc_a_$suffix"
    email    = "tc_a_$suffix@example.com"
    password = "Test123456!"
} | ConvertTo-Json

$bodyB = @{
    username = "tc_b_$suffix"
    email    = "tc_b_$suffix@example.com"
    password = "Test123456!"
} | ConvertTo-Json

$authA = Invoke-RestMethod -Method Post -Uri "$base/auth/register" `
    -ContentType "application/json" -Body $bodyA
$authB = Invoke-RestMethod -Method Post -Uri "$base/auth/register" `
    -ContentType "application/json" -Body $bodyB

$tokenA = $authA.access_token
$tokenB = $authB.access_token
```

### TC15: Độ dài câu hỏi tối đa

Tạo conversation cho user A:

```powershell
$conv = Invoke-RestMethod -Method Post -Uri "$base/conversations" `
    -Headers @{ Authorization = "Bearer $tokenA" } `
    -ContentType "application/json" -Body '{"title":"TC15 max length"}'
$convId = $conv.id
```

Hàm gửi câu hỏi dài `$n` ký tự và in HTTP status:

```powershell
function Send-TC15([int]$n) {
    $payload = @{ content = ("x" * $n) } | ConvertTo-Json -Compress
    $payload | Out-File -Encoding utf8 "$env:TEMP\tc15.json"

    # --max-time 8: N và N-1 là SSE nên sẽ mở stream; hết thời gian sẽ tự đóng.
    curl.exe -s -o NUL -w "n=$n -> HTTP %{http_code}`n" --max-time 8 `
        -X POST "$base/conversations/$convId/messages" `
        -H "Authorization: Bearer $tokenA" `
        -H "Content-Type: application/json" `
        --data-binary "@$env:TEMP\tc15.json"
}
```

Chạy lần lượt:

```powershell
Send-TC15 1999   # N-1 -> 200
Send-TC15 2000   # N   -> 200
Send-TC15 2001   # N+1 -> 422
```

Xem thông báo lỗi của trường hợp N+1:

```powershell
$payload = @{ content = ("x" * 2001) } | ConvertTo-Json -Compress
$payload | Out-File -Encoding utf8 "$env:TEMP\tc15_too_long.json"

curl.exe -s -X POST "$base/conversations/$convId/messages" `
    -H "Authorization: Bearer $tokenA" `
    -H "Content-Type: application/json" `
    --data-binary "@$env:TEMP\tc15_too_long.json"
```

Kết quả mong đợi:

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "content"],
      "msg": "String should have at most 2000 characters",
      "ctx": { "max_length": 2000 }
    }
  ]
}
```

### TC18: User thường gọi API admin

```powershell
curl.exe -i -H "Authorization: Bearer $tokenB" "$base/stats"
```

Kết quả mong đợi:

```text
HTTP/1.1 403 Forbidden
...
{"detail":"Admin access required"}
```

Không được có các field `total_users`, `total_conversations`, `total_messages`... trong body.

Đối chứng với admin (mặc định `admin` / `admin123`):

```powershell
$adminBody = @{ username = "admin"; password = "admin123" } | ConvertTo-Json
$adminAuth = Invoke-RestMethod -Method Post -Uri "$base/auth/login" `
    -ContentType "application/json" -Body $adminBody

curl.exe -s -H "Authorization: Bearer $($adminAuth.access_token)" "$base/stats"
```

Kết quả mong đợi: HTTP 200 kèm các field thống kê.

### TC19: User B truy cập hội thoại của user A

Tạo conversation và gửi 1 message bằng user A:

```powershell
$conv = Invoke-RestMethod -Method Post -Uri "$base/conversations" `
    -Headers @{ Authorization = "Bearer $tokenA" } `
    -ContentType "application/json" -Body '{"title":"TC19 private"}'
$convId = $conv.id

$msg = @{ content = "TC19 secret message" } | ConvertTo-Json -Compress
$msg | Out-File -Encoding utf8 "$env:TEMP\tc19_msg.json"

curl.exe -s -o NUL -w "send -> HTTP %{http_code}`n" --max-time 15 `
    -X POST "$base/conversations/$convId/messages" `
    -H "Authorization: Bearer $tokenA" `
    -H "Content-Type: application/json" `
    --data-binary "@$env:TEMP\tc19_msg.json"
```

User A đọc messages của mình (đối chứng):

```powershell
curl.exe -s -H "Authorization: Bearer $tokenA" `
    "$base/conversations/$convId/messages"
```

Kết quả mong đợi: HTTP 200, có message chứa `TC19 secret message`.

User B đọc messages của conversation đó:

```powershell
curl.exe -i -H "Authorization: Bearer $tokenB" `
    "$base/conversations/$convId/messages"
```

Kết quả mong đợi:

```text
HTTP/1.1 403 Forbidden
...
{"detail":"Access denied"}
```

Body **không được** chứa `TC19 secret message`, `content`, hay `sender_type`.

## 4. Test bằng Postman

1. Tạo request `POST {{base}}/auth/register` cho user A và user B, lưu `access_token`.
2. **TC15**:
   - `POST {{base}}/conversations` với Bearer token user A → lấy `id`.
   - `POST {{base}}/conversations/{id}/messages` với body `{"content":"..."}`.
   - Lần lượt thay content dài 1999, 2000, 2001 ký tự.
   - Kỳ vọng: 200, 200, 422.
3. **TC18**:
   - `GET {{base}}/stats` với Bearer token user B.
   - Kỳ vọng: 403 `{"detail":"Admin access required"}`.
4. **TC19**:
   - Tạo conversation + message bằng token user A.
   - `GET {{base}}/conversations/{id}/messages` với token user B.
   - Kỳ vọng: 403 `{"detail":"Access denied"}`, body không có nội dung tin nhắn.

## 5. Bảng kết quả

| Test case | Thao tác | Kỳ vọng | Trạng thái |
|---|---|---|---|
| TC15 | Gửi câu hỏi N-1 ký tự | 200 (được chấp nhận) | PASS |
| TC15 | Gửi câu hỏi N ký tự | 200 (được chấp nhận) | PASS |
| TC15 | Gửi câu hỏi N+1 ký tự | 422, thông báo giới hạn 2000 | PASS |
| TC18 | User thường gọi `GET /api/v1/stats` | 403, không lộ dữ liệu | PASS |
| TC19 | User B đọc messages của user A | 403, không lộ nội dung | PASS |
