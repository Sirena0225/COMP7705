"""
多语言情感分析模块
支持中文和英文的情感分析和风险识别
"""

import os
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from models import (
    ProcessedChunk, SentimentResult, RiskAlert, 
    SentimentPolarity, RiskLevel, RiskCategory,
    AnalysisOutput
)


class PromptTemplate(ABC):
    """提示词模板抽象基类"""
    
    @abstractmethod
    def get_sentiment_prompt(self) -> str:
        """获取情绪分析提示词"""
        pass
    
    @abstractmethod
    def get_risk_prompt(self) -> str:
        """获取风险识别提示词"""
        pass


class ChinesePromptTemplate(PromptTemplate):
    """中文提示词模板"""
    
    def get_sentiment_prompt(self) -> str:
        return """你是一位专业的金融舆情分析师，擅长分析港股新闻和公告的情绪倾向。

任务：分析以下关于{stock_name}({stock_code})的财经文本，给出客观、准确的情绪评估。

文本内容：
{content}

分析步骤（请逐步思考）：
1. 事件识别：文本描述的核心事件是什么？（如：财报发布、高管变动、监管处罚、产品发布等）
2. 影响判断：该事件对公司股价是利好、利空还是中性？考虑：
   - 对收入/利润的直接影响
   - 对行业竞争格局的影响
   - 对监管风险的影响
   - 对市场情绪的影响
3. 程度评估：影响是轻微、中等还是重大？
4. 证据提取：列出支持你判断的关键原文短语（最多3个）

输出要求（严格JSON格式）：
{{
  "sentiment_score": [-1.0到1.0之间的浮点数，-1为极度负面，+1为极度正面，0为中性],
  "confidence": [0.0到1.0，模型对此判断的置信度],
  "polarity": ["positive", "neutral", "negative"],
  "category_scores": {{
    "earnings": [-1到1, 业绩相关],
    "regulatory": [-1到1, 监管相关],
    "market": [-1到1, 市场情绪相关],
    "management": [-1到1, 管理层相关],
    "product": [-1到1, 产品业务相关]
  }},
  "key_phrases": ["关键短语1", "关键短语2", "关键短语3"],
  "reasoning": "简要解释你的判断逻辑，50-100字",
  "uncertainty": "如果存在信息不足或歧义，请在此说明"
}}

注意：
- 保持客观，避免过度解读
- 如果文本同时包含正面和负面信息，综合评估净影响
- 对数字敏感：收入增长、利润率变化、罚款金额等
- 港股特定语境："北水流入"通常为正面，"供股"通常为负面，"闪崩"为极度负面
"""
    
    def get_risk_prompt(self) -> str:
        return """你是一位金融风险预警专家，专门识别港股新闻中的潜在风险信号。

任务：从以下关于{stock_name}({stock_code})的文本中，识别是否存在特定类别的风险。

文本内容：
{content}

风险分类体系：
1. 监管风险（regulatory）
   - 反垄断调查（antitrust）
   - 数据安全审查（data_security）
   - 牌照/准入限制（license）
2. 财务风险（financial）
   - 债务违约（default）
   - 业绩不及预期（earnings_miss）
   - 审计问题（audit）
3. 运营风险（operational）
   - 高管离职（executive_departure）
   - 产品安全问题（product_safety）
   - 供应链中断（supply_chain）
4. ESG风险（esg）
   - 环境违规（environmental）
   - 社会责任问题（social）
   - 治理缺陷（governance）

分析步骤：
1. 逐类检查文本是否提及相关风险信号
2. 对识别出的风险，评估严重程度（1-10分）
3. 提取风险描述的原文片段

输出要求（严格JSON格式）：
{{
  "has_risk": [true/false],
  "risks": [
    {{
      "category": "regulatory_antitrust",
      "level": "high/medium/low",
      "score": 0.0-1.0,
      "title": "风险简短标题",
      "description": "风险详细描述，50-100字",
      "affected_aspects": ["业务A", "业务B"],
      "source_snippet": "原文片段，20-50字",
      "urgency": "immediate/short_term/medium_term"
    }}
  ],
  "overall_assessment": "整体风险评估摘要"
}}

注意：
- 如无明确风险信号，has_risk设为false，risks为空数组
- 避免过度敏感：正常业务调整、预期内的业绩波动不构成高风险
- 关注具体数字：罚款金额、债务到期日、高管持股比例变化等
"""


