#!/bin/bash

# ============================================================
# 港股舆情分析系统 - 快速安装脚本
# ============================================================

set -e

echo "==============================================="
echo "港股舆情分析系统 - 环境安装"
echo "==============================================="

# 检查 Python 版本
echo -e "\n📝 检查 Python 版本..."
python3 --version

# 创建虚拟环境 (可选)
if [ ! -d "venv" ]; then
    echo -e "\n📦 创建虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ 虚拟环境已创建并激活"
else
    echo -e "\n✅ 虚拟环境已存在"
    source venv/bin/activate
fi

# 升级 pip
echo -e "\n📦 升级 pip..."
python -m pip install --upgrade pip

# 安装依赖
echo -e "\n📦 安装项目依赖..."
pip install -r requirements.txt

# 创建必要的目录
echo -e "\n📁 创建必要的目录..."
mkdir -p data/chroma_db
mkdir -p logs
mkdir -p online_test_results

# 检查和创建 .env 文件
if [ ! -f ".env" ]; then
    echo -e "\n⚙️  创建 .env 文件..."
    cp .env.example .env
    echo "✅ .env 文件已创建，请在其中填入 API Key"
else
    echo -e "\n✅ .env 文件已存在"
fi

# 检查 API Key
echo -e "\n🔍 检查 API 密钥配置..."
if grep -q "sk-xxxxx" .env; then
    echo "⚠️  检测到 .env 中仍有默认的占位符"
    echo "   请在 .env 中填入实际的 API Key:"
    echo ""
    echo "   1. DeepSeek (推荐)"
    echo "      LLM_API_KEY=sk-xxxxx-your-key-xxxxx"
    echo "      获取: https://platform.deepseek.com"
    echo ""
    echo "      或"
    echo ""
    echo "   2. OpenAI"
    echo "      OPENAI_API_KEY=sk-xxxxx-your-key-xxxxx"
    echo "      获取: https://platform.openai.com/api-keys"
    echo ""
else
    echo "✅ API 密钥已配置"
fi

# 完成
echo -e "\n==============================================="
echo "✅ 安装完成！"
echo "==============================================="

echo -e "\n后续步骤:"
echo "1. 配置 API Key"
echo "   编辑 .env 文件，填入实际的 API 密钥"
echo ""
echo "2. 测试 LLM 集成"
echo "   python setup_llm.py"
echo ""
echo "3. 运行演示"
echo "   python demo_online_testing.py"
echo ""
echo "4. 启动标注应用"
echo "   streamlit run annotation_app.py"
echo ""

echo "📚 查看文档: ONLINE_TESTING_QUICKSTART.md"
