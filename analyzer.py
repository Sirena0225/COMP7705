"""
文本分析模块 - LLM情绪分析
功能：使用大语言模型进行情绪打分、风险识别
"""

import os
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from models import (
    ProcessedChunk, SentimentResult, RiskAlert, 
    SentimentPolarity, RiskLevel, RiskCategory,
    AnalysisOutput
)


class LLMSentimentAnalyzer:
    """
    LLM情绪分析器
    核心组件：使用DeepSeek-V3或GPT-4o-mini进行金融情绪分析
    """
    
    def __init__(self, model_name: str = "deepseek-chat", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        
        # 初始化客户端
        if "deepseek" in model_name:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1"
            )
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
        
        # 加载提示词模板
        self.sentiment_prompt = self._load_sentiment_prompt()
        self.risk_prompt = self._load_risk_prompt()
        
        # 统计信息
        self.total_calls = 0
        self.total_tokens = 0
    
    def _load_sentiment_prompt(self) -> str:
        """加载情绪分析提示词模板"""
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
    
    def _load_risk_prompt(self) -> str:
        """加载风险识别提示词模板"""
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
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _call_llm(self, prompt: str, temperature: float = 0.1) -> Dict[str, Any]:
        """
        调用LLM API（带重试机制）
        
        输入：提示词字符串
        输出：解析后的JSON字典
        """
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "你是一位专业的金融分析师，擅长港股舆情分析。请严格按照要求的JSON格式输出，不要添加markdown代码块标记。"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        elapsed = int((time.time() - start_time) * 1000)
        self.total_calls += 1
        self.total_tokens += response.usage.total_tokens if response.usage else 0
        
        # 解析响应
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试清理后重试
            cleaned = content.strip().strip('```json').strip('```').strip()
            return json.loads(cleaned)
    
    def analyze_sentiment(self, chunk: ProcessedChunk) -> SentimentResult:
        """
        分析单个文本块的情绪
        
        输入：ProcessedChunk对象
        输出：SentimentResult对象
        """
        # 构建提示词
        prompt = self.sentiment_prompt.format(
            stock_name=chunk.stock_code.replace('.HK', ''),
            stock_code=chunk.stock_code,
            content=chunk.content
        )
        
        # 调用LLM
        llm_result = self._call_llm(prompt)
        
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
            supporting_evidence=[chunk.content[max(0, chunk.content.find(p)-20):chunk.content.find(p)+len(p)+20] 
                               for p in llm_result.get("key_phrases", [])[:2]],
            model_version=self.model_name,
            processing_time_ms=int((time.time() - time.time()) * 1000)  # 实际应在调用前后计时
        )
        
        return result
    
    def analyze_risks(self, chunk: ProcessedChunk) -> List[RiskAlert]:
        """
        识别文本块中的风险
        
        输入：ProcessedChunk对象
        输出：RiskAlert对象列表（可能为空）
        """
        prompt = self.risk_prompt.format(
            stock_name=chunk.stock_code.replace('.HK', ''),
            stock_code=chunk.stock_code,
            content=chunk.content
        )
        
        llm_result = self._call_llm(prompt, temperature=0.2)
        
        alerts = []
        if not llm_result.get("has_risk", False):
            return alerts
        
        for risk_data in llm_result.get("risks", []):
            # 映射风险等级
            level_map = {
                "high": RiskLevel.HIGH,
                "medium": RiskLevel.MEDIUM,
                "low": RiskLevel.LOW
            }
            
            # 映射风险类别
            category_str = risk_data.get("category", "operational_executive")
            try:
                category = RiskCategory(category_str)
            except ValueError:
                category = RiskCategory.OPERATIONAL_EXECUTIVE  # 默认
            
            alert = RiskAlert(
                alert_id=f"risk_{chunk.chunk_id}_{len(alerts)}",
                text_id=chunk.parent_text_id,
                stock_code=chunk.stock_code,
                risk_category=category,
                risk_level=level_map.get(risk_data.get("level", "medium"), RiskLevel.MEDIUM),
                risk_score=float(risk_data.get("score", 0.5)),
                risk_title=risk_data.get("title", "未命名风险"),
                risk_description=risk_data.get("description", ""),
                affected_aspects=risk_data.get("affected_aspects", []),
                source_text_snippet=risk_data.get("source_snippet", chunk.content[:50]),
                source_text_location=chunk.content.find(risk_data.get("source_snippet", "")) if risk_data.get("source_snippet") else 0,
                detected_at=datetime.now(),
                valid_until=None  # 可根据urgency设置
            )
            alerts.append(alert)
        
        return alerts
    
    def analyze(self, chunk: ProcessedChunk) -> AnalysisOutput:
        """
        完整分析流程：情绪 + 风险
        
        输入：单个ProcessedChunk
        输出：完整的AnalysisOutput
        """
        # 并行执行情绪分析和风险识别（实际可优化为单次LLM调用）
        sentiment = self.analyze_sentiment(chunk)
        risks = self.analyze_risks(chunk)
        
        output = AnalysisOutput(
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment=sentiment,
            risks=risks,
            chunks=[chunk]
        )
        
        # 计算综合评分
        output.calculate_composite()
        
        return output
    
    def analyze_batch(self, chunks: List[ProcessedChunk]) -> List[AnalysisOutput]:
        """
        批量分析（带速率限制）
        
        输入：文本块列表
        输出：AnalysisOutput列表
        """
        results = []
        for chunk in chunks:
            if not chunk.is_relevant:
                continue  # 跳过低相关性块
            
            try:
                result = self.analyze(chunk)
                results.append(result)
                
                # 简单速率限制：每分钟最多20次调用
                if self.total_calls % 20 == 0:
                    time.sleep(3)
                    
            except Exception as e:
                print(f"分析失败 {chunk.chunk_id}: {str(e)}")
                continue
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "avg_tokens_per_call": self.total_tokens / max(self.total_calls, 1),
            "model": self.model_name
        }


