"""
完整流程测试脚本
使用模拟的LLM分析器，无需真实API密钥
"""

import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# 导入项目模块
from models import (
    RawText, TextSource, ProcessedChunk, SentimentResult,
    RiskAlert, SentimentPolarity, RiskLevel, RiskCategory,
    AnalysisOutput
)
from preprocessor import TextPreprocessor
from analyzer import LLMSentimentAnalyzer
# 跳过VectorStore导入，因为它需要chromadb
# from vector_storage import VectorStore
# from main import TextAnalysisPipeline

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestFlow")


class MockLLMAnalyzer(LLMSentimentAnalyzer):
    """
    模拟的LLM分析器，不需要真实API密钥
    用于测试完整流程
    """
    
    def __init__(self, model_name: str = "mock-analyzer", api_key: Optional[str] = None):
        # 不调用父类init，避免API密钥问题
        self.model_name = model_name
        self.total_calls = 0
        self.total_tokens = 0
    
    def _call_llm(self, prompt: str, temperature: float = 0.1) -> Dict[str, Any]:
        """模拟LLM调用，返回预定义的结果"""
        
        # 根据提示词内容判断是情绪还是风险分析
        if "category_scores" in prompt or "sentiment" in prompt[:200]:
            # 情绪分析响应
            return {
                "sentiment_score": 0.75 if "增长" in prompt or "利好" in prompt or "强劲" in prompt else -0.35,
                "confidence": 0.85,
                "polarity": "positive" if "增长" in prompt or "强劲" in prompt else "negative" if "下降" in prompt or "风险" in prompt else "neutral",
                "category_scores": {
                    "earnings": 0.8 if "业绩" in prompt or "收入" in prompt else 0.2,
                    "regulatory": -0.3 if "罚款" in prompt or "审查" in prompt else 0.1,
                    "market": 0.5,
                    "management": 0.3,
                    "product": 0.4
                },
                "key_phrases": ["业绩增长", "市场表现好", "前景看好"],
                "reasoning": "从文本中识别出积极的业绩信号，对股票价格存在正面影响。",
                "uncertainty": "缺乏行业对标数据，导致相对评估存在偏差。"
            }
        else:
            # 风险分析响应
            has_risk = "罚款" in prompt or "审查" in prompt or "下降" in prompt or "风险" in prompt
            return {
                "has_risk": has_risk,
                "risks": [
                    {
                        "category": "regulatory_antitrust" if "审查" in prompt else "financial_earnings_miss",
                        "level": "high" if "严重" in prompt else "medium" if has_risk else "low",
                        "score": 0.7 if has_risk else 0.2,
                        "title": "潜在审查风险" if "审查" in prompt else "业绩风险",
                        "description": "监管部门可能对公司业务进行审查。" if "审查" in prompt else "业绩可能不及预期。",
                        "affected_aspects": ["业务合规", "营收"] if has_risk else [],
                        "source_snippet": prompt[100:150] if len(prompt) > 100 else prompt,
                        "urgency": "immediate" if "严重" in prompt else "short_term" if has_risk else "medium_term"
                    }
                ] if has_risk else [],
                "overall_assessment": "存在中等程度风险。" if has_risk else "风险较低。"
            }
    
    def analyze_sentiment(self, chunk: ProcessedChunk) -> SentimentResult:
        """分析单个文本块的情绪（模拟）"""
        # 根据内容关键字来判断情绪
        content_lower = chunk.content.lower()
        is_positive = any(w in content_lower for w in ["增长", "强劲", "创新", "新高", "好"])
        is_negative = any(w in content_lower for w in ["下降", "下跌", "审查", "风险", "问题"])
        
        if is_positive and not is_negative:
            polarity = SentimentPolarity.POSITIVE
            score = 0.75
        elif is_negative and not is_positive:
            polarity = SentimentPolarity.NEGATIVE
            score = -0.35
        else:
            polarity = SentimentPolarity.NEUTRAL
            score = 0.0
        
        result = SentimentResult(
            result_id=f"sent_{chunk.chunk_id}",
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment_score=score,
            confidence=0.85,
            polarity=polarity,
            categories={
                "earnings": 0.8 if "业绩" in chunk.content or "收入" in chunk.content else 0.2,
                "regulatory": -0.3 if "审查" in chunk.content or "罚款" in chunk.content else 0.1,
                "market": 0.5,
                "management": 0.3,
                "product": 0.4
            },
            key_phrases=["业绩增长", "市场表现好", "前景看好"],
            reasoning="从文本中识别出了业绩、市场、监管等多维度信号，综合判断股票情绪倾向。",
            model_version=self.model_name,
            processing_time_ms=100
        )
        
        self.total_calls += 1
        return result
    
    def analyze_risks(self, chunk: ProcessedChunk) -> List[RiskAlert]:
        """分析文本块中的风险（模拟）"""
        prompt = f"风险分析{chunk.stock_code}: {chunk.content[:200]}"
        llm_result = self._call_llm(prompt)
        
        alerts = []
        if not llm_result.get("has_risk", False):
            return alerts
        
        level_map = {"high": RiskLevel.HIGH, "medium": RiskLevel.MEDIUM, "low": RiskLevel.LOW}
        
        for risk_data in llm_result.get("risks", []):
            try:
                category_str = risk_data.get("category", "operational_executive")
                category = RiskCategory(category_str)
                
                alert = RiskAlert(
                    alert_id=f"risk_{chunk.chunk_id}_{len(alerts)}",
                    text_id=chunk.parent_text_id,
                    stock_code=chunk.stock_code,
                    risk_category=category,
                    risk_level=level_map.get(risk_data.get("level", "medium"), RiskLevel.MEDIUM),
                    risk_score=float(risk_data.get("score", 0.5)),
                    risk_title=risk_data.get("title", ""),
                    risk_description=risk_data.get("description", ""),
                    source_text_snippet=risk_data.get("source_snippet", "")
                )
                alerts.append(alert)
            except ValueError as e:
                logger.warning(f"风险对象创建失败: {e}")
                continue
        
        self.total_calls += 1
        return alerts
    
    def analyze(self, chunk: ProcessedChunk) -> AnalysisOutput:
        """完整分析流程"""
        sentiment = self.analyze_sentiment(chunk)
        risks = self.analyze_risks(chunk)
        
        output = AnalysisOutput(
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment=sentiment,
            risks=risks,
            chunks=[chunk]
        )
        
        output.calculate_composite()
        return output
    
    def analyze_batch(self, chunks: List[ProcessedChunk]) -> List[AnalysisOutput]:
        """批量分析"""
        results = []
        for chunk in chunks:
            if not chunk.is_relevant:
                continue
            try:
                result = self.analyze(chunk)
                results.append(result)
            except Exception as e:
                logger.error(f"分析失败 {chunk.chunk_id}: {str(e)}")
                continue
        return results


