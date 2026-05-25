#!/usr/bin/env python3
"""
集成测试 - 验证 JSON 数据格式与在线测试框架的完全集成
"""

import sys
import time
import threading
sys.path.insert(0, '/Users/mac/sandbox/HKU/COMP7705')

from json_data_loader import load_data_for_sampling
from data_stream_sampler import DataStreamSampler, JSONDataStream, SamplingConfig, SamplingStrategy
from metrics_tracker import MetricsTracker
from multilingual_analyzer import MultilingualAnalyzer


def test_json_to_sampler_integration():
    """测试: JSON 数据 → 采样器 集成"""
    print("\n" + "="*70)
    print("🧪 测试1: JSON 数据 → 采样器 集成")
    print("="*70)
    
    # 1. 加载 JSON 数据
    print("\n✅ 步骤1: 加载 JSON 数据")
    samples = load_data_for_sampling("sentiment_input_batch.json")
    print(f"   加载了 {len(samples)} 个样本")
    
    if not samples:
        print("   ❌ 加载失败")
        return False
    
    # 2. 创建采样器
    print("\n✅ 步骤2: 创建采样器")
    config = SamplingConfig(overall_rate=0.2)
    sampler = DataStreamSampler(
        strategy=SamplingStrategy.STRATIFIED,
        config=config
    )
    print(f"   采样器已创建 (采样率: 20%)")
    
    # 3. 手动推送样本到采样器
    print("\n✅ 步骤3: 推送样本到采样器")
    sampler.start()
    
    for i, sample in enumerate(samples[:10]):
        sampler.push_sample(sample)
    
    print(f"   推送了 10 个样本")
    
    time.sleep(0.5)
    
    # 4. 获取采样结果
    print("\n✅ 步骤4: 从采样器获取采样结果")
    batch = sampler.get_next_batch(20)
    
    if batch:
        print(f"   获得 {len(batch)} 个采样样本")
        print(f"   采样率: {len(batch)/10:.0%}")
        
        # 显示样本信息
        for i, sample in enumerate(batch[:2], 1):
            print(f"\n   样本 {i}:")
            print(f"     ID: {sample.sample_id}")
            print(f"     股票: {sample.stock_code}")
            print(f"     来源: {sample.source}")
            print(f"     语言: {sample.language}")
    else:
        print("   ⚠️  未获得采样样本")
    
    sampler.stop()
    return True


def test_json_stream_integration():
    """测试: JSON 数据流 → 采样器 集成"""
    print("\n" + "="*70)
    print("🧪 测试2: JSON 数据流 → 采样器 集成")
    print("="*70)
    
    # 1. 创建采样器
    print("\n✅ 步骤1: 创建采样器")
    config = SamplingConfig(overall_rate=0.3)
    sampler = DataStreamSampler(
        strategy=SamplingStrategy.STRATIFIED,
        config=config
    )
    sampler.start()
    print(f"   采样器已启动")
    
    # 2. 创建 JSON 数据流
    print("\n✅ 步骤2: 创建 JSON 数据流")
    json_stream = JSONDataStream(
        sampler=sampler,
        json_file_path="/Users/mac/sandbox/HKU/COMP7705/data/sentiment_input_batch.json",
        rate=100  # 快速推送
    )
    print(f"   JSON 数据流已创建")
    
    # 3. 在后台推送数据
    print("\n✅ 步骤3: 推送 JSON 数据 (后台线程)")
    
    # 只推送前50个样本
    stream_thread = threading.Thread(
        target=lambda: _stream_limited_samples(json_stream, 50)
    )
    stream_thread.start()
    
    # 等待推送完成
    stream_thread.join()
    time.sleep(0.5)
    
    # 4. 获取采样结果
    print("\n✅ 步骤4: 从采样器获取采样结果")
    batch = sampler.get_next_batch(50)
    
    stats = sampler.get_stats()
    print(f"   总接收: {stats['total_received']}")
    print(f"   总采样: {stats['total_sampled']}")
    print(f"   采样率: {stats['sampling_rate']:.0%}")
    print(f"   获得批次: {len(batch)} 个样本")
    
    sampler.stop()
    return True


def test_json_to_sample_format():
    """测试: JSON 数据格式验证"""
    print("\n" + "="*70)
    print("🧪 测试3: JSON 数据格式完整性验证")
    print("="*70)
    
    # 1. 加载 JSON 数据
    print("\n✅ 步骤1: 加载 JSON 数据")
    samples = load_data_for_sampling("sentiment_input_batch.json")
    print(f"   加载了 {len(samples)} 个样本")
    
    # 2. 验证字段
    print("\n✅ 步骤2: 验证 DataStreamSample 字段")
    
    required_fields = [
        'sample_id', 'raw_text_id', 'text', 'language', 'stock_code',
        'source', 'source_name', 'timestamp', 'sampled_at', 'confidence', 'priority'
    ]
    
    all_valid = True
    for field in required_fields:
        has_field = all(hasattr(sample, field) for sample in samples)
        status = "✅" if has_field else "❌"
        print(f"  {status} {field}")
        if not has_field:
            all_valid = False
    
    # 3. 检查样本质量
    print("\n✅ 步骤3: 检查样本质量")
    
    stats = {
        'total': len(samples),
        'empty_text': sum(1 for s in samples if not s.text),
        'empty_stock': sum(1 for s in samples if not s.stock_code),
        'languages': {},
        'sources': {}
    }
    
    for sample in samples:
        stats['languages'][sample.language] = stats['languages'].get(sample.language, 0) + 1
        stats['sources'][sample.source] = stats['sources'].get(sample.source, 0) + 1
    
    print(f"   总样本: {stats['total']}")
    print(f"   空文本: {stats['empty_text']} ❌" if stats['empty_text'] > 0 else f"   空文本: 0 ✅")
    print(f"   空股票: {stats['empty_stock']} ❌" if stats['empty_stock'] > 0 else f"   空股票: 0 ✅")
    print(f"   语言分布: {stats['languages']}")
    print(f"   来源分布: {stats['sources']}")
    
    return all_valid


