# 港股舆情多语言分析系统

面向港股新闻/公告的多语言情感分析、RAG 语义检索与在线 A/B 测试框架。课程与实验数据默认放在 `data/` 目录。

## 项目结构

```
COMP7705/
├── main.py                          # 主管线 + FastAPI 服务（:8001）
├── models.py                        # 共享数据模型
├── multilingual_preprocessor.py     # 多语言预处理
├── multilingual_analyzer.py           # 多语言 LLM 分析 + RAG 适配器
├── vector_storage.py                # ChromaDB 向量库 + RAG 检索
├── run_rag_retrieval_experiment.py  # RAG 检索精度实验（推荐）
├── run_react_agent_poc.py           # ReAct Agent PoC（依赖 rag_db + LLM）
├── agent/sentinel_agent.py          # LangGraph ReAct 编排
├── tools/financial_tools.py       # 向量检索 / 行情工具
├── evaluation/
│   └── retrieval_eval.py            # Top-1 / Recall@5 / MRR / NDCG@5 等指标
├── online_test_framework.py         # 在线测试主控
├── shadow_testing_env.py            # 影子 A/B 测试
├── evaluation_engine.py             # 评估引擎
├── metrics_tracker.py               # 指标持久化（SQLite）
├── feedback_controller.py           # 自动反馈调参
├── annotation_interface.py          # 人工标注任务
├── data_stream_sampler.py           # 数据流采样
├── json_data_loader.py              # JSON → 采样样本
├── demo_analysis.py                 # 离线舆情分析演示（Mock LLM）
├── demo_online_testing.py           # 在线测试演示
├── setup.py / setup_llm.py          # 环境安装与 API 校验
└── mocks/mock_llm.py                # 无 API 时的 Mock 分析器
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入密钥后编辑 .env
python setup.py        # 可选：创建目录与检查依赖
python setup_llm.py    # 可选：校验 LLM / Embedding API
```

### 2. 环境变量（`.env`）

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` | DeepSeek 等 LLM API Key（舆情分析） |
| `LLM_MODEL` | 默认 `deepseek-chat` |
| `DASHSCOPE_API_KEY` | 阿里云百炼 Key（**Embedding 默认使用**） |
| `DASHSCOPE_REGION` | `intl`（新加坡，默认）或 `cn`（北京） |
| `EMBEDDING_BACKEND` | `dashscope`（默认）/ `openai` / `local` / `auto` |
| `EMBEDDING_MODEL` | 默认 `text-embedding-v3` |

### 3. 常用命令

```bash
# RAG 检索精度实验（构建向量库 + 评估，结果写入 rag_experiment_results.json）
python run_rag_retrieval_experiment.py

# 离线舆情分析演示（无需 LLM Key，使用 Mock）
python demo_analysis.py

# 在线测试端到端演示（JSON 数据流 + 影子测试 + 评估）
python demo_online_testing.py

# 分项演示（采样、评估、标注等）
python demo_online_testing.py --full

# ReAct Agent PoC（需先构建 rag_db）
python run_rag_retrieval_experiment.py
python run_react_agent_poc.py --stock 09988.HK              # 需 LLM_API_KEY
python run_react_agent_poc.py --offline --stock 09988.HK    # 离线验证工具链

# 启动 API 服务（需 pip install fastapi uvicorn）
python main.py
```

## 两条主线

### A. 舆情分析管线

`RawText` → `MultilingualTextPreprocessor` → `MultilingualAnalyzer` → `VectorStore` / `RAGQueryEngine`

- **入口**：`main.py`（`TextAnalysisPipeline`）、`demo_analysis.py`（Mock）
- **API**：`POST /analyze`、`GET /sentiment/{code}`、`POST /rag/query` 等

### B. RAG 检索实验

`run_rag_retrieval_experiment.py` 一键完成：

1. 加载 `data/sentiment_input_batch.json`
2. 百炼 Embedding 写入 ChromaDB（`./rag_db`）
3. 自动生成测试查询并评估

**输出指标**：Top-1 Accuracy、Top-5 Recall、MRR、NDCG@5、Avg. Retrieval Latency

### C. ReAct Agent（Sentinel PoC）

`run_react_agent_poc.py` 演示 **推理 → 工具 → 再推理** 闭环，工具直接复用 RAG 向量库：

| 工具 | 作用 |
|------|------|
| `search_financial_news` | 语义检索 `rag_db` 中的新闻/公告 |
| `summarize_stock_news` | 按主题聚合多只相关片段 |
| `get_stock_price` | yfinance 拉取最新行情 |

架构：`LangGraph create_react_agent` + `ChatOpenAI(DeepSeek)` + 上述工具 → JSON 风险结论。

### D. 在线测试框架

`data_stream_sampler` → `OnlineTestingFramework` → `ShadowTestingEnvironment` → `EvaluationEngine` → `FeedbackController`

- 无 `LLM_API_KEY` 时影子测试自动使用 `MockLLMAnalyzer`
- 设计细节见 [ONLINE_TESTING_GUIDE.md](ONLINE_TESTING_GUIDE.md)

## 数据格式

批量 JSON 字段说明见 [JSON_FORMAT_GUIDE.md](JSON_FORMAT_GUIDE.md)。示例数据：

- `data/sentiment_input_batch.json`

## 精简说明（2026-05）

已移除与主线重复的模块，统一为**一套多语言栈**：

| 已删除 | 原因 |
|--------|------|
| `preprocessor.py` / `analyzer.py` | 由 `multilingual_*` 替代 |
| `demo_enhanced_embedding.py` | 逻辑已并入 `vector_storage.py` |
| 旧版空壳 `agent/` 占位 | 已替换为可运行 PoC（`run_react_agent_poc.py`） |
| `evaluation/run_evaluation.py` | 接口过时；RAG 评估用 `run_rag_retrieval_experiment.py` |
| 多份重复 Markdown 指南 | 内容合并进本 README |

## 延伸阅读

- [ONLINE_TESTING_GUIDE.md](ONLINE_TESTING_GUIDE.md) — 在线测试架构
- [JSON_FORMAT_GUIDE.md](JSON_FORMAT_GUIDE.md) — 输入 JSON 规范
- [API_CONTACT.md](API_CONTACT.md) — API 与联系方式

## 许可与数据

使用真实外部数据前请完成合规与脱敏审查。示例 JSON 仅用于课程实验。
