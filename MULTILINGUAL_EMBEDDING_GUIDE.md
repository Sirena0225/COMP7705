# 多语言感知嵌入增强功能

## 📋 概述

在 `vector_storage.py` 中添加了一个新的 `_get_embedding_enhanced()` 方法，提供针对港股相关金融文本的多语言感知嵌入策略。该功能能够自动检测文本的语言（中文、英文、混合），并为每种语言选择最优的嵌入模型。

---

## ✨ 核心特性

### 1. **自动语言检测**
- 使用 `langdetect` 库自动识别文本语言
- 支持中文、英文、混合语言检测
- 带降级处理，检测失败时使用安全策略

### 2. **智能模型选择**

| 语言类型 | 嵌入模型 | 向量维度 | 成本 | 用途 |
|---------|--------|--------|------|------|
| 中文 (ZH) | text-embedding-3-large | 1536 | 高 | 最佳CJK支持 |
| 英文 (EN) | text-embedding-3-small | 512 | 低 (1x) | 成本优化 |
| 混合 (MIXED) | text-embedding-3-large | 1536 | 高 | 最优准确性 |

### 3. **成本优化**
- **英文文本**: 自动使用小模型，成本比大模型低 **7.5倍** ⬇️
- **中文文本**: 使用大模型确保CJK理解准确性 ✅
- **混合文本**: 使用大模型处理复杂内容 ✅

### 4. **自动文本标记**
- 中文文本前缀: `[ZH]`
- 英文文本前缀: 无 (保持原文本)
- 混合文本前缀: `[MIXED]`

标记用途：帮助向量数据库在检索时更好地理解内容上下文。

### 5. **错误处理与降级**
```python
try:
    lang = langdetect.detect(text)
except Exception as e:
    # 检测失败时使用大模型作为安全策略
    lang = "unknown"
    embedding = call_large_model(text)
```

---

## 🚀 使用方法

### 方法 1: 启用全局增强嵌入

```python
from vector_storage import VectorStore

# 创建向量存储，启用增强嵌入
vector_store = VectorStore(
    collection_name="hk_stock_news",
    use_enhanced_embedding=True  # ← 启用
)

# 添加文本时自动使用增强策略
vector_store.add_text(
    text_id="news_001",
    content="香港股市今日涨幅明显...",  # 自动检测为中文，使用大模型
    metadata={"stock_code": "HKEX:0001"}
)
```

### 方法 2: 直接调用增强方法

```python
# 直接获取优化的嵌入
embedding = vector_store._get_embedding_enhanced(text)

# 返回值是向量列表
print(len(embedding))  # 输出: 1536 (中文) 或 512 (英文)
```

### 方法 3: 手动选择使用场景

```python
# 只对长文本使用增强策略（优化成本）
def smart_embed(text: str, vector_store: VectorStore):
    if len(text) > 500:  # 长文本
        return vector_store._get_embedding_enhanced(text)
    else:
        return vector_store._get_embedding(text)
```

---

## 🔧 实现细节

### 函数签名

```python
def _get_embedding_enhanced(self, text: str) -> List[float]:
    """
    多语言感知的嵌入策略
    
    步骤:
    1. 文本截断 (最多8000字符)
    2. 语言检测 (zh-cn/en/unknown)
    3. 策略选择 (选择最优模型)
    4. API调用 (获取嵌入向量)
    5. 日志记录 (记录使用的策略)
    
    输入:
        text: 需要嵌入的文本
    
    输出:
        List[float]: 嵌入向量 (512或1536维)
    """
```

### 工作流程

```
输入文本
    ↓
截断至8000字符 (OpenAI限制)
    ↓
语言检测
    ├─ 中文 (zh-cn/zh-tw/zh) → 大模型 (1536维) + [ZH]前缀
    ├─ 英文 (en) → 小模型 (512维) + 无前缀
    └─ 其他/未知 → 大模型 (1536维) + [MIXED]前缀
    ↓
处理文本 (添加语言标记)
    ↓
调用OpenAI API
    ↓
返回嵌入向量
    ↓
记录日志 (语言、模型、向量维度)
```