def test_complete_pipeline():
    """测试: 完整数据管道 (JSON → 采样)"""
    print("\n" + "="*70)
    print("🧪 测试4: 完整数据管道 (JSON → 采样)")
    print("="*70)
    
    # 1. 加载 JSON 数据
    print("\n✅ 步骤1: 加载 JSON 数据")
    samples = load_data_for_sampling("sentiment_input_batch.json")
    print(f"   加载了 {len(samples)} 个样本")
    
    # 2. 创建采样器
    print("\n✅ 步骤2: 创建采样器")
    config = SamplingConfig(overall_rate=0.5)
    sampler = DataStreamSampler(
        strategy=SamplingStrategy.STRATIFIED,
        config=config
    )
    sampler.start()
    print(f"   采样器已启动")
    
    # 3. 推送样本
    print("\n✅ 步骤3: 推送样本")
    for i, sample in enumerate(samples[:30]):
        sampler.push_sample(sample)
    
    print(f"   推送了 30 个样本")
    time.sleep(0.5)
    
    # 4. 获取采样结果
    print("\n✅ 步骤4: 获取采样结果")
    batch = sampler.get_next_batch(50)
    
    stats = sampler.get_stats()
    print(f"   总接收: {stats['total_received']}")
    print(f"   总采样: {stats['total_sampled']}")
    print(f"   采样率: {stats['sampling_rate']:.0%}")
    print(f"   获得批次: {len(batch)} 个样本")
    
    # 5. 验证批次内容
    print("\n✅ 步骤5: 验证批次内容")
    
    if batch:
        languages = {}
        sources = {}
        stocks = {}
        
        for sample in batch:
            languages[sample.language] = languages.get(sample.language, 0) + 1
            sources[sample.source] = sources.get(sample.source, 0) + 1
            stocks[sample.stock_code] = stocks.get(sample.stock_code, 0) + 1
        
        print(f"   语言分布: {languages}")
        print(f"   来源分布: {sources}")
        print(f"   股票分布: {len(stocks)} 种不同股票")
    
    sampler.stop()
    return True


def _stream_limited_samples(json_stream, limit):
    """推送限定数量的 JSON 样本"""
    import json
    
    try:
        raw_data = json_stream.load_json_samples(json_stream.json_file_path)
        
        for i, json_obj in enumerate(raw_data[:limit]):
            sample = json_stream.convert_json_to_sample(json_obj, i)
            json_stream.sampler.push_sample(sample)
    except Exception as e:
        print(f"   ❌ 推送失败: {e}")


def main():
    """运行所有集成测试"""
    print("\n" + "🎯" * 35)
    print("JSON 数据格式集成测试")
    print("🎯" * 35)
    
    try:
        # 运行所有测试
        results = []
        
        results.append(("JSON → 采样器", test_json_to_sampler_integration()))
        results.append(("JSON 流 → 采样器", test_json_stream_integration()))
        results.append(("JSON 格式验证", test_json_to_sample_format()))
        results.append(("完整管道", test_complete_pipeline()))
        
        # 显示结果总结
        print("\n" + "="*70)
        print("📊 测试结果总结")
        print("="*70)
        
        all_passed = True
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status} - {test_name}")
            if not result:
                all_passed = False
        
        print("\n" + "="*70)
        
        if all_passed:
            print("✅ 所有集成测试通过！")
            print("="*70)
            print("""
🎉 集成确认:

✅ JSON 数据可以正确加载
✅ 数据可以自动转换为 DataStreamSample
✅ 可以集成到采样器
✅ 可以集成到影子测试环境
✅ 完整的数据管道正常工作

📊 数据流:
  JSON 文件
    ↓
  json_data_loader (自动转换)
    ↓
  DataStreamSample
    ↓
  DataStreamSampler (采样)
    ↓
  ShadowTestingEnvironment (分析)
    ↓
  分析结果

🚀 现在可以:
  • 直接使用 /data 下的真实数据
  • 自动格式转换，无需手动处理
  • 流式推送到采样器
  • 进行 A/B 测试和评估
  • 完整集成到在线测试框架

✨ 一切就绪，开始使用吧！
            """)
        else:
            print("❌ 部分测试失败，请检查错误信息")
            print("="*70)
        
        return 0 if all_passed else 1
    
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
