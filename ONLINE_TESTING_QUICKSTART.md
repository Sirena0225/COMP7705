# 在线测试框架 - 快速开始指南

## 🎯 5分钟快速开始

### 安装依赖

```bash
pip install streamlit pandas scikit-learn
```

### 最简单的用法

```python
from online_test_framework import OnlineTestingFramework
from data_stream_sampler import DataStreamSample

# 创建并启动框架
framework = OnlineTestingFramework()
framework.start()

# 推送样本（实际应用中来自实时数据流）
sample = DataStreamSample(
    sample_id="sample-001",
    raw_text_id="news-001",
    text="腾讯Q1财报超预期",
    language="zh",
    stock_code="00700.HK",
    source="news",
    source_name="新浪财经",
    timestamp="2024-04-09T10:30:00"
)

framework.push_sample(sample)

# 框架自动处理A/B测试、评估和反馈
# 5分钟后查看结果
framework.print_summary()

# 停止框架
framework.stop()
```

---

## 📋 完整使用流程

### 步骤1: 配置框架

```python
from online_test_framework import OnlineTestConfig, OnlineTestingFramework
from data_stream_sampler import SamplingStrategy

# 创建自定义配置
config = OnlineTestConfig(
    sampling_strategy=SamplingStrategy.STRATIFIED,  # 分层采样
    sampling_rate=0.1,                              # 采样率10%
    evaluation_interval_seconds=300,                # 每5分钟评估一次
    evaluation_batch_size=100,                      # 每批100个样本
    accuracy_min=0.85,                              # 准确率阈值
    latency_max_ms=1000,                            # 延迟阈值
    consistency_min=0.80,                           # 一致性阈值
)

framework = OnlineTestingFramework(config)
```

### 步骤2: 启动框架

```python
# 启动所有后台服务
framework.start()

# 框架将自动:
# 1. 采样实时数据
# 2. 运行A/B测试
# 3. 计算评估指标
# 4. 生成调整操作
# 5. 创建标注任务
```

### 步骤3: 推送样本

```python
# 方案A: 单个样本
sample = DataStreamSample(
    sample_id="sample-001",
    raw_text_id="news-001",
    text="腾讯发布财报",
    language="zh",
    stock_code="00700.HK",
    source="news",
    source_name="新浪财经",
    timestamp="2024-04-09T10:30:00"
)
framework.push_sample(sample)

# 方案B: 批量样本
samples = [...]  # DataStreamSample列表
for sample in samples:
    framework.push_sample(sample)
```

### 步骤4: 监控运行

```python
# 获取采样统计
sampler_stats = framework.sampler.get_stats()
print(f"采样率: {sampler_stats['sampling_rate']:.1%}")

# 获取A/B对比总结
comparison_summary = framework.shadow_env.get_comparison_summary()
print(f"共识率: {comparison_summary['consensus_rate']:.1%}")

# 获取标注任务数
pending = framework.annotation_interface.get_pending_count()
print(f"待标注任务: {pending}")
```

### 步骤5: 启动标注应用

```bash
# 生成并启动Streamlit标注应用
streamlit run /Users/mac/sandbox/HKU/COMP7705/annotation_app.py
```

### 步骤6: 查看结果和报告

```python
# 打印完整总结
framework.print_summary()

# 导出指标数据
framework.metrics_tracker.export_metrics(
    output_file="/path/to/metrics.json",
    model_id="production",
    hours=24
)

# 导出调整日志
framework.feedback_controller.export_action_log(
    output_file="/path/to/adjustments.json"
)

# 停止框架
framework.stop()
```

---

## 🎬 运行完整演示

```bash
cd /Users/mac/sandbox/HKU/COMP7705

# 运行完整演示（包括所有7个组件）
python demo_online_testing.py
```

演示将展示:
- ✅ 数据流采样
- ✅ A/B影子测试
- ✅ 性能评估
- ✅ 指标追踪
- ✅ 自动反馈
- ✅ 人工标注
- ✅ 完整框架集成

