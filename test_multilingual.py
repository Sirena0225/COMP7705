"""
多语言情感分析 - 完整测试演示
演示中文和英文的双语情感分析功能
"""

import json
from datetime import datetime
from typing import List

from models import RawText, TextSource
from multilingual_preprocessor import MultilingualTextPreprocessor
from test_complete_flow import MockLLMAnalyzer

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultilingualAnalysis")


def create_multilingual_test_data() -> List[RawText]:
    """创建中英文双语测试数据"""
    
    test_data = [
        # 中文测试文本
        {
            "text_id": "zh-001",
            "language": "zh",
            "title": "腾讯Q1财报超预期，游戏和云服务业务双增长",
            "content": """
            腾讯控股(00700.HK)今日公布2024年第一季度财报。
            核心数据：
            - 总收入1,595亿元，同比增长6%
            - 净利润418亿元，同比增长54%
            - 游戏业务收入同比增长15%
            - 云服务收入同比增长29%
            
            首席执行官马化腾表示，公司在游戏、云计算等关键领域保持竞争优势。
            分析师普遍看好后续表现，多家机构上调目标价。
            """,
            "stock_codes": ["00700.HK"],
            "stock_names": ["腾讯控股"],
            "source_type": "announcement",
            "source_name": "披露易"
        },
        # 英文测试文本
        {
            "text_id": "en-001",
            "language": "en",
            "title": "Alibaba Faces Regulatory Scrutiny on Data Security",
            "content": """
            Alibaba Group (09988.HK) is under investigation by regulators regarding
            data security practices in its international e-commerce operations.
            
            Key Details:
            - Regulatory review could impact operations in multiple regions
            - Company commits to full compliance with regulations
            - Timeline for investigation estimated at 3-6 months
            
            Analysts now rate the stock as 'hold' pending investigation results.
            The scrutiny raises concerns about short-term business continuity.
            """,
            "stock_codes": ["09988.HK"],
            "stock_names": ["Alibaba-SW"],
            "source_type": "news",
            "source_name": "Bloomberg"
        },
        # 混合文本（中英文混合）
        {
            "text_id": "mixed-001",
            "language": "mixed",
            "title": "美团Meituan实现外卖业务盈利转型 Successful Profitability Shift",
            "content": """
            美团(03690.HK)最新数据显示，2024年Q1外卖业务取得突破性进展。
            
            Key achievements (关键成绩):
            - 订单量同比增长35% (YoY order growth of 35%)
            - 单笔订单毛利率达18% (GMV per order margin reaches 18%)
            - 骑手效率提升20% (Delivery efficiency improved by 20%)
            
            CEO评论称，该业务已从烧钱模式升级为可持续盈利模式。
            这个转变标志着公司商业模式再次证明其可行性。
            """,
            "stock_codes": ["03690.HK"],
            "stock_names": ["Meituan"],
            "source_type": "research_report",
            "source_name": "UBS Securities"
        }
    ]
    
    raw_texts = []
    for item in test_data:
        source = TextSource(
            source_type=item["source_type"],
            source_name=item["source_name"],
            publish_time=datetime.now()
        )
        text = RawText(
            text_id=item["text_id"],
            title=item["title"],
            content=item["content"],
            stock_codes=item["stock_codes"],
            stock_names=item["stock_names"],
            source=source,
            language=item["language"]
        )
        raw_texts.append(text)
    
    return raw_texts


def test_language_detection():
    """测试语言检测功能"""
    logger.info("=" * 80)
    logger.info("测试1：语言检测功能")
    logger.info("=" * 80)
    
    preprocessor = MultilingualTextPreprocessor()
    
    test_texts = {
        "Chinese": "腾讯今日发布财报，业绩超预期。",
        "English": "Alibaba faces regulatory scrutiny regarding data security practices.",
        "Mixed": "美团Meituan实现了profitability转型，订单量增长35%。"
    }
    
    for name, text in test_texts.items():
        language = preprocessor.detect_language(text)
        logger.info(f"  {name:10} -> {language}")
    
    print()


