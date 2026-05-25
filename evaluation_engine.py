"""
评估引擎 - 计算模型性能指标
支持准确率、延迟、一致性、召回率等多维度评估
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics
from datetime import datetime


class EvaluationMetric(Enum):
    """评估指标类型"""
    ACCURACY = "accuracy"              # 准确率
    PRECISION = "precision"            # 精确率
    RECALL = "recall"                  # 召回率
    F1_SCORE = "f1_score"             # F1分数
    LATENCY = "latency"                # 延迟
    THROUGHPUT = "throughput"          # 吞吐量
    CONSISTENCY = "consistency"        # 一致性
    CONFIDENCE = "confidence"          # 置信度


@dataclass
class EvaluationResult:
    """评估结果"""
    metric_name: str
    value: float
    baseline: Optional[float] = None   # 基线值用于对比
    delta: Optional[float] = None      # 与基线的差值
    status: str = "normal"             # 正常/改进/下降
    timestamp: str = ""


@dataclass
class ModelEvaluation:
    """模型评估报告"""
    model_id: str
    evaluation_date: str
    total_samples: int
    results: Dict[str, EvaluationResult]
    metadata: Dict = None


class EvaluationEngine:
    """评估引擎 - 计算性能指标"""
    
    def __init__(self):
        """初始化评估引擎"""
        self.baseline_metrics: Dict[str, Dict[str, float]] = {}  # {model_id: {metric: value}}
    
    def set_baseline(self, model_id: str, metrics: Dict[str, float]):
        """设置基线指标"""
        self.baseline_metrics[model_id] = metrics
    
    def evaluate_sentiment_accuracy(
        self,
        predictions: List[str],
        ground_truth: List[str]
    ) -> EvaluationResult:
        """
        评估情感分类准确率
        
        Args:
            predictions: 模型预测 ["positive", "negative", ...]
            ground_truth: 真实标签
        
        Returns:
            准确率结果
        """
        if len(predictions) != len(ground_truth):
            raise ValueError("预测和真实标签长度不匹配")
        
        correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        accuracy = correct / len(predictions) if predictions else 0
        
        return EvaluationResult(
            metric_name="sentiment_accuracy",
            value=accuracy,
            timestamp=datetime.now().isoformat()
        )
    
    def evaluate_risk_detection(
        self,
        predictions: List[Tuple[str, float]],  # (risk_level, confidence)
        ground_truth: List[str]  # true risk level
    ) -> Dict[str, EvaluationResult]:
        """
        评估风险识别性能
        
        Args:
            predictions: 模型预测
            ground_truth: 真实风险等级
        
        Returns:
            {metric_name: result}
        """
        if len(predictions) != len(ground_truth):
            raise ValueError("预测和真实标签长度不匹配")
        
        # 二分类：有风险(yellow/red) vs 无风险(green)
        pred_positive = [1 if p[0] in ["yellow", "red"] else 0 for p in predictions]
        true_positive = [1 if g in ["yellow", "red"] else 0 for g in ground_truth]
        
        # 计算TP, FP, TN, FN
        tp = sum(1 for p, t in zip(pred_positive, true_positive) if p == 1 and t == 1)
        fp = sum(1 for p, t in zip(pred_positive, true_positive) if p == 1 and t == 0)
        tn = sum(1 for p, t in zip(pred_positive, true_positive) if p == 0 and t == 0)
        fn = sum(1 for p, t in zip(pred_positive, true_positive) if p == 0 and t == 1)
        
        # 计算指标
        accuracy = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            "accuracy": EvaluationResult(
                metric_name="risk_accuracy",
                value=accuracy,
                timestamp=datetime.now().isoformat()
            ),
            "precision": EvaluationResult(
                metric_name="risk_precision",
                value=precision,
                timestamp=datetime.now().isoformat()
            ),
            "recall": EvaluationResult(
                metric_name="risk_recall",
                value=recall,
                timestamp=datetime.now().isoformat()
            ),
            "f1": EvaluationResult(
                metric_name="risk_f1",
                value=f1,
                timestamp=datetime.now().isoformat()
            ),
        }
    
    def evaluate_latency(
        self,
        processing_times_ms: List[float]
    ) -> Dict[str, EvaluationResult]:
        """
        评估处理延迟
        
        Args:
            processing_times_ms: 每个样本的处理时间(毫秒)
        
        Returns:
            {metric_name: result}
        """
        if not processing_times_ms:
            return {}
        
        sorted_times = sorted(processing_times_ms)
        n = len(sorted_times)
        
        mean = statistics.mean(processing_times_ms)
        median = statistics.median(processing_times_ms)
        p95 = sorted_times[int(n * 0.95)] if n > 0 else 0
        p99 = sorted_times[int(n * 0.99)] if n > 0 else 0
        
        return {
            "mean": EvaluationResult(
                metric_name="latency_mean",
                value=mean,
                timestamp=datetime.now().isoformat()
            ),
            "median": EvaluationResult(
                metric_name="latency_median",
                value=median,
                timestamp=datetime.now().isoformat()
            ),
            "p95": EvaluationResult(
                metric_name="latency_p95",
                value=p95,
                timestamp=datetime.now().isoformat()
            ),
            "p99": EvaluationResult(
                metric_name="latency_p99",
                value=p99,
                timestamp=datetime.now().isoformat()
            ),
        }
    
    def evaluate_consistency(
        self,
        model_a_predictions: List[Dict],
        model_b_predictions: List[Dict]
    ) -> Dict[str, EvaluationResult]:
        """
        评估两个模型的一致性
        
        Args:
            model_a_predictions: 模型A的预测
            model_b_predictions: 模型B的预测
        
        Returns:
            {metric_name: result}
        """
        if len(model_a_predictions) != len(model_b_predictions):
            raise ValueError("两个模型的预测数量不匹配")
        
        # 极性一致性
        polarity_matches = sum(
            1 for a, b in zip(model_a_predictions, model_b_predictions)
            if a.get("polarity") == b.get("polarity")
        )
        polarity_consistency = polarity_matches / len(model_a_predictions)
        
        # 风险等级一致性
        risk_matches = sum(
            1 for a, b in zip(model_a_predictions, model_b_predictions)
            if a.get("risk_level") == b.get("risk_level")
        )
        risk_consistency = risk_matches / len(model_a_predictions)
        
        # 情绪分数相关性 (Spearman或Pearson)
        sentiment_scores_a = [a.get("sentiment_score", 0) for a in model_a_predictions]
        sentiment_scores_b = [b.get("sentiment_score", 0) for b in model_b_predictions]
        
        correlation = self._calculate_correlation(sentiment_scores_a, sentiment_scores_b)
        
        # 综合一致性
        overall_consistency = (
            polarity_consistency * 0.4 +
            risk_consistency * 0.3 +
            correlation * 0.3
        )
        
        return {
            "polarity": EvaluationResult(
                metric_name="consistency_polarity",
                value=polarity_consistency,
                timestamp=datetime.now().isoformat()
            ),
            "risk_level": EvaluationResult(
                metric_name="consistency_risk_level",
                value=risk_consistency,
                timestamp=datetime.now().isoformat()
            ),
            "sentiment_correlation": EvaluationResult(
                metric_name="consistency_sentiment_correlation",
                value=correlation,
                timestamp=datetime.now().isoformat()
            ),
            "overall": EvaluationResult(
                metric_name="consistency_overall",
                value=overall_consistency,
                timestamp=datetime.now().isoformat()
            ),
        }
    
    @staticmethod
    def _calculate_correlation(a: List[float], b: List[float]) -> float:
        """计算Pearson相关系数"""
        if len(a) < 2 or len(b) < 2:
            return 0.0
        
        mean_a = statistics.mean(a)
        mean_b = statistics.mean(b)
        
        numerator = sum((ai - mean_a) * (bi - mean_b) for ai, bi in zip(a, b))
        
        std_a = statistics.stdev(a) if len(set(a)) > 1 else 0
        std_b = statistics.stdev(b) if len(set(b)) > 1 else 0
        
        if std_a == 0 or std_b == 0:
            return 0.0
        
        correlation = numerator / (std_a * std_b * len(a))
        return max(-1, min(1, correlation))  # 限制在[-1, 1]
    
    def evaluate_language_coverage(
        self,
        predictions: List[Dict]  # {language: str, processed: bool, ...}
    ) -> Dict[str, EvaluationResult]:
        """
        评估对各语言的覆盖和处理能力
        
        Returns:
            {language: result}
        """
        language_groups = {}
        
        for pred in predictions:
            lang = pred.get("language", "unknown")
            if lang not in language_groups:
                language_groups[lang] = {"total": 0, "processed": 0}
            
            language_groups[lang]["total"] += 1
            if pred.get("processed", False):
                language_groups[lang]["processed"] += 1
        
        results = {}
        for lang, stats in language_groups.items():
            coverage = (
                stats["processed"] / stats["total"]
                if stats["total"] > 0 else 0
            )
            results[lang] = EvaluationResult(
                metric_name=f"coverage_{lang}",
                value=coverage,
                timestamp=datetime.now().isoformat()
            )
        
        return results
    
    def evaluate_confidence_calibration(
        self,
        predictions: List[Tuple[float, bool]]  # (confidence, is_correct)
    ) -> EvaluationResult:
        """
        评估置信度校准 (预测置信度与实际准确率的一致性)
        
        返回0表示完美校准，值越大表示校准越差
        """
        if not predictions:
            return EvaluationResult(metric_name="confidence_calibration", value=0)
        
        # 按置信度分组
        bins = {
            "0-25": {"confidence": [], "correct": []},
            "25-50": {"confidence": [], "correct": []},
            "50-75": {"confidence": [], "correct": []},
            "75-100": {"confidence": [], "correct": []},
        }
        
        for conf, is_correct in predictions:
            if conf < 0.25:
                bin_key = "0-25"
            elif conf < 0.5:
                bin_key = "25-50"
            elif conf < 0.75:
                bin_key = "50-75"
            else:
                bin_key = "75-100"
            
            bins[bin_key]["confidence"].append(conf)
            bins[bin_key]["correct"].append(1 if is_correct else 0)
        
        # 计算每个bin的校准误差
        calibration_errors = []
        for bin_key, data in bins.items():
            if data["confidence"]:
                avg_confidence = statistics.mean(data["confidence"])
                actual_accuracy = statistics.mean(data["correct"])
                error = abs(avg_confidence - actual_accuracy)
                calibration_errors.append(error)
        
        # 平均校准误差
        mean_calibration_error = (
            statistics.mean(calibration_errors)
            if calibration_errors else 0
        )
        
        return EvaluationResult(
            metric_name="confidence_calibration",
            value=mean_calibration_error,
            timestamp=datetime.now().isoformat()
        )
    
    def compare_with_baseline(
        self,
        model_id: str,
        current_metrics: Dict[str, float]
    ) -> Dict[str, EvaluationResult]:
        """
        与基线指标对比
        
        Returns:
            {metric_name: result_with_delta}
        """
        baseline = self.baseline_metrics.get(model_id, {})
        
        results = {}
        for metric_name, current_value in current_metrics.items():
            baseline_value = baseline.get(metric_name)
            
            result = EvaluationResult(
                metric_name=metric_name,
                value=current_value,
                baseline=baseline_value,
                timestamp=datetime.now().isoformat()
            )
            
            if baseline_value is not None:
                result.delta = current_value - baseline_value
                
                # 判断状态
                if result.delta > 0.05:  # 改进超过5%
                    result.status = "improved"
                elif result.delta < -0.05:  # 下降超过5%
                    result.status = "degraded"
                else:
                    result.status = "stable"
            
            results[metric_name] = result
        
        return results
    
    def generate_evaluation_report(
        self,
        model_id: str,
        evaluation_results: Dict[str, EvaluationResult],
        sample_count: int
    ) -> ModelEvaluation:
        """
        生成完整的评估报告
        
        Returns:
            模型评估对象
        """
        return ModelEvaluation(
            model_id=model_id,
            evaluation_date=datetime.now().isoformat(),
            total_samples=sample_count,
            results=evaluation_results,
            metadata={
                "baseline": self.baseline_metrics.get(model_id, {}),
            }
        )


# 便利函数
def quick_evaluate_sentiment(predictions: List[str], ground_truth: List[str]) -> float:
    """快速评估情感分类准确率"""
    engine = EvaluationEngine()
    result = engine.evaluate_sentiment_accuracy(predictions, ground_truth)
    return result.value


def quick_evaluate_latency(processing_times_ms: List[float]) -> Dict[str, float]:
    """快速评估延迟指标"""
    engine = EvaluationEngine()
    results = engine.evaluate_latency(processing_times_ms)
    return {k: v.value for k, v in results.items()}
