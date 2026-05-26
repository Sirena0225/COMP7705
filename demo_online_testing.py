"""
在线测试框架 - 完整演示和测试脚本
展示实时数据处理、A/B测试、评估和反馈的完整流程
"""

import argparse
import time
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA = PROJECT_ROOT / "data" / "sentiment_input_batch.json"

from data_stream_sampler import (
    DataStreamSampler,
    DataStreamSample,
    SamplingStrategy,
    SamplingConfig,
    RealTimeDataStream
)
from shadow_testing_env import ShadowTestingEnvironment
from evaluation_engine import EvaluationEngine
from metrics_tracker import MetricsTracker
from feedback_controller import FeedbackController
from annotation_interface import AnnotationInterface
from online_test_framework import (
    OnlineTestingFramework,
    OnlineTestConfig
)

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OnlineTestDemo")


def demo_data_stream_sampler():
    """演示1: 数据流采样器"""
    print("\n" + "="*70)
    print("演示1️⃣ : 数据流采样器 (DataStreamSampler)")
    print("="*70)
    
    # 创建采样器
    config = SamplingConfig(
        overall_rate=0.1,
        language_weights={"zh": 0.5, "en": 0.3, "mixed": 0.2},
        source_weights={"news": 0.4, "social_media": 0.3}
    )
    
    sampler = DataStreamSampler(
        strategy=SamplingStrategy.STRATIFIED,
        config=config
    )
    
    print("\n✅ 采样器配置:")
    print(f"  策略: STRATIFIED (分层采样)")
    print(f"  整体采样率: {config.overall_rate:.0%}")
    print(f"  语言权重: {config.language_weights}")
    
    # 启动采样
    sampler.start()
    
    # 创建实时数据流
    stream = RealTimeDataStream(sampler=sampler, rate=15)
    
    print("\n🚀 推送实时数据流 (15个样本/秒, 运行10秒)...")
    stream.start_streaming(duration_seconds=10)
    
    # 打印统计
    time.sleep(1)
    sampler.print_stats()
    
    sampler.stop()


def demo_shadow_testing():
    """演示2: 影子测试环境"""
    print("\n" + "="*70)
    print("演示2️⃣ : 影子测试环境 (ShadowTestingEnvironment)")
    print("="*70)
    
    shadow_env = ShadowTestingEnvironment()
    
    # 测试文本
    test_cases = [
        {
            "id": "case-001",
            "text": "腾讯Q1财报超预期，游戏和云服务业务双增长。",
            "language": "zh"
        },
        {
            "id": "case-002",
            "text": "Alibaba faces regulatory scrutiny on data security.",
            "language": "en"
        },
        {
            "id": "case-003",
            "text": "美团Meituan外卖业务实现盈利 achieving profitability.",
            "language": "mixed"
        }
    ]
    
    print("\n🔄 并行运行生产模型和候选模型...")
    
    for case in test_cases:
        try:
            prod_result, cand_result = shadow_env.analyze_with_both_models(
                text=case["text"],
                text_id=case["id"],
                language=case["language"]
            )
            
            # 比较
            comparison = shadow_env.compare_results(prod_result, cand_result)
            
            print(f"\n📊 【{case['id']}】 ({case['language']})")
            print(f"  文本: {case['text'][:40]}...")
            print(f"  生产模型 - 极性: {prod_result.polarity:8} | 情绪: {prod_result.sentiment_score:+.3f} | 延迟: {prod_result.processing_time_ms:.1f}ms")
            print(f"  候选模型 - 极性: {cand_result.polarity:8} | 情绪: {cand_result.sentiment_score:+.3f} | 延迟: {cand_result.processing_time_ms:.1f}ms")
            print(f"  ✅ 一致性评分: {comparison.consistency_score:.1f}/100")
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    # 打印对比报告
    shadow_env.print_comparison_report()


def demo_evaluation_engine():
    """演示3: 评估引擎"""
    print("\n" + "="*70)
    print("演示3️⃣ : 评估引擎 (EvaluationEngine)")
    print("="*70)
    
    engine = EvaluationEngine()
    
    # 测试情感分类准确率
    print("\n📊 情感分类准确率:")
    predictions = ["positive", "negative", "positive", "neutral", "positive"]
    ground_truth = ["positive", "negative", "neutral", "neutral", "positive"]
    
    accuracy = engine.evaluate_sentiment_accuracy(predictions, ground_truth)
    print(f"  预测: {predictions}")
    print(f"  真实: {ground_truth}")
    print(f"  准确率: {accuracy.value:.0%}")
    
    # 测试延迟
    print("\n⏱️ 处理延迟统计:")
    latencies = [50, 120, 80, 95, 150, 200, 100, 110, 140, 99]
    latency_results = engine.evaluate_latency(latencies)
    
    for name, result in latency_results.items():
        print(f"  {name}: {result.value:.1f}ms")
    
    # 测试置信度校准
    print("\n🎯 置信度校准:")
    predictions_conf = [
        (0.9, True),   # 高置信且正确
        (0.8, True),
        (0.3, False),  # 低置信但错误
        (0.7, False),  # 高置信但错误
    ]
    
    calibration = engine.evaluate_confidence_calibration(predictions_conf)
    print(f"  校准误差: {calibration.value:.3f} (越小越好)")


