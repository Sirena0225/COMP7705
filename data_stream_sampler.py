"""
数据流采样器 - 从实时数据流中按比例采样
支持按来源、语言、股票等维度的采样策略
"""

import random
import queue
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict


class SamplingStrategy(Enum):
    """采样策略"""
    UNIFORM = "uniform"                    # 均匀采样 (固定比例)
    STRATIFIED = "stratified"              # 分层采样 (按维度均衡)
    ADAPTIVE = "adaptive"                  # 自适应采样 (根据置信度调整)
    RISK_AWARE = "risk_aware"              # 风险感知采样 (高风险样本优先)


@dataclass
class DataStreamSample:
    """数据流样本"""
    sample_id: str
    raw_text_id: str
    text: str
    language: str
    stock_code: str
    source: str  # "news", "social_media", "research_report" 等
    source_name: str
    timestamp: str
    sampled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.0  # 模型预测的置信度（用于自适应采样）
    priority: int = 0  # 采样优先级（用于风险感知采样）


@dataclass
class SamplingConfig:
    """采样配置"""
    overall_rate: float = 0.1                    # 整体采样率 10%
    min_samples_per_batch: int = 50              # 每批最少样本数
    max_samples_per_batch: int = 500             # 每批最多样本数
    language_weights: Dict[str, float] = field(  # 各语言采样权重
        default_factory=lambda: {"zh": 0.5, "en": 0.3, "mixed": 0.2}
    )
    source_weights: Dict[str, float] = field(    # 各来源采样权重
        default_factory=lambda: {
            "news": 0.4,
            "social_media": 0.3,
            "research_report": 0.2,
            "announcement": 0.1
        }
    )
    high_risk_rate: float = 1.0                  # 高风险样本采样率 (100%)
    low_confidence_rate: float = 0.5             # 低置信度样本采样率


