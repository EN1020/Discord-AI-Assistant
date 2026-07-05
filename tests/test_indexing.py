import json
import tempfile
import unittest
from pathlib import Path

from discord_ai_bot.indexing import chunk_text, load_docs, rec_to_text


class IndexingTests(unittest.TestCase):
    def test_rec_to_text_formats_faq_records(self):
        text = rec_to_text(
            {
                "question": "問題？",
                "answer": "答案。",
                "keywords_zh": ["測試", "索引"],
                "tags": ["faq"],
            }
        )
        self.assertIn("Q: 問題？", text)
        self.assertIn("A: 答案。", text)
        self.assertIn("keywords_zh: 測試, 索引", text)

    def test_chunk_text_overlaps_large_text(self):
        text = "\n\n".join(f"section {index} " + ("x" * 120) for index in range(10))
        chunks = chunk_text(text, max_chars=250, overlap=50)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 300 for chunk in chunks))

    def test_load_docs_reads_json_and_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "faq.json").write_text(
                json.dumps([{"id": "one", "question": "Q?", "answer": "A."}], ensure_ascii=False),
                encoding="utf-8",
            )
            (root / "note.txt").write_text("hello local docs", encoding="utf-8")

            docs = load_docs(root, chunk_chars=100, chunk_overlap=10)

        ids = {item["id"] for item in docs}
        self.assertIn("one", ids)
        self.assertIn("note.txt", ids)

    def test_load_docs_deduplicates_same_record_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = [{"id": "same", "question": "Q?", "answer": "A."}]
            (root / "one.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            (root / "two.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            docs = load_docs(root, chunk_chars=100, chunk_overlap=10)

        self.assertEqual([item["id"] for item in docs].count("same"), 1)


if __name__ == "__main__":
    unittest.main()
