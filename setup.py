#!/usr/bin/env python3
"""
港股舆情分析系统 - 快速安装脚本 (Python 版本)
适用于 Windows/Mac/Linux
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description=""):
    """运行命令并捕获错误"""
    if description:
        print(f"\n📝 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ 命令失败: {cmd}")
            print(result.stderr)
            return False
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False

def create_directory(path):
    """创建目录"""
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {path}")
    else:
        print(f"✅ 目录已存在: {path}")

def create_env_file():
    """创建 .env 文件"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print("✅ .env 文件已创建（从 .env.example 复制）")
        else:
            print("⚠️  .env.example 文件不存在")
            return False
    else:
        print("✅ .env 文件已存在")
    
    return True

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    print(f"\n📝 Python 版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 需要 Python 3.8 或更高版本")
        return False
    
    print("✅ Python 版本满足要求")
    return True

def install_dependencies():
    """安装依赖"""
    print("\n📦 安装项目依赖...")
    
    # 升级 pip
    print("\n   升级 pip...")
    run_command(f"{sys.executable} -m pip install --upgrade pip", "")
    
    # 安装 requirements.txt
    if os.path.exists("requirements.txt"):
        print("\n   安装 requirements.txt 中的依赖...")
        return run_command(f"{sys.executable} -m pip install -r requirements.txt", "")
    else:
        print("❌ requirements.txt 文件不存在")
        return False

def setup_directories():
    """设置必要的目录"""
    print("\n📁 创建必要的目录...")
    
    directories = [
        "data/chroma_db",
        "logs",
        "online_test_results"
    ]
    
    for directory in directories:
        create_directory(directory)

def check_api_keys():
    """检查 API 密钥配置"""
    print("\n🔍 检查 API 密钥配置...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env 文件不存在")
        return False
    
    with open(env_file, "r") as f:
        content = f.read()
    
    if "sk-xxxxx" in content:
        print("⚠️  检测到 .env 中仍有默认的占位符")
        print("\n   请在 .env 中填入实际的 API Key:")
        print("\n   1️⃣  DeepSeek (推荐)")
        print("      LLM_API_KEY=sk-xxxxx-your-key-xxxxx")
        print("      获取: https://platform.deepseek.com")
        print("\n   2️⃣  OpenAI")
        print("      OPENAI_API_KEY=sk-xxxxx-your-key-xxxxx")
        print("      获取: https://platform.openai.com/api-keys")
        return False
    
    if "LLM_API_KEY=" in content or "OPENAI_API_KEY=" in content:
        print("✅ API 密钥已配置")
        return True
    
    return False

def test_imports():
    """测试关键库的导入"""
    print("\n✅ 测试关键库导入...")
    
    required_libs = [
        ("openai", "OpenAI API 客户端"),
        ("dotenv", "环境变量管理"),
        ("jieba", "中文分词"),
        ("nltk", "英文处理"),
    ]
    
    for lib_name, description in required_libs:
        try:
            __import__(lib_name)
            print(f"   ✅ {description} ({lib_name})")
        except ImportError:
            print(f"   ❌ {description} ({lib_name}) - 未安装")
            return False
    
    return True

def main():
    """主流程"""
    print("=" * 60)
    print("港股舆情分析系统 - 环境安装")
    print("=" * 60)
    
    # 检查 Python 版本
    if not check_python_version():
        return False
    
    # 安装依赖
    print("\n" + "=" * 60)
    print("步骤 1: 安装依赖")
    print("=" * 60)
    if not install_dependencies():
        print("\n❌ 依赖安装失败")
        return False
    
    # 测试导入
    print("\n" + "=" * 60)
    print("步骤 2: 测试关键库")
    print("=" * 60)
    if not test_imports():
        print("\n❌ 关键库导入失败")
        return False
    
    # 设置目录
    print("\n" + "=" * 60)
    print("步骤 3: 创建目录")
    print("=" * 60)
    setup_directories()
    
    # 创建 .env
    print("\n" + "=" * 60)
    print("步骤 4: 配置环境变量")
    print("=" * 60)
    if not create_env_file():
        return False
    
    # 检查 API 密钥
    print("\n" + "=" * 60)
    print("步骤 5: 检查 API 密钥")
    print("=" * 60)
    has_api_keys = check_api_keys()
    
    # 完成
    print("\n" + "=" * 60)
    print("✅ 安装完成！")
    print("=" * 60)
    
    print("\n📋 后续步骤:")
    
    if not has_api_keys:
        print("\n1️⃣  配置 API Key")
        print("   编辑 .env 文件，填入实际的 API 密钥")
        print("   获取方式:")
        print("   - DeepSeek: https://platform.deepseek.com")
        print("   - OpenAI: https://platform.openai.com/api-keys")
    
    print("\n2️⃣  测试 LLM 集成")
    print("   python setup_llm.py")
    
    print("\n3️⃣  运行演示")
    print("   python demo_online_testing.py")
    
    print("\n4️⃣  启动标注应用")
    print("   streamlit run annotation_app.py")
    
    print("\n📚 文档:")
    print("   快速开始: ONLINE_TESTING_QUICKSTART.md")
    print("   完整设计: ONLINE_TESTING_GUIDE.md")
    print("   项目导航: README_ONLINE_TESTING.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