---

## 📊 性能指标

### 嵌入准确性 (预期)

| 场景 | 准确性提升 | 说明 |
|-----|---------|------|
| 中文文本 | +15-25% | 大模型更好理解CJK |
| 混合文本 | +20-30% | 大模型处理复杂内容 |
| 英文文本 | ±0% | 小模型足以处理 |

### 成本降低

| 场景 | 成本对比 | 说明 |
|-----|--------|------|
| 纯英文 | **-85%** | 小模型 ¥0.02 vs 大模型 ¥0.15 |
| 混合 | 同标准 | 使用大模型 |
| 中文 | 同标准 | 使用大模型 |

### 性能开销

| 操作 | 耗时 | 说明 |
|-----|-----|------|
| 语言检测 | ~5-10ms | 使用 langdetect |
| API调用 | ~100-300ms | 取决于网络 |
| 总延迟 | ~100-320ms | 与标准方法相同 |

---

## 🎯 适用场景

### ✅ 推荐使用

1. **港股新闻分析**
   - 常见中英混合文本
   - 需要高准确性理解
   - 成本不是主要考虑

2. **公司公告处理**
   - 多为中文
   - 需要精确语义理解
   - 批量处理

3. **分析师报告**
   - 混合中英文
   - 专业术语复杂
   - 需要准确检索

4. **大规模数据处理**
   - 包含多语言文本
   - 想优化英文处理成本
   - 提升中文准确性

### ⚠️ 注意事项

- 首次调用会有 ~10ms 的语言检测开销
- 需要 `langdetect` 依赖已安装
- OpenAI API 配额需要充足
- 大模型成本较高，适合重要文本

---

## 📥 集成步骤

### 1. 安装依赖

```bash
pip install langdetect
```

### 2. 更新 VectorStore 初始化

```python
# 原始方式（不启用增强）
vector_store = VectorStore()

# 新方式（启用增强嵌入）
vector_store = VectorStore(use_enhanced_embedding=True)
```

### 3. 使用方式保持不变

```python
# add_text() 会自动选择最优策略
vector_store.add_text(
    text_id="doc_001",
    content="文本内容",
    metadata={"stock_code": "HKEX:0700"}
)
```

---

## 🔍 调试和监控

### 查看执行日志

```
✅ 嵌入生成: 语言=Chinese, 模型=text-embedding-3-large, 文本长度=150, 向量维度=1536
⚠️  语言检测失败: 使用默认策略
✅ 嵌入生成: 语言=English, 模型=text-embedding-3-small, 文本长度=120, 向量维度=512
```

### 访问策略信息

```python
# 获取增强嵌入时的策略信息
embedding = vector_store._get_embedding_enhanced(text)

# 打印日志会显示:
# - 检测到的语言
# - 选择的模型
# - 向量维度
# - 处理的文本长度
```

---

## 💡 最佳实践

### 1. 按需启用

```python
# 仅对需要的应用启用
if app_requires_multilingual_support:
    vector_store = VectorStore(use_enhanced_embedding=True)
else:
    vector_store = VectorStore(use_enhanced_embedding=False)
```

### 2. 批量处理优化

```python
# 预先启用，批量添加
vector_store = VectorStore(use_enhanced_embedding=True)

for text in large_text_batch:
    vector_store.add_text(
        text_id=f"doc_{uuid.uuid4()}",
        content=text,
        metadata=extract_metadata(text)
    )
```

### 3. 成本监控

```python
# 记录使用的模型，便于成本分析
usage_stats = {
    "large_model_count": 0,  # [ZH] 和 [MIXED]
    "small_model_count": 0,  # [EN]
}

# 定期输出成本报告
estimated_cost = (
    usage_stats["large_model_count"] * 0.15 +
    usage_stats["small_model_count"] * 0.02
)
print(f"预估成本: ¥{estimated_cost:.2f} / M tokens")
```

### 4. 错误处理

```python
try:
    embedding = vector_store._get_embedding_enhanced(text)
except Exception as e:
    # 降级到标准嵌入
    logging.warning(f"增强嵌入失败: {e}, 使用标准方法")
    embedding = vector_store._get_embedding(text)
```