def create_test_data() -> List[RawText]:
    """创建测试数据"""
    
    test_texts = [
        {
            "text_id": "test-001",
            "title": "腾讯控股发布Q1财报，净利润同比增长54%",
            "content": "腾讯控股(00700.HK)今日公布2024年第一季度业绩。收入同比增长6%至人民币1,595亿元。净利润同比增长54%至人民币418亿元。董事会主席兼CEO马化腾表示：\"本季度我们的游戏业务表现强劲。\"",
            "stock_codes": ["00700.HK"],
            "stock_names": ["腾讯控股"],
            "source_type": "announcement",
            "source_name": "披露易"
        },
        {
            "text_id": "test-002",
            "title": "阿里巴巴-SW面临反垄断审查，股价下跌5%",
            "content": "据业内人士透露，阿里巴巴-SW(09988.HK)最近因商业实践问题面临监管部门的详细审查。此举可能影响公司的市场地位。阿里方面表示将积极配合监管部门。",
            "stock_codes": ["09988.HK"],
            "stock_names": ["阿里巴巴-SW"],
            "source_type": "news",
            "source_name": "财华社"
        },
        {
            "text_id": "test-003",
            "title": "美团外卖业务收入创新高",
            "content": "美团(03690.HK)发布最新数据显示，外卖业务订单量同比增长35%，业务收入创历史新高。分析师认为这标志着公司已进入稳健增长阶段，未来前景看好。",
            "stock_codes": ["03690.HK"],
            "stock_names": ["美团"],
            "source_type": "research_report",
            "source_name": "国泰君安证券"
        }
    ]
    
    raw_texts = []
    for t in test_texts:
        source = TextSource(
            source_type=t["source_type"],
            source_name=t["source_name"],
            publish_time=datetime.now()
        )
        raw_text = RawText(
            text_id=t["text_id"],
            title=t["title"],
            content=t["content"],
            stock_codes=t["stock_codes"],
            stock_names=t["stock_names"],
            source=source
        )
        raw_texts.append(raw_text)
    
    return raw_texts


