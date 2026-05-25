"""
指标追踪器 - 记录和分析模型性能指标
支持实时指标计算、时间序列管理和统计分析
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics
from pathlib import Path


class MetricType(Enum):
    """指标类型"""
    ACCURACY = "accuracy"              # 准确率
    LATENCY = "latency"                # 延迟 (ms)
    CONSISTENCY = "consistency"        # 一致性 (新旧模型对比)
    CONFIDENCE = "confidence"          # 置信度
    LANGUAGE_COVERAGE = "lang_coverage" # 语言覆盖率
    RISK_PRECISION = "risk_precision"  # 风险识别精确率
    SENTIMENT_F1 = "sentiment_f1"      # 情感分析F1分数


@dataclass
class MetricPoint:
    """单个指标数据点"""
    timestamp: str
    metric_type: str
    value: float
    model_id: str
    batch_id: str
    language: str
    stock_code: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class MetricSummary:
    """指标汇总统计"""
    metric_type: str
    model_id: str
    period: str  # "1h", "1d", "7d", "30d"
    count: int
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    p95: float
    p99: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MetricsTracker:
    """指标追踪器 - 管理所有性能指标"""
    
    def __init__(self, db_path: str = "/Users/mac/sandbox/HKU/COMP7705/metrics.db"):
        """
        初始化指标追踪器
        
        Args:
            db_path: SQLite数据库路径
        """
        self.db_path = db_path
        self.memory_buffer: List[MetricPoint] = []  # 内存缓冲区
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                model_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                language TEXT NOT NULL,
                stock_code TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引用于快速查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp_metric 
            ON metrics(timestamp, metric_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_metric 
            ON metrics(model_id, metric_type)
        """)
        
        conn.commit()
        conn.close()
    
    def record_metric(self, point: MetricPoint):
        """记录单个指标点"""
        self.memory_buffer.append(point)
        
        # 缓冲区满时批量写入
        if len(self.memory_buffer) >= 100:
            self._flush_buffer()
    
    def record_batch_metrics(self, metrics: List[MetricPoint]):
        """批量记录指标"""
        self.memory_buffer.extend(metrics)
        
        if len(self.memory_buffer) >= 100:
            self._flush_buffer()
    
    def _flush_buffer(self):
        """将缓冲区数据写入数据库"""
        if not self.memory_buffer:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for point in self.memory_buffer:
            cursor.execute("""
                INSERT INTO metrics 
                (timestamp, metric_type, value, model_id, batch_id, language, stock_code, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                point.timestamp,
                point.metric_type,
                point.value,
                point.model_id,
                point.batch_id,
                point.language,
                point.stock_code,
                json.dumps(point.metadata) if point.metadata else None
            ))
        
        conn.commit()
        conn.close()
        self.memory_buffer.clear()
    
    def get_metric_summary(
        self,
        metric_type: str,
        model_id: str,
        hours: int = 1
    ) -> Optional[MetricSummary]:
        """
        获取指定时间范围内的指标汇总
        
        Args:
            metric_type: 指标类型
            model_id: 模型ID
            hours: 时间范围（小时）
        
        Returns:
            指标汇总
        """
        # 确保缓冲区数据已写入
        self._flush_buffer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查询时间范围内的数据
        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT value FROM metrics
            WHERE metric_type = ? AND model_id = ? AND timestamp > ?
            ORDER BY value
        """, (metric_type, model_id, time_threshold))
        
        values = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not values:
            return None
        
        # 计算统计量
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        mean = statistics.mean(values)
        median = statistics.median(values)
        std_dev = statistics.stdev(values) if n > 1 else 0
        
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        summary = MetricSummary(
            metric_type=metric_type,
            model_id=model_id,
            period=f"{hours}h",
            count=n,
            mean=mean,
            median=median,
            std_dev=std_dev,
            min_value=min(values),
            max_value=max(values),
            p95=sorted_values[p95_idx] if p95_idx < n else sorted_values[-1],
            p99=sorted_values[p99_idx] if p99_idx < n else sorted_values[-1]
        )
        
        return summary
    
    def get_model_comparison(
        self,
        metric_type: str,
        model_ids: List[str],
        hours: int = 1
    ) -> Dict[str, MetricSummary]:
        """
        比较多个模型的指标
        
        Returns:
            {model_id: MetricSummary}
        """
        results = {}
        for model_id in model_ids:
            summary = self.get_metric_summary(metric_type, model_id, hours)
            if summary:
                results[model_id] = summary
        
        return results
    
    def get_language_metrics(
        self,
        model_id: str,
        hours: int = 1
    ) -> Dict[str, Dict[str, float]]:
        """
        获取按语言分组的指标
        
        Returns:
            {language: {metric_type: value}}
        """
        self._flush_buffer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT language, metric_type, AVG(value) as avg_value
            FROM metrics
            WHERE model_id = ? AND timestamp > ?
            GROUP BY language, metric_type
        """, (model_id, time_threshold))
        
        results = {}
        for language, metric_type, avg_value in cursor.fetchall():
            if language not in results:
                results[language] = {}
            results[language][metric_type] = avg_value
        
        conn.close()
        return results
    
    def get_time_series(
        self,
        metric_type: str,
        model_id: str,
        interval_minutes: int = 10,
        hours: int = 24
    ) -> List[Tuple[str, float]]:
        """
        获取时间序列数据
        
        Args:
            metric_type: 指标类型
            model_id: 模型ID
            interval_minutes: 采样间隔（分钟）
            hours: 时间范围（小时）
        
        Returns:
            [(timestamp, average_value), ...]
        """
        self._flush_buffer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        # 获取原始数据
        cursor.execute("""
            SELECT timestamp, value FROM metrics
            WHERE metric_type = ? AND model_id = ? AND timestamp > ?
            ORDER BY timestamp
        """, (metric_type, model_id, time_threshold))
        
        raw_data = cursor.fetchall()
        conn.close()
        
        if not raw_data:
            return []
        
        # 按时间间隔聚合
        time_buckets = {}
        for ts, value in raw_data:
            # 创建时间桶标签
            dt = datetime.fromisoformat(ts)
            bucket_key = (dt - timedelta(minutes=dt.minute % interval_minutes)).isoformat()
            
            if bucket_key not in time_buckets:
                time_buckets[bucket_key] = []
            time_buckets[bucket_key].append(value)
        
        # 计算每个桶的平均值
        time_series = [
            (ts, statistics.mean(values))
            for ts, values in sorted(time_buckets.items())
        ]
        
        return time_series
    
    def get_anomalies(
        self,
        metric_type: str,
        model_id: str,
        std_dev_threshold: float = 3.0,
        hours: int = 1
    ) -> List[MetricPoint]:
        """
        检测异常值（超过N倍标准差）
        
        Args:
            std_dev_threshold: 标准差倍数阈值
        
        Returns:
            异常的指标点列表
        """
        summary = self.get_metric_summary(metric_type, model_id, hours)
        if not summary or summary.std_dev == 0:
            return []
        
        # 计算异常范围
        lower_bound = summary.mean - (std_dev_threshold * summary.std_dev)
        upper_bound = summary.mean + (std_dev_threshold * summary.std_dev)
        
        # 从内存缓冲区中查找（最新数据可能还未写入数据库）
        anomalies = []
        for point in self.memory_buffer:
            if (point.metric_type == metric_type and 
                point.model_id == model_id and
                (point.value < lower_bound or point.value > upper_bound)):
                anomalies.append(point)
        
        return anomalies
    
    def export_metrics(
        self,
        output_file: str,
        model_id: str,
        hours: int = 24
    ):
        """
        导出指标为JSON
        
        Args:
            output_file: 输出文件路径
            model_id: 模型ID
            hours: 时间范围
        """
        self._flush_buffer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        time_threshold = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute("""
            SELECT timestamp, metric_type, value, batch_id, language, stock_code
            FROM metrics
            WHERE model_id = ? AND timestamp > ?
            ORDER BY timestamp
        """, (model_id, time_threshold))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为字典列表
        data = []
        for row in rows:
            data.append({
                "timestamp": row[0],
                "metric_type": row[1],
                "value": row[2],
                "batch_id": row[3],
                "language": row[4],
                "stock_code": row[5]
            })
        
        # 写入JSON
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def clear_old_data(self, days: int = 30):
        """
        清理超过指定天数的数据
        
        Args:
            days: 保留天数
        """
        self._flush_buffer()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            DELETE FROM metrics WHERE timestamp < ?
        """, (cutoff_time,))
        
        conn.commit()
        conn.close()


# 全局指标追踪器实例
_metrics_tracker: Optional[MetricsTracker] = None


def get_metrics_tracker() -> MetricsTracker:
    """获取全局指标追踪器"""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = MetricsTracker()
    return _metrics_tracker


def record_metric(
    metric_type: str,
    value: float,
    model_id: str,
    batch_id: str,
    language: str,
    stock_code: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """便利函数：记录单个指标"""
    point = MetricPoint(
        timestamp=datetime.now().isoformat(),
        metric_type=metric_type,
        value=value,
        model_id=model_id,
        batch_id=batch_id,
        language=language,
        stock_code=stock_code,
        metadata=metadata or {}
    )
    get_metrics_tracker().record_metric(point)
