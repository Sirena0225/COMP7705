"""
文本分析模块 - 主控流程
功能：整合各组件，提供统一接口，处理消息队列
"""

import os
import json
import asyncio
from typing import List, Optional
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TextAnalysisModule")

# 导入各组件
from models import RawText, TextSource, AnalysisOutput
from multilingual_preprocessor import MultilingualTextPreprocessor
from multilingual_analyzer import MultilingualAnalyzer, RAGLLMAdapter
from vector_storage import VectorStore, RAGQueryEngine


class TextAnalysisPipeline:
    """
    文本分析主流程
    整合预处理、LLM分析、向量存储
    """
    
    def __init__(self):
        logger.info("初始化文本分析管道...")
        
        # 初始化各组件
        self.preprocessor = MultilingualTextPreprocessor()
        llm = MultilingualAnalyzer(
            model_name=os.getenv("LLM_MODEL", "deepseek-chat"),
            api_key=os.getenv("LLM_API_KEY"),
        )
        self.analyzer = llm
        self.vector_store = VectorStore(
            collection_name="hk_stock_analysis",
            persist_directory="./data/chroma_db",
        )
        self.rag_engine = RAGQueryEngine(self.vector_store, RAGLLMAdapter(llm))
        
        # 统计
        self.processed_count = 0
        self.failed_count = 0
    
    def process_single(self, raw_text: RawText) -> Optional[AnalysisOutput]:
        """
        处理单条原始文本（完整流程）
        
        输入：RawText对象
        输出：AnalysisOutput对象，失败返回None
        """
        try:
            logger.info(f"处理文本: {raw_text.text_id} | 股票: {raw_text.stock_codes}")
            
            # 步骤1：预处理
            chunks = self.preprocessor.process(raw_text)
            logger.info(f"  生成 {len(chunks)} 个文本块")
            
            # 步骤2：LLM分析（仅处理相关块）
            relevant_chunks = [c for c in chunks if c.is_relevant]
            if not relevant_chunks:
                logger.warning(f"  无相关文本块，跳过")
                return None
            
            # 批量分析
            lang = raw_text.language if raw_text.language != "mixed" else "zh"
            analysis_results = self.analyzer.analyze_batch(relevant_chunks, language=lang)
            logger.info(f"  完成 {len(analysis_results)} 条分析")
            
            # 步骤3：合并结果（同一text_id的多股票结果）
            # 简化：返回第一个结果（实际应按股票聚合）
            if not analysis_results:
                return None
            
            final_output = analysis_results[0]
            
            # 步骤4：向量存储
            doc_ids = self.vector_store.add_analysis_result(final_output)
            logger.info(f"  向量库存储: {len(doc_ids)} 条文档")
            
            self.processed_count += 1
            return final_output
            
        except Exception as e:
            logger.error(f"处理失败 {raw_text.text_id}: {str(e)}")
            self.failed_count += 1
            return None
    
    def process_batch(self, raw_texts: List[RawText]) -> List[AnalysisOutput]:
        """
        批量处理
        """
        results = []
        for text in raw_texts:
            result = self.process_single(text)
            if result:
                results.append(result)
        return results
    
    def query_sentiment(self, stock_code: str, days: int = 7) -> dict:
        """
        查询某股票近期情绪趋势
        """
        timeline = self.vector_store.get_sentiment_timeline(stock_code, limit=days*5)
        
        if not timeline:
            return {
                "stock_code": stock_code,
                "period": f"最近{days}天",
                "status": "无数据",
                "current_sentiment": 0,
                "trend": "unknown"
            }
        
        # 计算趋势
        scores = [t['sentiment_score'] for t in timeline]
        avg_score = sum(scores) / len(scores)
        
        # 简单趋势判断
        if len(scores) >= 3:
            recent = sum(scores[:3]) / 3
            older = sum(scores[-3:]) / 3 if len(scores) >= 6 else scores[-1]
            trend = "上升" if recent > older + 0.1 else "下降" if recent < older - 0.1 else "平稳"
        else:
            trend = "数据不足"
        
        return {
            "stock_code": stock_code,
            "period": f"最近{days}天",
            "data_points": len(timeline),
            "current_sentiment": round(avg_score, 3),
            "trend": trend,
            "recent_scores": [round(s, 2) for s in scores[:5]]
        }
    
    def query_risks(self, stock_code: str) -> dict:
        """
        查询某股票当前风险
        """
        risks = self.vector_store.search_risks(stock_code, days=30)
        
        high_risks = [r for r in risks if r['metadata'].get('risk_level') == 'red']
        medium_risks = [r for r in risks if r['metadata'].get('risk_level') == 'yellow']
        
        return {
            "stock_code": stock_code,
            "risk_summary": "高风险" if high_risks else "中等风险" if medium_risks else "低风险",
            "high_risk_count": len(high_risks),
            "medium_risk_count": len(medium_risks),
            "recent_risks": [
                {
                    "category": r['metadata'].get('risk_category'),
                    "level": r['metadata'].get('risk_level'),
                    "score": r['metadata'].get('risk_score'),
                    "description": r['content'][:100]
                }
                for r in risks[:3]
            ]
        }
    
    def rag_query(self, question: str, stock_code: Optional[str] = None) -> dict:
        """
        RAG问答接口
        """
        return self.rag_engine.answer(question, stock_code)
    
    def get_stats(self) -> dict:
        """获取模块统计信息"""
        return {
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "success_rate": f"{(self.processed_count/(self.processed_count+self.failed_count)*100):.1f}%" if (self.processed_count+self.failed_count) > 0 else "N/A",
            "llm_stats": self.analyzer.get_stats(),
            "vector_store": {
                "collection": self.vector_store.collection.name,
                "count": self.vector_store.collection.count()
            }
        }


