#!/usr/bin/env python3
"""Đăng ký hoặc xóa webhook Telegram.

Cách dùng (từ thư mục rag_chatbot_backend):

    python scripts/telegram_webhook.py --url https://api.example.com/api/v1/channels/telegram/webhook
    python scripts/telegram_webhook.py --delete

Script đọc TELEGRAM_BOT_TOKEN và TELEGRAM_WEBHOOK_SECRET từ .env, nên token
không xuất hiện trong lịch sử shell.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.channels.telegram import (  # noqa: E402
    TELEGRAM_BOT_COMMANDS,
    TelegramAPIError,
    TelegramClient,
)
from app.config import get_settings  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not settings.telegram_bot_token:
        print(
            "Thiếu TELEGRAM_BOT_TOKEN trong .env. "
            "Tạo bot với @BotFather trước nhé.",
            file=sys.stderr,
        )
        return 1

    async with TelegramClient(settings.telegram_bot_token) as bot:
        try:
            if args.delete:
                result = await bot.delete_webhook(drop_pending_updates=False)
                print(f"Đã xóa webhook: {result}")
                return 0

            if not args.url:
                print(
                    "Cần --url https://<backend>/api/v1/channels/telegram/webhook",
                    file=sys.stderr,
                )
                return 1

            if not settings.telegram_webhook_secret:
                print(
                    "Cảnh báo: TELEGRAM_WEBHOOK_SECRET chưa đặt. "
                    "Backend sẽ từ chối webhook khi ENVIRONMENT != development.",
                    file=sys.stderr,
                )

            result = await bot.set_webhook(
                args.url,
                secret_token=settings.telegram_webhook_secret,
            )
            await bot.set_my_commands(TELEGRAM_BOT_COMMANDS)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except TelegramAPIError as exc:
            print(f"Lỗi Telegram: {exc}", file=sys.stderr)
            return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Đăng ký/xóa webhook Telegram cho RAG chatbot",
    )
    parser.add_argument(
        "--url",
        help="URL công khai của backend, ví dụ https://api.example.com/api/v1/channels/telegram/webhook",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Xóa webhook hiện tại để quay lại polling",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