def demo_metrics_tracker():
    """演示4: 指标追踪器"""
    print("\n" + "="*70)
    print("演示4️⃣ : 指标追踪器 (MetricsTracker)")
    print("="*70)
    
    tracker = MetricsTracker()
    
    print("\n📝 记录100个性能指标...")
    
    # 模拟记录指标
    from metrics_tracker import MetricPoint
    
    for i in range(100):
        timestamp = (time.time() - (100 - i)) * 1000
        
        # 记录准确率
        point1 = MetricPoint(
            timestamp=f"2024-04-09T10:{str(i//60).zfill(2)}:{str(i%60).zfill(2)}Z",
            metric_type="accuracy",
            value=0.85 + (i % 5) * 0.01,
            model_id="production",
            batch_id=f"batch-{i//10}",
            language="zh" if i % 3 == 0 else "en"
        )
        tracker.record_metric(point1)
    
    # 获取统计
    print("\n📊 查询统计数据...")
    summary = tracker.get_metric_summary("accuracy", "production", hours=1)
    
    if summary:
        print(f"  样本数: {summary.count}")
        print(f"  平均值: {summary.mean:.3f}")
        print(f"  中位数: {summary.median:.3f}")
        print(f"  P95: {summary.p95:.3f}")
        print(f"  标准差: {summary.std_dev:.3f}")


def demo_feedback_controller():
    """演示5: 反馈控制器"""
    print("\n" + "="*70)
    print("演示5️⃣ : 反馈控制器 (FeedbackController)")
    print("="*70)
    
    controller = FeedbackController()
    
    # 模拟评估结果
    evaluation_results = {
        "accuracy": 0.82,          # 低于阈值0.85
        "avg_confidence": 0.65,    # 低于阈值0.70
        "latency_p95": 1200,       # 高于阈值1000ms
    }
    
    error_samples = [
        {"text": "样本1", "prediction": "positive", "ground_truth": "negative", "confidence": 0.8},
        {"text": "样本2", "prediction": "positive", "ground_truth": "neutral", "confidence": 0.85},
    ]
    
    from evaluation_engine import PerformanceThreshold
    thresholds = PerformanceThreshold()
    
    print("\n🔍 分析并生成调整操作...")
    print(f"  准确率: {evaluation_results['accuracy']:.0%} (阈值: {thresholds.accuracy_min:.0%})")
    print(f"  置信度: {evaluation_results['avg_confidence']:.0%} (阈值: {thresholds.confidence_min:.0%})")
    print(f"  延迟P95: {evaluation_results['latency_p95']:.0f}ms (阈值: {thresholds.latency_max_ms:.0f}ms)")
    
    actions = controller.analyze_and_generate_actions(
        evaluation_results=evaluation_results,
        error_samples=error_samples,
        thresholds=thresholds
    )
    
    print(f"\n✅ 生成了 {len(actions)} 个调整操作:")
    for action in actions:
        print(f"  - {action.adjustment_type.value}: {action.action}")
        print(f"    参数: {action.parameters}")


def demo_annotation_interface():
    """演示6: 人工标注接口"""
    print("\n" + "="*70)
    print("演示6️⃣ : 人工标注接口 (AnnotationInterface)")
    print("="*70)
    
    interface = AnnotationInterface()
    
    from annotation_interface import AnnotationTask, AnnotationResult
    
    # 创建标注任务
    print("\n📝 创建标注任务...")
    
    tasks = [
        AnnotationTask(
            task_id="task-001",
            text="腾讯财报超预期",
            text_id="text-001",
            language="zh",
            stock_code="00700.HK",
            source="news",
            production_result={"sentiment_score": 0.7, "polarity": "positive"},
            candidate_result={"sentiment_score": -0.2, "polarity": "neutral"},
            priority=2,
            reason="一致性低 (45%)"
        ),
        AnnotationTask(
            task_id="task-002",
            text="Alibaba regulatory review",
            text_id="text-002",
            language="en",
            stock_code="09988.HK",
            source="news",
            production_result={"sentiment_score": -0.3, "polarity": "negative"},
            candidate_result={"sentiment_score": 0.0, "polarity": "neutral"},
            priority=1,
            reason="一致性低 (65%)"
        ),
    ]
    
    interface.add_batch_tasks(tasks)
    print(f"  ✅ 已创建 {len(tasks)} 个标注任务")
    
    # 获取下一个任务
    print("\n👤 标注者开始标注...")
    task = interface.get_next_task("annotator_001")
    
    if task:
        print(f"  📋 任务: {task.task_id}")
        print(f"  文本: {task.text}")
        print(f"  优先级: {'🔴' if task.priority == 2 else '🟡'}")
        
        # 提交标注结果
        result = AnnotationResult(
            task_id=task.task_id,
            annotator_id="annotator_001",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            gold_standard_polarity="positive",
            gold_standard_risk_level="yellow",
            confidence=0.95,
            notes="文本明确表达积极情绪",
        )
        
        if interface.submit_annotation(result):
            print(f"  ✅ 标注已提交")
    
    # 显示统计
    stats = interface.get_annotation_stats()
    print(f"\n📊 标注统计:")
    print(f"  待标注任务: {stats['pending_tasks']}")
    print(f"  已完成: {stats['total_completed']}")



