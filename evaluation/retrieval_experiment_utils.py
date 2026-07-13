"""Utilities for building more faithful retrieval experiments."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence


EN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}

ZH_STOPWORDS = {
    "一个",
    "一些",
    "以及",
    "公司",
    "市场",
    "我们",
    "显示",
    "表示",
    "认为",
    "进行",
    "相关",
    "其中",
    "今日",
    "最新",
    "消息",
    "业务",
    "风险",
    "港股",
    "股份",
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _ensure_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_clean_text(item) for item in value if _clean_text(item)]
    if isinstance(value, str):
        if "," in value:
            return [_clean_text(item) for item in value.split(",") if _clean_text(item)]
        cleaned = _clean_text(value)
        return [cleaned] if cleaned else []
    cleaned = _clean_text(value)
    return [cleaned] if cleaned else []


def normalize_stock_code(stock_code: Optional[str]) -> str:
    if not stock_code:
        return ""
    code = _clean_text(stock_code).upper()
    match = re.fullmatch(r"(?:0*)?(\d{1,5})(?:\.HK)?", code)
    if match:
        return f"{int(match.group(1)):05d}.HK"
    return code


def build_searchable_text(item: Dict[str, Any]) -> str:
    title = _clean_text(item.get("title"))
    content = _clean_text(item.get("content"))
    stock_names = _ensure_list(item.get("stock_names"))
    stock_codes = [normalize_stock_code(code) for code in _ensure_list(item.get("stock_codes"))]
    source_type = _clean_text(item.get("source_type"))

    sections = []
    if title:
        sections.append(f"标题: {title}")
    if stock_names:
        sections.append(f"股票名称: {' '.join(stock_names)}")
    if stock_codes:
        sections.append(f"股票代码: {' '.join(stock_codes)}")
    if source_type:
        sections.append(f"来源类型: {source_type}")
    if content:
        sections.append(f"正文: {content}")
    return "\n".join(sections).strip()


def build_query_text(item: Dict[str, Any], max_chars: int = 120) -> str:
    title = _clean_text(item.get("title"))
    content = _clean_text(item.get("content"))
    stock_names = _ensure_list(item.get("stock_names"))
    stock_codes = [normalize_stock_code(code) for code in _ensure_list(item.get("stock_codes"))]

    query_core = title or content[:max_chars]
    prefix_parts = []
    if stock_names:
        prefix_parts.append(stock_names[0])
    if stock_codes:
        prefix_parts.append(stock_codes[0])

    query = " ".join(part for part in prefix_parts + [query_core] if part).strip()
    return query[:max_chars]


def _tokenize_topic_terms(text: str) -> List[str]:
    tokens: List[str] = []
    text = _clean_text(text).lower()
    fragments = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+(?:\.[a-z]{2,})?", text)

    for fragment in fragments:
        if re.search(r"[\u4e00-\u9fff]", fragment):
            if fragment in ZH_STOPWORDS:
                continue
            if len(fragment) <= 2:
                tokens.append(fragment)
                continue
            for i in range(len(fragment) - 1):
                bigram = fragment[i : i + 2]
                if bigram not in ZH_STOPWORDS:
                    tokens.append(bigram)
        else:
            if fragment in EN_STOPWORDS or fragment.isdigit():
                continue
            tokens.append(fragment)
            normalized_code = normalize_stock_code(fragment)
            if normalized_code and normalized_code != fragment.upper():
                tokens.append(normalized_code.lower())

    return tokens


def _document_term_weights(item: Dict[str, Any]) -> Counter:
    title = _clean_text(item.get("title"))
    content = _clean_text(item.get("content"))[:500]
    combined = Counter()
    for token in _tokenize_topic_terms(title):
        combined[token] += 2
    for token in _tokenize_topic_terms(content):
        combined[token] += 1
    return combined


def _parse_date(value: Any) -> Optional[datetime]:
    text = _clean_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def document_topic_similarity(source_doc: Dict[str, Any], candidate_doc: Dict[str, Any]) -> float:
    source_terms = _document_term_weights(source_doc)
    candidate_terms = _document_term_weights(candidate_doc)
    if not source_terms or not candidate_terms:
        return 0.0

    overlap = set(source_terms) & set(candidate_terms)
    if not overlap:
        return 0.0

    weighted_overlap = sum(min(source_terms[term], candidate_terms[term]) for term in overlap)
    total_weight = sum(source_terms.values()) + sum(candidate_terms.values()) - weighted_overlap
    similarity = weighted_overlap / max(total_weight, 1)

    source_date = _parse_date(source_doc.get("published_at"))
    candidate_date = _parse_date(candidate_doc.get("published_at"))
    if source_date and candidate_date:
        day_gap = abs((source_date - candidate_date).days)
        if day_gap <= 7:
            similarity += 0.05
        elif day_gap <= 30:
            similarity += 0.02

    if _clean_text(source_doc.get("source_type")) == _clean_text(candidate_doc.get("source_type")):
        similarity += 0.01

    return similarity


def select_relevant_documents(
    source_doc: Dict[str, Any],
    candidate_docs: Sequence[Dict[str, Any]],
    max_relevant_docs: int = 3,
    min_topic_overlap: float = 0.08,
    min_shared_terms: int = 2,
) -> List[str]:
    source_id = _clean_text(source_doc.get("text_id"))
    source_terms = set(_document_term_weights(source_doc))
    ranked: List[tuple[float, str]] = []

    for candidate_doc in candidate_docs:
        candidate_id = _clean_text(candidate_doc.get("text_id"))
        if not candidate_id or candidate_id == source_id:
            continue

        candidate_terms = set(_document_term_weights(candidate_doc))
        shared_terms = len(source_terms & candidate_terms)
        similarity = document_topic_similarity(source_doc, candidate_doc)
        if similarity < min_topic_overlap or shared_terms < min_shared_terms:
            continue

        ranked.append((similarity, candidate_id))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [candidate_id for _, candidate_id in ranked[:max_relevant_docs]]


def generate_test_queries_from_documents(
    raw_data: Sequence[Dict[str, Any]],
    min_docs_per_stock: int = 2,
    max_queries_per_stock: int = 3,
    max_relevant_docs: int = 3,
    min_topic_overlap: float = 0.08,
) -> List[Dict[str, Any]]:
    stocks_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in raw_data:
        for stock_code in _ensure_list(item.get("stock_codes")):
            normalized = normalize_stock_code(stock_code)
            if normalized:
                stocks_data[normalized].append(item)

    queries: List[Dict[str, Any]] = []
    for stock_code, docs in stocks_data.items():
        if len(docs) < min_docs_per_stock:
            continue

        docs_by_richness = sorted(
            docs,
            key=lambda doc: len(_clean_text(doc.get("title"))) + len(_clean_text(doc.get("content"))),
            reverse=True,
        )

        generated = 0
        for doc in docs_by_richness:
            relevant_ids = select_relevant_documents(
                source_doc=doc,
                candidate_docs=docs,
                max_relevant_docs=max_relevant_docs,
                min_topic_overlap=min_topic_overlap,
            )
            if not relevant_ids:
                continue

            query = build_query_text(doc)
            source_text_id = _clean_text(doc.get("text_id"))
            if not query or not source_text_id:
                continue

            queries.append(
                {
                    "query": query,
                    "stock_code": stock_code,
                    "relevant_ids": relevant_ids,
                    "source_text_id": source_text_id,
                    "exclude_text_ids": [source_text_id],
                }
            )
            generated += 1
            if generated >= max_queries_per_stock:
                break

    return queries


def load_annotated_test_queries(path: str) -> List[Dict[str, Any]]:
    import json

    queries: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            stock_code = normalize_stock_code(record.get("stock_code"))
            relevant_ids = list(record.get("relevant_ids", []))
            if not stock_code or not record.get("query") or not relevant_ids:
                continue
            queries.append(
                {
                    "query": _clean_text(record["query"]),
                    "stock_code": stock_code,
                    "relevant_ids": relevant_ids,
                    "exclude_text_ids": list(record.get("exclude_text_ids", [])),
                    "source_text_id": _clean_text(record.get("source_text_id")),
                    "relevance_scores": record.get("relevance_scores", {}),
                }
            )
    return queries
