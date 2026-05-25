**项目概述**

本仓库实现一个面向港股舆情的多语言情感分析与在线测试框架，包含：多语言预处理与分析、影子（A/B）测试、评估引擎、自动反馈与人工标注接口。真实运行时请将生产数据放入 `data/` 目录；仓库根目录下的若干 `.json` 文件为示例/模拟数据用于演示和测试。


**主要文件（精简）**

- [data](data)：真实或示例数据目录（请将真实数据放在此目录下）。
- [multilingual_preprocessor.py](multilingual_preprocessor.py#L1): 多语言预处理器（`MultilingualTextPreprocessor`）。
- [multilingual_analyzer.py](multilingual_analyzer.py#L1): 多语言分析器（`MultilingualAnalyzer`，含提示词模板与 LLM 调用）。
- [online_test_framework.py](online_test_framework.py#L1): 在线测试主控（`OnlineTestingFramework`、`OnlineTestConfig`）。
- [data_stream_sampler.py](data_stream_sampler.py#L1): 数据采样器与流模拟器（`DataStreamSampler`、`JSONDataStream`）。
- [shadow_testing_env.py](shadow_testing_env.py#L1): 影子测试环境与结果对比工具。
- [evaluation_engine.py](evaluation_engine.py#L1): 性能评估工具与度量计算。
- [metrics_tracker.py](metrics_tracker.py#L1): 指标记录与查询（SQLite 存储）。
- [feedback_controller.py](feedback_controller.py#L1): 自动反馈与调整逻辑（提示词/阈值/采样）。
- [annotation_interface.py](annotation_interface.py#L1): 人工标注接口与任务管理（Streamlit 支持）。
- [demo_online_testing.py](demo_online_testing.py#L1): 在线测试演示脚本（多场景示例）。
- [demo_analysis.py](demo_analysis.py#L1): 舆情分析示例脚本（真实示例文本）。
- [requirements.txt](requirements.txt#L1): 依赖清单。


**快速上手**

1) 创建并激活 Python 虚拟环境，安装依赖：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2) 运行分析示例（离线演示）：

```bash
python demo_analysis.py
```

3) 运行在线测试演示（本地模拟流 + A/B 流程）：

```bash
python demo_online_testing.py
```

4) 若要启动人工标注界面（暂未完善该部分）：

```bash
streamlit run annotation_interface.py
```


**环境变量**

- 若使用真实 LLM，请设置 `LLM_API_KEY`（和可选 `LLM_MODEL`）：

```bash
export LLM_API_KEY="your_api_key"
export LLM_MODEL="deepseek-chat"
```

如果不设置，框架会以 mock 模型运行以便离线演示和调试。


**典型工作流**

1. 数据通过 [data_stream_sampler.py](data_stream_sampler.py#L1) 进入采样器（支持 JSON 数据流和实时推送）。
2. 采样后的样本由 [online_test_framework.py](online_test_framework.py#L1) 驱动，进入 [shadow_testing_env.py](shadow_testing_env.py#L1) 并行执行生产/候选模型分析。
3. 评估使用 [evaluation_engine.py](evaluation_engine.py#L1) 计算多维指标，并由 [metrics_tracker.py](metrics_tracker.py#L1) 持久化。
4. [feedback_controller.py](feedback_controller.py#L1) 根据阈值与评估结果生成调整动作（提示词优化 / 阈值修改 / 采样策略）。
5. 不一致或低置信度样本会进入 [annotation_interface.py](annotation_interface.py#L1) 供人工复核，生成黄金标签用于后续回训练或提示词改进。


**数据说明**

- 将生产数据放在 `data/` 下（例如 `data/*.json`）。仓库内 `sentiment_input_batch.json`、`sentiment_input_with_prices.json` 等为演示/测试数据样例，便于本地调试。
- 使用真实数据前请确保已通过合规和隐私审查，必要时进行脱敏/审计。


**使用示例（Python）**

```python
from multilingual_preprocessor import MultilingualTextPreprocessor
from multilingual_analyzer import MultilingualAnalyzer

text = "腾讯(00700.HK) 发布季度财报，业绩超预期。"
pre = MultilingualTextPreprocessor()
chunks = pre.process(text)

analyzer = MultilingualAnalyzer()
res = analyzer.analyze(chunks[0], language='zh')
print(res)
```


**依赖与环境**

见 [requirements.txt](requirements.txt#L1)。主要依赖包括 `jieba`, `nltk`, `openai`（或 DeepSeek 兼容客户端）、`streamlit`、`pandas`、`sqlalchemy` 等。


**验证与演示**

- 运行 `python demo_online_testing.py` 将依次演示采样、影子测试、评估、反馈与标注任务的创建（脚本内包含 8 个演示项）。
- 运行 `python demo_analysis.py` 会演示如何用几个真实示例文本生成分析报告并保存到 `analysis_report.json`。


**贡献 & 联系**

- 欢迎提交 issue 或 pull request。请先阅读代码注释与示例，遵循仓库的风格和测试约定。
- 使用真实外部数据时，请在提交前确保已获得相应权限并遵守隐私法规。


---

（说明：README 已根据仓库主要模块与示例脚本重写，突出运行方式、数据位置与典型工作流）

| 资源 | 链接 |
|-----|------|
| 完整设计 | [ONLINE_TESTING_GUIDE.md](ONLINE_TESTING_GUIDE.md) |
| 集成指南 | [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) |
| 运行演示 | `python demo_online_testing.py` |
| 标注应用 | `streamlit run annotation_app.py` |

---

**项目更新**: 2026-05-23  
**系统状态**: 开发中 
**版本**: v2.0 (多语言 + 在线测试框架)
