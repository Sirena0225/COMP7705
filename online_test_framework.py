"""
在线测试框架 - 完整的实时数据处理和评估系统
整合数据流采样、影子测试、评估引擎、反馈控制等所有组件
"""

import os
import time
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from data_stream_sampler import (
    DataStreamSampler,
    DataStreamSample,
    SamplingStrategy,
    SamplingConfig
)
from shadow_testing_env import ShadowTestingEnvironment
from evaluation_engine import EvaluationEngine, PerformanceThreshold
from metrics_tracker import MetricsTracker, record_metric
from feedback_controller import FeedbackController, AdjustmentType
from annotation_interface import AnnotationInterface, AnnotationTask


@dataclass
class OnlineTestConfig:
    """在线测试配置"""
    # 采样配置
    sampling_strategy: SamplingStrategy = SamplingStrategy.STRATIFIED
    sampling_rate: float = 0.1
    
    # 评估配置
    evaluation_interval_seconds: int = 300  # 5分钟评估一次
    evaluation_batch_size: int = 100
    
    # 性能阈值
    accuracy_min: float = 0.85
    latency_max_ms: float = 1000
    consistency_min: float = 0.80
    
    # LLM 配置
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    use_mock_models: bool = not bool(os.getenv("LLM_API_KEY"))  # 无API时使用Mock
    
    # 输出路径
    output_dir: str = "./online_test_results"


