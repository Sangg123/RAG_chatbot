import unittest

from app.channels.base import parse_command
from app.channels.telegram import parse_update, split_telegram_text


def _private_update(text: str = "Xin chào") -> dict:
    return {
        "update_id": 100,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Nguyễn",
                "last_name": "An",
                "username": "nguyenan",
            },
            "chat": {"id": 123456789, "type": "private"},
            "date": 0,
            "text": text,
        },
    }


class ParseUpdateTests(unittest.TestCase):
    def test_private_text_message(self) -> None:
        incoming = parse_update(_private_update())
        self.assertIsNotNone(incoming)
        assert incoming is not None
        self.assertEqual(incoming.channel, "telegram")
        self.assertEqual(incoming.external_user_id, "123456789")
        self.assertEqual(incoming.external_chat_id, "123456789")
        self.assertEqual(incoming.display_name, "Nguyễn An")
        self.assertEqual(incoming.external_username, "nguyenan")
        self.assertTrue(incoming.is_private)

    def test_non_text_message_is_ignored(self) -> None:
        update = _private_update()
        update["message"].pop("text")
        update["message"]["sticker"] = {"file_id": "abc"}
        self.assertIsNone(parse_update(update))

    def test_edited_message_is_ignored(self) -> None:
        update = _private_update()
        update["edited_message"] = update.pop("message")
        self.assertIsNone(parse_update(update))

    def test_group_message_is_not_private(self) -> None:
        update = _private_update()
        update["message"]["chat"] = {"id": -100123, "type": "group"}
        incoming = parse_update(update)
        self.assertIsNotNone(incoming)
        assert incoming is not None
        self.assertFalse(incoming.is_private)
        self.assertEqual(incoming.external_chat_id, "-100123")


class ParseCommandTests(unittest.TestCase):
    def test_command_with_bot_mention(self) -> None:
        self.assertEqual(
            parse_command("/help@ShopBot"),
            ("/help", ""),
        )

    def test_command_with_arguments(self) -> None:
        self.assertEqual(
            parse_command("/link nguyen.van.an password123"),
            ("/link", "nguyen.van.an password123"),
        )

    def test_plain_text_is_not_command(self) -> None:
        self.assertIsNone(parse_command("Đơn DH123 ở đâu?"))


class SplitTelegramTextTests(unittest.TestCase):
    def test_short_text_is_kept(self) -> None:
        self.assertEqual(split_telegram_text("Xin chào"), ["Xin chào"])

    def test_empty_text_is_ignored(self) -> None:
        self.assertEqual(split_telegram_text("   "), [])

    def test_long_text_is_split_under_limit(self) -> None:
        paragraph = "Đây là một câu trả lời khá dài. " * 20
        chunks = split_telegram_text(paragraph, limit=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 100)
        self.assertEqual(
            "".join(chunks).replace(" ", ""),
            paragraph.strip().replace(" ", ""),
        )


if __name__ == "__main__":
    unittest.main()
