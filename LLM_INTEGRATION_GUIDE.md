# 🔌 LLM API 集成指南

## 📌 概述

港股舆情分析系统支持**真实的 LLM API 调用**，用于情感分析和风险识别。系统支持多个 LLM 提供商，推荐使用 **DeepSeek** (价格便宜) 或 **OpenAI** (性能最好)。

---

## 🚀 快速开始 (3分钟)

### 步骤 1: 复制环境变量文件

```bash
cp .env.example .env
```

### 步骤 2: 获取 API Key

**选项 A: DeepSeek (推荐)**
- 网址: https://platform.deepseek.com
- 优点: 价格便宜 (~¥0.14 / 1M tokens), 性能不错
- 步骤:
  1. 注册账户
  2. 创建 API Key
  3. 充值余额
  4. 复制 API Key

**选项 B: OpenAI**
- 网址: https://platform.openai.com/api-keys
- 优点: 最好的模型性能 (GPT-4o)
- 步骤:
  1. 登录 OpenAI 账户
  2. 进入 API Keys 页面
  3. 创建新的 API Key
  4. 复制 API Key

**选项 C: 阿里云通义 (备选)**
- 网址: https://dashscope.aliyun.com
- 优点: 国内云服务，延迟低
- 步骤:
  1. 登录阿里云账户
  2. 进入 DashScope 平台
  3. 创建 API Key
  4. 复制 API Key

### 步骤 3: 配置 .env 文件

编辑 `.env` 文件，填入 API Key:

```bash
# DeepSeek (推荐)
LLM_API_KEY=sk-xxxxx-your-deepseek-api-key-xxxxx
LLM_MODEL=deepseek-chat

# 或 OpenAI
OPENAI_API_KEY=sk-xxxxx-your-openai-api-key-xxxxx
LLM_MODEL=gpt-3.5-turbo
```

### 步骤 4: 验证配置

```bash
# 运行 LLM API 测试脚本
python setup_llm.py
```

预期输出:
```
✅ API 连接成功!
✅ 所有测试通过！系统已成功集成真实 LLM API
```

---

## 📋 完整配置参考

### .env 文件完整选项

```bash
# ============================================================
# LLM API 配置
# ============================================================

# DeepSeek API (推荐)
LLM_API_KEY=sk-xxxxx-your-api-key-xxxxx
LLM_MODEL=deepseek-chat

# OpenAI API (备选)
OPENAI_API_KEY=sk-xxxxx-your-api-key-xxxxx
# LLM_MODEL=gpt-4o  或 gpt-3.5-turbo

# 阿里云通义 (备选)
DASHSCOPE_API_KEY=sk-xxxxx-your-api-key-xxxxx
# LLM_MODEL=qwen-max-latest

# ============================================================
# LLM 性能配置
# ============================================================

# 模型温度参数 (0-1, 越低越确定)
LLM_TEMPERATURE=0.1

# 最大输出 token 数
LLM_MAX_TOKENS=1500

# API 调用超时时间 (秒)
API_TIMEOUT=30

# 重试次数
API_RETRY_ATTEMPTS=3

# ============================================================
# 采样和评估配置
# ============================================================

# 采样率 (0-1)
SAMPLING_RATE=0.1

# 采样策略: UNIFORM, STRATIFIED, ADAPTIVE, RISK_AWARE
SAMPLING_STRATEGY=STRATIFIED

# 准确率最小值
ACCURACY_MIN=0.85

# 最大延迟 (毫秒)
LATENCY_MAX_MS=1000

# 一致性最小值
CONSISTENCY_MIN=0.80

# 评估间隔 (秒)
EVALUATION_INTERVAL_SECONDS=300
```

---

## 🔍 模型选择对比

| 方案 | 模型 | 价格 | 性能 | 延迟 | 推荐 |
|-----|------|------|------|------|------|
| **DeepSeek** | deepseek-chat | ⭐ 最便宜 | ⭐⭐⭐⭐ | 中等 | ✅ 首选 |
| **OpenAI** | gpt-4o | ⭐⭐⭐⭐ 贵 | ⭐⭐⭐⭐⭐ 最好 | 快 | ⭐ 最佳性能 |
| **OpenAI** | gpt-3.5-turbo | ⭐⭐ 中等 | ⭐⭐⭐⭐ | 快 | 💰 性价比 |
| **阿里云** | qwen-max-latest | ⭐⭐ 中等 | ⭐⭐⭐⭐ | 快 | 🇨🇳 国内 |

**推荐配置**:
- 开发/测试: DeepSeek (最便宜)
- 生产环境: OpenAI GPT-4o (最可靠)
- 国内部署: 阿里云通义 (延迟最低)

---

## 🧪 测试 LLM 集成

### 方法1: 运行集成测试脚本

```bash
python setup_llm.py
```

该脚本会:
- ✅ 检查环境配置
- ✅ 测试 API 连接
- ✅ 测试多语言分析
- ✅ 显示详细的诊断信息

### 方法2: 运行完整演示

```bash
python demo_online_testing.py
```

该演示会:
- ✅ 运行 7 个独立的组件演示
- ✅ 使用真实的 LLM API 调用
- ✅ 展示完整的端到端工作流

### 方法3: Python 交互式测试