class OnlineTestingFramework:
    """在线测试框架 - 主控制器"""
    
    def __init__(self, config: Optional[OnlineTestConfig] = None):
        """初始化框架"""
        self.config = config or OnlineTestConfig()
        
        # 创建输出目录
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        
        # 初始化各组件
        sampling_config = SamplingConfig(overall_rate=self.config.sampling_rate)
        self.sampler = DataStreamSampler(
            strategy=self.config.sampling_strategy,
            config=sampling_config
        )
        
        self.metrics_tracker = MetricsTracker()
        
        # 初始化影子测试环境，使用真实或Mock分析器
        self.shadow_env = ShadowTestingEnvironment(
            metrics_tracker=self.metrics_tracker,
            production_model=self.config.llm_model,
            candidate_model=self.config.llm_model,
            use_mock=self.config.use_mock_models
        )
        
        self.evaluation_engine = EvaluationEngine()
        self.feedback_controller = FeedbackController()
        self.annotation_interface = AnnotationInterface()
        
        # 统计
        self.stats = {
            "total_samples_received": 0,
            "total_samples_processed": 0,
            "total_comparisons": 0,
            "start_time": datetime.now().isoformat(),
            "llm_model": self.config.llm_model,
            "using_mock_models": self.config.use_mock_models,
        }
        
        # 控制标志
        self._running = False
        self._lock = threading.Lock()
    
    def configure_feedback_callbacks(self):
        """配置反馈控制器的回调函数"""
        
        def prompt_optimization_callback(action):
            """提示词优化回调"""
            print(f"🔧 优化提示词: {action.parameters}")
            # 这里可以实现实际的提示词更新逻辑
            return True
        
        def threshold_adjustment_callback(action):
            """阈值调整回调"""
            print(f"📊 调整阈值: {action.parameters}")
            # 这里可以实现实际的阈值更新逻辑
            return True
        
        def sampling_strategy_callback(action):
            """采样策略调整回调"""
            print(f"🎲 调整采样策略: {action.parameters}")
            # 这里可以实现实际的采样率更新逻辑
            return True
        
        self.feedback_controller.register_callback(
            AdjustmentType.PROMPT_ENGINEERING,
            prompt_optimization_callback
        )
        self.feedback_controller.register_callback(
            AdjustmentType.THRESHOLD_ADJUSTMENT,
            threshold_adjustment_callback
        )
        self.feedback_controller.register_callback(
            AdjustmentType.SAMPLING_STRATEGY,
            sampling_strategy_callback
        )
    
    def start(self):
        """启动在线测试框架"""
        print("\n" + "="*70)
        print("🚀 启动在线测试框架")
        print("="*70)
        
        # 显示 LLM 配置
        if self.config.use_mock_models:
            print("⚠️  使用 Mock 分析器 (调试模式)")
            print("   提示: 设置 LLM_API_KEY 环境变量以使用真实 LLM API")
        else:
            print(f"✅ 使用真实 LLM API")
            print(f"   模型: {self.config.llm_model}")
            print(f"   API Key: {self.config.llm_api_key[:20]}...")
        
        self._running = True
        self.configure_feedback_callbacks()
        
        # 启动采样处理
        self.sampler.start()
        
        # 启动评估线程
        evaluation_thread = threading.Thread(
            target=self._evaluation_loop,
            daemon=True
        )
        evaluation_thread.start()
        
        print("✅ 在线测试框架已启动")
    
    def stop(self):
        """停止在线测试框架"""
        self._running = False
        self.sampler.stop()
        print("🛑 在线测试框架已停止")
    
    def push_sample(self, sample: DataStreamSample):
        """推送样本到框架"""
        self.sampler.push_sample(sample)
        
        with self._lock:
            self.stats["total_samples_received"] += 1
    
    def _evaluation_loop(self):
        """评估主循环"""
        thresholds = PerformanceThreshold(
            accuracy_min=self.config.accuracy_min,
            latency_max_ms=self.config.latency_max_ms,
            consistency_min=self.config.consistency_min,
        )
        
        while self._running:
            try:
                # 获取一批样本
                batch = self.sampler.get_next_batch(self.config.evaluation_batch_size)
                
                if not batch:
                    time.sleep(1)
                    continue
                
                print(f"\n📦 处理批次: {len(batch)} 个样本")
                
                # 处理批次
                self._process_batch(batch, thresholds)
                
                # 等待下一个评估周期
                time.sleep(self.config.evaluation_interval_seconds)
                
            except Exception as e:
                print(f"❌ 评估循环出错: {e}")
                time.sleep(5)
    
    def _process_batch(
        self,
        batch: List[DataStreamSample],
        thresholds: PerformanceThreshold
    ):
        """处理一个批次的样本"""
        batch_id = f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # 第1步: A/B测试 (并行运行生产模型和候选模型)
        print(f"  1️⃣  运行A/B测试 ({len(batch)} 个样本)...")
        
        comparisons = []
        error_samples = []
        
        for sample in batch:
            try:
                prod_result, cand_result = self.shadow_env.analyze_with_both_models(
                    text=sample.text,
                    text_id=sample.sample_id,
                    language=sample.language
                )
                
                # 比较结果
                comparison = self.shadow_env.compare_results(prod_result, cand_result)
                comparisons.append(comparison)
                
                # 记录一致性指标
                record_metric(
                    metric_type="consistency",
                    value=comparison.consistency_score,
                    model_id="comparison",
                    batch_id=batch_id,
                    language=sample.language,
                    stock_code=sample.stock_code
                )
                
                # 如果一致性低，记录为错误样本
                if comparison.consistency_score < thresholds.consistency_min * 100:
                    error_samples.append({
                        "text": sample.text,
                        "prediction": comparison.production_result.polarity,
                        "confidence": comparison.production_result.confidence,
                        "consistency": comparison.consistency_score
                    })
                    
            except Exception as e:
                print(f"    ❌ 样本 {sample.sample_id} 处理失败: {e}")
        
        print(f"  ✅ A/B测试完成: {len(comparisons)} 个对比结果")
        
        with self._lock:
            self.stats["total_comparisons"] += len(comparisons)
        
        # 第2步: 评估
        print(f"  2️⃣  评估模型性能...")
        
        evaluation_results = self._evaluate_batch(comparisons)
        
        # 记录评估结果
        for metric_name, value in evaluation_results.items():
            record_metric(
                metric_type=metric_name,
                value=value,
                model_id="production",
                batch_id=batch_id,
                language="mixed"
            )
        
        # 第3步: 自适应反馈
        print(f"  3️⃣  分析并生成反馈...")
        
        actions = self.feedback_controller.analyze_and_generate_actions(
            evaluation_results=evaluation_results,
            error_samples=error_samples,
            thresholds=thresholds
        )
        
        if actions:
            print(f"    📋 生成 {len(actions)} 个调整操作")
            
            # 执行调整
            results = self.feedback_controller.apply_actions(actions)
            
            successful = sum(1 for v in results.values() if v)
            print(f"    ✅ 成功执行 {successful}/{len(actions)} 个调整")
        
        # 第4步: 人机协同 (创建标注任务)
        print(f"  4️⃣  创建人工标注任务...")
        
        # 转换为标注任务（一致性低的样本）
        annotation_tasks = []
        for comp in comparisons:
            if comp.consistency_score < thresholds.consistency_min * 100:
                task = AnnotationTask(
                    task_id=comp.text_id,
                    text="",  # 需要从原始样本获取
                    text_id=comp.text_id,
                    language=comp.language,
                    stock_code="",
                    source="",
                    production_result=asdict(comp.production_result),
                    candidate_result=asdict(comp.candidate_result),
                    priority=2 if comp.consistency_score < 50 else 1,
                    reason=f"一致性低 ({comp.consistency_score:.1f}%)"
                )
                annotation_tasks.append(task)
        
        if annotation_tasks:
            self.annotation_interface.add_batch_tasks(annotation_tasks)
            print(f"    📝 创建 {len(annotation_tasks)} 个标注任务")
        
        # 输出批次报告
        self._save_batch_report(batch_id, comparisons, evaluation_results, actions)
    
    def _evaluate_batch(self, comparisons: List) -> Dict[str, float]:
        """评估一个批次"""
        if not comparisons:
            return {}
        
        results = {}
        
        # 计算一致性
        consistencies = [c.consistency_score for c in comparisons]
        results["consistency_mean"] = sum(consistencies) / len(consistencies)
        results["consistency_min"] = min(consistencies)
        
        # 计算其他指标
        sentiment_diffs = [c.sentiment_diff for c in comparisons]
        results["sentiment_diff_mean"] = sum(sentiment_diffs) / len(sentiment_diffs)
        
        latencies_prod = [c.production_result.processing_time_ms for c in comparisons]
        latencies_cand = [c.candidate_result.processing_time_ms for c in comparisons]
        
        results["latency_prod_p95"] = sorted(latencies_prod)[int(len(latencies_prod) * 0.95)]
        results["latency_cand_p95"] = sorted(latencies_cand)[int(len(latencies_cand) * 0.95)]
        
        polarity_agreement = sum(
            1 for c in comparisons if c.polarity_agreement
        ) / len(comparisons)
        results["polarity_agreement_rate"] = polarity_agreement
        
        return results
    
    def _save_batch_report(
        self,
        batch_id: str,
        comparisons: List,
        evaluation_results: Dict,
        actions: List
    ):
        """保存批次报告"""
        report = {
            "batch_id": batch_id,
            "timestamp": datetime.now().isoformat(),
            "comparison_count": len(comparisons),
            "evaluation_results": evaluation_results,
            "action_count": len(actions),
            "comparison_summary": {
                "avg_consistency": sum(
                    c.consistency_score for c in comparisons
                ) / len(comparisons) if comparisons else 0,
                "polarity_agreement_rate": sum(
                    1 for c in comparisons if c.polarity_agreement
                ) / len(comparisons) if comparisons else 0,
            }
        }
        
        report_file = Path(self.config.output_dir) / f"{batch_id}_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"  💾 报告已保存: {report_file}")
    
    def print_summary(self):
        """打印框架总结"""
        print("\n" + "="*70)
        print("📊 在线测试框架 - 运行总结")
        print("="*70)
        
        with self._lock:
            stats = self.stats.copy()
        
        print(f"总样本数: {stats['total_samples_received']}")
        print(f"处理样本数: {stats['total_samples_processed']}")
        print(f"A/B对比数: {stats['total_comparisons']}")
        
        # 采样统计
        sampler_stats = self.sampler.get_stats()
        print(f"\n📥 采样统计:")
        print(f"  采样率: {sampler_stats['sampling_rate']:.1%}")
        print(f"  按语言: {sampler_stats['samples_by_language']}")
        
        # 影子测试总结
        comparison_summary = self.shadow_env.get_comparison_summary()
        if comparison_summary:
            print(f"\n🔄 影子测试总结:")
            print(f"  对比总数: {comparison_summary['total_comparisons']}")
            print(f"  共识率: {comparison_summary['consensus_rate']:.1%}")
            print(f"  平均一致性: {comparison_summary['avg_consistency']:.1f}/100")
        
        # 反馈控制总结
        adjustment_summary = self.feedback_controller.get_adjustment_summary()
        print(f"\n⚙️  反馈控制总结:")
        print(f"  总调整次数: {adjustment_summary['total_actions']}")
        print(f"  提示词优化: {adjustment_summary['prompt_optimizations']}")
        
        # 标注统计
        annotation_stats = self.annotation_interface.get_annotation_stats()
        print(f"\n📝 标注统计:")
        print(f"  待标注任务: {annotation_stats['pending_tasks']}")
        print(f"  已完成: {annotation_stats['total_completed']}")


