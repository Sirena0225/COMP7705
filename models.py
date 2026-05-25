"""
文本分析模块 - 数据模型定义
定义文本对象、情绪结果、风险警报的数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json


class SentimentPolarity(Enum):
    """情绪极性枚举"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "green"      # 🟢
    MEDIUM = "yellow"  # 🟡
    HIGH = "red"       # 🔴


class RiskCategory(Enum):
    """风险类别枚举"""
    REGULATORY_ANTITRUST = "regulatory_antitrust"
    REGULATORY_DATA = "regulatory_data_security"
    REGULATORY_LICENSE = "regulatory_license"
    FINANCIAL_DEFAULT = "financial_default"
    FINANCIAL_EARNINGS = "financial_earnings_miss"
    FINANCIAL_AUDIT = "financial_audit_issue"
    OPERATIONAL_EXECUTIVE = "operational_executive_departure"
    OPERATIONAL_PRODUCT = "operational_product_safety"
    OPERATIONAL_SUPPLY = "operational_supply_chain"
    ESG_ENVIRONMENTAL = "esg_environmental"
    ESG_SOCIAL = "esg_social"
    ESG_GOVERNANCE = "esg_governance"


@dataclass
class TextSource:
    """文本来源信息"""
    source_type: str  # "news", "announcement", "social_media", "research_report"
    source_name: str  # "财华社", "披露易", "雪球", etc.
    url: Optional[str] = None
    publish_time: Optional[datetime] = None
    fetch_time: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "url": self.url,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "fetch_time": self.fetch_time.isoformat()
        }


@dataclass
class RawText:
    """原始文本对象 - 输入"""
    text_id: str  # 唯一标识 UUID
    title: str
    content: str
    stock_codes: List[str]  # 关联的股票代码，如 ["00700.HK", "09988.HK"]
    stock_names: List[str]  # 对应的中文名，如 ["腾讯控股", "阿里巴巴-SW"]
    source: TextSource
    language: str = "zh"  # "zh", "en", "mixed"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_text(self) -> str:
        """合并标题和正文"""
        return f"{self.title}\n{self.content}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_id": self.text_id,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "stock_codes": self.stock_codes,
            "stock_names": self.stock_names,
            "source": self.source.to_dict(),
            "language": self.language,
            "metadata": self.metadata
        }


@dataclass
class ProcessedChunk:
    """预处理后的文本块"""
    chunk_id: str
    parent_text_id: str
    stock_code: str  # 每个块只关联一个主要股票，避免歧义
    content: str
    start_idx: int  # 在原文中的起始位置
    end_idx: int
    entities: List[Dict[str, Any]] = field(default_factory=list)  # 识别的实体
    keywords: List[str] = field(default_factory=list)
    is_relevant: bool = True  # 是否与股票真正相关（过滤噪音）


@dataclass
class SentimentResult:
    """情绪分析结果 - 核心输出"""
    result_id: str
    text_id: str
    stock_code: str
    
    # 情绪分数
    sentiment_score: float  # -1.0 (极度负面) 到 +1.0 (极度正面)
    confidence: float  # 0.0 到 1.0，模型置信度
    polarity: SentimentPolarity
    
    # 细分维度
    categories: Dict[str, float] = field(default_factory=dict)  # 各维度情绪
    # 如 {"earnings": 0.5, "regulatory": -0.8, "market": 0.2}
    
    # 可解释性
    key_phrases: List[str] = field(default_factory=list)  # 关键短语
    reasoning: str = ""  # 推理过程
    supporting_evidence: List[str] = field(default_factory=list)  # 支持证据原文片段
    
    # 元数据
    model_version: str = ""
    processing_time_ms: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "text_id": self.text_id,
            "stock_code": self.stock_code,
            "sentiment_score": round(self.sentiment_score, 4),
            "confidence": round(self.confidence, 4),
            "polarity": self.polarity.value,
            "categories": self.categories,
            "key_phrases": self.key_phrases,
            "reasoning": self.reasoning,
            "supporting_evidence": self.supporting_evidence,
            "model_version": self.model_version,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RiskAlert:
    """风险警报对象"""
    alert_id: str
    text_id: str
    stock_code: str
    
    risk_category: RiskCategory
    risk_level: RiskLevel
    risk_score: float  # 0.0 到 1.0
    
    # 风险详情
    risk_title: str  # 简短标题，如 "监管处罚风险"
    risk_description: str  # 详细描述
    affected_aspects: List[str] = field(default_factory=list)  # 影响方面
    
    # 溯源信息
    source_text_snippet: str = ""  # 原文片段
    source_text_location: int = 0  # 在原文中的位置
    
    # 时间信息
    detected_at: datetime = field(default_factory=datetime.now)
    valid_until: Optional[datetime] = None  # 风险有效期
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "text_id": self.text_id,
            "stock_code": self.stock_code,
            "risk_category": self.risk_category.value,
            "risk_level": self.risk_level.value,
            "risk_score": round(self.risk_score, 4),
            "risk_title": self.risk_title,
            "risk_description": self.risk_description,
            "affected_aspects": self.affected_aspects,
            "source_text_snippet": self.source_text_snippet,
            "detected_at": self.detected_at.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None
        }


@dataclass
class AnalysisOutput:
    """完整分析输出 - 聚合情绪结果和风险警报"""
    text_id: str
    stock_code: str
    
    sentiment: Optional[SentimentResult] = None
    risks: List[RiskAlert] = field(default_factory=list)
    chunks: List[ProcessedChunk] = field(default_factory=list)
    
    # 综合评分
    composite_score: float = 0.0  # 综合情绪-风险评分
    
    def calculate_composite(self) -> float:
        """计算综合评分：情绪分数 + 风险调整"""
        if not self.sentiment:
            return 0.0
        
        base = self.sentiment.sentiment_score * self.sentiment.confidence
        
        # 风险调整：高风险负面事件会放大负面分数
        risk_penalty = 0.0
        for risk in self.risks:
            if risk.risk_level == RiskLevel.HIGH:
                risk_penalty += 0.3 * risk.risk_score
            elif risk.risk_level == RiskLevel.MEDIUM:
                risk_penalty += 0.15 * risk.risk_score
        
        self.composite_score = base - risk_penalty
        return self.composite_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text_id": self.text_id,
            "stock_code": self.stock_code,
            "sentiment": self.sentiment.to_dict() if self.sentiment else None,
            "risks": [r.to_dict() for r in self.risks],
            "composite_score": round(self.composite_score, 4),
            "risk_count": len(self.risks),
            "high_risk_count": sum(1 for r in self.risks if r.risk_level == RiskLevel.HIGH)
        }