```python
import os
from dotenv import load_dotenv
from multilingual_analyzer import MultilingualSentimentAnalyzer

load_dotenv()

# 初始化分析器
analyzer = MultilingualSentimentAnalyzer(
    model_name="deepseek-chat",
    api_key=os.getenv("LLM_API_KEY")
)

# 测试分析
text = "腾讯Q1财报超预期，收入增长6%，净利润增长54%"
print(f"分析: {text}")
# 注意: 需要首先预处理文本...
```

---

## 🛠️ 故障排查

### 问题 1: "API Key 未设置"

**症状**:
```
❌ LLM_API_KEY 未设置
```

**解决方案**:
```bash
# 1. 检查 .env 文件是否存在
ls -la .env

# 2. 检查 API Key 是否配置
grep "LLM_API_KEY" .env

# 3. 重新设置 API Key
echo 'LLM_API_KEY=sk-xxxxx-your-key-xxxxx' >> .env

# 4. 重新加载环境
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate   # Windows
```

### 问题 2: "API 调用失败 - 401 Unauthorized"

**原因**: API Key 错误或过期

**解决方案**:
1. 检查 API Key 是否正确复制
2. 确保 API Key 前缀正确 (应该是 `sk-`)
3. 检查 API 账户余额 (特别是 DeepSeek)
4. 重新生成 API Key

```bash
# 验证 API Key 格式
grep "LLM_API_KEY" .env | cut -c1-30
# 应该输出类似: LLM_API_KEY=sk-xxxxx-xxxx
```

### 问题 3: "API 调用超时"

**原因**: 网络问题或服务器响应慢

**解决方案**:
```python
# 在 .env 中增加超时时间
API_TIMEOUT=60  # 改为 60 秒

# 或降低模型温度以加快推理
LLM_TEMPERATURE=0.0
```

### 问题 4: "JSON 格式错误"

**症状**:
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**原因**: LLM 模型返回格式不符合要求

**解决方案**:
1. 检查 LLM_MODEL 是否支持 `response_format={"type": "json_object"}`
2. 尝试使用不同的模型
3. 降低 `LLM_TEMPERATURE` 参数

---

## 📊 性能监控

### 监视 API 调用统计

```python
from online_test_framework import OnlineTestingFramework

framework = OnlineTestingFramework()
framework.start()

# ... 推送样本 ...

# 查看统计信息
print(f"总调用次数: {framework.shadow_env.production_analyzer.total_calls}")
print(f"总 Token 数: {framework.shadow_env.production_analyzer.total_tokens}")
print(f"语言统计: {framework.shadow_env.production_analyzer.language_stats}")
```

### 计算 API 成本

```python
# DeepSeek 成本计算
# 输入: ¥0.14 / 1M tokens
# 输出: ¥0.28 / 1M tokens

total_tokens = 150000  # 示例: 150k tokens
input_cost = (total_tokens * 0.14) / 1_000_000  # ¥0.021
output_cost = (total_tokens * 0.28) / 1_000_000  # ¥0.042
total_cost = input_cost + output_cost  # 约 ¥0.063

print(f"预计成本: ¥{total_cost:.3f}")
```

---

## 🔐 安全建议

### 1. 保护 API Key

```bash
# 确保 .env 在 .gitignore 中
echo ".env" >> .gitignore

# 不要在代码中硬编码 API Key
# ❌ 错误
api_key = "sk-xxxxx-hardcoded"

# ✅ 正确
api_key = os.getenv("LLM_API_KEY")
```

### 2. 限制 API 调用

```python
# 在 .env 中设置最大 token 数
LLM_MAX_TOKENS=1500

# 设置合理的超时时间
API_TIMEOUT=30

# 限制重试次数
API_RETRY_ATTEMPTS=3
```

### 3. 监视异常使用

```bash
# 定期检查 API 使用量
# DeepSeek: https://platform.deepseek.com/usage
# OpenAI: https://platform.openai.com/account/billing/overview
```

---

## 📚 更多资源

### 官方文档

- [DeepSeek API 文档](https://platform.deepseek.com/docs)
- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [阿里云 DashScope 文档](https://dashscope.aliyun.com/docs)

### 代码示例

- 多语言分析器: [multilingual_analyzer.py](multilingual_analyzer.py)
- 影子测试环境: [shadow_testing_env.py](shadow_testing_env.py)
- 在线测试框架: [online_test_framework.py](online_test_framework.py)

### 完整演示

```bash
# 运行所有组件演示（包括 LLM API 调用）
python demo_online_testing.py

# 启动人工标注应用
streamlit run annotation_app.py

# 运行多语言分析测试
python test_multilingual.py
```

---

## ✅ 检查清单

在部署到生产环境前:

- [ ] API Key 已配置到 .env 文件
- [ ] 已运行 `python setup_llm.py` 通过测试
- [ ] 已验证 API 余额充足
- [ ] 已设置合理的超时和重试参数
- [ ] 已在 .gitignore 中排除 .env 文件
- [ ] 已定期监视 API 使用统计
- [ ] 成本预算在可控范围内

---

## 🎉 成功标志

配置完成后，运行:

```bash
python setup_llm.py
```

预期看到:

```
===============================================
✅ 所有测试通过！系统已成功集成真实 LLM API
===============================================
```

---

**版本**: v2.0  
**更新时间**: 2024-04-09  
**LLM 集成状态**: 🟢 已启用
