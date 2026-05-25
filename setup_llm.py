"""
==========================================================
真实 LLM API 集成测试
演示实际调用 DeepSeek 或 OpenAI API 进行港股舆情分析
==========================================================
"""

import os
import sys
import json
from dotenv import load_dotenv
import logging
from datetime import datetime

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LLMIntegrationTest")

# ============================================================
# 快速诊断
# ============================================================

def check_environment():
    """检查环境配置是否正确"""
    logger.info("=" * 60)
    logger.info("环境诊断")
    logger.info("=" * 60)
    
    # 检查 API Key
    llm_api_key = os.getenv("LLM_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not llm_api_key and not openai_api_key:
        logger.error("❌ 未配置 API Key")
        logger.error("请设置环境变量:")
        logger.error("  export LLM_API_KEY='your-key'    # 用于 DeepSeek")
        logger.error("  或")
        logger.error("  export OPENAI_API_KEY='your-key' # 用于 OpenAI")
        return False
    
    if llm_api_key and llm_api_key.startswith("sk-"):
        logger.info(f"✅ LLM_API_KEY: {llm_api_key[:20]}...")
    else:
        logger.warning(f"⚠️  LLM_API_KEY 格式可能不正确")
    
    if openai_api_key and openai_api_key.startswith("sk-"):
        logger.info(f"✅ OPENAI_API_KEY: {openai_api_key[:20]}...")
    
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    logger.info(f"✅ 使用模型: {model}")
    
    return True


def test_deepseek_api():
    """测试 DeepSeek API 连接"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 DeepSeek API")
    logger.info("=" * 60)
    
    try:
        import openai
        
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            logger.error("❌ LLM_API_KEY 未设置")
            return False
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        logger.info("📤 发送测试请求到 DeepSeek...")
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是金融分析师，用JSON回应"},
                {"role": "user", "content": """分析这段港股新闻的情绪。严格按以下JSON格式回应，不要额外说明：
{
  "sentiment_score": 0.5,
  "confidence": 0.8,
  "polarity": "neutral"
}
新闻内容：腾讯Q1财报超预期，收入增长6%，净利润增长54%。"""}
            ],
            temperature=0.1,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        logger.info(f"✅ API 连接成功!")
        logger.info(f"   响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        logger.info(f"   Token 用量: {response.usage.total_tokens}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ API 调用失败: {str(e)}")
        logger.error(f"   错误类型: {type(e).__name__}")
        return False


def test_openai_api():
    """测试 OpenAI API 连接 (备选)"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 OpenAI API (备选)")
    logger.info("=" * 60)
    
    try:
        import openai
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("⚠️  OPENAI_API_KEY 未设置，跳过此测试")
            return None
        
        client = openai.OpenAI(api_key=api_key)
        
        logger.info("📤 发送测试请求到 OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst, respond in JSON"},
                {"role": "user", "content": """Analyze the sentiment of this HK stock news. Respond strictly in JSON format:
{
  "sentiment_score": 0.5,
  "confidence": 0.8,
  "polarity": "neutral"
}
News: Tencent Q1 results beat expectations, revenue up 6%, net profit up 54%."""}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        # 尝试提取 JSON
        try:
            result = json.loads(content)
        except:
            # 如果不是纯 JSON，尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"raw_response": content}
        
        logger.info(f"✅ OpenAI API 连接成功!")
        logger.info(f"   响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        logger.info(f"   Token 用量: {response.usage.total_tokens}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ OpenAI API 调用失败: {str(e)}")
        return False


def test_multilingual_analysis():
    """测试多语言情感分析"""
    logger.info("\n" + "=" * 60)
    logger.info("测试多语言情感分析")
    logger.info("=" * 60)
    
    try:
        from multilingual_analyzer import MultilingualSentimentAnalyzer
        from multilingual_preprocessor import MultilingualTextPreprocessor
        from models import ProcessedChunk
        
        # 初始化
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            logger.error("❌ 缺少 API Key")
            return False
        
        logger.info("初始化多语言分析器...")
        analyzer = MultilingualSentimentAnalyzer(
            model_name="deepseek-chat",
            api_key=api_key
        )
        
        preprocessor = MultilingualTextPreprocessor()
        
        # 测试中文文本
        logger.info("\n📝 测试中文文本...")
        chinese_text = "腾讯Q1财报超预期，游戏业务增长15%，云服务收入增长29%。分析师上调目标价。"
        
        chunks = preprocessor.process(chinese_text)
        if chunks:
            chunk = chunks[0]
            logger.info(f"   原文: {chunk.content[:50]}...")
            logger.info(f"   语言: {chunk.language}")
            
            logger.info("   调用 LLM 进行分析...")
            result = analyzer.analyze_sentiment(chunk, language="zh")
            
            logger.info(f"✅ 中文分析完成:")
            logger.info(f"   情感分数: {result.sentiment_score:.2f}")
            logger.info(f"   极性: {result.polarity}")
            logger.info(f"   置信度: {result.confidence:.2f}")
            logger.info(f"   关键短语: {', '.join(result.key_phrases)}")
        
        # 测试英文文本
        logger.info("\n📝 测试英文文本...")
        english_text = "Alibaba announced a major strategic shift. The company will focus on cloud services and domestic consumption. Analysts are cautiously optimistic about the new direction."
        
        chunks = preprocessor.process(english_text)
        if chunks:
            chunk = chunks[0]
            logger.info(f"   原文: {chunk.content[:50]}...")
            logger.info(f"   语言: {chunk.language}")
            
            logger.info("   调用 LLM 进行分析...")
            result = analyzer.analyze_sentiment(chunk, language="en")
            
            logger.info(f"✅ 英文分析完成:")
            logger.info(f"   情感分数: {result.sentiment_score:.2f}")
            logger.info(f"   极性: {result.polarity}")
            logger.info(f"   置信度: {result.confidence:.2f}")
            logger.info(f"   关键短语: {', '.join(result.key_phrases)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 多语言分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    logger.info("\n" + "🚀 " * 30)
    logger.info("港股舆情分析系统 - LLM API 真实集成测试")
    logger.info("🚀 " * 30)
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 第1步: 环境诊断
    if not check_environment():
        logger.error("\n❌ 环境配置不完整，无法继续")
        logger.info("\n快速修复步骤:")
        logger.info("1. 复制 .env.example 为 .env")
        logger.info("2. 在 .env 中填入真实的 API Key:")
        logger.info("   LLM_API_KEY=sk-xxxxx  (DeepSeek)")
        logger.info("   或")
        logger.info("   OPENAI_API_KEY=sk-xxxxx  (OpenAI)")
        logger.info("3. 运行: python setup.py")
        return False
    
    # 第2步: 安装依赖
    logger.info("\n" + "=" * 60)
    logger.info("检查依赖")
    logger.info("=" * 60)
    
    try:
        import openai
        logger.info(f"✅ openai: {openai.__version__}")
    except ImportError:
        logger.error("❌ openai 未安装")
        logger.info("   运行: pip install -r requirements.txt")
        return False
    
    # 第3步: 测试 API 连接
    deepseek_ok = test_deepseek_api()
    openai_ok = test_openai_api()
    
    if not deepseek_ok and not openai_ok:
        logger.error("\n❌ 两个 API 都无法连接")
        return False
    
    # 第4步: 测试多语言分析
    if not test_multilingual_analysis():
        logger.error("\n❌ 多语言分析测试失败")
        return False
    
    # 成功
    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有测试通过！系统已成功集成真实 LLM API")
    logger.info("=" * 60)
    logger.info("\n后续步骤:")
    logger.info("1. 运行演示: python demo_online_testing.py")
    logger.info("2. 启动标注应用: streamlit run annotation_app.py")
    logger.info("3. 查看文档: ONLINE_TESTING_QUICKSTART.md")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