class EnglishPromptTemplate(PromptTemplate):
    """英文提示词模板"""
    
    def get_sentiment_prompt(self) -> str:
        return """You are a professional financial news sentiment analyst specializing in Hong Kong stock analysis and sentiment assessment.

Task: Analyze the following financial text about {stock_name} ({stock_code}) and provide an objective and accurate sentiment assessment.

Text Content:
{content}

Analysis Steps (Please think step by step):
1. Event Identification: What is the core event described in the text? (e.g., earnings release, executive changes, regulatory penalties, product launch, etc.)
2. Impact Assessment: Is this event positive, negative, or neutral for the stock price? Consider:
   - Direct impact on revenue/profit
   - Impact on industry competition
   - Impact on regulatory risks
   - Impact on market sentiment
3. Magnitude Assessment: Is the impact minor, moderate, or significant?
4. Evidence Extraction: List key phrases from the text that support your judgment (max 3)

Output Requirements (Strict JSON format):
{{
  "sentiment_score": [float between -1.0 and 1.0, -1 for extremely negative, +1 for extremely positive, 0 for neutral],
  "confidence": [float between 0.0 and 1.0, confidence level of this judgment],
  "polarity": ["positive", "neutral", "negative"],
  "category_scores": {{
    "earnings": [-1 to 1, earnings-related sentiment],
    "regulatory": [-1 to 1, regulatory-related sentiment],
    "market": [-1 to 1, market sentiment],
    "management": [-1 to 1, management-related sentiment],
    "product": [-1 to 1, product/business sentiment]
  }},
  "key_phrases": ["key phrase 1", "key phrase 2", "key phrase 3"],
  "reasoning": "Brief explanation of your judgment, 50-100 words",
  "uncertainty": "Any information gaps or ambiguities that affect the analysis"
}}

Important Notes:
- Maintain objectivity and avoid over-interpretation
- If the text contains both positive and negative signals, provide a net assessment
- Pay attention to numbers: revenue growth, margin changes, fine amounts, etc.
- Context matters: Global economic factors, industry trends, company strategy
"""
    
    def get_risk_prompt(self) -> str:
        return """You are a financial risk warning expert specializing in identifying potential risk signals in Hong Kong stock news.

Task: From the following text about {stock_name} ({stock_code}), identify any specific risk categories that may be present.

Text Content:
{content}

Risk Classification System:
1. Regulatory Risk
   - Antitrust investigations
   - Data security reviews
   - License/access restrictions
2. Financial Risk
   - Debt default
   - Earnings miss
   - Audit issues
3. Operational Risk
   - Executive departure
   - Product safety issues
   - Supply chain disruption
4. ESG Risk
   - Environmental violations
   - Social responsibility issues
   - Governance defects

Analysis Steps:
1. Check each risk category for relevant signals
2. Assess the severity of identified risks (1-10 scale)
3. Extract relevant quotes from the text

Output Requirements (Strict JSON format):
{{
  "has_risk": [true/false],
  "risks": [
    {{
      "category": "regulatory_antitrust",
      "level": "high/medium/low",
      "score": 0.0-1.0,
      "title": "Brief risk title",
      "description": "Detailed description of the risk, 50-100 words",
      "affected_aspects": ["business area A", "business area B"],
      "source_snippet": "Direct quote from text, 20-50 words",
      "urgency": "immediate/short_term/medium_term"
    }}
  ],
  "overall_assessment": "Overall risk assessment summary"
}}

Important Notes:
- If no explicit risk signals are found, set has_risk to false and risks to empty array
- Avoid excessive sensitivity: normal business adjustments don't constitute high risk
- Focus on specific indicators: fine amounts, debt maturity dates, insider ownership changes
"""