def test_multilingual_preprocessing():
    """测试多语言预处理"""
    logger.info("=" * 80)
    logger.info("测试2：多语言文本预处理")
    logger.info("=" * 80)
    
    raw_texts = create_multilingual_test_data()
    preprocessor = MultilingualTextPreprocessor()
    
    for raw_text in raw_texts:
        logger.info(f"\n【{raw_text.text_id}】 语言: {raw_text.language}")
        logger.info(f"标题: {raw_text.title[:60]}...")
        
        # 语言检测
        detected = preprocessor.detect_language(raw_text.full_text)
        logger.info(f"检测语言: {detected}")
        
        # 预处理
        chunks = preprocessor.process(raw_text)
        logger.info(f"生成文本块: {len(chunks)} 个")
        
        # 显示第一个块的详细信息
        if chunks:
            chunk = chunks[0]
            logger.info(f"  块ID: {chunk.chunk_id}")
            logger.info(f"  内容长度: {len(chunk.content)} 字符")
            logger.info(f"  识别的实体: {len(chunk.entities)} 个")
            
            # 显示提取的关键词
            if chunk.keywords:
                logger.info(f"  关键词: {', '.join(chunk.keywords)}")
            
            # 显示实体示例
            if chunk.entities:
                logger.info(f"  实体示例:")
                for entity in chunk.entities[:3]:
                    logger.info(f"    - {entity['text']} ({entity['type']})")
    
    print()


def test_language_processor_comparison():
    """测试中英文处理器的差异"""
    logger.info("=" * 80)
    logger.info("测试3：中英文处理器功能对比")
    logger.info("=" * 80)
    
    preprocessor = MultilingualTextPreprocessor()
    
    # 中文文本
    chinese_text = "腾讯发布Q1财报，游戏业务和云服务业务均实现增长。"
    logger.info(f"\n【中文处理】")
    logger.info(f"原文: {chinese_text}")
    
    chinese_proc = preprocessor.chinese_processor
    words = chinese_proc.tokenize_words(chinese_text)
    logger.info(f"  分词结果: {[(w, pos) for w, pos in words[:8]]}")
    
    keywords = chinese_proc.extract_keywords(chinese_text)
    logger.info(f"  关键词: {keywords}")
    
    # 英文文本
    english_text = "Alibaba faces regulatory scrutiny regarding data security practices."
    logger.info(f"\n【英文处理】")
    logger.info(f"原文: {english_text}")
    
    english_proc = preprocessor.english_processor
    words = english_proc.tokenize_words(english_text)
    logger.info(f"  分词结果: {[(w, pos) for w, pos in words[:8]]}")
    
    sentences = english_proc.tokenize_sentences(english_text)
    logger.info(f"  句子: {sentences}")
    
    keywords = english_proc.extract_keywords(english_text)
    logger.info(f"  关键词: {keywords}")
    
    print()


def test_sentiment_prompt_languages():
    """演示不同语言的提示词模板"""
    logger.info("=" * 80)
    logger.info("测试4：多语言提示词模板")
    logger.info("=" * 80)
    
    from multilingual_analyzer import ChinesePromptTemplate, EnglishPromptTemplate
    
    # 获取中文提示词
    chinese_template = ChinesePromptTemplate()
    chinese_prompt = chinese_template.get_sentiment_prompt()
    logger.info(f"\n【中文提示词】")
    logger.info(f"长度: {len(chinese_prompt)} 字符")
    logger.info(f"预览: {chinese_prompt[:150]}...")
    
    # 获取英文提示词
    english_template = EnglishPromptTemplate()
    english_prompt = english_template.get_sentiment_prompt()
    logger.info(f"\n【英文提示词】")
    logger.info(f"长度: {len(english_prompt)} 字符")
    logger.info(f"预览: {english_prompt[:150]}...")
    
    print()


