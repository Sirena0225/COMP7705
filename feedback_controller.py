"""
反馈控制器 - 根据评估结果自动调整模型参数
支持提示词优化、阈值调整和自动补救
"""

from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class AdjustmentType(Enum):
    """调整类型"""
    PROMPT_ENGINEERING = "prompt_engineering"    # 提示词优化
    THRESHOLD_ADJUSTMENT = "threshold_adjustment" # 阈值调整
    SAMPLING_STRATEGY = "sampling_strategy"       # 采样策略调整
    FEATURE_ENGINEERING = "feature_engineering"   # 特征工程调整


@dataclass
class PerformanceThreshold:
    """性能阈值"""
    accuracy_min: float = 0.85            # 准确率最低值
    latency_max_ms: float = 1000          # 最大延迟 (毫秒)
    consistency_min: float = 0.80         # 最小一致性
    confidence_min: float = 0.70          # 最小置信度


@dataclass
class AdjustmentAction:
    """调整操作"""
    adjustment_type: AdjustmentType
    target: str                           # 调整目标 (metric_name, prompt_id等)
    action: str                           # 具体操作描述
    parameters: Dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"               # pending/applied/rolled_back


class PromptOptimizer:
    """提示词优化器"""
    
    def __init__(self):
        """初始化优化器"""
        self.prompt_history: List[Dict] = []
    
    def analyze_sentiment_errors(
        self,
        error_samples: List[Dict]
    ) -> List[str]:
        """
        分析情感分析错误样本，提出改进建议
        
        Args:
            error_samples: [{text, prediction, ground_truth, confidence}, ...]
        
        Returns:
            改进建议列表
        """
        suggestions = []
        
        # 分析错误模式
        false_positives = [s for s in error_samples if s.get("prediction") == "positive" and s.get("ground_truth") != "positive"]
        false_negatives = [s for s in error_samples if s.get("prediction") != "positive" and s.get("ground_truth") == "positive"]
        
        if len(false_positives) > len(error_samples) * 0.5:
            suggestions.append("❌ 正面倾向过强：增加负面信号的权重")
        
        if len(false_negatives) > len(error_samples) * 0.5:
            suggestions.append("❌ 正面倾向不足：增加正面信号的权重")
        
        # 检查高置信度但错误的样本
        high_conf_errors = [
            s for s in error_samples
            if s.get("confidence", 0) > 0.8
        ]
        
        if high_conf_errors:
            suggestions.append(f"⚠️  {len(high_conf_errors)}个高置信度错误：审查提示词的表述")
        
        return suggestions
    
    def generate_improved_prompt(
        self,
        original_prompt: str,
        suggestions: List[str],
        language: str = "zh"
    ) -> str:
        """
        基于建议生成改进的提示词
        
        Args:
            original_prompt: 原始提示词
            suggestions: 改进建议列表
            language: 语言
        
        Returns:
            改进后的提示词
        """
        # 这里是简化的实现，实际生产环境需要更复杂的逻辑
        improved = original_prompt
        
        for suggestion in suggestions:
            if "增加负面信号的权重" in suggestion:
                if language == "zh":
                    improved += "\n\n[注意] 加强对负面信号的识别：市场风险、监管挑战、业绩下滑等"
                else:
                    improved += "\n\n[NOTE] Enhance detection of negative signals: market risks, regulatory challenges, performance decline"
            
            elif "增加正面信号的权重" in suggestion:
                if language == "zh":
                    improved += "\n\n[注意] 加强对正面信号的识别：增长机会、战略优化、技术创新等"
                else:
                    improved += "\n\n[NOTE] Enhance detection of positive signals: growth opportunities, strategic optimization, technology innovation"
        
        return improved
    
    def record_prompt_change(
        self,
        from_prompt: str,
        to_prompt: str,
        reason: str
    ):
        """记录提示词变化"""
        self.prompt_history.append({
            "timestamp": datetime.now().isoformat(),
            "from_hash": hash(from_prompt),
            "to_hash": hash(to_prompt),
            "reason": reason,
            "changes_count": sum(
                1 for a, b in zip(from_prompt, to_prompt) if a != b
            )
        })