# 批量优化版本：单次LLM调用完成情绪和风险分析
class OptimizedLLMAnalyzer(LLMSentimentAnalyzer):
    """
    优化版本：单次LLM调用同时完成情绪分析和风险识别
    减少API调用次数50%，降低成本
    """
    
    def _load_sentiment_prompt(self) -> str:
        """覆盖为组合提示词"""
        return """你是一位专业的金融舆情分析师，同时擅长情绪评估和风险识别。

任务：分析以下关于{stock_name}({stock_code})的财经文本，输出情绪评分和风险警报。

文本内容：
{content}

分析要求：
1. 情绪分析：判断文本对股价的利好/利空程度（-1到+1）
2. 风险识别：检查是否存在监管、财务、运营、ESG四类风险
3. 证据提取：列出关键原文短语支持你的判断

输出JSON格式：
{{
  "sentiment": {{
    "score": -1.0到1.0,
    "confidence": 0.0到1.0,
    "polarity": "positive/neutral/negative",
    "categories": {{"earnings": -1到1, "regulatory": -1到1, ...}},
    "key_phrases": ["短语1", "短语2"],
    "reasoning": "判断逻辑"
  }},
  "risks": {{
    "has_risk": true/false,
    "risk_list": [
      {{
        "category": "regulatory_antitrust/financial_default/...",
        "level": "high/medium/low",
        "score": 0.0-1.0,
        "title": "风险标题",
        "description": "风险描述",
        "source_snippet": "原文片段"
      }}
    ]
  }}
}}
"""
    
    def analyze(self, chunk: ProcessedChunk) -> AnalysisOutput:
        """优化的单次调用分析"""
        prompt = self._load_sentiment_prompt().format(
            stock_name=chunk.stock_code.replace('.HK', ''),
            stock_code=chunk.stock_code,
            content=chunk.content
        )
        
        llm_result = self._call_llm(prompt)
        
        # 解析情绪部分
        sent_data = llm_result.get("sentiment", {})
        sentiment = SentimentResult(
            result_id=f"sent_{chunk.chunk_id}",
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment_score=float(sent_data.get("score", 0)),
            confidence=float(sent_data.get("confidence", 0.5)),
            polarity=SentimentPolarity(sent_data.get("polarity", "neutral")),
            categories=sent_data.get("categories", {}),
            key_phrases=sent_data.get("key_phrases", []),
            reasoning=sent_data.get("reasoning", ""),
            model_version=self.model_name + "_optimized"
        )
        
        # 解析风险部分
        risks_data = llm_result.get("risks", {})
        risks = []
        if risks_data.get("has_risk", False):
            for r in risks_data.get("risk_list", []):
                try:
                    alert = RiskAlert(
                        alert_id=f"risk_{chunk.chunk_id}_{len(risks)}",
                        text_id=chunk.parent_text_id,
                        stock_code=chunk.stock_code,
                        risk_category=RiskCategory(r.get("category", "operational_executive")),
                        risk_level=RiskLevel(r.get("level", "medium")),
                        risk_score=float(r.get("score", 0.5)),
                        risk_title=r.get("title", ""),
                        risk_description=r.get("description", ""),
                        source_text_snippet=r.get("source_snippet", "")
                    )
                    risks.append(alert)
                except (ValueError, KeyError):
                    continue
        
        output = AnalysisOutput(
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment=sentiment,
            risks=risks,
            chunks=[chunk]
        )
        output.calculate_composite()
        
        return output