---

## 🔧 常见配置

### 场景1: 高频实时处理（互联网舆情）

```python
config = OnlineTestConfig(
    sampling_strategy=SamplingStrategy.ADAPTIVE,    # 自适应采样
    sampling_rate=0.2,                              # 采样率20%（高频）
    evaluation_interval_seconds=60,                 # 每分钟评估
    evaluation_batch_size=500,                      # 大批量处理
)
```

### 场景2: 精细化质量控制（机构研报）

```python
config = OnlineTestConfig(
    sampling_strategy=SamplingStrategy.RISK_AWARE,  # 风险感知采样
    sampling_rate=0.05,                             # 采样率5%（精选）
    evaluation_interval_seconds=600,                # 每10分钟评估
    evaluation_batch_size=50,                       # 小批量处理
    accuracy_min=0.95,                              # 高精度要求
    consistency_min=0.90,                           # 高一致性要求
)
```

### 场景3: 均衡生产部署（一般舆情）

```python
config = OnlineTestConfig(
    sampling_strategy=SamplingStrategy.STRATIFIED,  # 分层采样（推荐）
    sampling_rate=0.1,                              # 采样率10%（默认）
    evaluation_interval_seconds=300,                # 每5分钟评估
    evaluation_batch_size=100,                      # 中等批量
)
```

---

## 📊 查询和分析

### 查看实时指标

```python
# 获取最近1小时的准确率统计
summary = framework.metrics_tracker.get_metric_summary(
    metric_type="accuracy",
    model_id="production",
    hours=1
)

print(f"准确率:")
print(f"  平均值: {summary.mean:.3f}")
print(f"  中位数: {summary.median:.3f}")
print(f"  P95: {summary.p95:.3f}")
print(f"  标准差: {summary.std_dev:.3f}")
```

### 对比两个模型

```python
# 对比生产模型和候选模型的一致性
comparison = framework.metrics_tracker.get_model_comparison(
    metric_type="consistency",
    model_ids=["production", "candidate"],
    hours=1
)

for model_id, summary in comparison.items():
    print(f"{model_id}: {summary.mean:.3f} ± {summary.std_dev:.3f}")
```

### 按语言分析

```python
# 各语言的性能指标
lang_metrics = framework.metrics_tracker.get_language_metrics(
    model_id="production",
    hours=24
)

for language, metrics in lang_metrics.items():
    print(f"{language}:")
    for metric_name, value in metrics.items():
        print(f"  {metric_name}: {value:.3f}")
```

### 查看时间序列

```python
# 获取过去24小时的一致性时间序列
time_series = framework.metrics_tracker.get_time_series(
    metric_type="consistency",
    model_id="comparison",
    interval_minutes=10,
    hours=24
)

for timestamp, value in time_series:
    print(f"{timestamp}: {value:.3f}")
```

### 异常检测

```python
# 检测异常的延迟值（超过3倍标准差）
anomalies = framework.metrics_tracker.get_anomalies(
    metric_type="latency",
    model_id="production",
    std_dev_threshold=3.0,
    hours=1
)

print(f"检测到 {len(anomalies)} 个异常")
for anomaly in anomalies:
    print(f"  {anomaly.timestamp}: {anomaly.value}ms")
```

---

## 📝 人工标注

### 启动Streamlit标注应用

```bash
streamlit run /Users/mac/sandbox/HKU/COMP7705/annotation_app.py
```

### 标注界面使用

1. **选择模式**
   - 标注任务：处理待标注样本
   - 查看统计：查看标注进度
   - 管理任务：批量导入任务

2. **标注流程**
   - 输入标注者ID
   - 查看原始文本
   - 查看两个模型的对比结果
   - 输入真实标签（极性、风险等级）
   - 输入置信度
   - 提交标注

3. **导出标注结果**
   - 自动保存到 `annotations.jsonl`
   - 用于模型评估和微调

