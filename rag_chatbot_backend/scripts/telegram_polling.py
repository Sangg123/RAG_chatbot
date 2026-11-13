#!/usr/bin/env python3
"""Chạy Telegram bot bằng long polling (dành cho local development).

Cách chạy (từ thư mục rag_chatbot_backend):

    python scripts/telegram_polling.py

Yêu cầu:
- TELEGRAM_BOT_TOKEN trong .env
- Postgres + Ollama (hoặc EMBEDDING_PROVIDER=gemini) đang chạy
- Bot chưa được đăng ký webhook (script sẽ tự deleteWebhook)

Production nên dùng webhook thay vì polling:
    python scripts/telegram_webhook.py --url https://<backend>/api/v1/channels/telegram/webhook
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.telegram_service import run_polling  # noqa: E402


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        asyncio.run(run_polling())
    except KeyboardInterrupt:
        print("\nĐã dừng Telegram bot.")


if __name__ == "__main__":
    main()
