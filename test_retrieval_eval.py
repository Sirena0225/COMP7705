import unittest

from evaluation.retrieval_eval import evaluate_retrieval_quality


class FakeVectorStore:
    def __init__(self, results):
        self._results = results

    def search(self, query, stock_code=None, n_results=10):
        return self._results[:n_results]


class RetrievalEvalTests(unittest.TestCase):
    def test_excludes_source_text_before_scoring(self):
        vector_store = FakeVectorStore(
            [
                {"id": "doc_self", "metadata": {"text_id": "doc_self"}},
                {"id": "doc_peer", "metadata": {"text_id": "doc_peer"}},
                {"id": "doc_other", "metadata": {"text_id": "doc_other"}},
            ]
        )

        metrics = evaluate_retrieval_quality(
            vector_store,
            test_queries=[
                {
                    "query": "腾讯 监管 审查",
                    "stock_code": "00700.HK",
                    "relevant_ids": ["doc_peer"],
                    "source_text_id": "doc_self",
                    "exclude_text_ids": ["doc_self"],
                }
            ],
            retrieval_k=3,
        )

        self.assertEqual(metrics["top1_accuracy"], 1.0)
        self.assertEqual(metrics["top5_recall"], 1.0)
        self.assertEqual(metrics["mrr"], 1.0)


if __name__ == "__main__":
    unittest.main()
