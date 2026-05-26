#!/usr/bin/env python3
"""
ReAct Agent 最小可行示例（PoC）

前置：已运行 run_rag_retrieval_experiment.py 构建 ./rag_db
环境：LLM_API_KEY（DeepSeek 等）、DASHSCOPE_API_KEY（Embedding，与 RAG 一致）

用法:
  python run_react_agent_poc.py
  python run_react_agent_poc.py --stock 09988.HK --question "近期监管与舆情风险如何？"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agent.sentinel_agent import (
    create_sentinel_agent,
    default_vector_store,
    run_agent_query,
    run_offline_react_demo,
)


def _check_vector_store(vs) -> int:
    try:
        return vs.collection.count()
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description="Sentinel ReAct Agent PoC")
    parser.add_argument("--stock", default="09988.HK", help="港股代码，如 09988.HK")
    parser.add_argument(
        "--question",
        default="结合近期新闻和股价，评估该股票是否存在监管或业绩方面的舆情风险？",
        help="分析问题",
    )
    parser.add_argument(
        "--db",
        default="./rag_db",
        help="ChromaDB 目录（与 RAG 实验相同）",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="离线演示：不调用 LLM，按 ReAct 链执行工具并规则合成结论",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("Sentinel ReAct Agent — PoC")
    print("=" * 70)

    if not Path(args.db).exists():
        print(f"\n❌ 未找到向量库目录 {args.db}")
        print("   请先运行: python run_rag_retrieval_experiment.py")
        sys.exit(1)

    vs = default_vector_store()
    n_docs = _check_vector_store(vs)
    print(f"\n📦 向量库: {args.db}  |  文档数: {n_docs}")
    if n_docs == 0:
        print("❌ 向量库为空，请先构建 RAG 索引")
        sys.exit(1)

    print(f"📌 股票: {args.stock}")
    print(f"❓ 问题: {args.question}\n")

    if args.offline:
        print("🔄 离线 ReAct 演示（检索 → 摘要 → 行情 → 合成）...\n")
        out = run_offline_react_demo(vs, args.question, args.stock)
    else:
        try:
            agent = create_sentinel_agent(vs)
        except ValueError as e:
            print(f"❌ {e}")
            print("   提示: 使用 --offline 可在无 LLM 时验证工具链与 RAG 集成")
            sys.exit(1)

        print("🔄 Agent 推理中（LangGraph ReAct + LLM）...\n")
        try:
            out = run_agent_query(agent, args.question, stock_code=args.stock)
        except Exception as e:
            err = str(e)
            if "403" in err or "unsupported_country" in err.lower():
                print("⚠️  LLM 不可用，自动切换为离线 ReAct 演示\n")
                out = run_offline_react_demo(vs, args.question, args.stock)
            else:
                raise

    print("【工具调用轨迹】")
    if not out["tool_trace"]:
        print("  (无工具调用 — 请检查 LLM 是否支持 function calling)")
    for step in out["tool_trace"]:
        if "thought" in step:
            print(f"  💭 {step['thought']}")
        elif "tool" in step:
            print(f"  → 调用 {step['tool']}({json.dumps(step['args'], ensure_ascii=False)})")
        elif "tool_result" in step:
            print(f"  ← {step['tool_result']}: {step['preview']}")

    print("\n【Agent 最终输出】")
    print(out["answer"])

    report_path = Path("react_agent_poc_result.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 完整结果已保存: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
