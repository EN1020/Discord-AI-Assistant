import unittest

from discord_ai_bot.discord_utils import append_sources, split_discord_message, strip_bot_mentions
from discord_ai_bot.openai_utils import Source


class DiscordUtilsTests(unittest.TestCase):
    def test_strip_bot_mentions_supports_nickname_mentions(self):
        self.assertEqual(strip_bot_mentions("<@123> hi", 123), "hi")
        self.assertEqual(strip_bot_mentions("<@!123> hi", 123), "hi")

    def test_split_discord_message_respects_limit(self):
        chunks = split_discord_message("hello " * 20, limit=30)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 30 for chunk in chunks))

    def test_append_sources(self):
        text = append_sources("answer", [Source(title="Example", url="https://example.com")])
        self.assertIn("Sources:", text)
        self.assertIn("https://example.com", text)


if __name__ == "__main__":
    unittest.main()
