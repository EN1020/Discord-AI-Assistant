import unittest

from discord_ai_bot.openai_utils import collect_sources, extract_output_text


class OpenAIUtilsTests(unittest.TestCase):
    def test_extract_output_text_from_response_shape(self):
        data = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "hello"},
                        {"type": "output_text", "text": " world"},
                    ]
                }
            ]
        }
        self.assertEqual(extract_output_text(data), "hello world")

    def test_collect_sources_from_web_search_sources_and_annotations(self):
        data = {
            "output": [
                {
                    "action": {
                        "sources": [
                            {"title": "One", "url": "https://one.example"},
                            {"title": "One again", "url": "https://one.example"},
                        ]
                    }
                },
                {
                    "content": [
                        {
                            "annotations": [
                                {"type": "url_citation", "title": "Two", "url": "https://two.example"}
                            ]
                        }
                    ]
                },
            ]
        }
        sources = collect_sources(data)
        self.assertEqual([source.url for source in sources], ["https://one.example", "https://two.example"])


if __name__ == "__main__":
    unittest.main()
