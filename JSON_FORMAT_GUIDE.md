# JSON 数据格式转换指南

## 📋 概述

本指南说明如何将 `/data` 目录下的 JSON 文件格式转换为程序内部的 `DataStreamSample` 格式，使其能直接集成到在线测试框架中。

## 🔄 数据格式映射

### 原始 JSON 格式 (`/data/sentiment_input_batch.json`)

```json
{
  "text_id": "doc-139",
  "language": "en",
  "title": "OVERSEAS REGULATORY ANNOUNCEMENT",
  "content": "OVERSEAS REGULATORY ANNOUNCEMENT Announcements and Notices...",
  "stock_codes": ["09988.HK"],
  "stock_names": ["BABA-W"],
  "source_type": "announcement",
  "source_name": "hkexnews",
  "published_at": "2026-05-20T21:03:00",
  "url": "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0520/2026052001340.pdf"
}
```

### DataStreamSample 格式（程序内部使用）

```python
DataStreamSample(
    sample_id="doc-139-0",              # text_id + 索引
    raw_text_id="doc-139",              # 原始 text_id
    text="OVERSEAS REGULATORY...",      # title + content 合并
    language="en",                      # 直接使用
    stock_code="09988.HK",              # stock_codes[0]
    source="announcement",              # source_type
    source_name="hkexnews",            # 直接使用
    timestamp="2026-05-20T21:03:00",   # published_at
    sampled_at="2026-05-21T...",       # 采样时刻 (自动生成)
    confidence=0.0,                     # 默认值
    priority=0                          # 默认值
)
```

## 📁 支持的数据文件

### 1. `sentiment_input_batch.json`
- 基础数据文件
- 包含 441 个样本
- 字段：text_id, language, title, content, stock_codes, stock_names, source_type, source_name, published_at, url

### 2. `sentiment_input_with_prices.json`
- 包含价格信息的数据文件
- 也是 441 个样本
- 额外字段：price_on_publish_date, previous_trading_day_price

## 🛠️ 使用方法

### 方法1: 快速测试

```bash
cd /Users/mac/sandbox/HKU/COMP7705
python test_json_format.py
```

这将验证：
- ✅ JSON 文件是否能正确加载
- ✅ 数据是否能正确转换为 DataStreamSample
- ✅ 所有必需字段是否已填充

### 方法2: 在代码中使用

#### 加载基础 JSON
```python
from json_data_loader import load_data_for_sampling

# 加载 JSON 数据并转换为 DataStreamSample 列表
samples = load_data_for_sampling("sentiment_input_batch.json")

print(f"加载了 {len(samples)} 个样本")
for sample in samples[:3]:
    print(f"  - {sample.sample_id} ({sample.language}) from {sample.source}")
```

#### 加载包含价格的 JSON
```python
from json_data_loader import load_data_with_prices

# 加载 JSON 数据和价格信息
data_with_prices = load_data_with_prices("sentiment_input_with_prices.json")

for item in data_with_prices[:3]:
    sample = item['sample']
    price = item['price_on_publish_date']
    print(f"  {sample.stock_code} 收盘价: ¥{price['close_price']}")
```

#### 集成到采样器
```python
from data_stream_sampler import DataStreamSampler, JSONDataStream, SamplingConfig, SamplingStrategy

# 创建采样器
config = SamplingConfig(overall_rate=0.1)
sampler = DataStreamSampler(
    strategy=SamplingStrategy.STRATIFIED,
    config=config
)

# 创建 JSON 数据流
json_stream = JSONDataStream(
    sampler=sampler,
    json_file_path="/Users/mac/sandbox/HKU/COMP7705/data/sentiment_input_batch.json",
    rate=50  # 每秒推送50个样本
)

# 启动采样
sampler.start()

# 推送数据
json_stream.stream_from_json(samples_per_second=50)

# 获取采样结果
batch = sampler.get_next_batch(100)
print(f"采样结果: {len(batch)} 个样本")

sampler.stop()
```

### 方法3: 在演示中使用

运行在线测试框架演示，选择演示 2️⃣：

```bash
python demo_online_testing.py
```

会进行以下演示：
1. 演示 1️⃣：数据流采样器 (模拟数据)
2. **演示 2️⃣：JSON 数据流** ← 真实数据
3. 演示 3️⃣ - 8️⃣：其他功能

## 📊 数据统计

从 `sentiment_input_batch.json` 加载的数据统计：