class DataStreamSampler:
    """数据流采样器"""
    
    def __init__(
        self,
        strategy: SamplingStrategy = SamplingStrategy.STRATIFIED,
        config: Optional[SamplingConfig] = None
    ):
        """
        初始化采样器
        
        Args:
            strategy: 采样策略
            config: 采样配置
        """
        self.strategy = strategy
        self.config = config or SamplingConfig()
        
        # 内部队列
        self.input_queue: queue.Queue = queue.Queue(maxsize=10000)
        self.output_queue: queue.Queue = queue.Queue(maxsize=1000)
        
        # 统计信息
        self.stats = {
            "total_received": 0,
            "total_sampled": 0,
            "samples_by_language": defaultdict(int),
            "samples_by_source": defaultdict(int),
            "high_risk_samples": 0,
            "low_confidence_samples": 0,
        }
        
        self._lock = threading.Lock()
        self._running = False
    
    def push_sample(self, sample: DataStreamSample):
        """
        推送样本到输入队列
        
        Args:
            sample: 样本数据
        """
        try:
            self.input_queue.put(sample, timeout=1)
            with self._lock:
                self.stats["total_received"] += 1
        except queue.Full:
            print("⚠️  输入队列已满，样本被丢弃")
    
    def should_sample(
        self,
        sample: DataStreamSample,
        context: Optional[Dict] = None
    ) -> bool:
        """
        判断是否应该采样此样本
        
        Args:
            sample: 样本
            context: 额外上下文信息
        
        Returns:
            是否采样
        """
        if self.strategy == SamplingStrategy.UNIFORM:
            return self._uniform_sample(sample)
        elif self.strategy == SamplingStrategy.STRATIFIED:
            return self._stratified_sample(sample)
        elif self.strategy == SamplingStrategy.ADAPTIVE:
            return self._adaptive_sample(sample)
        elif self.strategy == SamplingStrategy.RISK_AWARE:
            return self._risk_aware_sample(sample)
        
        return False
    
    def _uniform_sample(self, sample: DataStreamSample) -> bool:
        """均匀采样 - 固定概率"""
        return random.random() < self.config.overall_rate
    
    def _stratified_sample(self, sample: DataStreamSample) -> bool:
        """
        分层采样 - 按语言和来源均衡采样
        确保各语言、各来源都有足够的代表性样本
        """
        # 获取该语言和来源的采样率
        lang_weight = self.config.language_weights.get(sample.language, 0.2)
        source_weight = self.config.source_weights.get(sample.source, 0.1)
        
        # 综合采样概率
        combined_rate = min(1.0, lang_weight * source_weight * 10)  # 缩放因子
        
        return random.random() < combined_rate
    
    def _adaptive_sample(self, sample: DataStreamSample) -> bool:
        """
        自适应采样 - 根据置信度调整采样率
        高置信度样本采样率低（模型确定），低置信度样本采样率高（需要验证）
        """
        base_rate = self.config.overall_rate
        
        # 根据置信度调整
        if sample.confidence < 0.5:
            # 低置信度：更高采样率
            adjusted_rate = min(1.0, base_rate * 3)
        elif sample.confidence > 0.9:
            # 高置信度：更低采样率
            adjusted_rate = base_rate * 0.5
        else:
            # 中等置信度：保持基础采样率
            adjusted_rate = base_rate
        
        return random.random() < adjusted_rate
    
    def _risk_aware_sample(self, sample: DataStreamSample) -> bool:
        """
        风险感知采样 - 优先采样高风险样本
        """
        if sample.priority >= 2:  # 高风险 (priority >= 2)
            return random.random() < self.config.high_risk_rate
        elif sample.confidence < 0.5:  # 低置信度
            return random.random() < self.config.low_confidence_rate
        else:
            return random.random() < self.config.overall_rate
    
    def get_next_batch(
        self,
        batch_size: Optional[int] = None
    ) -> List[DataStreamSample]:
        """
        获取下一批样本
        
        Args:
            batch_size: 批大小（使用配置中的默认值）
        
        Returns:
            样本列表
        """
        if batch_size is None:
            batch_size = self.config.max_samples_per_batch
        
        batch = []
        deadline = datetime.now() + timedelta(seconds=5)
        
        while len(batch) < batch_size and datetime.now() < deadline:
            try:
                sample = self.output_queue.get(timeout=0.5)
                batch.append(sample)
            except queue.Empty:
                continue
        
        return batch if len(batch) >= self.config.min_samples_per_batch else []
    
    def process_stream(self, max_batches: Optional[int] = None):
        """
        处理数据流（后台线程）
        
        Args:
            max_batches: 处理最大批数（None表示无限制）
        """
        self._running = True
        batch_count = 0
        
        while self._running:
            try:
                # 从输入队列获取样本
                sample = self.input_queue.get(timeout=1)
                
                # 决定是否采样
                if self.should_sample(sample):
                    self.output_queue.put(sample)
                    
                    with self._lock:
                        self.stats["total_sampled"] += 1
                        self.stats["samples_by_language"][sample.language] += 1
                        self.stats["samples_by_source"][sample.source] += 1
                        
                        if sample.priority >= 2:
                            self.stats["high_risk_samples"] += 1
                        if sample.confidence < 0.5:
                            self.stats["low_confidence_samples"] += 1
                
                # 检查是否达到批数限制
                if max_batches and batch_count >= max_batches:
                    break
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ 处理流时出错: {e}")
    
    def start(self):
        """启动采样处理（后台线程）"""
        thread = threading.Thread(target=self.process_stream, daemon=True)
        thread.start()
    
    def stop(self):
        """停止采样处理"""
        self._running = False
    
    def get_stats(self) -> Dict:
        """获取采样统计"""
        with self._lock:
            return {
                **self.stats,
                "total_received": self.stats["total_received"],
                "total_sampled": self.stats["total_sampled"],
                "sampling_rate": (
                    self.stats["total_sampled"] / self.stats["total_received"]
                    if self.stats["total_received"] > 0 else 0
                ),
                "samples_by_language": dict(self.stats["samples_by_language"]),
                "samples_by_source": dict(self.stats["samples_by_source"]),
            }
    
    def print_stats(self):
        """打印采样统计"""
        stats = self.get_stats()
        
        print("\n" + "="*60)
        print("📊 数据流采样统计")
        print("="*60)
        print(f"总收到样本: {stats['total_received']}")
        print(f"采样样本数: {stats['total_sampled']}")
        print(f"采样率: {stats['sampling_rate']:.1%}")
        print(f"\n按语言分布:")
        for lang, count in stats['samples_by_language'].items():
            print(f"  {lang}: {count}")
        print(f"\n按来源分布:")
        for source, count in stats['samples_by_source'].items():
            print(f"  {source}: {count}")
        print(f"\n特殊样本:")
        print(f"  高风险样本: {stats['high_risk_samples']}")
        print(f"  低置信度样本: {stats['low_confidence_samples']}")