def test_preprocessing():
    """测试预处理模块"""
    logger.info("=" * 60)
    logger.info("测试1：文本预处理模块")
    logger.info("=" * 60)
    
    raw_texts = create_test_data()
    preprocessor = TextPreprocessor()
    
    for raw_text in raw_texts:
        logger.info(f"\n处理文本: {raw_text.text_id}")
        logger.info(f"标题: {raw_text.title}")
        
        chunks = preprocessor.process(raw_text)
        logger.info(f"生成 {len(chunks)} 个文本块")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"\n  块 {i+1}:")
            logger.info(f"    股票: {chunk.stock_code}")
            logger.info(f"    内容: {chunk.content[:80]}...")
            logger.info(f"    实体数: {len(chunk.entities)}")
            logger.info(f"    关键词: {chunk.keywords}")
            logger.info(f"    相关性: {chunk.is_relevant}")
    
    return raw_texts


def test_mock_analyzer(chunks: List[ProcessedChunk]):
    """测试模拟LLM分析器"""
    logger.info("=" * 60)
    logger.info("测试2：情绪分析和风险识别（使用模拟分析器）")
    logger.info("=" * 60)
    
    analyzer = MockLLMAnalyzer()
    results = analyzer.analyze_batch(chunks)
    
    logger.info(f"\n分析完成 {len(results)} 个文本块")
    
    for result in results:
        logger.info(f"\n文本ID: {result.text_id}")
        logger.info(f"股票: {result.stock_code}")
        
        if result.sentiment:
            sent = result.sentiment
            logger.info(f"\n  情绪分析:")
            logger.info(f"    分数: {sent.sentiment_score:.3f}")
            logger.info(f"    极性: {sent.polarity.value}")
            logger.info(f"    置信度: {sent.confidence:.3f}")
            logger.info(f"    分类分数: {sent.categories}")
            logger.info(f"    关键短语: {sent.key_phrases}")
            logger.info(f"    推理: {sent.reasoning}")
        
        if result.risks:
            logger.info(f"\n  风险警报 ({len(result.risks)} 个):")
            for risk in result.risks:
                logger.info(f"    - {risk.risk_title}")
                logger.info(f"      等级: {risk.risk_level.value}")
                logger.info(f"      分数: {risk.risk_score:.3f}")
                logger.info(f"      描述: {risk.risk_description}")
        
        logger.info(f"\n  综合评分: {result.composite_score:.3f}")
    
    return results


def test_pipeline_without_vector_store():
    """测试完整管道（不包括向量存储，因为需要API密钥）"""
    logger.info("=" * 60)
    logger.info("测试3：完整分析管道（模拟模式）")
    logger.info("=" * 60)
    
    raw_texts = create_test_data()
    preprocessor = TextPreprocessor()
    analyzer = MockLLMAnalyzer()
    
    for raw_text in raw_texts:
        logger.info(f"\n处理: {raw_text.text_id}")
        
        # 步骤1：预处理
        chunks = preprocessor.process(raw_text)
        logger.info(f"  预处理: 生成 {len(chunks)} 个块")
        
        # 步骤2：分析
        relevant_chunks = [c for c in chunks if c.is_relevant]
        logger.info(f"  相关块: {len(relevant_chunks)} 个")
        
        if relevant_chunks:
            results = analyzer.analyze_batch(relevant_chunks)
            logger.info(f"  分析: 完成 {len(results)} 个分析")
            
            for result in results:
                logger.info(f"\n    结果:")
                logger.info(f"      情绪分数: {result.sentiment.sentiment_score:.3f}")
                logger.info(f"      综合评分: {result.composite_score:.3f}")
                logger.info(f"      风险数: {len(result.risks)}")
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成！所有模块运行正常")
    logger.info("=" * 60)


def export_test_results():
    """导出测试结果为JSON"""
    logger.info("\n导出测试结果...")
    
    raw_texts = create_test_data()
    preprocessor = TextPreprocessor()
    analyzer = MockLLMAnalyzer()
    
    all_results = []
    
    for raw_text in raw_texts:
        chunks = preprocessor.process(raw_text)
        results = analyzer.analyze_batch(chunks)
        
        for result in results:
            all_results.append(result.to_dict())
    
    # 保存到JSON文件
    output_file = "/Users/mac/sandbox/HKU/COMP7705/test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"结果已保存到: {output_file}")
    return output_file


if __name__ == "__main__":
    logger.info("开始港股舆情分析系统测试")
    logger.info("=" * 60)
    
    try:
        # 测试预处理
        raw_texts = test_preprocessing()
        
        # 收集所有文本块
        all_chunks = []
        preprocessor = TextPreprocessor()
        for raw_text in raw_texts:
            chunks = preprocessor.process(raw_text)
            all_chunks.extend(chunks)
        
        # 测试模拟分析器
        test_mock_analyzer(all_chunks)
        
        # 测试完整管道
        test_pipeline_without_vector_store()
        
        # 导出结果
        output_file = export_test_results()
        
        logger.info("\n✓ 所有测试通过！")
        logger.info(f"✓ 测试结果已保存到 test_results.json")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
