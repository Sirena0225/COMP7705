"""
港股舆情分析系统 - 实际使用示例
演示如何使用系统进行真实的舆情分析
"""

import json
from datetime import datetime
from models import RawText, TextSource
from preprocessor import TextPreprocessor
from test_complete_flow import MockLLMAnalyzer

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("HKStockSentimentAnalysis")


def create_real_world_examples():
    """创建真实世界的例子"""
    
    examples = [
        {
            "text_id": "news-20240409-001",
            "title": "腾讯宣布Q1季度创纪录业绩，云服务和游戏业务齐增长",
            "content": """
            腾讯控股(00700.HK)今日发布2024年Q1季度财报，创下多项纪录。
            
            业绩亮点：
            - 总收入为人民币1,595亿元，同比增长6%
            - 净利润为人民币418亿元，同比增长54%
            - 游戏业务收入同比增长15%，国际市场表现强劲
            - 云服务收入同比增长29%，客户增加明显
            
            首席执行官马化腾表示：\"本季度业绩体现了我们在游戏、云计算等核心业务的竞争力。\"
            
            分析师普遍看好腾讯前景，目标价位上调至600港元。
            """,
            "stock_codes": ["00700.HK"],
            "stock_names": ["腾讯控股"],
            "source_type": "announcement",
            "source_name": "披露易"
        },
        {
            "text_id": "news-20240409-002", 
            "title": "阿里巴巴国际业务面临新的监管审查，短期承压",
            "content": """
            阿里巴巴-SW(09988.HK)股价今日下跌3.2%，跌幅超过大盘。
            
            根据行业消息人士爆料，监管部门最近对阿里巴巴的国际业务进行了详细的合规审查。
            涉及范围包括：
            - 跨境电商平台的商品真伪鉴别机制
            - 消费者数据隐私保护
            - 反垄断合规
            
            阿里巴巴表示将积极配合监管部门，并表示不会对业务运营造成重大影响。
            
            但分析师认为，短期内可能面临业务运营调整的风险。监管审查通常需要3-6个月。
            
            多家投行下调了阿里的评级至中性。
            """,
            "stock_codes": ["09988.HK"],
            "stock_names": ["阿里巴巴-SW"],
            "source_type": "news",
            "source_name": "财华社"
        },
        {
            "text_id": "news-20240409-003",
            "title": "美团2024年Q1外卖业务爆炸性增长，利润率创新高",
            "content": """
            美团(03690.HK)最新数据显示，外卖业务实现了显著增长。
            
            关键数据：
            - 2024年Q1订单量同比增长35%
            - 业务收入创历史新高
            - 单笔订单毛利率达到18%（去年同期为14%）
            - 骑手效率提升20%，成本控制良好
            
            该数据表明美团外卖业务已从烧钱模式转向盈利模式。
            
            分析机构纷纷表示，美团外卖业务的成功证明了其商业模式的可持续性。
            该业务预期将成为公司未来的主要利润来源。
            
            美团股价上升2.1%，多家券商上调目标价位。
            """,
            "stock_codes": ["03690.HK"],
            "stock_names": ["美团"],
            "source_type": "research_report",
            "source_name": "瑞银证券"
        },
        {
            "text_id": "news-20240409-004",
            "title": "小米汽车首款车型销售遭遇冷遇，市场需求低于预期",
            "content": """
            小米集团(01810.HK)汽车业务遇冷，首款量产车型SU7的销售表现未达预期。
            
            问题所在：
            - 4月上旬订单量仅为预计目标的60%
            - 竞争对手比亚迪、广汽等推出更有竞争力的产品定价
            - 消费者顾虑包括品质保证、售后服务等
            - 行业内有能品对小米造车团队的实力提出质疑
            
            小米方面回应称，这只是初期调整，市场教育仍需要时间。
            但投资者担忧，汽车业务的巨大资本投入可能面临收益不确定性。
            
            若干基金经理表示，将密切关注小米汽车业务的二季度销售数据。
            
            小米股价下跌4.3%。
            """,
            "stock_codes": ["01810.HK"],
            "stock_names": ["小米集团"],
            "source_type": "news",
            "source_name": "彭博通讯社"
        }
    ]
    
    raw_texts = []
    for item in examples:
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
            source=source
        )
        raw_texts.append(text)
    
    return raw_texts