class RealTimeDataStream:
    """实时数据流模拟器 - 用于测试"""
    
    def __init__(
        self,
        sampler: DataStreamSampler,
        rate: int = 10
    ):
        """
        初始化实时数据流
        
        Args:
            sampler: 采样器
            rate: 每秒推送样本数
        """
        self.sampler = sampler
        self.rate = rate
        self._running = False
    
    @staticmethod
    def generate_test_sample(index: int) -> DataStreamSample:
        """生成测试样本"""
        languages = ["zh", "en", "mixed"]
        sources = ["news", "social_media", "research_report", "announcement"]
        stock_codes = ["00700.HK", "09988.HK", "03690.HK", "01810.HK"]
        source_names = ["新浪财经", "Bloomberg", "UBS", "披露易"]
        
        sample = DataStreamSample(
            sample_id=f"sample-{index}",
            raw_text_id=f"text-{index}",
            text=f"Sample text {index}...",
            language=random.choice(languages),
            stock_code=random.choice(stock_codes),
            source=random.choice(sources),
            source_name=random.choice(source_names),
            timestamp=datetime.now().isoformat(),
            confidence=random.random(),
            priority=random.randint(0, 2)
        )
        
        return sample
    
    def start_streaming(self, duration_seconds: int = 60):
        """
        启动数据流（模拟实时输入）
        
        Args:
            duration_seconds: 流持续时间
        """
        import time
        
        start_time = datetime.now()
        sample_index = 0
        
        print(f"🚀 开始模拟实时数据流 ({duration_seconds}秒)")
        
        while (datetime.now() - start_time).total_seconds() < duration_seconds:
            for _ in range(self.rate):
                sample = self.generate_test_sample(sample_index)
                self.sampler.push_sample(sample)
                sample_index += 1
            
            time.sleep(1)
        
        print(f"✅ 数据流模拟完成")


class JSONDataStream:
    """从 JSON 文件加载数据的数据流"""
    
    def __init__(
        self,
        sampler: DataStreamSampler,
        json_file_path: str = "/Users/mac/sandbox/HKU/COMP7705/data/sentiment_input_batch.json",
        rate: float = 50  # 每秒推送样本数
    ):
        """
        初始化 JSON 数据流
        
        Args:
            sampler: 采样器
            json_file_path: JSON 文件路径
            rate: 每秒推送样本数
        """
        self.sampler = sampler
        self.json_file_path = json_file_path
        self.rate = rate
        self._running = False
    
    @staticmethod
    def load_json_samples(json_file_path: str) -> List[Dict]:
        """加载 JSON 文件"""
        import json
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print(f"⚠️  JSON 应该是数组，但是 {type(data)}")
                return []
            
            print(f"✅ 加载 {len(data)} 个 JSON 对象")
            return data
        except Exception as e:
            print(f"❌ JSON 加载失败: {e}")
            return []
    
    @staticmethod
    def convert_json_to_sample(raw_data: dict, index: int = 0) -> DataStreamSample:
        """
        将 JSON 数据转换为 DataStreamSample
        
        Args:
            raw_data: 原始 JSON 对象
            index: 样本索引
        
        Returns:
            DataStreamSample 对象
        """
        text_id = raw_data.get("text_id", f"doc-{index}")
        language = raw_data.get("language", "en")
        
        # 合并 title 和 content
        title = raw_data.get("title", "")
        content = raw_data.get("content", "")
        text = f"{title}\n{content}".strip() if title else content
        
        # 股票代码
        stock_codes = raw_data.get("stock_codes", [])
        stock_code = stock_codes[0] if isinstance(stock_codes, list) and stock_codes else ""
        
        # 来源信息
        source_type = raw_data.get("source_type", "announcement")
        source_name = raw_data.get("source_name", "unknown")
        published_at = raw_data.get("published_at", datetime.now().isoformat())
        
        sample = DataStreamSample(
            sample_id=f"{text_id}-{index}",
            raw_text_id=text_id,
            text=text,
            language=language,
            stock_code=stock_code,
            source=source_type,
            source_name=source_name,
            timestamp=published_at,
            confidence=0.0,
            priority=0
        )
        
        return sample
    
    def stream_from_json(self, samples_per_second: Optional[float] = None):
        """
        从 JSON 文件流式推送数据
        
        Args:
            samples_per_second: 每秒推送样本数（为 None 时表示尽快推送）
        """
        import json
        import time
        
        rate = samples_per_second if samples_per_second is not None else self.rate
        
        # 加载 JSON 数据
        raw_data = self.load_json_samples(self.json_file_path)
        
        if not raw_data:
            print("❌ 无法加载 JSON 数据")
            return
        
        print(f"🚀 开始流式推送 JSON 数据 ({len(raw_data)} 个样本, 速率: {rate}/秒)")
        
        self._running = True
        sample_index = 0
        
        for json_obj in raw_data:
            if not self._running:
                break
            
            # 转换为 DataStreamSample
            sample = self.convert_json_to_sample(json_obj, sample_index)
            
            # 推送到采样器
            self.sampler.push_sample(sample)
            
            sample_index += 1
            
            # 控制推送速率
            if rate > 0:
                time.sleep(1.0 / rate)
        
        print(f"✅ JSON 数据流推送完成")
    
    def stop(self):
        """停止数据流"""
        self._running = False
