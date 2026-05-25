#!/usr/bin/env python3
"""
港股舆情分析系统 - 快速诊断工具
检查环境配置、依赖、API 密钥等
"""

import os
import sys
import platform
from pathlib import Path
from dotenv import load_dotenv

def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"📋 {text}")
    print(f"{'='*60}")

def print_section(text):
    """打印小标题"""
    print(f"\n📝 {text}")
    print("-" * 40)

def check_mark(condition, text):
    """打印检查标记"""
    mark = "✅" if condition else "❌"
    print(f"  {mark} {text}")
    return condition

def diagnose():
    """完整诊断"""
    print_header("港股舘情分析系统 - 快速诊断")
    
    success = True
    
    # 1. Python 环境
    print_section("1️⃣  Python 环境")
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  Python 版本: {version}")
    print(f"  操作系统: {platform.system()} {platform.release()}")
    print(f"  Python 执行文件: {sys.executable}")
    
    if sys.version_info < (3, 8):
        check_mark(False, "Python 版本过低 (需要 3.8+)")
        success = False
    else:
        check_mark(True, "Python 版本符合要求")
    
    # 2. 项目文件
    print_section("2️⃣  项目文件")
    required_files = {
        ".env.example": "环境变量模板",
        "requirements.txt": "依赖包列表",
        "multilingual_analyzer.py": "多语言分析器",
        "online_test_framework.py": "在线测试框架",
        "demo_online_testing.py": "演示程序"
    }
    
    for filename, desc in required_files.items():
        exists = Path(filename).exists()
        check_mark(exists, f"{filename} ({desc})")
        if not exists:
            success = False
    
    # 3. 环境变量配置
    print_section("3️⃣  环境变量配置")
    load_dotenv()
    
    env_vars = {
        "LLM_API_KEY": "LLM API 密钥",
        "LLM_MODEL": "LLM 模型名称",
        "OPENAI_API_KEY": "OpenAI API 密钥 (可选)",
    }
    
    configured = False
    for var_name, desc in env_vars.items():
        value = os.getenv(var_name)
        if value:
            # 隐藏大部分密钥
            if "KEY" in var_name and len(value) > 20:
                display = f"{value[:10]}...{value[-10:]}"
            else:
                display = value
            check_mark(True, f"{var_name}: {display}")
            configured = True
        else:
            check_mark(False, f"{var_name}: 未设置")
    
    if not configured:
        print("  ⚠️  提示: 运行 'cp .env.example .env' 创建配置文件")
        success = False
    
    # 4. Python 依赖
    print_section("4️⃣  Python 依赖")
    required_packages = {
        "openai": "OpenAI/DeepSeek API 客户端",
        "dotenv": "环境变量管理",
        "jieba": "中文分词",
        "nltk": "英文处理",
        "pandas": "数据处理",
        "streamlit": "Web 应用框架",
        "chromadb": "向量数据库",
    }
    
    missing_packages = []
    for package_name, desc in required_packages.items():
        try:
            __import__(package_name)
            check_mark(True, f"{package_name} ({desc})")
        except ImportError:
            check_mark(False, f"{package_name} ({desc}) - 未安装")
            missing_packages.append(package_name)
            success = False
    
    if missing_packages:
        print(f"\n  💡 安装缺失的包:")
        print(f"     pip install {' '.join(missing_packages)}")
    
    # 5. 目录结构
    print_section("5️⃣  目录结构")
    directories = {
        "data": "数据存储目录",
        "logs": "日志目录",
        "online_test_results": "测试结果目录",
    }
    
    for dirname, desc in directories.items():
        exists = Path(dirname).exists()
        check_mark(exists, f"{dirname}/ ({desc})")
        if not exists:
            try:
                Path(dirname).mkdir(parents=True, exist_ok=True)
                print(f"       → 已创建")
            except Exception as e:
                print(f"       → 创建失败: {e}")
                success = False
    
    # 6. LLM API 测试 (如果配置了)
    print_section("6️⃣  LLM API 连接")
    api_key = os.getenv("LLM_API_KEY")
    
    if not api_key:
        check_mark(False, "LLM_API_KEY 未设置")
        print("  💡 提示: 设置环境变量以启用真实 API 调用")
        success = False
    else:
        check_mark(True, "LLM_API_KEY 已配置")
        
        # 尝试导入并初始化分析器
        try:
            from multilingual_analyzer import MultilingualSentimentAnalyzer
            analyzer = MultilingualSentimentAnalyzer(
                model_name=os.getenv("LLM_MODEL", "deepseek-chat"),
                api_key=api_key
            )
            check_mark(True, "多语言分析器已初始化")
        except Exception as e:
            check_mark(False, f"分析器初始化失败: {str(e)[:50]}...")
            success = False
    
    # 7. 文件权限
    print_section("7️⃣  文件权限")
    
    # 检查 .env 是否在 .gitignore
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        with open(gitignore_path) as f:
            gitignore_content = f.read()
        
        check_mark(".env" in gitignore_content, ".env 已在 .gitignore 中")
    else:
        check_mark(False, ".gitignore 不存在")
        success = False
    
    # 8. 推荐的后续步骤
    print_section("📋 推荐的后续步骤")
    
    if not configured:
        print("  1. 配置 LLM API 密钥:")
        print("     cp .env.example .env")
        print("     # 编辑 .env，填入 API Key")
        print()
    
    if missing_packages:
        print(f"  2. 安装缺失的依赖:")
        print(f"     pip install -r requirements.txt")
        print()
    
    print("  3. 测试 LLM 集成:")
    print("     python setup_llm.py")
    print()
    
    print("  4. 运行演示程序:")
    print("     python demo_online_testing.py")
    print()
    
    print("  5. 启动标注应用:")
    print("     streamlit run annotation_app.py")
    print()
    
    # 最终结果
    print_header("诊断结果")
    if success:
        print("✅ 系统配置正常，所有检查通过！")
        print("\n下一步: python setup_llm.py 测试 LLM API 连接")
        return True
    else:
        print("❌ 发现配置问题，请根据上面的提示进行修复")
        print("\n查看更多帮助: LLM_INTEGRATION_GUIDE.md")
        return False

def main():
    """主函数"""
    try:
        success = diagnose()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  诊断已中止")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 诊断过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
