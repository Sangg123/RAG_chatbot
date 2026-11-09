# Deploy miễn phí: Vercel + Render + Neon + Gemini

Hướng dẫn này triển khai theo **cách A**:

```
Người dùng
   │
   ├── Vercel (Next.js frontend, free Hobby)
   │
   └── Render (FastAPI backend, Docker, free 512 MB)
          ├── Neon Postgres + pgvector (free)
          └── Gemini API (chat + embedding, free tier)
```

- **Ollama chỉ dùng ở local.** Trên Render dùng Gemini embedding để không cần container 4 GB RAM.
- Code local vẫn chạy như cũ nếu để `EMBEDDING_PROVIDER=ollama`.
- Trên Render đặt `EMBEDDING_PROVIDER=gemini`.

> Đây là cấu hình cho demo/đồ án. Free tier có cold start, giới hạn RAM/CPU và quota AI; không phù hợp cho production thật.

---

## 0. Chuẩn bị

Cần có:

- Repo đã push lên GitHub.
- Tài khoản [Neon](https://neon.tech), [Render](https://render.com), [Vercel](https://vercel.com).
- Gemini API key từ [Google AI Studio](https://aistudio.google.com/).
- File `render.yaml` ở root repo (đã có trong project này).

Kiểm tra nhanh trên máy:

```powershell
cd rag_chatbot_backend
python --version
uv --version
docker --version
```

---

## 1. Tạo Gemini API key

1. Vào Google AI Studio → **Get API key** → tạo key.
2. Lưu key vào nơi an toàn. **Không** đưa key vào frontend hoặc commit lên Git.
3. Vào mục rate limits của project để xem quota free tier hiện tại.

Lưu ý:

- Free tier có thể dùng dữ liệu của bạn để cải thiện sản phẩm. Không upload tài liệu nội bộ/nhạy cảm.
- Người dùng ở EEA/UK/Thụy Sĩ chỉ dùng được paid tier.
- Model free/không free thay đổi theo thời gian; kiểm tra lại trong AI Studio.

---

## 2. Tạo database Neon

### 2.1. Tạo project

1. Đăng nhập Neon → **New Project**.
2. Chọn Postgres 16 hoặc 17.
3. Chọn region gần Việt Nam nhất (thường là **Singapore**).
4. Tạo project, lưu lại connection string.

### 2.2. Lấy connection string đúng cho asyncpg

Neon thường đưa ra URL dạng:

```text
postgresql://user:password@ep-xxx-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

App dùng SQLAlchemy async + asyncpg, nên đổi thành:

```text
postgresql+asyncpg://user:password@ep-xxx-pooler.ap-southeast-1.aws.neon.tech/neondb?ssl=require
```

Quy tắc:

- Đổi `postgresql://` → `postgresql+asyncpg://`.
- Đổi `sslmode=require` → `ssl=require`. App cũng tự chuẩn hóa `sslmode` và bỏ `channel_binding` nếu bạn dán nguyên URL Neon, nhưng viết đúng ngay từ đầu vẫn an toàn hơn.
- Nếu mật khẩu có ký tự đặc biệt (`@`, `:`, `/`, `#`...), phải URL-encode.
- Nên dùng host có `-pooler` để tránh lỗi IPv6 từ Render.
- Nếu gặp lỗi `prepared statement ... does not exist` với pooler, thêm `&prepared_statement_cache_size=0`:

```text
postgresql+asyncpg://user:password@ep-xxx-pooler.../neondb?ssl=require&prepared_statement_cache_size=0
```

### 2.3. Chạy migration lần đầu

Có thể để Render tự chạy, nhưng nên chạy thử từ máy local để phát hiện lỗi sớm.

**PowerShell:**

```powershell
cd rag_chatbot_backend

$env:DATABASE_URL="postgresql+asyncpg://user:password@ep-xxx-pooler.../neondb?ssl=require"
$env:JWT_SECRET_KEY="mot-chuoi-random-that-dai-va-bi-mat"
$env:GEMINI_API_KEY="your-gemini-key"

alembic upgrade head
```

Nếu thành công, kiểm tra extension:

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

Migration `20260407_000001_initial.py` đã có `CREATE EXTENSION IF NOT EXISTS vector`, nên Neon sẽ tự bật pgvector.

> Migration `20260411_000003_add_users_auth.py` tạo sẵn admin:
>
> - username: `admin`
> - password: `admin123`
>
> Biến `ADMIN_SEED_PASSWORD` hiện **không** được migration dùng. Phải đổi mật khẩu ngay sau khi deploy.

---

## 3. Deploy backend lên Render

### Cách 3.1. Dùng Blueprint (nhanh)

1. Push code lên GitHub, đảm bảo `render.yaml` ở root repo.
2. Render Dashboard → **New** → **Blueprint**.
3. Chọn repo.
4. Render đọc `render.yaml` và hỏi các biến `sync: false`:
   - `DATABASE_URL`: URL Neon ở bước 2.
   - `GEMINI_API_KEY`: key Gemini.
   - `BACKEND_CORS_ORIGINS`: tạm nhập `["http://localhost:3000"]`, sẽ đổi sau khi có domain Vercel.
5. Apply / Deploy.
6. Chờ build Docker xong. Lần đầu có thể mất vài phút.

### Cách 3.2. Tạo Web Service thủ công

Nếu không dùng Blueprint:

1. Render → **New** → **Web Service**.
2. Chọn repo GitHub.
3. Cấu hình:
   - **Runtime**: Docker
   - **Root Directory**: `rag_chatbot_backend`
   - **Dockerfile Path**: `Dockerfile`
   - **Plan**: Free
   - **Health Check Path**: `/health`
4. Thêm các biến môi trường ở bảng dưới.
5. Deploy.

### 3.3. Biến môi trường trên Render

| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...neon.tech/neondb?ssl=require` |
| `JWT_SECRET_KEY` | Chuỗi random dài, bí mật |
| `GEMINI_API_KEY` | Key Gemini |
| `GEMINI_CHAT_MODEL` | `gemini-3.5-flash` |
| `GEMINI_TITLE_MODEL` | `gemini-3.1-flash-lite` |
| `GEMINI_FALLBACK_MODELS` | `gemini-3.1-flash-lite` |
| `EMBEDDING_PROVIDER` | `gemini` |
| `GEMINI_EMBED_MODEL` | `gemini-embedding-001` |
| `GEMINI_EMBED_DIM` | `1536` |
| `GEMINI_EMBED_BATCH_SIZE` | `50` |
| `GEMINI_EMBED_MAX_RETRIES` | `3` |
| `SEMANTIC_CHUNKING_ENABLED` | `false` |
| `ENVIRONMENT` | `production` |
| `STORAGE_DIR` | `/tmp/rag_uploads` |
| `MAX_UPLOAD_MB` | `20` |
| `ALLOW_PUBLIC_REGISTRATION` | `false` |
| `BACKEND_CORS_ORIGINS` | `["https://your-app.vercel.app"]` (cập nhật sau) |

Ghi chú:

- `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` dùng mặc định trong `render.yaml` nếu cần.
- `ADMIN_SEED_*` không ảnh hưởng migration hiện tại.
- Không cần `OLLAMA_BASE_URL` trên Render.
- `STORAGE_DIR=/tmp/rag_uploads` chỉ là đĩa tạm. Code xóa file gốc sau khi xử lý, nên phù hợp demo; nếu cần lưu file lâu dài phải dùng object storage.

### 3.4. Kiểm tra backend

Mở:

```text
https://<render-service>.onrender.com/health
```

Kết quả mong đợi:

```json
{"status":"ok","embedding_provider":"gemini"}
```

Xem log Render để chắc chắn:

- `alembic upgrade head` chạy thành công.
- Uvicorn báo `Application startup complete`.
- Không có lỗi kết nối Neon.
- `/health` trả `embedding_provider: "gemini"`. Nếu vẫn là `"ollama"`, kiểm tra lại biến `EMBEDDING_PROVIDER`.

> Request đầu tiên sau 15 phút idle có thể mất khoảng 1 phút do Render free spin down. Đây là bình thường.

---

## 4. Deploy frontend lên Vercel

1. Vercel → **Add New** → **Project**.
2. Import repo GitHub.
3. Cấu hình:
   - **Root Directory**: `RAG_chatbot_frontend`
   - **Framework Preset**: Next.js
   - **Build Command**: `npm run build`
   - **Install Command**: `npm install`
4. Thêm Environment Variable:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://<render-service>.onrender.com/api/v1`
   - Chọn cả **Production** (và **Preview** nếu cần).
5. Deploy.
6. Copy domain Vercel, ví dụ:

```text
https://rag-chatbot-abc.vercel.app
```

7. Quay lại Render → Environment → sửa:

```text
BACKEND_CORS_ORIGINS=["https://rag-chatbot-abc.vercel.app"]
```

8. Save → Render redeploy.

Lưu ý:

- `NEXT_PUBLIC_API_URL` được nhúng vào bundle lúc build. Nếu đổi URL backend, phải **redeploy Vercel**.
- Không có dấu `/` ở cuối domain CORS.
- Nếu dùng Vercel Preview, mỗi lần deploy preview có domain khác; thêm domain đó vào CORS hoặc chỉ test trên Production.
- Vercel Hobby chỉ dùng cho mục đích cá nhân/phi thương mại. Đồ án/demo cá nhân phù hợp; nếu thương mại hóa phải lên Pro.

---

## 5. Đăng nhập và upload tài liệu

1. Mở domain Vercel.
2. Đăng nhập:
   - username: `admin`
   - password: `admin123`
3. Vào phần đổi mật khẩu, đổi ngay.
4. Vì `render.yaml` đặt `ALLOW_PUBLIC_REGISTRATION=false`, tài khoản thường do admin tạo tại `/admin/users`. Nếu muốn mở đăng ký công khai, đổi biến này thành `true` và cân nhắc thêm rate limit.
5. Tạo knowledge base.
6. Upload tài liệu (tối đa 20 MB theo cấu hình Render).
7. Theo dõi trạng thái:
   - `PENDING` → `PROCESSING` → `COMPLETED`
   - Nếu `FAILED`, xem log Render.

### Về dữ liệu cũ ở local

- Vector cũ dùng `embeddinggemma` (768 chiều), không tương thích với Gemini (1536 chiều).
- Code lọc theo `vector_dims`, nên vector cũ sẽ bị bỏ qua; đừng trộn dữ liệu cũ với dữ liệu mới.
- Code hiện **xóa file gốc sau khi xử lý**, nên muốn re-embed tài liệu cũ phải có lại file gốc và upload lại.
- Cách sạch nhất: dùng Neon DB mới, upload lại toàn bộ tài liệu.

> Nếu đổi `GEMINI_EMBED_MODEL` hoặc `GEMINI_EMBED_DIM` sau này, phải re-upload/re-embed toàn bộ tài liệu.

---

## 6. Chạy local vẫn như cũ

File `.env` local để:

```env
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=embeddinggemma
```

Chạy:

```powershell
docker compose up -d db ollama
cd rag_chatbot_backend
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Nếu muốn local cũng dùng Gemini:

```env
EMBEDDING_PROVIDER=gemini
GEMINI_EMBED_MODEL=gemini-embedding-001
GEMINI_EMBED_DIM=1536
```

Nhưng phải re-upload tài liệu vì vector Ollama cũ không dùng được với Gemini.

---

## 7. Troubleshooting

### 502/503 ở request đầu tiên

Render free đang spin up. Chờ 30–60 giây rồi thử lại. Có thể dùng một uptime monitor miễn phí để ping `/health`, nhưng đừng lạm dụng.

### CORS error trên browser

- `BACKEND_CORS_ORIGINS` phải là JSON array:

```text
["https://your-app.vercel.app"]
```

- Không có `/` cuối.
- Phải đúng `https://`.
- Sau khi sửa phải redeploy backend.

### `ModuleNotFoundError: psycopg2`

`DATABASE_URL` chưa đổi sang `postgresql+asyncpg://`.

### `prepared statement ... does not exist`

Đang dùng Neon pooler. Thêm:

```text
&prepared_statement_cache_size=0
```

hoặc dùng direct connection string của Neon.

### `Network is unreachable` / không kết nối được Neon

Có thể Render không đi được IPv6 tới host direct. Dùng host có `-pooler` của Neon.

### `429 RESOURCE_EXHAUSTED` từ Gemini

- Free tier đã hết quota tạm thời.
- Đã tắt `SEMANTIC_CHUNKING_ENABLED` chưa?
- Upload ít tài liệu hơn, file nhỏ hơn.
- Chờ quota reset hoặc kiểm tra rate limit trong AI Studio.
- Không bật billing nếu không muốn bị tính tiền.

### Gemini trả `400` khi embed

Có thể batch vượt giới hạn token. Giảm `GEMINI_EMBED_BATCH_SIZE` (ví dụ 20–50) hoặc giảm `CHUNK_SIZE`.

### Upload bị 502/OOM

Render free chỉ 512 MB RAM. Giảm `MAX_UPLOAD_MB`, dùng file PDF/DOCX nhỏ, hoặc bỏ bớt dependency nặng (`onnxruntime`, `markitdown[all]`) nếu chỉ cần định dạng cơ bản.

### Tài liệu kẹt ở `PROCESSING`

Background task có thể bị kill khi Render restart/spin down. Upload lại tài liệu và xem log. Với file lớn, xử lý có thể vượt quá thời gian instance còn thức.

### Frontend vẫn gọi `localhost:8000`

`NEXT_PUBLIC_API_URL` chưa được set lúc build, hoặc set sau khi build. Set lại trong Vercel rồi redeploy.

### Không đăng nhập được admin

Migration tạo admin/admin123. Nếu đã đổi mật khẩu, dùng mật khẩu mới. Nếu quên, có thể reset trực tiếp trong Neon bằng SQL (cẩn thận):

```sql
UPDATE users
SET hashed_password = '<bcrypt-hash-mới>'
WHERE username = 'admin';
```

Có thể dùng script Python với `bcrypt` để tạo hash.

---

## 8. Giới hạn free tier cần biết

| Dịch vụ | Giới hạn chính |
|---|---|
| Render Free Web Service | 512 MB RAM, 0.1 CPU, sleep sau 15 phút, wake ~1 phút, 750 giờ/tháng, ~5 GB bandwidth/tháng, không persistent disk |
| Neon Free | 1 GB storage/project, 100 CU-hours/tháng, scale-to-zero sau 5 phút |
| Vercel Hobby | Miễn phí cho cá nhân/phi thương mại, ~100 GB bandwidth/tháng |
| Gemini free tier | Quota theo project, có thể 429; dữ liệu có thể bị dùng để cải thiện sản phẩm |

- Không dùng Render Postgres free vì database free của Render **hết hạn sau 30 ngày**.
- Free tier không có backup tự động. Với dữ liệu quan trọng, tự export định kỳ.
- Nếu backend giữ connection 24/7, Neon có thể không scale-to-zero và đốt CU-hours. Có thể giảm pool size trong `database.py` nếu cần.

---

## 9. Checklist bảo mật

- [ ] Đổi mật khẩu admin sau lần đăng nhập đầu.
- [ ] `JWT_SECRET_KEY` là chuỗi random dài, không dùng giá trị mẫu.
- [ ] `ALLOW_PUBLIC_REGISTRATION=false` nếu chỉ muốn admin tạo user.
- [ ] `BACKEND_CORS_ORIGINS` chỉ chứa domain thật.
- [ ] Không commit `.env` hoặc API key.
- [ ] Không đưa `GEMINI_API_KEY` vào frontend.
- [ ] Cân nhắc thêm rate limit cho `/auth/login` nếu public lâu dài.
- [ ] Không upload tài liệu nhạy cảm lên Gemini free tier.

---

## 10. Tóm tắt lệnh deploy

```powershell
# 1. Kiểm tra code local
cd rag_chatbot_backend
python -m compileall app

# 2. Push code
cd ..
git add .
git commit -m "Add Gemini embedding provider and free deployment config"
git push

# 3. Render: tạo Blueprint/Web Service, nhập env, deploy
# 4. Vercel: import frontend, set NEXT_PUBLIC_API_URL, deploy
# 5. Cập nhật BACKEND_CORS_ORIGINS bằng domain Vercel
# 6. Đăng nhập admin/admin123 -> đổi mật khẩu -> upload tài liệu
```