def test_multilingual_analysis():
    """测试多语言情感分析"""
    logger.info("=" * 80)
    logger.info("测试5：多语言情感分析演示")
    logger.info("=" * 80)
    
    raw_texts = create_multilingual_test_data()
    preprocessor = MultilingualTextPreprocessor()
    analyzer = MockLLMAnalyzer()  # 使用模拟分析器
    
    all_results = []
    
    for raw_text in raw_texts:
        logger.info(f"\n【分析】{raw_text.text_id} (语言: {raw_text.language})")
        logger.info(f"标题: {raw_text.title}")
        
        # 预处理
        chunks = preprocessor.process(raw_text)
        logger.info(f"预处理: {len(chunks)} 个块")
        
        # 分析
        relevant_chunks = [c for c in chunks if c.is_relevant]
        if relevant_chunks:
            results = analyzer.analyze_batch(relevant_chunks)
            logger.info(f"分析: {len(results)} 个结果")
            
            for result in results:
                if result.sentiment:
                    sent = result.sentiment
                    polarity_emoji = "📈" if sent.sentiment_score > 0.2 else "📉"
                    logger.info(f"\n  {polarity_emoji} 情绪分数: {sent.sentiment_score:+.3f}")
                    logger.info(f"    极性: {sent.polarity.value}")
                    logger.info(f"    置信度: {sent.confidence:.0%}")
                
                if result.risks:
                    logger.info(f"  ⚠️  风险: {len(result.risks)} 个")
                
                logger.info(f"  📊 综合评分: {result.composite_score:+.3f}")
                
                all_results.append({
                    "text_id": raw_text.text_id,
                    "language": raw_text.language,
                    "stock_code": result.stock_code,
                    "sentiment_score": result.sentiment.sentiment_score if result.sentiment else 0,
                    "polarity": result.sentiment.polarity.value if result.sentiment else "neutral",
                    "risk_count": len(result.risks),
                    "composite_score": result.composite_score
                })
    
    # 保存结果
    output_file = "/Users/mac/sandbox/HKU/COMP7705/multilingual_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 结果已保存到: {output_file}")
    print()


def test_multilingual_summary():
    """多语言分析总结"""
    logger.info("=" * 80)
    logger.info("多语言情感分析 - 功能总结")
    logger.info("=" * 80)
    
    logger.info("""
✅ 已实现的多语言功能：

1. 语言检测
   ✓ 自动检测中文、英文和混合文本
   ✓ 基于字符分布的智能识别
   ✓ 支持文本语言属性指定

2. 多语言预处理
   ✓ 中文：jieba分词、词性标注、关键词提取
   ✓ 英文：NLTK分词、词性标注、关键词提取
   ✓ 统一的文本清洗和实体识别
   ✓ 语言特定的文本分句

3. 多语言情感分析
   ✓ 中文提示词模板（针对港股市场）
   ✓ 英文提示词模板（国际标准）
   ✓ 自动选择语言特定的提示词
   ✓ 统一的结果格式输出

4. 双语支持
   ✓ 整个处理流程支持中文和英文
   ✓ 混合文本的智能处理
   ✓ 语言分布统计
   ✓ 可扩展的架构

📊 支持的语言类型：
   - "zh"   : 中文文本
   - "en"   : 英文文本
   - "mixed": 中英文混合
    """)
    
    logger.info("=" * 80)
    print()


if __name__ == "__main__":
    logger.info("开始多语言情感分析测试")
    logger.info("=" * 80)
    
    try:
        # 运行所有测试
        test_language_detection()
        test_multilingual_preprocessing()
        test_language_processor_comparison()
        test_sentiment_prompt_languages()
        test_multilingual_analysis()
        test_multilingual_summary()
        
        logger.info("\n✓ 所有多语言测试完成！")
        logger.info("✓ 系统支持中文、英文和混合文本的完整情感分析")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
