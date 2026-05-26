"""
Sentinel ReAct Agent — 结合 RAG 检索与行情工具的金融舆情分析 PoC。
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from tools.financial_tools import (
    bind_vector_store,
    get_agent_tools,
    get_stock_price,
    search_financial_news,
    summarize_stock_news,
)
from vector_storage import VectorStore

load_dotenv()

SYSTEM_PROMPT = """你是港股舆情分析 Agent（Sentinel），负责结合检索证据与行情数据给出风险判断。

工作流程（ReAct）：
1. 收到用户问题后，先判断是否需要检索新闻（search_financial_news / summarize_stock_news）。
2. 若涉及股价表现或市场反应，可调用 get_stock_price。
3. 综合工具返回的 JSON 证据，输出结构化结论。

输出要求（最终回复必须是合法 JSON，不要 markdown 代码块）：
{
  "stock_code": "09988.HK",
  "summary": "100字以内结论",
  "sentiment": "positive|neutral|negative",
  "risk_level": "low|medium|high",
  "key_evidence": ["证据1", "证据2"],
  "tools_used": ["工具名列表"]
}

约束：
- 不得编造工具未返回的事实；证据不足时 risk_level 标为 medium 并在 summary 说明。
- stock_code 使用 .HK 后缀。
"""


def _create_chat_model():
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("未设置 LLM_API_KEY，无法运行 ReAct Agent（请在 .env 中配置）")

    model_name = os.getenv("LLM_MODEL", "deepseek-chat")
    kwargs: Dict[str, Any] = {
        "model": model_name,
        "api_key": api_key,
        "temperature": 0.1,
    }
    if "deepseek" in model_name.lower():
        kwargs["base_url"] = "https://api.deepseek.com/v1"
    return ChatOpenAI(**kwargs)


def create_sentinel_agent(
    vector_store: VectorStore,
    *,
    model: Optional[Any] = None,
):
    """
    创建已绑定向量库的 ReAct Agent。

    vector_store 应与 RAG 实验共用（默认 ./rag_db, collection rag_retrieval_test）。
    """
    bind_vector_store(vector_store)
    llm = model or _create_chat_model()
    return create_react_agent(
        model=llm,
        tools=get_agent_tools(),
        prompt=SYSTEM_PROMPT,
    )


def _extract_tool_trace(messages: List[Any]) -> List[Dict[str, Any]]:
    """从 LangGraph 消息列表提取工具调用轨迹（便于 PoC 演示）。"""
    trace = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                trace.append(
                    {
                        "tool": tc.get("name"),
                        "args": tc.get("args"),
                    }
                )
        elif isinstance(msg, ToolMessage):
            preview = msg.content if isinstance(msg.content, str) else str(msg.content)
            trace.append(
                {
                    "tool_result": msg.name,
                    "preview": preview[:200] + ("..." if len(preview) > 200 else ""),
                }
            )
    return trace


def run_agent_query(
    agent,
    question: str,
    stock_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行单次 Agent 查询，返回最终回复与工具调用轨迹。
    """
    user_text = question
    if stock_code:
        user_text = f"[股票: {stock_code}]\n{question}"

    result = agent.invoke({"messages": [HumanMessage(content=user_text)]})
    messages = result.get("messages", [])
    final = messages[-1].content if messages else ""

    return {
        "question": question,
        "stock_code": stock_code,
        "answer": final,
        "tool_trace": _extract_tool_trace(messages),
        "message_count": len(messages),
    }


def default_vector_store() -> VectorStore:
    """加载 RAG 实验默认向量库。"""
    return VectorStore(
        collection_name=os.getenv("RAG_COLLECTION", "rag_retrieval_test"),
        persist_directory=os.getenv("RAG_DB_PATH", "./rag_db"),
        use_enhanced_embedding=True,
    )


def run_offline_react_demo(
    vector_store: VectorStore,
    question: str,
    stock_code: str,
) -> Dict[str, Any]:
    """
    离线 ReAct 演示：不调用 LLM，按固定推理链执行工具并合成 JSON 结论。
    用于验证「检索 → 行情 → 综合」架构，以及 rag_db 数据可被 Agent 工具消费。
    """
    import json as _json

    bind_vector_store(vector_store)
    trace: List[Dict[str, Any]] = []

    # ReAct Step 1 — 检索新闻证据
    trace.append({"thought": "需要先从向量库检索与问题相关的新闻片段"})
    news_raw = search_financial_news.invoke(
        {"query": question, "stock_code": stock_code, "top_k": 5}
    )
    trace.append({"tool": "search_financial_news", "args": {"query": question, "stock_code": stock_code}})
    trace.append({"tool_result": "search_financial_news", "preview": news_raw[:220]})

    news_data = _json.loads(news_raw)
    hit_count = len(news_data.get("results", []))

    # ReAct Step 2 — 补充舆情摘要
    trace.append({"thought": "聚合该股票多片段摘要以把握整体舆情"})
    summary_raw = summarize_stock_news.invoke(
        {"stock_code": stock_code, "topic": "regulatory risk earnings sentiment"}
    )
    trace.append(
        {
            "tool": "summarize_stock_news",
            "args": {"stock_code": stock_code, "topic": "regulatory risk earnings sentiment"},
        }
    )
    trace.append({"tool_result": "summarize_stock_news", "preview": summary_raw[:220]})

    # ReAct Step 3 — 行情交叉验证
    trace.append({"thought": "拉取最新股价涨跌幅，辅助判断市场反应"})
    price_raw = get_stock_price.invoke({"stock_code": stock_code})
    trace.append({"tool": "get_stock_price", "args": {"stock_code": stock_code}})
    trace.append({"tool_result": "get_stock_price", "preview": price_raw})

    price_data = _json.loads(price_raw)
    change = price_data.get("change_pct", 0)

    # 规则合成（PoC）
    risk_keywords = ("监管", "调查", "处罚", "risk", "regulatory", "fine", "miss", "亏损")
    combined_text = news_raw.lower() + summary_raw.lower()
    has_risk_signal = any(k in combined_text for k in risk_keywords)

    if has_risk_signal or (isinstance(change, (int, float)) and change < -2):
        risk_level = "high" if has_risk_signal else "medium"
        sentiment = "negative"
    elif isinstance(change, (int, float)) and change > 1:
        risk_level = "low"
        sentiment = "positive"
    else:
        risk_level = "medium"
        sentiment = "neutral"

    snippets = [r.get("snippet", "") for r in news_data.get("results", [])[:3]]
    answer = {
        "stock_code": stock_code,
        "summary": (
            f"向量库命中 {hit_count} 条相关文档；"
            f"股价近一期涨跌 {change}%。"
            f"{'检索到监管/风险相关表述，建议关注。' if has_risk_signal else '未发现明显监管负面关键词。'}"
        ),
        "sentiment": sentiment,
        "risk_level": risk_level,
        "key_evidence": snippets,
        "tools_used": [
            "search_financial_news",
            "summarize_stock_news",
            "get_stock_price",
        ],
        "mode": "offline_react_demo",
    }

    return {
        "question": question,
        "stock_code": stock_code,
        "answer": _json.dumps(answer, ensure_ascii=False, indent=2),
        "tool_trace": trace,
        "message_count": len(trace),
        "mode": "offline",
    }
