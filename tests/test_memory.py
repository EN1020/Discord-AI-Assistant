import unittest

from discord_ai_bot.memory import ConversationKey, ConversationMemory


class ConversationMemoryTests(unittest.TestCase):
    def test_memory_is_scoped_and_trimmed(self):
        memory = ConversationMemory(max_messages=3)
        key_a = ConversationKey(guild_id=1, channel_id=2, user_id=3)
        key_b = ConversationKey(guild_id=1, channel_id=2, user_id=4)

        memory.add_user(key_a, "one")
        memory.add_assistant(key_a, "two")
        memory.add_user(key_a, "three")
        memory.add_assistant(key_a, "four")
        memory.add_user(key_b, "other")

        self.assertEqual(
            memory.snapshot(key_a),
            [
                {"role": "assistant", "content": "two"},
                {"role": "user", "content": "three"},
                {"role": "assistant", "content": "four"},
            ],
        )
        self.assertEqual(memory.snapshot(key_b), [{"role": "user", "content": "other"}])

    def test_clear_removes_only_that_key(self):
        memory = ConversationMemory(max_messages=4)
        key = ConversationKey(guild_id=1, channel_id=1, user_id=1)
        memory.add_user(key, "hello")
        memory.clear(key)
        self.assertEqual(memory.snapshot(key), [])


if __name__ == "__main__":
    unittest.main()
