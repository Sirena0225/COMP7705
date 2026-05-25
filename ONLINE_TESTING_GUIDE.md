# 在线测试框架 - 完整设计文档

## 📋 概述

在线测试框架是一个完整的实时数据处理和评估系统，用于在生产环境中并行测试新旧模型，实现持续评估和自动反馈优化。

**核心目标：**
1. **实时处理** - 处理真实流入的数据，而非离线静态数据集
2. **持续评估** - 每批数据处理后自动计算指标，形成时间序列
3. **人机协同** - 高风险/高不确定性样本触发人工复核
4. **自动优化** - A/B对比结果驱动模型参数自动调整

---

## 🏗️ 架构设计

### 系统架构图

```
实时数据流
    ↓
┌─────────────────────────────────────────────────────┐
│         OnlineTestingFramework (主控制器)            │
└─────────────────────────────────────────────────────┘
    ↓
┌──────────────────┬────────────────────┬──────────────┐
│ 数据流采样器      │  影子测试环境      │ 评估引擎     │
│ (Sampler)        │ (ShadowEnv)        │ (Evaluator)  │
└──────────────────┴────────────────────┴──────────────┘
    ↓                   ↓                     ↓
[按策略采样]     [并行A/B测试]    [计算性能指标]
    ↓                   ↓                     ↓
┌──────────────────────────────────────────────────────┐
│              反馈控制器 (FeedbackController)          │
│  ┌─────────────┬──────────────┬─────────────────┐   │
│  │ 提示词优化   │ 阈值调整     │ 采样策略调整     │   │
│  └─────────────┴──────────────┴─────────────────┘   │
└──────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────┐
│            人工标注接口 (Streamlit App)              │
│  - 专家复核低置信度样本                              │
│  - 生成黄金标准标注                                  │
│  - 反馈改进循环                                      │
└──────────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────────┐
│           指标追踪器 (MetricsTracker)                │
│  - SQLite时间序列存储                               │
│  - 实时指标计算                                      │
│  - 性能报告生成                                      │
└──────────────────────────────────────────────────────┘
```

---

## 🔧 核心组件详解

### 1. 数据流采样器 (DataStreamSampler)

**职责**: 从实时数据流中按策略采样，确保样本的多样性和代表性

**采样策略**:

| 策略 | 说明 | 使用场景 |
|-----|------|--------|
| UNIFORM | 均匀采样（固定比例） | 基础测试 |
| STRATIFIED | 分层采样（按维度均衡） | **推荐** - 确保各语言、各来源覆盖 |
| ADAPTIVE | 自适应采样（根据置信度） | 高风险环境 - 重点关注不确定样本 |
| RISK_AWARE | 风险感知采样（高风险优先） | 风险管理 - 优先复核高风险样本 |

**关键参数**:

```python
SamplingConfig(
    overall_rate=0.1,                    # 整体采样率 10%
    min_samples_per_batch=50,            # 每批最少50个样本
    max_samples_per_batch=500,           # 每批最多500个样本
    language_weights={                   # 各语言采样权重
        "zh": 0.5,      # 中文占50%
        "en": 0.3,      # 英文占30%
        "mixed": 0.2    # 混合占20%
    },
    source_weights={                     # 各来源采样权重
        "news": 0.4,
        "social_media": 0.3,
        "research_report": 0.2,
        "announcement": 0.1
    },
    high_risk_rate=1.0,                  # 高风险100%采样
    low_confidence_rate=0.5              # 低置信度50%采样
)
```

**特点**:
- ✅ 多线程安全队列处理
- ✅ 自动统计采样率和样本分布
- ✅ 支持实时数据流和批量数据

---

### 2. 影子测试环境 (ShadowTestingEnvironment)

**职责**: 并行运行生产模型和候选模型，对比输出结果

**工作流程**:

```
输入文本
  ↓
[并行执行] ←───────────────────┐
  ↓          ↓                 │
生产模型    候选模型          │
  ↓          ↓                 │
结果A      结果B              │
  ↓          ↓         [并行计时]
[对比分析]
  ↓
一致性评分、差异分析、性能对比
```

