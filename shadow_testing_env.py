"""
影子测试环境 - 并行运行生产模型和候选模型
支持A/B对比、差异分析和性能评估
"""

import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import os
from dotenv import load_dotenv

from multilingual_preprocessor import MultilingualTextPreprocessor
from multilingual_analyzer import MultilingualSentimentAnalyzer
from metrics_tracker import MetricsTracker, MetricPoint, record_metric

# 加载环境变量
load_dotenv()


class ModelVersion(Enum):
    """模型版本"""
    PRODUCTION = "production"        # 生产模型
    CANDIDATE = "candidate"          # 候选模型


@dataclass
class AnalysisResult:
    """分析结果"""
    model_version: str
    text_id: str
    language: str
    sentiment_score: float
    polarity: str
    confidence: float
    risk_level: str
    risk_count: int
    composite_score: float
    processing_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ComparisonResult:
    """A/B对比结果"""
    text_id: str
    language: str
    production_result: AnalysisResult
    candidate_result: AnalysisResult
    sentiment_diff: float          # 情绪分数差异
    polarity_agreement: bool       # 极性是否一致
    confidence_diff: float         # 置信度差异
    risk_agreement: bool           # 风险等级是否一致
    consistency_score: float       # 一致性评分 (0-100)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ShadowTestingEnvironment:
    """影子测试环境 - 并行运行两个模型"""
    
    def __init__(
        self,
        metrics_tracker: Optional[MetricsTracker] = None,
        production_model: str = "deepseek-chat",
        candidate_model: str = "deepseek-chat",
        use_mock: bool = False
    ):
        """
        初始化影子测试环境
        
        Args:
            metrics_tracker: 指标追踪器
            production_model: 生产模型名称
            candidate_model: 候选模型名称
            use_mock: 是否使用Mock分析器（调试用）
        """
        self.preprocessor = MultilingualTextPreprocessor()
        
        # 模型分析器 - 使用真实的 LLM API
        api_key = os.getenv("LLM_API_KEY")
        
        if use_mock or not api_key:
            # 调试模式：使用 Mock 分析器
            from test_complete_flow import MockLLMAnalyzer
            self.production_analyzer = MockLLMAnalyzer()
            self.candidate_analyzer = MockLLMAnalyzer()
        else:
            # 生产模式：使用真实的 LLM API
            self.production_analyzer = MultilingualSentimentAnalyzer(
                model_name=production_model,
                api_key=api_key
            )
            self.candidate_analyzer = MultilingualSentimentAnalyzer(
                model_name=candidate_model,
                api_key=api_key
            )
        
        self.metrics_tracker = metrics_tracker
        
        # 结果存储
        self.production_results: List[AnalysisResult] = []
        self.candidate_results: List[AnalysisResult] = []
        self.comparisons: List[ComparisonResult] = []
        
        # 统计
        self.stats = {
            "total_processed": 0,
            "total_compared": 0,
            "consensus_count": 0,
            "production_total_time_ms": 0,
            "candidate_total_time_ms": 0,
        }
        
        self._lock = threading.Lock()
    
    def analyze_with_both_models(
        self,
        text: str,
        text_id: str,
        language: str
    ) -> Tuple[AnalysisResult, AnalysisResult]:
        """
        使用两个模型同时分析文本
        
        Args:
            text: 输入文本
            text_id: 文本ID
            language: 语言
        
        Returns:
            (production_result, candidate_result)
        """
        # 预处理
        chunks = self.preprocessor.process(text)
        if not chunks:
            raise ValueError(f"预处理失败: {text_id}")
        
        chunk = chunks[0]
        
        # 并行运行两个模型
        prod_result = None
        cand_result = None
        error_prod = None
        error_cand = None
        
        def run_production():
            nonlocal prod_result, error_prod
            try:
                start = time.time()
                analysis = self.production_analyzer.analyze_batch([chunk])
                elapsed_ms = (time.time() - start) * 1000
                
                if analysis:
                    res = analysis[0]
                    prod_result = AnalysisResult(
                        model_version=ModelVersion.PRODUCTION.value,
                        text_id=text_id,
                        language=language,
                        sentiment_score=res.sentiment.sentiment_score if res.sentiment else 0,
                        polarity=res.sentiment.polarity.value if res.sentiment else "neutral",
                        confidence=res.sentiment.confidence if res.sentiment else 0,
                        risk_level=res.risks[0].risk_level.value if res.risks else "green",
                        risk_count=len(res.risks),
                        composite_score=res.composite_score,
                        processing_time_ms=elapsed_ms
                    )
            except Exception as e:
                error_prod = str(e)
        
        def run_candidate():
            nonlocal cand_result, error_cand
            try:
                start = time.time()
                analysis = self.candidate_analyzer.analyze_batch([chunk])
                elapsed_ms = (time.time() - start) * 1000
                
                if analysis:
                    res = analysis[0]
                    cand_result = AnalysisResult(
                        model_version=ModelVersion.CANDIDATE.value,
                        text_id=text_id,
                        language=language,
                        sentiment_score=res.sentiment.sentiment_score if res.sentiment else 0,
                        polarity=res.sentiment.polarity.value if res.sentiment else "neutral",
                        confidence=res.sentiment.confidence if res.sentiment else 0,
                        risk_level=res.risks[0].risk_level.value if res.risks else "green",
                        risk_count=len(res.risks),
                        composite_score=res.composite_score,
                        processing_time_ms=elapsed_ms
                    )
            except Exception as e:
                error_cand = str(e)
        
        # 并行执行
        t1 = threading.Thread(target=run_production)
        t2 = threading.Thread(target=run_candidate)
        
        t1.start()
        t2.start()
        
        t1.join(timeout=10)
        t2.join(timeout=10)
        
        if error_prod or error_cand:
            raise Exception(f"模型分析失败: prod={error_prod}, cand={error_cand}")
        
        # 记录指标
        if prod_result and self.metrics_tracker:
            record_metric(
                metric_type="latency",
                value=prod_result.processing_time_ms,
                model_id="production",
                batch_id=text_id,
                language=language
            )
        
        if cand_result and self.metrics_tracker:
            record_metric(
                metric_type="latency",
                value=cand_result.processing_time_ms,
                model_id="candidate",
                batch_id=text_id,
                language=language
            )
        
        # 更新统计
        with self._lock:
            self.production_results.append(prod_result)
            self.candidate_results.append(cand_result)
            self.stats["total_processed"] += 1
            if prod_result:
                self.stats["production_total_time_ms"] += prod_result.processing_time_ms
            if cand_result:
                self.stats["candidate_total_time_ms"] += cand_result.processing_time_ms
        
        return prod_result, cand_result
    
    def compare_results(
        self,
        prod_result: AnalysisResult,
        cand_result: AnalysisResult
    ) -> ComparisonResult:
        """
        比较两个模型的结果
        
        Args:
            prod_result: 生产模型结果
            cand_result: 候选模型结果
        
        Returns:
            比较结果
        """
        # 计算差异
        sentiment_diff = abs(prod_result.sentiment_score - cand_result.sentiment_score)
        polarity_agreement = prod_result.polarity == cand_result.polarity
        confidence_diff = abs(prod_result.confidence - cand_result.confidence)
        risk_agreement = prod_result.risk_level == cand_result.risk_level
        
        # 计算一致性评分
        # 基础分: 100
        consistency = 100.0
        
        # 极性一致性：占40%
        if not polarity_agreement:
            consistency -= 40
        
        # 风险等级一致性：占30%
        if not risk_agreement:
            consistency -= 30
        
        # 情绪分数接近度：占20%（差异小于0.2时满分）
        if sentiment_diff > 0.5:
            consistency -= 20
        elif sentiment_diff > 0.2:
            consistency -= 10
        
        # 置信度接近度：占10%
        if confidence_diff > 0.3:
            consistency -= 10
        elif confidence_diff > 0.1:
            consistency -= 5
        
        consistency = max(0, min(100, consistency))
        
        comparison = ComparisonResult(
            text_id=prod_result.text_id,
            language=prod_result.language,
            production_result=prod_result,
            candidate_result=cand_result,
            sentiment_diff=sentiment_diff,
            polarity_agreement=polarity_agreement,
            confidence_diff=confidence_diff,
            risk_agreement=risk_agreement,
            consistency_score=consistency
        )
        
        with self._lock:
            self.comparisons.append(comparison)
            self.stats["total_compared"] += 1
            if consistency > 80:  # 一致性好
                self.stats["consensus_count"] += 1
            
            # 记录一致性指标
            if self.metrics_tracker:
                record_metric(
                    metric_type="consistency",
                    value=consistency,
                    model_id="comparison",
                    batch_id=prod_result.text_id,
                    language=prod_result.language
                )
        
        return comparison
    
    def get_comparison_summary(self) -> Dict:
        """获取对比汇总"""
        if not self.comparisons:
            return {}
        
        consistencies = [c.consistency_score for c in self.comparisons]
        sentiment_diffs = [c.sentiment_diff for c in self.comparisons]
        
        return {
            "total_comparisons": len(self.comparisons),
            "consensus_rate": (
                self.stats["consensus_count"] / self.stats["total_compared"]
                if self.stats["total_compared"] > 0 else 0
            ),
            "avg_consistency": sum(consistencies) / len(consistencies),
            "min_consistency": min(consistencies),
            "max_consistency": max(consistencies),
            "avg_sentiment_diff": sum(sentiment_diffs) / len(sentiment_diffs),
            "polarity_agreement_rate": sum(
                1 for c in self.comparisons if c.polarity_agreement
            ) / len(self.comparisons),
            "risk_agreement_rate": sum(
                1 for c in self.comparisons if c.risk_agreement
            ) / len(self.comparisons),
            "avg_production_latency_ms": (
                self.stats["production_total_time_ms"] / self.stats["total_processed"]
                if self.stats["total_processed"] > 0 else 0
            ),
            "avg_candidate_latency_ms": (
                self.stats["candidate_total_time_ms"] / self.stats["total_processed"]
                if self.stats["total_processed"] > 0 else 0
            ),
        }
    
    def get_discrepancies(self, threshold: float = 70) -> List[ComparisonResult]:
        """
        获取一致性低于阈值的结果（需要人工复核）
        
        Args:
            threshold: 一致性阈值 (0-100)
        
        Returns:
            需要复核的比较结果
        """
        return [c for c in self.comparisons if c.consistency_score < threshold]
    
    def print_comparison_report(self):
        """打印对比报告"""
        summary = self.get_comparison_summary()
        
        print("\n" + "="*70)
        print("🔄 影子测试 - A/B对比报告")
        print("="*70)
        
        if not summary:
            print("❌ 无对比数据")
            return
        
        print(f"\n📊 总体统计:")
        print(f"  对比总数: {summary['total_comparisons']}")
        print(f"  共识率: {summary['consensus_rate']:.1%}")
        print(f"  平均一致性: {summary['avg_consistency']:.1f}/100")
        
        print(f"\n🎯 一致性分析:")
        print(f"  极性一致率: {summary['polarity_agreement_rate']:.1%}")
        print(f"  风险等级一致率: {summary['risk_agreement_rate']:.1%}")
        print(f"  平均情绪差异: {summary['avg_sentiment_diff']:+.3f}")
        
        print(f"\n⏱️  性能对比:")
        print(f"  生产模型平均延迟: {summary['avg_production_latency_ms']:.1f}ms")
        print(f"  候选模型平均延迟: {summary['avg_candidate_latency_ms']:.1f}ms")
        
        # 显示需要复核的样本
        discrepancies = self.get_discrepancies()
        if discrepancies:
            print(f"\n⚠️  需要复核的样本 ({len(discrepancies)}个):")
            for comp in discrepancies[:5]:
                print(f"  - {comp.text_id}: 一致性{comp.consistency_score:.1f}%")
                if not comp.polarity_agreement:
                    print(f"    ❌ 极性不一致: {comp.production_result.polarity} vs {comp.candidate_result.polarity}")
                if not comp.risk_agreement:
                    print(f"    ❌ 风险不一致: {comp.production_result.risk_level} vs {comp.candidate_result.risk_level}")
