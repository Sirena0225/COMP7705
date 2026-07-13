import unittest

from evaluation.retrieval_experiment_utils import (
    build_searchable_text,
    generate_test_queries_from_documents,
    normalize_stock_code,
    select_relevant_documents,
)


class RetrievalExperimentUtilsTests(unittest.TestCase):
    def test_build_searchable_text_includes_title_and_stock_metadata(self):
        text = build_searchable_text(
            {
                "title": "腾讯面临监管审查",
                "content": "腾讯云业务回应合规问题。",
                "stock_names": ["腾讯控股"],
                "stock_codes": ["700"],
                "source_type": "news",
            }
        )

        self.assertIn("腾讯面临监管审查", text)
        self.assertIn("腾讯控股", text)
        self.assertIn("00700.HK", text)
        self.assertIn("腾讯云业务回应合规问题", text)

    def test_select_relevant_documents_filters_unrelated_same_stock_docs(self):
        source_doc = {
            "text_id": "doc_a",
            "title": "阿里国际业务接受监管审查",
            "content": "跨境电商 合规 审查 数据 隐私",
            "source_type": "news",
            "published_at": "2026-06-01T10:00:00",
        }
        related_doc = {
            "text_id": "doc_b",
            "title": "阿里跨境电商合规整改进展",
            "content": "监管 审查 合规 隐私 业务 调整",
            "source_type": "news",
            "published_at": "2026-06-03T10:00:00",
        }
        unrelated_doc = {
            "text_id": "doc_c",
            "title": "阿里云季度收入创新高",
            "content": "云计算 业绩 增长 利润率 提升",
            "source_type": "announcement",
            "published_at": "2026-06-02T10:00:00",
        }

        relevant_ids = select_relevant_documents(
            source_doc=source_doc,
            candidate_docs=[related_doc, unrelated_doc],
        )

        self.assertIn("doc_b", relevant_ids)
        self.assertNotIn("doc_c", relevant_ids)

    def test_generate_queries_marks_source_doc_for_exclusion(self):
        raw_data = [
            {
                "text_id": "doc_a",
                "title": "腾讯游戏业务增长但遭遇监管审查",
                "content": "游戏 业务 增长 监管 审查 未成年人",
                "stock_codes": ["00700.HK"],
                "stock_names": ["腾讯控股"],
                "source_type": "news",
            },
            {
                "text_id": "doc_b",
                "title": "腾讯未成年人保护整改进展",
                "content": "监管 审查 游戏 合规 整改 进展",
                "stock_codes": ["700"],
                "stock_names": ["腾讯控股"],
                "source_type": "news",
            },
        ]

        queries = generate_test_queries_from_documents(raw_data)

        self.assertEqual(len(queries), 2)
        self.assertEqual(queries[0]["stock_code"], "00700.HK")
        self.assertIn("source_text_id", queries[0])
        self.assertEqual(queries[0]["exclude_text_ids"], [queries[0]["source_text_id"]])
        self.assertEqual(normalize_stock_code("700"), "00700.HK")


if __name__ == "__main__":
    unittest.main()