class ThresholdAdjuster:
    """阈值调整器"""
    
    def __init__(self, initial_thresholds: Optional[PerformanceThreshold] = None):
        """初始化"""
        self.current_thresholds = initial_thresholds or PerformanceThreshold()
        self.adjustment_history: List[Dict] = []
    
    def adjust_confidence_threshold(
        self,
        low_confidence_errors: List[Dict],
        high_confidence_errors: List[Dict]
    ) -> float:
        """
        根据错误样本动态调整置信度阈值
        
        Args:
            low_confidence_errors: 低置信度但正确的样本
            high_confidence_errors: 高置信度但错误的样本
        
        Returns:
            调整后的阈值
        """
        # 计算置信度阈值
        # 目标：最大化准确率，同时保持足够的覆盖率
        
        current = self.current_thresholds.confidence_min
        
        # 如果高置信度错误率高，降低阈值
        if high_confidence_errors and len(high_confidence_errors) > 10:
            adjustment = -0.05
        # 如果低置信度但正确的样本多，提高阈值
        elif low_confidence_errors and len(low_confidence_errors) > 20:
            adjustment = 0.03
        else:
            adjustment = 0
        
        new_threshold = max(0.5, min(1.0, current + adjustment))
        
        self.adjustment_history.append({
            "metric": "confidence_threshold",
            "old_value": current,
            "new_value": new_threshold,
            "reason": "Based on error analysis",
            "timestamp": datetime.now().isoformat()
        })
        
        self.current_thresholds.confidence_min = new_threshold
        return new_threshold
    
    def adjust_latency_target(
        self,
        current_p95_latency: float,
        target_latency: float = 1000
    ) -> float:
        """
        根据实时延迟调整目标
        
        Args:
            current_p95_latency: 当前P95延迟
            target_latency: 目标延迟
        
        Returns:
            调整后的目标
        """
        current = self.current_thresholds.latency_max_ms
        
        # 如果当前延迟远超目标，逐步提高标准
        if current_p95_latency > target_latency * 1.5:
            new_target = current * 1.1  # 放宽10%
        elif current_p95_latency < target_latency * 0.8:
            new_target = current * 0.95  # 收紧5%
        else:
            new_target = current
        
        self.adjustment_history.append({
            "metric": "latency_target",
            "old_value": current,
            "new_value": new_target,
            "current_p95": current_p95_latency,
            "timestamp": datetime.now().isoformat()
        })
        
        self.current_thresholds.latency_max_ms = new_target
        return new_target


