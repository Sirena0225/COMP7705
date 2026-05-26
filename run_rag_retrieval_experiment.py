"""
RAG 检索精度完整实验脚本
一键运行，无需额外配置
"""

import json
import os
import time
from pathlib import Path
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from vector_storage import VectorStore
from evaluation.retrieval_eval import evaluate_retrieval_quality


class RAGExperiment:
    """RAG 检索精度实验管理器"""
    
    def __init__(self, data_path='data/sentiment_input_batch.json'):
        self.data_path = data_path
        self.raw_data = None
        self.test_queries = None
        self.vector_store = None
        self.results = {}
    
    def load_data(self):
        """加载原始数据"""
        print("\n" + "="*70)
        print("📋 步骤1: 加载数据")
        print("="*70)
        
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.raw_data = json.load(f)
        
        print(f"✅ 已加载 {len(self.raw_data)} 个文本样本")
        
        # 统计信息
        sources = defaultdict(int)
        languages = defaultdict(int)
        
        for item in self.raw_data:
            sources[item.get('source_type', 'unknown')] += 1
            languages[item.get('language', 'unknown')] += 1
        
        print(f"\n📊 数据统计:")
        print(f"  • 来源类型: {dict(sources)}")
        print(f"  • 语言分布: {dict(languages)}")
    
    def build_vector_store(self, use_enhanced=True):
        """构建向量库"""
        print("\n" + "="*70)
        print("🔨 步骤2: 构建向量库")
        print("="*70)
        
        embedding_mode = "增强模式" if use_enhanced else "标准模式"
        print(f"\n使用 {embedding_mode} (use_enhanced_embedding={use_enhanced})")
        
        self.vector_store = VectorStore(
            collection_name="rag_retrieval_test",
            persist_directory="./rag_db",
            use_enhanced_embedding=use_enhanced,
        )
        backend = self.vector_store.embedding_backend
        if backend == "dashscope":
            print(f"  • 嵌入后端: 阿里云百炼 (DashScope)")
            print(f"  • 嵌入模型: {self.vector_store.embedding_model}")
        elif backend == "local":
            print("  • 嵌入后端: 本地模型 (sentence-transformers)")
        else:
            print(f"  • 嵌入后端: {backend}")
            print(f"  • 嵌入模型: {self.vector_store.embedding_model}")
        
        start_time = time.time()
        success_count = 0
        
        for i, item in enumerate(self.raw_data):
            try:
                stock_codes = item.get('stock_codes', [])
                self.vector_store.add_text(
                    text_id=item.get('text_id', f'doc_{i}'),
                    content=item.get('content', item.get('title', '')),
                    metadata={
                        'stock_code': stock_codes[0] if stock_codes else 'unknown',
                        'stock_codes': ','.join(stock_codes),
                        'source': item.get('source_type', 'unknown'),
                        'language': item.get('language', 'en'),
                        'published_at': item.get('published_at', ''),
                    }
                )
                success_count += 1
            except Exception as e:
                if i % 50 == 0:
                    print(f"  ⚠️  处理文本 {i} 失败: {e}")
                continue
            
            if (i + 1) % 100 == 0:
                print(f"  ✓ 已处理 {i + 1}/{len(self.raw_data)} 个文本")
        
        build_time = time.time() - start_time
        
        print(f"\n✅ 向量库构建完成")
        print(f"  • 成功处理: {success_count}/{len(self.raw_data)}")
        print(f"  • 耗时: {build_time:.2f}s")
        print(f"  • 平均速度: {success_count/build_time:.1f} 条/秒")
        
        self.results['build_time'] = build_time
        self.results['success_count'] = success_count
    
    def generate_test_queries(self, min_docs_per_stock=2, max_queries_per_stock=3):
        """从数据中生成测试查询"""
        print("\n" + "="*70)
        print("📝 步骤3: 生成测试查询")
        print("="*70)
        
        # 按股票分组
        stocks_data = defaultdict(list)
        for item in self.raw_data:
            for stock_code in item.get('stock_codes', []):
                stocks_data[stock_code].append(item)
        
        print(f"✅ 从数据中提取了 {len(stocks_data)} 个不同的股票代码")
        
        # 为每个股票创建查询
        self.test_queries = []
        
        for stock_code, docs in stocks_data.items():
            if len(docs) < min_docs_per_stock:
                continue
            
            # 从文本中提取查询
            for doc in docs[:max_queries_per_stock]:
                content = doc.get('content', '')
                title = doc.get('title', '')
                
                # 使用标题或前80个字符作为查询
                query_text = (title if title else content)[:100]
                
                # 找到同股票的其他相关文本
                relevant_ids = [
                    d.get('text_id', '') for d in docs 
                    if d.get('text_id', '') and d != doc
                ]
                
                if query_text and relevant_ids:
                    self.test_queries.append({
                        'query': query_text,
                        'stock_code': stock_code,
                        'relevant_ids': relevant_ids,
                    })
        
        print(f"✅ 生成了 {len(self.test_queries)} 个测试查询")
        print(f"\n📌 查询示例:")
        for i, q in enumerate(self.test_queries[:3]):
            print(f"\n  查询 {i+1}:")
            print(f"    文本: {q['query'][:60]}...")
            print(f"    股票: {q['stock_code']}")
            print(f"    相关文档: {len(q['relevant_ids'])} 个")
    
    def evaluate_retrieval(self, retrieval_k=10):
        """评估检索精度（Top-1 Accuracy / Top-5 Recall / MRR / NDCG@5 / 延迟）"""
        print("\n" + "="*70)
        print("🔍 步骤4: 评估检索精度")
        print("="*70)
        
        start_time = time.time()
        
        metrics = evaluate_retrieval_quality(
            self.vector_store,
            test_queries=self.test_queries,
            retrieval_k=retrieval_k,
        )
        
        eval_time = time.time() - start_time
        
        print(f"\n✅ 评估完成 (总耗时: {eval_time:.2f}s, 查询数: {metrics['num_queries']})")
        
        self.results['eval_time'] = eval_time
        self.results['metrics'] = metrics
        
        return metrics
    
    def display_results(self):
        """显示评估结果"""
        print("\n" + "="*70)
        print("📊 RAG 检索精度评估结果")
        print("="*70)
        
        print(f"\n【实验配置】")
        print(f"  • 文本样本数: {len(self.raw_data)}")
        print(f"  • 测试查询数: {len(self.test_queries)}")
        print(f"  • 向量库构建时间: {self.results.get('build_time', 0):.2f}s")
        print(f"  • 评估时间: {self.results.get('eval_time', 0):.2f}s")
        
        metrics = self.results.get('metrics', {})
        
        print(f"\n【RAG 检索精度指标】")
        print(f"  • Top-1 Accuracy          : {metrics.get('top1_accuracy', 0):.4f}")
        print(f"    (首位命中相关文档的查询比例, 越高越好, 最高 1.0)")
        print(f"  • Top-5 Recall            : {metrics.get('top5_recall', 0):.4f}")
        print(f"    (前 5 条结果覆盖的相关文档比例, 越高越好, 最高 1.0)")
        print(f"  • MRR                     : {metrics.get('mrr', 0):.4f}")
        print(f"    (首个相关文档平均倒数排名, 越高越好, 最高 1.0)")
        print(f"  • NDCG@5                  : {metrics.get('ndcg@5', 0):.4f}")
        print(f"    (前 5 位排序质量, 越高越好, 最高 1.0)")
        print(f"  • Avg. Retrieval Latency  : {metrics.get('avg_retrieval_latency_ms', 0):.2f} ms")
        print(f"    (单次 search() 平均耗时, 越低越好)")
        
        overall_score = (
            metrics.get('top1_accuracy', 0) * 0.25 +
            metrics.get('top5_recall', 0) * 0.25 +
            metrics.get('mrr', 0) * 0.25 +
            metrics.get('ndcg@5', 0) * 0.25
        )
        
        if overall_score >= 0.8:
            rating = "🌟🌟🌟 优秀"
        elif overall_score >= 0.6:
            rating = "🌟🌟 良好"
        elif overall_score >= 0.4:
            rating = "🌟 一般"
        else:
            rating = "⚠️  需要改进"
        
        print(f"\n【综合评分】")
        print(f"  • 总体表现: {rating}")
        print(f"  • 综合分数: {overall_score:.4f} / 1.0000")
    
    def save_results(self, filename='rag_experiment_results.json'):
        """保存结果到文件"""
        metrics = self.results.get('metrics', {})
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'config': {
                'num_samples': len(self.raw_data),
                'num_test_queries': len(self.test_queries),
                'data_source': self.data_path,
                'embedding_backend': self.vector_store.embedding_backend,
                'embedding_model': self.vector_store.embedding_model,
            },
            'timing': {
                'build_time_seconds': self.results.get('build_time', 0),
                'eval_time_seconds': self.results.get('eval_time', 0),
            },
            'quality': {
                'successful_samples': self.results.get('success_count', 0),
            },
            'retrieval_metrics': {
                'top1_accuracy': metrics.get('top1_accuracy'),
                'top5_recall': metrics.get('top5_recall'),
                'mrr': metrics.get('mrr'),
                'ndcg@5': metrics.get('ndcg@5'),
                'avg_retrieval_latency_ms': metrics.get('avg_retrieval_latency_ms'),
            },
            'metrics': self.results.get('metrics', {}),
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 结果已保存到: {filename}")
    
    def run_complete_experiment(self, use_enhanced=True):
        """运行完整实验"""
        print("\n" + "#"*70)
        print("# RAG 检索精度完整实验")
        print("#"*70)
        
        # 执行步骤
        self.load_data()
        self.build_vector_store(use_enhanced=use_enhanced)
        self.generate_test_queries()
        self.evaluate_retrieval()
        self.display_results()
        self.save_results()
        
        print("\n" + "#"*70)
        print("# 实验完成! ✨")
        print("#"*70)


def main():
    """主函数"""
    
    # 确保数据文件存在
    data_path = 'data/sentiment_input_batch.json'
    if not Path(data_path).exists():
        print(f"❌ 错误: 未找到数据文件 {data_path}")
        print("请确保已正确放置数据文件")
        return
    
    # 创建实验管理器
    experiment = RAGExperiment(data_path=data_path)
    
    # 运行实验
    experiment.run_complete_experiment(use_enhanced=True)
    
    # 可选: 对比实验
    print("\n" + "="*70)
    print("💡 提示: 你也可以禁用增强嵌入进行对比")
    print("="*70)
    print("# experiment = RAGExperiment()")
    print("# experiment.run_complete_experiment(use_enhanced=False)")


if __name__ == "__main__":
    main()