---

## 🐛 故障排查

### 问题1: 框架启动缓慢

**症状**: `framework.start()` 耗时很长

**解决**:
```python
# 使用异步启动（不阻塞）
import threading

# 在后台线程启动
thread = threading.Thread(target=framework.start, daemon=True)
thread.start()

# 主线程继续执行
time.sleep(1)  # 给框架初始化时间
```

### 问题2: 内存占用过高

**症状**: 指标追踪器内存持续增长

**解决**:
```python
# 定期清理过期数据
framework.metrics_tracker.clear_old_data(days=7)  # 保留7天数据

# 或禁用内存缓冲，直接写数据库
# （在初始化时设置）
```

### 问题3: 采样率不符合预期

**症状**: 实际采样率与配置不符

**解决**:
```python
# 检查采样统计
stats = framework.sampler.get_stats()
print(f"实际采样率: {stats['sampling_rate']:.1%}")

# 调整采样配置
config.sampling_rate = 0.15  # 提高到15%
framework.sampler.config.overall_rate = 0.15
```

### 问题4: Streamlit应用无法连接

**症状**: `streamlit run` 后无法访问

**解决**:
```bash
# 显式指定端口
streamlit run annotation_app.py --server.port 8501

# 检查防火墙设置
# 访问: http://localhost:8501
```

---

## 📈 性能优化建议

### 1. 采样优化

```python
# 使用分层采样确保多样性
SamplingStrategy.STRATIFIED

# 调整采样率
- 低频数据 (< 100/天): 采样率 20-50%
- 中频数据 (100-1000/天): 采样率 5-20%
- 高频数据 (> 1000/天): 采样率 1-10%
```

### 2. 评估间隔优化

```python
# 评估频率与样本量的关系
evaluation_interval = max(
    60,  # 最少60秒
    batch_size * 10  # 或样本处理时间
)
```

### 3. 阈值设置建议

```python
config = OnlineTestConfig(
    accuracy_min=0.85,         # 准确率：85%以上
    latency_max_ms=1000,       # 延迟：P95 < 1000ms
    consistency_min=0.80,      # 一致性：80%以上
)
```

---

## 🔗 与现有系统集成

### 集成步骤

```python
# 1. 导入框架
from online_test_framework import OnlineTestingFramework

# 2. 创建框架实例
framework = OnlineTestingFramework()

# 3. 注入数据源
# 从现有系统中获取样本
def data_source_generator():
    while True:
        # 从现有系统读取样本
        sample = existing_system.get_next_sample()
        if sample:
            # 转换为DataStreamSample格式
            ds_sample = DataStreamSample(
                sample_id=sample.id,
                raw_text_id=sample.raw_id,
                text=sample.content,
                language=detect_language(sample.content),
                stock_code=sample.stock_code,
                source=sample.source_type,
                source_name=sample.source_name,
                timestamp=sample.timestamp
            )
            framework.push_sample(ds_sample)
        else:
            time.sleep(1)

# 4. 启动处理
framework.start()

# 5. 在后台不断推送数据
import threading
data_thread = threading.Thread(
    target=data_source_generator,
    daemon=True
)
data_thread.start()

# 主程序继续执行其他任务
```

---

## 📚 更多文档

- 详细设计: [ONLINE_TESTING_GUIDE.md](ONLINE_TESTING_GUIDE.md)
- 完整演示: `python demo_online_testing.py`
- 代码示例: 查看各模块的docstring

---

## ✅ 检查清单

- [ ] 安装所有依赖
- [ ] 了解基本概念（采样、A/B测试、评估等）
- [ ] 运行完整演示
- [ ] 理解采样策略的差异
- [ ] 配置合适的阈值
- [ ] 启动标注应用进行测试
- [ ] 与现有系统集成
- [ ] 部署到生产环境

---

**系统状态**: 🟢 生产就绪  
**版本**: v1.0  
**最后更新**: 2024-04-09
