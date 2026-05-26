"""
RAG retrieval quality evaluation metrics
"""
import time
from typing import List, Dict, Any
import numpy as np


def calculate_top1_accuracy(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """Top-1 Accuracy: 1 if the first retrieved doc is relevant, else 0."""
    if not retrieved_ids or not relevant_ids:
        return 0.0
    return 1.0 if retrieved_ids[0] in relevant_ids else 0.0


def calculate_mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """Mean Reciprocal Rank component for a single query."""
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, 1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


def calculate_recall_at_k(
    retrieved_ids: List[str], relevant_ids: List[str], k: int = 5
) -> float:
    """Recall@k: proportion of relevant docs found in top-k."""
    if not relevant_ids:
        return 1.0
    retrieved_top_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    return len(retrieved_top_k & relevant_set) / len(relevant_set)


def calculate_ndcg_at_k(
    retrieved_ids: List[str], relevant_ids: List[str], k: int = 5
) -> float:
    """NDCG@k with binary relevance."""
    def dcg(ids, relevant_set, max_k):
        score = 0.0
        for rank, doc_id in enumerate(ids[:max_k], 1):
            if doc_id in relevant_set:
                score += 1.0 / np.log2(rank + 1)
        return score

    relevant_set = set(relevant_ids)
    dcg_score = dcg(retrieved_ids, relevant_set, k)

    ideal_ids = relevant_ids + [f"dummy_{i}" for i in range(k - len(relevant_ids))]
    idcg_score = dcg(ideal_ids, relevant_set, k)

    return dcg_score / idcg_score if idcg_score > 0 else 0.0


def evaluate_retrieval_quality(
    vector_store,
    test_queries: List[Dict[str, Any]],
    retrieval_k: int = 10,
) -> Dict[str, float]:
    """
    Evaluate retrieval quality on annotated test set.

    Returns standard RAG retrieval metrics:
      - top1_accuracy
      - top5_recall
      - mrr
      - ndcg@5
      - avg_retrieval_latency_ms

    test_queries format:
    [
        {
            "query": "search text",
            "stock_code": "00700.HK",
            "relevant_ids": ["doc_id_1", "doc_id_2", ...]
        },
        ...
    ]
    """
    per_query = {
        "top1_accuracy": [],
        "top5_recall": [],
        "mrr": [],
        "ndcg@5": [],
        "retrieval_latency_ms": [],
    }

    for query_item in test_queries:
        t0 = time.perf_counter()
        retrieved = vector_store.search(
            query=query_item["query"],
            stock_code=query_item.get("stock_code"),
            n_results=retrieval_k,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        retrieved_ids = [
            doc["metadata"].get("text_id", doc["id"]) for doc in retrieved
        ]
        relevant_ids = query_item["relevant_ids"]

        per_query["top1_accuracy"].append(
            calculate_top1_accuracy(retrieved_ids, relevant_ids)
        )
        per_query["top5_recall"].append(
            calculate_recall_at_k(retrieved_ids, relevant_ids, k=5)
        )
        per_query["mrr"].append(calculate_mrr(retrieved_ids, relevant_ids))
        per_query["ndcg@5"].append(
            calculate_ndcg_at_k(retrieved_ids, relevant_ids, k=5)
        )
        per_query["retrieval_latency_ms"].append(latency_ms)

    def mean(values: List[float]) -> float:
        return float(np.mean(values)) if values else 0.0

    return {
        "top1_accuracy": mean(per_query["top1_accuracy"]),
        "top5_recall": mean(per_query["top5_recall"]),
        "mrr": mean(per_query["mrr"]),
        "ndcg@5": mean(per_query["ndcg@5"]),
        "avg_retrieval_latency_ms": mean(per_query["retrieval_latency_ms"]),
        "num_queries": len(test_queries),
    }