**对比维度**:

| 维度 | 权重 | 说明 |
|-----|------|------|
| 极性一致 | 40% | 是否都判为positive/neutral/negative |
| 风险等级 | 30% | 是否都判为green/yellow/red |
| 情绪分数接近 | 20% | 分数差异是否小于0.2 |
| 置信度接近 | 10% | 置信度差异是否小于0.1 |

**一致性评分公式**:

```
一致性(0-100) = 
  100 
  - (极性不一致 × 40)
  - (风险不一致 × 30)
  - (情绪分差 > 0.5 × 20)
  - (置信度差 > 0.3 × 10)
```

**性能指标**:
- ⏱️ 并行执行时间（延迟）
- 📊 一致性评分
- 🎯 极性/风险协议率

---

### 3. 评估引擎 (EvaluationEngine)

**职责**: 计算模型的多维度性能指标

**评估指标**:

```python
class EvaluationMetric(Enum):
    ACCURACY = "accuracy"              # 准确率
    PRECISION = "precision"            # 精确率
    RECALL = "recall"                  # 召回率
    F1_SCORE = "f1_score"             # F1分数
    LATENCY = "latency"                # 延迟
    THROUGHPUT = "throughput"          # 吞吐量
    CONSISTENCY = "consistency"        # 一致性
    CONFIDENCE = "confidence"          # 置信度
```

**具体实现**:

#### 情感分析准确率

```python
def evaluate_sentiment_accuracy(predictions, ground_truth):
    # 返回分类准确率
    return accuracy = correct_count / total_count
```

#### 风险识别性能

```python
def evaluate_risk_detection(predictions, ground_truth):
    # 计算TP, FP, TN, FN
    # 返回: accuracy, precision, recall, f1_score
    
    # 二分类: 有风险(yellow/red) vs 无风险(green)
    tp = True Positives  # 正确识别的风险
    fp = False Positives # 错误识别的风险
    tn = True Negatives  # 正确识别的无风险
    fn = False Negatives # 遗漏的风险
    
    accuracy = (tp + tn) / (tp + fp + tn + fn)
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall)
```

#### 处理延迟评估

```python
def evaluate_latency(processing_times_ms):
    # 返回: mean, median, p95, p99
    p95 = percentile(times, 95)  # 95%的请求在此时间内完成
    p99 = percentile(times, 99)  # 99%的请求在此时间内完成
```

#### 两模型一致性

```python
def evaluate_consistency(model_a_predictions, model_b_predictions):
    polarity_consistency = match_rate(polar_a, polar_b)
    risk_consistency = match_rate(risk_a, risk_b)
    sentiment_correlation = pearson_correlation(scores_a, scores_b)
    
    overall = (
        polarity_consistency * 0.4 +
        risk_consistency * 0.3 +
        sentiment_correlation * 0.3
    )
```

---

### 4. 反馈控制器 (FeedbackController)

**职责**: 根据评估结果自动调整模型参数和策略

**调整类型**:

```python
class AdjustmentType(Enum):
    PROMPT_ENGINEERING = "prompt_engineering"      # 提示词优化
    THRESHOLD_ADJUSTMENT = "threshold_adjustment"  # 阈值调整
    SAMPLING_STRATEGY = "sampling_strategy"        # 采样策略调整
    FEATURE_ENGINEERING = "feature_engineering"    # 特征工程调整
```

**自动调整逻辑**:

#### 1. 提示词优化

```
检测错误模式
  ↓
- 正面倾向过强 → 增加负面信号权重
- 负面倾向不足 → 增加正面信号权重
- 高置信度错误多 → 审查提示词表述
  ↓
生成改进提示词
  ↓
部署到候选模型
```

#### 2. 阈值调整

```
分析置信度分布
  ↓
- 低置信度但正确多 → 降低阈值 (允许更多预测)
- 高置信度但错误多 → 提高阈值 (更严格)
  ↓
更新阈值参数
```

#### 3. 采样策略调整