| 字段 | 值 |
|------|-----|
| 总样本数 | 441 |
| 语言分布 | en: 441 (100%) |
| 来源分布 | announcement: 241 (54.7%), news: 200 (45.3%) |
| 股票代码 | 15 种不同的股票代码 |
| 时间范围 | 2026-05-20 ~ 2026-05-21 |

## 🔧 自定义转换逻辑

如果需要修改转换逻辑（例如为 `confidence` 和 `priority` 字段赋值），可以修改 `json_data_loader.py` 中的 `convert_to_sample()` 方法：

```python
@staticmethod
def convert_to_sample(raw_data: dict, index: int = 0) -> DataStreamSample:
    """将原始 JSON 数据转换为 DataStreamSample"""
    
    # ...existing code...
    
    # 自定义转换逻辑
    confidence = 0.0
    priority = 0
    
    # 例如：根据 source_type 设置优先级
    if raw_data.get("source_type") == "announcement":
        priority = 1  # 公告类优先级为 1
    
    # 例如：根据发布时间设置置信度
    published_at = raw_data.get("published_at", "")
    if "latest" in published_at or recent:
        confidence = 0.9  # 最近发布的内容置信度高
    
    sample = DataStreamSample(
        # ...existing fields...
        confidence=confidence,
        priority=priority
    )
    
    return sample
```

## 📝 API 参考

### JSONDataLoader 类

```python
class JSONDataLoader:
    
    # 加载基础 JSON
    def load_batch_json(filename: str) -> List[DataStreamSample]
    
    # 加载包含价格的 JSON
    def load_with_prices(filename: str) -> List[dict]
    
    # 保存转换后的数据
    def save_converted_data(samples: List[DataStreamSample], output_filename: str) -> bool
    
    # 静态方法：转换单个数据
    @staticmethod
    def convert_to_sample(raw_data: dict, index: int = 0) -> DataStreamSample
```

### JSONDataStream 类

```python
class JSONDataStream:
    
    def __init__(sampler: DataStreamSampler, json_file_path: str, rate: float = 50)
    
    # 流式推送 JSON 数据
    def stream_from_json(samples_per_second: Optional[float] = None)
    
    # 加载 JSON 文件
    @staticmethod
    def load_json_samples(json_file_path: str) -> List[Dict]
    
    # 转换 JSON 数据
    @staticmethod
    def convert_json_to_sample(raw_data: dict, index: int = 0) -> DataStreamSample
```

## ✅ 验证清单

- [x] JSON 文件可以正常加载
- [x] 数据可以正确转换为 DataStreamSample 格式
- [x] 所有必需字段都已填充
- [x] 可以集成到采样器
- [x] 支持流式推送数据
- [x] 支持两种 JSON 文件格式

## 🚀 下一步

1. **运行测试**
   ```bash
   python test_json_format.py
   ```

2. **在演示中查看效果**
   ```bash
   python demo_online_testing.py
   # 选择演示 2️⃣
   ```

3. **集成到你的代码**
   ```python
   from json_data_loader import load_data_for_sampling
   from data_stream_sampler import JSONDataStream, DataStreamSampler
   
   # 使用真实数据进行在线测试
   ```

## 📚 相关文件

- `json_data_loader.py` - JSON 数据加载和转换模块
- `data_stream_sampler.py` - 包含 `JSONDataStream` 类
- `test_json_format.py` - 验证数据格式的测试脚本
- `demo_online_testing.py` - 包含 JSON 数据流演示
- `/data/sentiment_input_batch.json` - 原始数据文件

## 💡 常见问题

### Q: 为什么 `confidence` 和 `priority` 字段都是 0？
A: 这些字段在原始 JSON 文件中不存在。你可以自定义转换逻辑来为这些字段赋值。

### Q: 如何向转换后的数据添加新字段？
A: 修改 `json_data_loader.py` 中的 `convert_to_sample()` 方法，添加你需要的逻辑。

### Q: 是否支持其他 JSON 格式？
A: 可以。修改 `JSONDataLoader.convert_to_sample()` 方法来适配不同的 JSON 结构。

### Q: 如何提高数据推送的速度？
A: 增加 `JSONDataStream` 初始化时的 `rate` 参数，或在 `stream_from_json()` 中传递更大的 `samples_per_second` 值。

## 🎯 总结

通过使用 `json_data_loader.py` 和 `JSONDataStream` 类，你可以：

✅ 自动将 `/data` 下的 JSON 文件转换为程序所需的格式  
✅ 直接集成真实数据到在线测试框架  
✅ 无需手动数据处理  
✅ 支持流式数据推送  
✅ 保持代码清晰和可维护  

现在程序的输入格式已与 `/data` 下的 JSON 格式完全匹配！