class FeedbackController:
    """反馈控制器 - 协调各种调整操作"""
    
    def __init__(self):
        """初始化"""
        self.prompt_optimizer = PromptOptimizer()
        self.threshold_adjuster = ThresholdAdjuster()
        self.pending_actions: List[AdjustmentAction] = []
        self.applied_actions: List[AdjustmentAction] = []
        self.callbacks: Dict[AdjustmentType, Callable] = {}
    
    def register_callback(
        self,
        adjustment_type: AdjustmentType,
        callback: Callable[[AdjustmentAction], bool]
    ):
        """
        注册调整回调函数
        
        Args:
            adjustment_type: 调整类型
            callback: 回调函数 (接收AdjustmentAction，返回成功状态)
        """
        self.callbacks[adjustment_type] = callback
    
    def analyze_and_generate_actions(
        self,
        evaluation_results: Dict[str, float],
        error_samples: List[Dict],
        thresholds: PerformanceThreshold
    ) -> List[AdjustmentAction]:
        """
        分析评估结果并生成调整操作
        
        Args:
            evaluation_results: {metric_name: value}
            error_samples: 错误样本列表
            thresholds: 性能阈值
        
        Returns:
            需要执行的调整操作列表
        """
        actions = []
        
        # 分析准确率
        accuracy = evaluation_results.get("accuracy", 0)
        if accuracy < thresholds.accuracy_min:
            # 生成提示词优化建议
            suggestions = self.prompt_optimizer.analyze_sentiment_errors(error_samples)
            
            if suggestions:
                actions.append(AdjustmentAction(
                    adjustment_type=AdjustmentType.PROMPT_ENGINEERING,
                    target="sentiment_prompt",
                    action="optimize_based_on_errors",
                    parameters={
                        "current_accuracy": accuracy,
                        "target_accuracy": thresholds.accuracy_min,
                        "suggestions": suggestions,
                        "error_count": len(error_samples)
                    }
                ))
        
        # 分析置信度
        confidence = evaluation_results.get("avg_confidence", 0)
        if confidence < thresholds.confidence_min:
            actions.append(AdjustmentAction(
                adjustment_type=AdjustmentType.THRESHOLD_ADJUSTMENT,
                target="confidence_threshold",
                action="adjust_based_on_low_confidence",
                parameters={
                    "current_confidence": confidence,
                    "target_confidence": thresholds.confidence_min
                }
            ))
        
        # 分析延迟
        latency_p95 = evaluation_results.get("latency_p95", 0)
        if latency_p95 > thresholds.latency_max_ms:
            actions.append(AdjustmentAction(
                adjustment_type=AdjustmentType.SAMPLING_STRATEGY,
                target="sampling_rate",
                action="reduce_sampling_for_speed",
                parameters={
                    "current_latency_p95": latency_p95,
                    "target_latency": thresholds.latency_max_ms
                }
            ))
        
        return actions
    
    def apply_actions(self, actions: List[AdjustmentAction]) -> Dict[str, bool]:
        """
        执行调整操作
        
        Args:
            actions: 调整操作列表
        
        Returns:
            {action_id: success_status}
        """
        results = {}
        
        for action in actions:
            # 查找对应的回调
            callback = self.callbacks.get(action.adjustment_type)
            
            if callback:
                try:
                    success = callback(action)
                    action.status = "applied" if success else "failed"
                    
                    if success:
                        self.applied_actions.append(action)
                    
                    results[id(action)] = success
                except Exception as e:
                    print(f"❌ 执行调整操作失败: {e}")
                    results[id(action)] = False
            else:
                print(f"⚠️  未找到调整类型 {action.adjustment_type} 的回调")
                results[id(action)] = False
        
        return results
    
    def rollback_actions(self, actions: List[AdjustmentAction]):
        """
        回滚调整操作
        
        Args:
            actions: 要回滚的操作列表
        """
        for action in actions:
            action.status = "rolled_back"
            print(f"⚙️  回滚操作: {action.adjustment_type.value} - {action.action}")
    
    def get_adjustment_summary(self) -> Dict:
        """获取调整总结"""
        return {
            "total_actions": len(self.applied_actions),
            "prompt_optimizations": sum(
                1 for a in self.applied_actions
                if a.adjustment_type == AdjustmentType.PROMPT_ENGINEERING
            ),
            "threshold_adjustments": sum(
                1 for a in self.applied_actions
                if a.adjustment_type == AdjustmentType.THRESHOLD_ADJUSTMENT
            ),
            "sampling_strategy_changes": sum(
                1 for a in self.applied_actions
                if a.adjustment_type == AdjustmentType.SAMPLING_STRATEGY
            ),
            "latest_adjustments": [
                {
                    "type": a.adjustment_type.value,
                    "target": a.target,
                    "timestamp": a.timestamp
                }
                for a in self.applied_actions[-5:]
            ]
        }
    
    def export_action_log(self, output_file: str):
        """导出调整日志"""
        log = {
            "timestamp": datetime.now().isoformat(),
            "applied_actions": [
                {
                    "type": a.adjustment_type.value,
                    "target": a.target,
                    "action": a.action,
                    "parameters": a.parameters,
                    "timestamp": a.timestamp
                }
                for a in self.applied_actions
            ],
            "pending_actions": [
                {
                    "type": a.adjustment_type.value,
                    "target": a.target,
                    "action": a.action,
                    "parameters": a.parameters
                }
                for a in self.pending_actions
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