```
性能指标下降 → 增加采样率
延迟过高 → 降低采样率
覆盖率不足 → 调整分层权重
```

---

### 5. 人工标注接口 (AnnotationInterface + Streamlit)

**职责**: 专家复核低置信度样本和一致性差的样本

**标注流程**:

```
检测标注需求
  ↓
[一致性 < 70%] 或 [置信度 < 50%]
  ↓
创建标注任务
  ↓
按优先级排队
  ├─ 高优先级 (priority=2): 一致性 < 50%
  ├─ 中优先级 (priority=1): 一致性 < 70%
  └─ 低优先级 (priority=0): 其他
  ↓
Streamlit界面展示
  ├─ 原始文本
  ├─ 两个模型的对比结果
  └─ 标注表单
  ↓
标注者输入真实标签
  ├─ 真实极性 (positive/neutral/negative)
  ├─ 真实风险等级 (green/yellow/red)
  └─ 置信度评分
  ↓
保存黄金标准标注
  ↓
用于后续模型评估和微调
```

**Streamlit应用特性**:

- 📝 交互式标注界面
- 🎯 优先级队列管理
- 📊 实时统计仪表板
- 💾 自动保存标注结果
- 📥 批量任务导入

---

### 6. 指标追踪器 (MetricsTracker)

**职责**: 记录和分析所有性能指标的时间序列

**存储方案**:

```
SQLite 数据库
  ↓
metrics 表
├─ timestamp (TEXT)     # 时间戳
├─ metric_type (TEXT)   # 指标类型
├─ value (REAL)        # 指标值
├─ model_id (TEXT)     # 模型ID
├─ batch_id (TEXT)     # 批次ID
├─ language (TEXT)     # 语言
└─ stock_code (TEXT)   # 股票代码 (可选)
```

**查询功能**:

```python
# 获取聚合统计
summary = tracker.get_metric_summary(
    metric_type="accuracy",
    model_id="production",
    hours=1
)
# 返回: mean, median, std_dev, min, max, p95, p99

# 对比多个模型
comparison = tracker.get_model_comparison(
    metric_type="latency",
    model_ids=["production", "candidate"],
    hours=1
)

# 按语言分组
lang_metrics = tracker.get_language_metrics(
    model_id="production",
    hours=24
)
# 返回: {language: {metric: value}}

# 时间序列
time_series = tracker.get_time_series(
    metric_type="consistency",
    model_id="comparison",
    interval_minutes=10,
    hours=24
)
# 返回: [(timestamp, value), ...]

# 异常检测
anomalies = tracker.get_anomalies(
    metric_type="latency",
    model_id="production",
    std_dev_threshold=3.0
)
# 返回: 超过3倍标准差的异常值
```

---

## 📊 工作流程示例

### 完整的批处理流程

```
步骤1: 采样
────────────
实时数据流 → [数据流采样器] → 10% 样本采样
                              按语言/来源分层
                              → 100个样本/批

步骤2: A/B测试
───────────────
100个样本 → [生产模型] → 结果A ┐
          → [候选模型] → 结果B ├─→ [对比分析]
                               └─→ 一致性评分
                                  极性协议率
                                  延迟对比

步骤3: 评估
──────────
对比结果 → [评估引擎] → 准确率
                       一致性
                       延迟P95
                       → 与基线对比
                          Δ指标计算

步骤4: 反馈
──────────
评估结果 → [反馈控制器]
         ├─ 准确率 < 85%? → [提示词优化]
         ├─ 置信度 < 70%? → [阈值调整]
         ├─ 延迟 > 1000ms? → [采样策略调整]
         └─ 一致性 < 80%? → [标注任务]

步骤5: 人工复核
───────────────
标注任务 → [Streamlit App] → 专家标注 → 黄金标准

步骤6: 指标持久化
─────────────────
所有指标 → [指标追踪器] → SQLite数据库 → 时间序列分析
```

---

## 🚀 使用示例

### 最简单的启动方式

