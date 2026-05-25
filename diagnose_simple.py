#!/usr/bin/env python3
"""
港股舘情分析系统 - 快速诊断工具 (最小版本)
"""

import os
import sys
import platform
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"📋 {text}")
    print(f"{'='*60}")

def print_section(text):
    print(f"\n📝 {text}")
    print("-" * 40)

def check_mark(condition, text):
    mark = "✅" if condition else "❌"
    print(f"  {mark} {text}")
    return condition

def diagnose():
    print_header("港股舘情分析系统 - 快速诊断")
    
    success = True
    
    # 1. Python 环境
    print_section("1️⃣  Python 环境")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  Python 版本: {version}")
    print(f"  操作系统: {platform.system()}")
    
    if sys.version_info < (3, 8):
        check_mark(False, "Python 版本过低 (需要 3.8+)")
        success = False
    else:
        check_mark(True, "Python 版本符合要求 (3.8+)")
    
    # 2. 项目文件
    print_section("2️⃣  项目文件")
    required_files = [
        ".env.example",
        "requirements.txt",
        ".gitignore",
        "multilingual_analyzer.py",
        "online_test_framework.py",
        "shadow_testing_env.py",
        "demo_online_testing.py",
        "setup_llm.py"
    ]
    
    for filename in required_files:
        exists = Path(filename).exists()
        check_mark(exists, filename)
        if not exists:
            success = False
    
    # 3. 环境变量
    print_section("3️⃣  环境变量配置")
    
    llm_api_key = os.getenv("LLM_API_KEY")
    llm_model = os.getenv("LLM_MODEL", "deepseek-chat")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if llm_api_key:
        display = f"{llm_api_key[:10]}...{llm_api_key[-10:]}"
        check_mark(True, f"LLM_API_KEY: {display}")
    else:
        check_mark(False, "LLM_API_KEY: 未设置")
        success = False
    
    check_mark(True, f"LLM_MODEL: {llm_model}")
    
    if openai_key:
        display = f"{openai_key[:10]}...{openai_key[-10:]}"
        check_mark(True, f"OPENAI_API_KEY: {display}")
    else:
        check_mark(False, "OPENAI_API_KEY: 未设置 (可选)")
    
    # 4. 重要文档
    print_section("4️⃣  文档文件")
    doc_files = [
        ("LLM_INTEGRATION_GUIDE.md", "LLM 集成指南"),
        ("LLM_INTEGRATION_SUMMARY.md", "集成总结"),
        ("README_ONLINE_TESTING.md", "项目导航"),
        ("ONLINE_TESTING_QUICKSTART.md", "快速开始"),
    ]
    
    for filename, desc in doc_files:
        exists = Path(filename).exists()
        check_mark(exists, f"{filename} ({desc})")
    
    # 5. .env 配置
    print_section("5️⃣  .env 文件状态")
    env_exists = Path(".env").exists()
    env_example_exists = Path(".env.example").exists()
    
    if env_exists:
        check_mark(True, ".env 文件已存在")
    else:
        check_mark(False, ".env 文件不存在")
        if env_example_exists:
            print("  💡 提示: 运行 'cp .env.example .env' 创建配置文件")
            success = False
    
    check_mark(env_example_exists, ".env.example 模板文件")
    
    # 6. 安全配置
    print_section("6️⃣  安全配置")
    
    gitignore_exists = Path(".gitignore").exists()
    check_mark(gitignore_exists, ".gitignore 安全配置")
    
    if gitignore_exists:
        with open(".gitignore") as f:
            gitignore_content = f.read()
        check_mark(".env" in gitignore_content, ".env 在 .gitignore 中")
    
    # 7. 快速诊断
    print_section("7️⃣  快速诊断")
    
    if not success and not llm_api_key:
        print("  ⚠️  LLM API 未配置")
        print("     系统将使用 Mock 模型运行演示")
        print("     要启用真实 API，请:")
        print("     1. cp .env.example .env")
        print("     2. 编辑 .env 并填入 API Key")
        success = True  # 允许继续，但在 Mock 模式
    
    # 后续步骤
    print_section("📋 后续步骤")
    
    if not Path(".env").exists():
        print("  1️⃣  创建 .env 配置文件:")
        print("     cp .env.example .env")
        print()
    
    print("  2️⃣  安装依赖:")
    print("     python setup.py  或")
    print("     pip install -r requirements.txt")
    print()
    
    if llm_api_key:
        print("  3️⃣  验证 LLM 集成:")
        print("     python setup_llm.py")
        print()
    
    print("  4️⃣  运行演示:")
    print("     python demo_online_testing.py")
    print()
    
    print("  5️⃣  启动标注应用:")
    print("     streamlit run annotation_app.py")
    print()
    
    # 最终结果
    print_header("诊断结果")
    
    if llm_api_key:
        print("✅ 系统已配置 LLM API")
        print("   运行 'python setup_llm.py' 测试连接")
    else:
        print("⚠️  LLM API 未配置，系统将使用 Mock 模型")
        print("   查看 LLM_INTEGRATION_GUIDE.md 配置真实 API")
    
    print("\n📚 文档:")
    print("   - LLM_INTEGRATION_SUMMARY.md (完成总结)")
    print("   - LLM_INTEGRATION_GUIDE.md (详细指南)")
    print("   - README_ONLINE_TESTING.md (项目导航)")
    
    return True

def main():
    try:
        diagnose()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 诊断失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