def analyze_and_report():
    """分析真实世界数据并生成报告"""
    
    logger.info("=" * 80)
    logger.info("港股舆情分析系统 - 实时分析演示")
    logger.info("=" * 80)
    
    # 准备数据
    raw_texts = create_real_world_examples()
    preprocessor = TextPreprocessor()
    analyzer = MockLLMAnalyzer()
    
    # 存储所有分析结果
    all_results = []
    sentiment_by_stock = {}
    
    for raw_text in raw_texts:
        logger.info(f"\n【处理文本】 {raw_text.text_id}")
        logger.info(f"标题：{raw_text.title}")
        logger.info(f"来源：{raw_text.source.source_name}")
        
        # 预处理
        chunks = preprocessor.process(raw_text)
        logger.info(f"→ 预处理：生成 {len(chunks)} 个文本块")
        
        # 分析
        relevant_chunks = [c for c in chunks if c.is_relevant]
        if relevant_chunks:
            results = analyzer.analyze_batch(relevant_chunks)
            
            for result in results:
                logger.info(f"\n【分析结果】 {result.stock_code}")
                
                # 情绪分析
                if result.sentiment:
                    sent = result.sentiment
                    polarity_emoji = "📈" if sent.sentiment_score > 0.2 else "📉" if sent.sentiment_score < -0.2 else "→"
                    logger.info(f"{polarity_emoji} 情绪分数: {sent.sentiment_score:+.3f}")
                    logger.info(f"  极性: {sent.polarity.value}")
                    logger.info(f"  置信度: {sent.confidence:.1%}")
                    logger.info(f"  分类维度:")
                    for dim, score in sent.categories.items():
                        logger.info(f"    - {dim}: {score:+.1f}")
                
                # 风险分析
                if result.risks:
                    logger.info(f"⚠️  风险警报 ({len(result.risks)} 个):")
                    for risk in result.risks:
                        level_emoji = "🔴" if risk.risk_level.value == "red" else "🟡" if risk.risk_level.value == "yellow" else "🟢"
                        logger.info(f"  {level_emoji} {risk.risk_title}")
                        logger.info(f"     类型: {risk.risk_category.value}")
                        logger.info(f"     分数: {risk.risk_score:.2f}")
                
                # 综合评分
                logger.info(f"📊 综合评分: {result.composite_score:+.3f}")
                
                # 添加到结果集
                all_results.append({
                    "stock_code": result.stock_code,
                    "stock_name": raw_text.stock_names[0] if raw_text.stock_names else "",
                    "text_id": raw_text.text_id,
                    "sentiment_score": result.sentiment.sentiment_score if result.sentiment else 0,
                    "polarity": result.sentiment.polarity.value if result.sentiment else "neutral",
                    "risk_count": len(result.risks),
                    "composite_score": result.composite_score,
                    "title": raw_text.title
                })
                
                # 按股票统计
                if result.stock_code not in sentiment_by_stock:
                    sentiment_by_stock[result.stock_code] = []
                sentiment_by_stock[result.stock_code].append(result.composite_score)
    
    # 生成总结报告
    logger.info("\n" + "=" * 80)
    logger.info("舆情分析总结报告")
    logger.info("=" * 80)
    
    logger.info("\n【股票情绪汇总】")
    logger.info(f"{'股票代码':<12} {'股票名称':<10} {'情绪分数':<10} {'综合评分':<10} {'前景':<10}")
    logger.info("-" * 52)
    
    for stock_code, scores in sentiment_by_stock.items():
        avg_sentiment = sum(scores) / len(scores) if scores else 0
        stock_name = next((r["stock_name"] for r in all_results if r["stock_code"] == stock_code), "")
        
        if avg_sentiment > 0.2:
            outlook = "👍 看好"
        elif avg_sentiment < -0.2:
            outlook = "👎 看衰"
        else:
            outlook = "➡️  中性"
        
        logger.info(f"{stock_code:<12} {stock_name:<10} {avg_sentiment:+.3f}      {avg_sentiment:+.3f}      {outlook:<10}")
    
    # 风险统计
    logger.info("\n【风险识别统计】")
    risk_count = sum(r["risk_count"] for r in all_results)
    high_risk = sum(1 for r in all_results if r["composite_score"] < -0.2)
    neutral_risk = sum(1 for r in all_results if -0.2 <= r["composite_score"] <= 0.2)
    low_risk = sum(1 for r in all_results if r["composite_score"] > 0.2)
    
    logger.info(f"总报告数: {len(all_results)}")
    logger.info(f"风险警报数: {risk_count}")
    logger.info(f"高风险报告: {high_risk} 篇")
    logger.info(f"中性报告: {neutral_risk} 篇")
    logger.info(f"低风险报告: {low_risk} 篇")
    
    # 保存详细结果
    output_file = "/Users/mac/sandbox/HKU/COMP7705/analysis_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "analysis_count": len(all_results),
            "summary": {
                "total_reports": len(all_results),
                "risk_alerts": risk_count,
                "high_risk_count": high_risk,
                "neutral_count": neutral_risk,
                "low_risk_count": low_risk
            },
            "stock_sentiment": {
                code: {
                    "avg_score": sum(scores) / len(scores),
                    "samples": len(scores)
                }
                for code, scores in sentiment_by_stock.items()
            },
            "detailed_results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n✅ 详细报告已保存到: {output_file}")
    logger.info("=" * 80)
    
    return all_results, sentiment_by_stock


if __name__ == "__main__":
    try:
        results, stocks = analyze_and_report()
        logger.info("\n✓ 分析完成！")
    except Exception as e:
        logger.error(f"✗ 分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