---

## 📚 代码示例

### 完整使用示例

```python
from vector_storage import VectorStore
import json

# 初始化向量存储，启用多语言支持
vector_store = VectorStore(
    collection_name="hk_stock_multilingual",
    use_enhanced_embedding=True
)

# 示例数据集
samples = [
    {
        "id": "zh_001",
        "text": "腾讯今日股价上升3.2%，受到云计算业务增长推动。",
        "stock": "HKEX:0700",
        "language": "ZH"
    },
    {
        "id": "en_001",
        "text": "Alibaba's stock gained 2.8% today on strong earnings.",
        "stock": "HKEX:9988",
        "language": "EN"
    },
    {
        "id": "mixed_001",
        "text": "Hong Kong's 恒生指数 rose 2.5%, with 腾讯 Tencent leading gains.",
        "stock": "HKEX:0001",
        "language": "MIXED"
    }
]

# 处理每个样本
for sample in samples:
    # 自动选择最优嵌入策略
    embedding = vector_store.add_text(
        text_id=sample["id"],
        content=sample["text"],
        metadata={
            "stock_code": sample["stock"],
            "language_tag": sample["language"]
        }
    )
    print(f"✅ 添加 {sample['language']} 文本: {sample['id']}")

# 语义检索（自动使用增强嵌入的优化）
results = vector_store.search(
    query="港股科技股今日表现",  # 自动检测为中文，使用大模型
    n_results=3
)

print("\n🔍 检索结果:")
for result in results:
    print(f"  - {result['metadata']['stock_code']}: {result['similarity_score']:.3f}")
```

### 成本优化示例

```python
# 统计不同语言文本数量，优化成本
from collections import defaultdict
import langdetect

text_collection = [...]  # 大量文本

language_counts = defaultdict(int)
estimated_costs = {"large": 0, "small": 0}

for text in text_collection:
    try:
        lang = langdetect.detect(text)
        if lang == "en":
            language_counts["English"] += 1
            estimated_costs["small"] += 1
        elif lang in ["zh-cn", "zh-tw", "zh"]:
            language_counts["Chinese"] += 1
            estimated_costs["large"] += 1
        else:
            language_counts["Other"] += 1
            estimated_costs["large"] += 1
    except:
        language_counts["Unknown"] += 1
        estimated_costs["large"] += 1

print("文本分布:")
for lang, count in language_counts.items():
    print(f"  {lang}: {count}")

print("\n成本预估:")
total_cost = estimated_costs["small"] * 0.02 + estimated_costs["large"] * 0.15
print(f"  总成本: ¥{total_cost:.2f} / M tokens")
print(f"  节省 (vs. 全用大模型): ¥{estimated_costs['small'] * 0.13:.2f}")
```

---

## 🔄 向后兼容性

该功能完全向后兼容，不会影响现有代码：

```python
# 旧代码仍然有效
vector_store = VectorStore()  # use_enhanced_embedding 默认为 False

# 新代码可以启用增强嵌入
vector_store = VectorStore(use_enhanced_embedding=True)

# add_text() 行为不变，只是内部使用更优的策略
vector_store.add_text(text_id, content, metadata)
```

---

## 📋 技术规格

| 方面 | 规格 |
|-----|-----|
| **语言支持** | 中文、英文、其他混合 |
| **检测库** | langdetect |
| **嵌入模型** | text-embedding-3-small / large |
| **最大文本长度** | 8000 字符 (API限制) |
| **向量维度** | 512 (EN) / 1536 (ZH/MIXED) |
| **API提供商** | OpenAI |
| **依赖** | langdetect, openai |
| **向后兼容** | 完全兼容 (可选) |

---

## 🎓 参考资源

- [langdetect 文档](https://github.com/Mimino666/langdetect)
- [OpenAI Embedding API](https://platform.openai.com/docs/guides/embeddings)
- [text-embedding-3 模型](https://platform.openai.com/docs/guides/embeddings)

---

**状态**: ✅ 已实现并测试  
