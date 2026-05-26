"""
离线 Mock LLM 分析器，用于演示与无 API Key 时的影子测试。
"""

from typing import List, Dict, Any

from models import (
    ProcessedChunk,
    AnalysisOutput,
    SentimentResult,
    SentimentPolarity,
)


class MockLLMAnalyzer:
    """基于关键词的简易分析器，接口与 MultilingualAnalyzer 兼容。"""

    def __init__(self, model_name: str = "mock"):
        self.model_name = model_name
        self.total_calls = 0
        self.total_tokens = 0

    def _score_text(self, text: str) -> float:
        positive = ("增长", "超预期", "上调", "强劲", "创纪录", "beat", "growth", "record")
        negative = ("下跌", "亏损", "调查", "处罚", "减持", "miss", "decline", "risk", "fine")
        score = 0.0
        lower = text.lower()
        for w in positive:
            if w in text or w in lower:
                score += 0.2
        for w in negative:
            if w in text or w in lower:
                score -= 0.25
        return max(-1.0, min(1.0, score))

    def analyze(self, chunk: ProcessedChunk, language: str = "zh") -> AnalysisOutput:
        self.total_calls += 1
        score = self._score_text(chunk.content)
        polarity = (
            SentimentPolarity.POSITIVE
            if score > 0.15
            else SentimentPolarity.NEGATIVE
            if score < -0.15
            else SentimentPolarity.NEUTRAL
        )
        sentiment = SentimentResult(
            result_id=f"mock_sent_{chunk.chunk_id}",
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment_score=score,
            confidence=0.75,
            polarity=polarity,
            categories={"earnings": score, "market": score * 0.5},
            key_phrases=chunk.keywords[:3] if chunk.keywords else [],
            reasoning="MockLLMAnalyzer 关键词启发式结果",
            model_version=self.model_name,
        )
        output = AnalysisOutput(
            text_id=chunk.parent_text_id,
            stock_code=chunk.stock_code,
            sentiment=sentiment,
            risks=[],
            chunks=[chunk],
        )
        output.calculate_composite()
        return output

    def analyze_batch(
        self, chunks: List[ProcessedChunk], language: str = "zh"
    ) -> List[AnalysisOutput]:
        results = []
        for chunk in chunks:
            if chunk.is_relevant:
                results.append(self.analyze(chunk, language=language))
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
            "model": self.model_name,
        }

    def _call_llm(self, prompt: str, language: str = "en", temperature: float = 0.1) -> Dict[str, Any]:
        """供 RAGLLMAdapter 使用的简易 JSON 响应。"""
        self.total_calls += 1
        return {
            "answer": "基于检索内容的 Mock 回答（未调用真实 LLM）。",
            "confidence": "low",
            "sources_used": [1],
            "missing_info": "",
        }