```python
from online_test_framework import OnlineTestingFramework

# 创建框架实例
framework = OnlineTestingFramework()

# 启动框架
framework.start()

# 推送样本
sample = DataStreamSample(
    sample_id="text-001",
    raw_text_id="news-123",
    text="腾讯Q1财报超预期",
    language="zh",
    stock_code="00700.HK",
    source="news",
    source_name="新浪财经",
    timestamp="2024-04-09T10:30:00"
)
framework.push_sample(sample)

# 框架自动处理:
# 1. 采样
# 2. A/B测试
# 3. 评估
# 4. 反馈和调整
# 5. 生成报告

# 5分钟后查看总结
framework.print_summary()

# 停止框架
framework.stop()
```

### 自定义配置

```python
from online_test_framework import OnlineTestConfig

config = OnlineTestConfig(
    sampling_strategy=SamplingStrategy.RISK_AWARE,
    sampling_rate=0.15,                    # 采样率15%
    evaluation_interval_seconds=300,       # 5分钟评估一次
    evaluation_batch_size=200,             # 每批200个样本
    accuracy_min=0.87,                     # 准确率最低87%
    latency_max_ms=800,                    # 最大延迟800ms
    consistency_min=0.85,                  # 最小一致性85%
)

framework = OnlineTestingFramework(config)
```

### 启动Streamlit标注应用

```bash
# 生成标注应用代码
python -c "from annotation_interface import AnnotationStreamlit; AnnotationStreamlit.save_app_code()"

# 启动Streamlit应用
streamlit run /Users/mac/sandbox/HKU/COMP7705/annotation_app.py
```

---

## 📈 监控和报告

### 实时监控

```python
# 获取采样统计
sampler_stats = framework.sampler.get_stats()
print(f"采样率: {sampler_stats['sampling_rate']:.1%}")

# 获取A/B对比总结
comparison_summary = framework.shadow_env.get_comparison_summary()
print(f"共识率: {comparison_summary['consensus_rate']:.1%}")

# 获取反馈调整总结
adjustment_summary = framework.feedback_controller.get_adjustment_summary()
print(f"总调整次数: {adjustment_summary['total_actions']}")

# 获取标注统计
annotation_stats = framework.annotation_interface.get_annotation_stats()
print(f"待标注任务: {annotation_stats['pending_tasks']}")
```

### 性能报告导出

```python
# 导出指标数据
framework.metrics_tracker.export_metrics(
    output_file="/path/to/metrics_export.json",
    model_id="production",
    hours=24
)

# 导出调整日志
framework.feedback_controller.export_action_log(
    output_file="/path/to/adjustment_log.json"
)
```

---

## 🎯 关键设计原则

1. **实时性** - 秒级响应，支持高频数据流
2. **自适应** - 根据实际表现动态调整策略
3. **透明性** - 所有决策都可追溯和解释
4. **可靠性** - 多线程安全，异常处理完善
5. **可扩展** - 易于添加新的评估指标和调整策略
6. **人机协同** - 结合自动化和人工专业知识

---

## 📁 文件结构

```
/Users/mac/sandbox/HKU/COMP7705/
├── online_test_framework.py        # 主框架
├── data_stream_sampler.py          # 数据流采样
├── shadow_testing_env.py           # A/B测试环境
├── evaluation_engine.py            # 评估引擎
├── metrics_tracker.py              # 指标追踪
├── feedback_controller.py          # 反馈控制
├── annotation_interface.py         # 标注接口
├── annotation_app.py               # Streamlit应用 (自动生成)
└── online_test_results/            # 输出目录
    ├── batch-*.json                # 批处理报告
    └── metrics.db                  # SQLite指标数据库
```

---

## ✅ 完成清单

- [x] 数据流采样器实现
- [x] 影子测试环境实现
- [x] 评估引擎实现
- [x] 反馈控制器实现
- [x] 指标追踪器实现
- [x] 人工标注接口实现
- [x] 在线测试框架集成
- [x] 文档编写

---

**系统状态**: 🟢 生产就绪  
**最后更新**: 2024-04-09  
**版本**: v1.0