class MultilingualAnalyzer:
    """
    多语言情感分析器
    支持中文和英文的情感分析和风险识别
    """
    
    def __init__(self, model_name: str = "deepseek-chat", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        
        # 初始化API客户端
        if "deepseek" in model_name:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1"
            )
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
        
        # 加载语言特定的提示词模板
        self.chinese_prompts = ChinesePromptTemplate()
        self.english_prompts = EnglishPromptTemplate()
        
        # 统计信息
        self.total_calls = 0
        self.total_tokens = 0
        self.language_stats = {"zh": 0, "en": 0, "mixed": 0}
    
    def get_prompt_template(self, language: str) -> PromptTemplate:
        """根据语言获取相应的提示词模板"""
        if language == 'en':
            return self.english_prompts
        else:
            # 中文和混合文本使用中文模板
            return self.chinese_prompts
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _call_llm(self, prompt: str, language: str, temperature: float = 0.1) -> Dict[str, Any]:
        """
        调用LLM API（带重试机制）
        支持多语言
        """
        start_time = time.time()
        
        # 根据语言选择系统提示词
        if language == 'en':
            system_prompt = "You are a professional financial analyst specializing in Hong Kong stock market sentiment analysis. Provide responses strictly in the JSON format specified."
        else:
            system_prompt = "你是一位专业的金融分析师，擅长港股舆情分析。请严格按照要求的JSON格式输出，不要添加markdown代码块标记。"
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        elapsed = int((time.time() - start_time) * 1000)
        self.total_calls += 1
        self.total_tokens += response.usage.total_tokens if response.usage else 0
        
        # 记录语言统计
        self.language_stats[language] += 1
        
        # 解析响应
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # 尝试清理后重试
            cleaned = content.strip().strip('```json').strip('```').strip()
            return json.loads(cleaned)
    
    def analyze_sentiment(self, chunk: ProcessedChunk, language: str = 'zh') -> SentimentResult:
        """
        分析单个文本块的情绪
        支持中文和英文
        """
        template = self.get_prompt_template(language)
        
        prompt = template.get_sentiment_prompt().format(
            stock_name=chunk.stock_code.replace('.HK', ''),
            stock_code=chunk.stock_code,
            content=chunk.content
        )
        
        # 调用LLM
        llm_result = self._call_llm(prompt, language)
        
        # 解析极性
        polarity_str = llm_result.get("polarity", "neutral")
        polarity = SentimentPolarity(polarity_str)
        
        # 构建结果对象
        result = SentimentResult(
            result_id=f"sent_{chunk.chunk_id}",
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment_score=float(llm_result.get("sentiment_score", 0)),
            confidence=float(llm_result.get("confidence", 0.5)),
            polarity=polarity,
            categories=llm_result.get("category_scores", {}),
            key_phrases=llm_result.get("key_phrases", [])[:3],
            reasoning=llm_result.get("reasoning", ""),
            model_version=f"{self.model_name}_{language}",
            processing_time_ms=100
        )
        
        return result
    
    def analyze_risks(self, chunk: ProcessedChunk, language: str = 'zh') -> List[RiskAlert]:
        """
        识别文本块中的风险
        支持中文和英文
        """
        template = self.get_prompt_template(language)
        
        prompt = template.get_risk_prompt().format(
            stock_name=chunk.stock_code.replace('.HK', ''),
            stock_code=chunk.stock_code,
            content=chunk.content
        )
        
        llm_result = self._call_llm(prompt, language, temperature=0.2)
        
        alerts = []
        if not llm_result.get("has_risk", False):
            return alerts
        
        level_map = {
            "high": RiskLevel.HIGH,
            "medium": RiskLevel.MEDIUM,
            "low": RiskLevel.LOW
        }
        
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
                    risk_title=risk_data.get("title", "Unnamed Risk"),
                    risk_description=risk_data.get("description", ""),
                    source_text_snippet=risk_data.get("source_snippet", "")
                )
                alerts.append(alert)
            except ValueError:
                continue
        
        return alerts
    
    def analyze(self, chunk: ProcessedChunk, language: str = 'zh') -> AnalysisOutput:
        """
        完整分析流程（情绪 + 风险）
        支持中文和英文
        """
        sentiment = self.analyze_sentiment(chunk, language)
        risks = self.analyze_risks(chunk, language)
        
        output = AnalysisOutput(
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment=sentiment,
            risks=risks,
            chunks=[chunk]
        )
        
        output.calculate_composite()
        return output
    
    def analyze_batch(self, chunks: List[ProcessedChunk], language: str = 'zh') -> List[AnalysisOutput]:
        """
        批量分析（带速率限制）
        支持中文和英文
        """
        results = []
        for chunk in chunks:
            if not chunk.is_relevant:
                continue
            
            try:
                result = self.analyze(chunk, language)
                results.append(result)
                
                # 简单速率限制
                if self.total_calls % 20 == 0:
                    time.sleep(3)
                    
            except Exception as e:
                print(f"Analysis failed {chunk.chunk_id}: {str(e)}")
                continue
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": self.total_tokens / max(self.total_calls, 1),
            "model": self.model_name,
            "language_distribution": self.language_stats
        }