def demo_json_data_stream():
    """演示7: 从 JSON 文件加载真实数据的数据流"""
    print("\n" + "="*70)
    print("演示7️⃣ : 从 JSON 文件加载真实数据")
    print("="*70)
    
    from data_stream_sampler import DataStreamSampler, JSONDataStream, SamplingStrategy, SamplingConfig
    
    # 创建采样器
    config = SamplingConfig(
        overall_rate=0.1,
        language_weights={"zh": 0.5, "en": 0.3, "mixed": 0.2},
        source_weights={"news": 0.4, "social_media": 0.3, "announcement": 0.3}
    )
    
    sampler = DataStreamSampler(
        strategy=SamplingStrategy.STRATIFIED,
        config=config
    )
    
    print("\n✅ 采样器配置:")
    print(f"  策略: STRATIFIED (分层采样)")
    print(f"  整体采样率: {config.overall_rate:.0%}")
    print(f"  语言权重: {config.language_weights}")
    
    # 启动采样
    sampler.start()
    
    # 创建 JSON 数据流
    json_stream = JSONDataStream(
        sampler=sampler,
        json_file_path=str(DEFAULT_DATA),
        rate=50  # 每秒推送50个样本
    )
    
    print("\n📂 使用 JSON 数据源:")
    print(f"  文件: {DEFAULT_DATA}")
    print(f"  推送速率: 50 样本/秒")
    
    # 在后台线程运行数据流
    print("\n🚀 启动 JSON 数据流...")
    stream_thread = threading.Thread(
        target=lambda: json_stream.stream_from_json(samples_per_second=50)
    )
    stream_thread.start()
    
    # 获取样本
    print("\n📊 采样结果:")
    time.sleep(3)  # 等待样本被采样
    batch = sampler.get_next_batch(10)
    
    if batch:
        print(f"\n  获得 {len(batch)} 个采样样本:")
        for i, sample in enumerate(batch[:3], 1):
            print(f"\n  样本 {i}:")
            print(f"    ID: {sample.sample_id}")
            print(f"    文本长度: {len(sample.text)} 字符")
            print(f"    语言: {sample.language}")
            print(f"    股票代码: {sample.stock_code}")
            print(f"    来源: {sample.source} ({sample.source_name})")
            print(f"    时间戳: {sample.timestamp}")
    
    # 等待数据流完成
    stream_thread.join()
    
    # 打印统计
    print("\n📈 采样统计:")
    sampler.print_stats()
    
    sampler.stop()


def demo_complete_online_testing():
    """演示8: 完整在线测试框架 (使用 JSON 数据)"""
    print("\n" + "="*70)
    print("演示8️⃣ : 完整在线测试框架 (使用 JSON 数据)")
    print("="*70)
    
    from data_stream_sampler import JSONDataStream
    
    # 创建配置
    config = OnlineTestConfig(
        sampling_strategy=SamplingStrategy.STRATIFIED,
        sampling_rate=0.1,
        evaluation_interval_seconds=3,        # 每3秒评估一次
        evaluation_batch_size=5,
        accuracy_min=0.85,
        latency_max_ms=1000,
        consistency_min=0.80,
    )
    
    # 创建框架
    print("\n🚀 初始化在线测试框架...")
    framework = OnlineTestingFramework(config)
    framework.start()
    
    # 使用 JSON 数据流推送样本
    print("\n📤 从 JSON 文件推送样本到框架...")
    
    json_stream = JSONDataStream(
        sampler=framework.sampler,
        json_file_path=str(DEFAULT_DATA),
        rate=50  # 每秒推送50个样本
    )
    
    # 在后台线程运行数据流
    import threading
    stream_thread = threading.Thread(
        target=lambda: json_stream.stream_from_json(samples_per_second=50)
    )
    stream_thread.start()
    
    # 等待处理
    print("\n⏳ 等待处理完成...")
    stream_thread.join()
    time.sleep(2)
    
    # 打印总结
    framework.print_summary()
    
    # 停止框架
    framework.stop()



def main():
    """默认运行端到端在线测试；--full 运行全部分项演示。"""
    parser = argparse.ArgumentParser(description="港股舆情在线测试演示")
    parser.add_argument(
        "--full",
        action="store_true",
        help="依次运行采样、影子测试、评估等分项演示",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🎬 港股舆情 - 在线测试演示")
    print("=" * 70)

    try:
        if args.full:
            for fn in (
                demo_data_stream_sampler,
                demo_json_data_stream,
                demo_shadow_testing,
                demo_evaluation_engine,
                demo_metrics_tracker,
                demo_feedback_controller,
                demo_annotation_interface,
            ):
                fn()
            print()
        demo_complete_online_testing()
        print("\n✅ 演示完成。输出目录: ./online_test_results/")
    except KeyboardInterrupt:
        print("\n⚠️  演示已中断")
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
