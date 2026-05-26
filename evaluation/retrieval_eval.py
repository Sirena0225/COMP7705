"""
RAG retrieval quality evaluation metrics
"""
from typing import List, Dict, Any
import numpy as np

def calculate_mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """
    Calculate Mean Reciprocal Rank
    Returns 1/rank of first relevant document, or 0 if none found
    """
    for rank, doc_id in enumerate(retrieved_ids, 1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0

def calculate_recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int = 5) -> float:
    """
    Calculate Recall@k: proportion of relevant docs retrieved in top-k
    """
    if not relevant_ids:
        return 1.0  # No relevant docs = perfect recall
    retrieved_top_k = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    return len(retrieved_top_k & relevant_set) / len(relevant_set)

def calculate_ndcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int = 5) -> float:
    """
    Calculate NDCG@k: Normalized Discounted Cumulative Gain
    Assumes binary relevance (1 if relevant, 0 otherwise)
    """
    def dcg(ids, relevant_set, max_k):
        score = 0.0
        for rank, doc_id in enumerate(ids[:max_k], 1):
            if doc_id in relevant_set:
                score += 1.0 / np.log2(rank + 1)
        return score
    
    relevant_set = set(relevant_ids)
    dcg_score = dcg(retrieved_ids, relevant_set, k)
    
    # Ideal DCG: all relevant docs at top positions
    ideal_ids = relevant_ids + [f"dummy_{i}" for i in range(k - len(relevant_ids))]
    idcg_score = dcg(ideal_ids, relevant_set, k)
    
    return dcg_score / idcg_score if idcg_score > 0 else 0.0

def evaluate_retrieval_quality(
    vector_store,
    test_queries: List[Dict[str, Any]],
    k_values: List[int] = [1, 3, 5, 10]
) -> Dict[str, float]:
    """
    Evaluate retrieval quality on annotated test set
    
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
    results = {f"recall@{k}": [] for k in k_values}
    results["mrr"] = []
    results["ndcg@5"] = []
    
    for query_item in test_queries:
        retrieved = vector_store.search(
            query=query_item["query"],
            stock_code=query_item.get("stock_code"),
            n_results=max(k_values)
        )
        retrieved_ids = [doc["id"] for doc in retrieved]
        relevant_ids = query_item["relevant_ids"]
        
        # Calculate metrics
        results["mrr"].append(calculate_mrr(retrieved_ids, relevant_ids))
        results["ndcg@5"].append(calculate_ndcg_at_k(retrieved_ids, relevant_ids, k=5))
        
        for k in k_values:
            results[f"recall@{k}"].append(
                calculate_recall_at_k(retrieved_ids, relevant_ids, k=k)
            )
    
    # Aggregate results
    return {
        metric: float(np.mean(values)) if values else 0.0
        for metric, values in results.items()
    }