pipeline = TextAnalysisPipeline()
app = None


def create_api_app():
    """创建 FastAPI 应用（需安装 fastapi、uvicorn）。"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    api = FastAPI(title="文本分析模块API", version="1.0")

    class TextInput(BaseModel):
        text_id: str
        title: str
        content: str
        stock_codes: List[str]
        stock_names: List[str]
        source_type: str
        source_name: str
        publish_time: Optional[str] = None

    class RAGQuery(BaseModel):
        question: str
        stock_code: Optional[str] = None

    @api.post("/analyze", response_model=dict)
    async def analyze_text(input_data: TextInput):
        raw = RawText(
            text_id=input_data.text_id,
            title=input_data.title,
            content=input_data.content,
            stock_codes=input_data.stock_codes,
            stock_names=input_data.stock_names,
            source=TextSource(
                source_type=input_data.source_type,
                source_name=input_data.source_name,
                publish_time=datetime.fromisoformat(input_data.publish_time)
                if input_data.publish_time
                else None,
            ),
        )
        result = pipeline.process_single(raw)
        if not result:
            raise HTTPException(status_code=500, detail="分析失败")
        return result.to_dict()

    @api.post("/analyze/batch")
    async def analyze_batch(texts: List[TextInput]):
        raws = [
            RawText(
                text_id=t.text_id,
                title=t.title,
                content=t.content,
                stock_codes=t.stock_codes,
                stock_names=t.stock_names,
                source=TextSource(
                    source_type=t.source_type, source_name=t.source_name
                ),
            )
            for t in texts
        ]
        results = pipeline.process_batch(raws)
        return {"processed": len(results), "results": [r.to_dict() for r in results]}

    @api.get("/sentiment/{stock_code}")
    async def get_sentiment(stock_code: str, days: int = 7):
        return pipeline.query_sentiment(stock_code, days)

    @api.get("/risks/{stock_code}")
    async def get_risks(stock_code: str):
        return pipeline.query_risks(stock_code)

    @api.post("/rag/query")
    async def rag_query(query: RAGQuery):
        return pipeline.rag_query(query.question, query.stock_code)

    @api.get("/stats")
    async def get_stats():
        return pipeline.get_stats()

    @api.get("/health")
    async def health_check():
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}

    return api


# 消息队列消费者（异步处理）
async def message_queue_consumer():
    """
    RabbitMQ消费者
    持续监听队列，处理 incoming 文本
    """
    import aio_pika
    
    connection = await aio_pika.connect_robust(
        os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    )
    
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("raw_text_queue", durable=True)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        data = json.loads(message.body)
                        raw = RawText(**data)
                        pipeline.process_single(raw)
                    except Exception as e:
                        logger.error(f"队列处理失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    app = create_api_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
    
    # 同时启动队列消费者（需要异步运行）
    # asyncio.run(message_queue_consumer())