"""
文本分析模块 - 向量存储与RAG
功能：文本向量化、向量数据库存储、语义检索
"""

import os
from typing import List, Dict, Any, Optional
import hashlib
import json

import chromadb
from chromadb.config import Settings
import openai
import langdetect


class VectorStore:
    """
    向量存储管理器
    基于ChromaDB，支持文本嵌入存储和语义检索
    """
    
    def __init__(self, 
                 collection_name: str = "hk_stock_news",
                 persist_directory: str = "./chroma_db",
                 embedding_model: str = "text-embedding-3-small",
                 use_enhanced_embedding: bool = False):
        
        self.embedding_model = embedding_model
        self.use_enhanced_embedding = use_enhanced_embedding
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # 初始化ChromaDB客户端
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
        
        # 初始化Embedding客户端
        self.embed_client = openai.OpenAI(api_key=self.api_key)
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的向量嵌入"""
        # 截断长文本
        text = text[:8000] if len(text) > 8000 else text
        
        response = self.embed_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    def _get_embedding_enhanced(self, text: str) -> List[float]:
        """
        多语言感知的嵌入策略 - 支持混合ZH/EN金融文本
        
        功能：
        - 自动检测文本语言（中文/英文/混合）
        - 为中文文本使用大模型以获得更好的CJK覆盖
        - 为英文文本使用小模型以降低成本
        - 为混合文本使用大模型并添加明确标记
        
        输入：文本内容
        输出：优化的向量嵌入
        """
        # 截断长文本
        text = text[:8000] if len(text) > 8000 else text
        
        # Step 1: 语言检测（带降级处理）
        try:
            lang = langdetect.detect(text)
        except Exception as e:
            # 若检测失败，默认为未知语言，使用大模型
            lang = "unknown"
            print(f"⚠️ 语言检测失败: {str(e)}, 使用默认策略")
        
        # Step 2: 策略选择
        if lang in ["zh-cn", "zh-tw", "zh"]:
            # 中文为主：使用大模型以获得更好的CJK支持
            embedding_model = "text-embedding-3-large"
            processed_text = f"[ZH] {text}"
            language_tag = "Chinese"
        elif lang == "en":
            # 英文：使用小模型以降低成本
            embedding_model = "text-embedding-3-small"
            processed_text = text
            language_tag = "English"
        else:
            # 混合/未知语言：使用大模型并添加混合标记
            embedding_model = "text-embedding-3-large"
            processed_text = f"[MIXED] {text}"
            language_tag = "Mixed/Unknown"
        
        # Step 3: 调用API获取嵌入
        try:
            response = self.embed_client.embeddings.create(
                input=[processed_text],
                model=embedding_model
            )
            embedding = response.data[0].embedding
            
            # 记录使用的策略
            print(f"✅ 嵌入生成: 语言={language_tag}, 模型={embedding_model}, "
                  f"文本长度={len(text)}, 向量维度={len(embedding)}")
            
            return embedding
        except Exception as e:
            print(f"❌ 嵌入生成失败: {str(e)}, 使用标准模型降级")
            # 降级处理：使用标准模型
            response = self.embed_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
    
    def add_text(self, 
                 text_id: str,
                 content: str,
                 metadata: Dict[str, Any],
                 embedding: Optional[List[float]] = None) -> str:
        """
        添加文本到向量库
        
        输入：
            text_id: 唯一标识
            content: 文本内容
            metadata: 元数据（股票代码、时间、来源、情绪分数等）
            embedding: 预计算的向量（可选）
        
        输出：文档ID
        """
        # 生成唯一ID
        doc_id = hashlib.md5(f"{text_id}_{metadata.get('stock_code', 'unknown')}".encode()).hexdigest()
        
        # 计算embedding
        if embedding is None:
            if self.use_enhanced_embedding:
                # 使用多语言感知的增强嵌入
                embedding = self._get_embedding_enhanced(content)
            else:
                # 使用标准嵌入
                embedding = self._get_embedding(content)
        
        # 添加到集合
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "text_id": text_id,
                "content_preview": content[:200],
                **metadata
            }]
        )
        
        return doc_id
    
    def add_analysis_result(self, analysis_output: Any) -> List[str]:
        """
        添加分析结果到向量库
        包括：原文、情绪解释、风险描述分别存储
        
        输入：AnalysisOutput对象
        输出：添加的文档ID列表
        """
        from models import AnalysisOutput  # 避免循环导入
        
        if not isinstance(analysis_output, AnalysisOutput):
            raise TypeError("Expected AnalysisOutput instance")
        
        added_ids = []
        stock_code = analysis_output.stock_code
        
        # 1. 存储原文块
        for chunk in analysis_output.chunks:
            doc_id = self.add_text(
                text_id=chunk.chunk_id,
                content=chunk.content,
                metadata={
                    "stock_code": stock_code,
                    "type": "original_text",
                    "parent_text_id": chunk.parent_text_id,
                    "keywords": ",".join(chunk.keywords[:5])
                }
            )
            added_ids.append(doc_id)
        
        # 2. 存储情绪分析（如果有）
        if analysis_output.sentiment:
            sent = analysis_output.sentiment
            reasoning_text = f"""
            股票：{stock_code}
            情绪分数：{sent.sentiment_score}（{sent.polarity.value}）
            置信度：{sent.confidence}
            分析逻辑：{sent.reasoning}
            关键短语：{', '.join(sent.key_phrases)}
            """
            
            doc_id = self.add_text(
                text_id=sent.result_id,
                content=reasoning_text,
                metadata={
                    "stock_code": stock_code,
                    "type": "sentiment_analysis",
                    "sentiment_score": sent.sentiment_score,
                    "polarity": sent.polarity.value,
                    "confidence": sent.confidence,
                    "categories": json.dumps(sent.categories)
                }
            )
            added_ids.append(doc_id)
        
        # 3. 存储风险警报（如果有）
        for risk in analysis_output.risks:
            risk_text = f"""
            股票：{stock_code}
            风险类型：{risk.risk_category.value}
            风险等级：{risk.risk_level.value}
            风险分数：{risk.risk_score}
            标题：{risk.risk_title}
            描述：{risk.risk_description}
            影响方面：{', '.join(risk.affected_aspects)}
            原文证据：{risk.source_text_snippet}
            """
            
            doc_id = self.add_text(
                text_id=risk.alert_id,
                content=risk_text,
                metadata={
                    "stock_code": stock_code,
                    "type": "risk_alert",
                    "risk_category": risk.risk_category.value,
                    "risk_level": risk.risk_level.value,
                    "risk_score": risk.risk_score,
                    "detected_at": risk.detected_at.isoformat()
                }
            )
            added_ids.append(doc_id)
        
        return added_ids
    
    def search(self, 
               query: str, 
               stock_code: Optional[str] = None,
               filter_type: Optional[str] = None,
               n_results: int = 5) -> List[Dict[str, Any]]:
        """
        语义检索
        
        输入：
            query: 查询文本
            stock_code: 可选，限制特定股票
            filter_type: 可选，限制文档类型（original_text/sentiment_analysis/risk_alert）
            n_results: 返回结果数量
        
        输出：匹配文档列表，包含内容和相似度分数
        """
        # 生成查询向量
        query_embedding = self._get_embedding(query)
        
        # 构建过滤条件
        where_clause = {}
        if stock_code:
            where_clause["stock_code"] = stock_code
        if filter_type:
            where_clause["type"] = filter_type
        
        # 执行检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # 格式化输出
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "similarity_score": 1 - results['distances'][0][i]  # 距离转相似度
            })
        
        return formatted_results
    
    def search_risks(self, stock_code: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        专门检索某股票的近期风险
        
        输入：股票代码，时间范围（天）
        输出：风险警报列表（按时间倒序）
        """
        # 构造风险相关查询
        query = f"{stock_code} 最近风险 监管 财务 运营问题"
        
        return self.search(
            query=query,
            stock_code=stock_code,
            filter_type="risk_alert",
            n_results=10
        )
    
    def get_sentiment_timeline(self, stock_code: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取某股票的情绪分析时间线
        
        输入：股票代码，数量限制
        输出：按时间排序的情绪记录
        """
        # 使用metadata过滤获取所有情绪分析
        results = self.collection.get(
            where={
                "stock_code": stock_code,
                "type": "sentiment_analysis"
            },
            limit=limit,
            include=["metadatas"]
        )
        
        # 按时间排序
        timeline = []
        for meta in results['metadatas']:
            timeline.append({
                "timestamp": meta.get('created_at', 'unknown'),
                "sentiment_score": meta.get('sentiment_score', 0),
                "polarity": meta.get('polarity', 'unknown'),
                "confidence": meta.get('confidence', 0)
            })
        
        return sorted(timeline, key=lambda x: x['timestamp'], reverse=True)
    
    def delete_old_records(self, days: int = 90):
        """清理旧记录（保留最近N天）"""
        # ChromaDB不支持直接按时间删除，需要遍历
        # 实际实现中可添加时间戳过滤
        pass
    
    def persist(self):
        """持久化数据到磁盘"""
        # ChromaDB自动持久化，此方法用于确保写入
        pass


class RAGQueryEngine:
    """
    RAG查询引擎
    结合向量检索和LLM生成，回答用户问题
    """
    
    def __init__(self, vector_store: VectorStore, llm_analyzer: Any):
        self.vector_store = vector_store
        self.llm = llm_analyzer
    
    def answer(self, query: str, stock_code: Optional[str] = None) -> Dict[str, Any]:
        """
        RAG问答
        
        输入：用户查询，可选股票代码限制
        输出：带引用的回答
        """
        # 1. 检索相关文档
        contexts = self.vector_store.search(
            query=query,
            stock_code=stock_code,
            n_results=5
        )
        
        if not contexts:
            return {
                "answer": "未找到相关信息。",
                "sources": [],
                "confidence": "low"
            }
        
        # 2. 构建上下文
        context_text = "\n\n".join([
            f"[来源{i+1}] {ctx['metadata'].get('type', 'unknown')}: {ctx['content'][:300]}"
            for i, ctx in enumerate(contexts)
        ])
        
        # 3. 构造提示词
        prompt = f"""基于以下检索到的新闻片段，回答用户的问题。

用户问题：{query}

检索到的信息：
{context_text}

要求：
1. 直接回答问题，简明扼要（100字以内）
2. 每个事实后标注来源编号（如[来源1]）
3. 如果信息不足，明确说明"根据现有资料无法确定"
4. 保持客观，不添加检索内容外的推测

输出JSON格式：
{{
  "answer": "你的回答",
  "sources_used": [1, 2],
  "confidence": "high/medium/low",
  "missing_info": "如有信息缺口，在此说明"
}}"""
        
        # 4. 调用LLM生成回答
        try:
            result = self.llm._call_llm(prompt)
            return {
                "answer": result.get("answer", ""),
                "sources": [
                    {
                        "index": i+1,
                        "type": ctx['metadata'].get('type'),
                        "stock": ctx['metadata'].get('stock_code'),
                        "similarity": round(ctx['similarity_score'], 3),
                        "snippet": ctx['content'][:100]
                    }
                    for i, ctx in enumerate(contexts)
                ],
                "confidence": result.get("confidence", "medium"),
                "missing_info": result.get("missing_info", "")
            }
        except Exception as e:
            return {
                "answer": f"生成回答时出错：{str(e)}",
                "sources": [],
                "confidence": "error"
            }
    
    def generate_daily_summary(self, stock_code: str, date: str) -> str:
        """
        生成每日舆情摘要
        
        输入：股票代码，日期
        输出：AI生成的200字摘要
        """
        # 检索当日所有相关文档
        contexts = self.vector_store.search(
            query=f"{stock_code} {date} 新闻 公告 业绩",
            stock_code=stock_code,
            n_results=10
        )
        
        if not contexts:
            return f"{stock_code}在{date}无重大舆情事件。"
        
        # 统计情绪分布
        sentiments = [ctx['metadata'].get('sentiment_score', 0) for ctx in contexts 
                     if ctx['metadata'].get('type') == 'sentiment_analysis']
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # 提取关键风险
        risks = [ctx for ctx in contexts if ctx['metadata'].get('type') == 'risk_alert']
        
        # 生成摘要
        prompt = f"""为{stock_code}生成{date}的每日舆情摘要。

当日要点：
{chr(10).join([f"- {ctx['content'][:100]}" for ctx in contexts[:5]])}

情绪倾向：{'正面' if avg_sentiment > 0.2 else '负面' if avg_sentiment < -0.2 else '中性'}
风险事件：{len(risks)}件

要求：
1. 200字以内
2. 涵盖最重要的1-2个事件
3. 说明整体市场情绪
4. 提及主要风险（如有）

输出纯文本，不要JSON。"""

        try:
            result = self.llm._call_llm(prompt)
            return result.get("answer", result.get("reasoning", "摘要生成失败"))
        except:
            # 降级方案：简单拼接
            return f"{stock_code}当日摘要：共{len(contexts)}条相关资讯，整体情绪{'积极' if avg_sentiment > 0 else '谨慎'}。"