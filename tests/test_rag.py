import unittest

import numpy as np

from discord_ai_bot.rag import RAG, _l2_normalize


class RagTests(unittest.TestCase):
    def test_l2_normalize(self):
        vector = _l2_normalize(np.array([3.0, 4.0], dtype="float32"))
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0)

    def test_search_orders_by_cosine_score(self):
        rag = RAG.__new__(RAG)
        rag.X = np.array([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
        rag.meta = [{"id": "x"}, {"id": "y"}]

        hits = rag._search([0.9, 0.1], k=2)

        self.assertEqual(hits[0][0]["id"], "x")
        self.assertGreater(hits[0][1], hits[1][1])


if __name__ == "__main__":
    unittest.main()
