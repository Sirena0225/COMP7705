"""
ReAct Agent 工具：对接 RAG 向量库与行情数据。
"""

from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING

import yfinance as yf
from langchain_core.tools import tool

if TYPE_CHECKING:
    from vector_storage import VectorStore

_vector_store: Optional["VectorStore"] = None


def bind_vector_store(store: "VectorStore") -> None:
    """在创建 Agent 前注入已构建的 VectorStore（与 RAG 实验共用 rag_db）。"""
    global _vector_store
    _vector_store = store


@tool
def search_financial_news(query: str, stock_code: str, top_k: int = 5) -> str:
    """
    在 ChromaDB 向量库中语义检索与 query 相关的港股新闻/公告片段。
    stock_code 须带 .HK 后缀，例如 09988.HK、00700.HK。
  top_k 为返回条数，默认 5。
    """
    if _vector_store is None:
        return json.dumps({"error": "向量库未初始化，请先运行 RAG 实验构建 rag_db"}, ensure_ascii=False)

    hits = _vector_store.search(query=query, stock_code=stock_code, n_results=top_k)
    if not hits:
        return json.dumps(
            {"stock_code": stock_code, "query": query, "results": [], "note": "未检索到相关文档"},
            ensure_ascii=False,
        )

    rows = []
    for i, h in enumerate(hits, 1):
        meta = h.get("metadata") or {}
        rows.append(
            {
                "rank": i,
                "text_id": meta.get("text_id", h.get("id")),
                "similarity": round(h.get("similarity_score", 0), 4),
                "source": meta.get("source", "unknown"),
                "published_at": meta.get("published_at", ""),
                "snippet": (h.get("content") or "")[:280],
            }
        )
    return json.dumps({"stock_code": stock_code, "query": query, "results": rows}, ensure_ascii=False)


@tool
def summarize_stock_news(stock_code: str, topic: str = "recent risks and sentiment") -> str:
    """
    针对某只股票检索与 topic 相关的多条新闻摘要（向量检索 + 聚合），
    用于快速了解舆情概况。stock_code 例如 09988.HK。
    """
    if _vector_store is None:
        return json.dumps({"error": "向量库未初始化"}, ensure_ascii=False)

    hits = _vector_store.search(
        query=f"{stock_code} {topic}",
        stock_code=stock_code,
        n_results=8,
    )
    snippets = [(h.get("content") or "")[:160] for h in hits]
    return json.dumps(
        {
            "stock_code": stock_code,
            "topic": topic,
            "hit_count": len(snippets),
            "snippets": snippets,
        },
        ensure_ascii=False,
    )


@tool
def get_stock_price(stock_code: str) -> str:
    """
    获取港股最新收盘价与涨跌幅（yfinance）。
    stock_code 须为 yfinance 格式，如 09988.HK。
    """
    try:
        # yfinance 对部分港股代码更认 9988.HK 而非 09988.HK
        candidates = [stock_code]
        if stock_code.endswith(".HK") and stock_code[:-3].isdigit():
            stripped = stock_code[:-3].lstrip("0") or "0"
            alt = f"{stripped}.HK"
            if alt != stock_code:
                candidates.append(alt)

        hist = None
        used_code = stock_code
        for code in candidates:
            hist = yf.Ticker(code).history(period="5d")
            if hist is not None and not hist.empty:
                used_code = code
                break
        if hist is None or hist.empty:
            return json.dumps({"error": f"无行情数据: {stock_code}"}, ensure_ascii=False)
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        change_pct = (latest["Close"] - prev["Close"]) / prev["Close"] * 100
        return json.dumps(
            {
                "stock_code": stock_code,
                "yf_symbol": used_code,
                "close": round(float(latest["Close"]), 2),
                "change_pct": round(float(change_pct), 2),
                "volume": int(latest["Volume"]),
                "as_of": str(hist.index[-1].date()),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e), "stock_code": stock_code}, ensure_ascii=False)


def get_agent_tools():
    """返回注册给 ReAct Agent 的工具列表。"""
    return [search_financial_news, summarize_stock_news, get_stock_price]
