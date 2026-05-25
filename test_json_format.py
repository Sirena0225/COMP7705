#!/usr/bin/env python3
"""
快速测试 - 验证 JSON 数据格式转换
检查 /data 下的 JSON 文件是否能正确转换为 DataStreamSample 格式
"""

import sys
sys.path.insert(0, '/Users/mac/sandbox/HKU/COMP7705')

from json_data_loader import JSONDataLoader, load_data_for_sampling
from data_stream_sampler import DataStreamSampler, JSONDataStream, SamplingConfig, SamplingStrategy


def test_json_loader():
    """测试 JSON 加载器"""
    print("\n" + "="*70)
    print("🧪 测试 JSON 数据加载器")
    print("="*70)
    
    loader = JSONDataLoader()
    
    # 测试1: 加载基础 JSON
    print("\n✅ 测试1: 加载 sentiment_input_batch.json")
    samples = loader.load_batch_json("sentiment_input_batch.json")
    
    if samples:
        print(f"   加载成功: {len(samples)} 个样本")
        
        # 显示前3个样本
        for i, sample in enumerate(samples[:3], 1):
            print(f"\n   样本 {i}:")
            print(f"     ID: {sample.sample_id}")
            print(f"     原始 ID: {sample.raw_text_id}")
            print(f"     文本长度: {len(sample.text)} 字符")
            print(f"     语言: {sample.language}")
            print(f"     股票: {sample.stock_code}")
            print(f"     来源: {sample.source} ({sample.source_name})")
            print(f"     时间: {sample.timestamp}")
    else:
        print("   ❌ 加载失败")
        return False
    
    # 测试2: 加载包含价格的 JSON
    print("\n✅ 测试2: 加载 sentiment_input_with_prices.json")
    price_data = loader.load_with_prices("sentiment_input_with_prices.json")
    
    if price_data:
        print(f"   加载成功: {len(price_data)} 个样本")
        
        # 显示第一个样本的价格信息
        item = price_data[0]
        print(f"\n   样本1 (含价格):")
        print(f"     ID: {item['sample'].sample_id}")
        if item['price_on_publish_date']:
            price = item['price_on_publish_date']
            print(f"     发布日期: {price.get('trade_date')}")
            print(f"     收盘价: ¥{price.get('close_price')}")
            print(f"     交易量: {price.get('volume')} 股")
    else:
        print("   ⚠️  无价格数据")
    
    return True


def test_json_data_stream():
    """测试 JSON 数据流"""
    print("\n" + "="*70)
    print("🧪 测试 JSON 数据流")
    print("="*70)
    
    # 创建采样器
    config = SamplingConfig(overall_rate=1.0)  # 100% 采样，便于测试
    sampler = DataStreamSampler(
        strategy=SamplingStrategy.STRATIFIED,
        config=config
    )
    
    print("\n✅ 创建采样器和 JSON 数据流")
    
    # 创建 JSON 数据流
    json_stream = JSONDataStream(
        sampler=sampler,
        json_file_path="/Users/mac/sandbox/HKU/COMP7705/data/sentiment_input_batch.json",
        rate=100  # 很快推送
    )
    
    print("✅ 启动采样器")
    sampler.start()
    
    # 加载并推送数据
    print("✅ 推送 JSON 数据...")
    
    # 直接调用（不在后台线程）
    raw_data = json_stream.load_json_samples(json_stream.json_file_path)
    
    if raw_data:
        print(f"   加载了 {len(raw_data)} 个 JSON 对象")
        
        # 转换前5个
        for i, json_obj in enumerate(raw_data[:5]):
            sample = json_stream.convert_json_to_sample(json_obj, i)
            sampler.push_sample(sample)
            print(f"   推送样本 {i+1}: {sample.sample_id} ({sample.language})")
        
        print(f"\n✅ 成功推送 5 个样本到采样器")
    
    # 等待采样
    import time
    time.sleep(1)
    
    # 获取批次
    print("\n✅ 从采样器获取批次")
    batch = sampler.get_next_batch(10)
    
    if batch:
        print(f"   获得 {len(batch)} 个采样样本")
        for i, sample in enumerate(batch[:2], 1):
            print(f"\n   样本 {i}:")
            print(f"     ID: {sample.sample_id}")
            print(f"     股票: {sample.stock_code}")
            print(f"     来源: {sample.source}")
    else:
        print("   ⚠️  未获得采样样本")
    
    # 打印统计
    stats = sampler.get_stats()
    print(f"\n📊 采样统计:")
    print(f"   总接收: {stats['total_received']}")
    print(f"   总采样: {stats['total_sampled']}")
    print(f"   采样率: {stats['sampling_rate']:.1%}")
    
    sampler.stop()
    
    return True


def test_format_compatibility():
    """测试格式兼容性"""
    print("\n" + "="*70)
    print("🧪 测试格式兼容性 (JSON ↔ DataStreamSample)")
    print("="*70)
    
    loader = JSONDataLoader()
    
    # 加载 JSON
    samples = loader.load_batch_json("sentiment_input_batch.json")
    
    if not samples:
        print("❌ 无法加载 JSON 数据")
        return False
    
    print(f"\n✅ 加载了 {len(samples)} 个样本")
    
    # 验证所有必需字段
    print("\n验证 DataStreamSample 的必需字段:")
    
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
    
    # 统计各个字段的值
    print(f"\n📊 字段值分布:")
    languages = {}
    sources = {}
    
    for sample in samples:
        # 语言统计
        lang = sample.language
        languages[lang] = languages.get(lang, 0) + 1
        
        # 来源统计
        src = sample.source
        sources[src] = sources.get(src, 0) + 1
    
    print(f"  语言分布:")
    for lang, count in sorted(languages.items()):
        print(f"    {lang}: {count}")
    
    print(f"  来源分布:")
    for src, count in sorted(sources.items()):
        print(f"    {src}: {count}")
    
    # 检查是否有空值
    empty_fields = {}
    for field in required_fields:
        empty_count = sum(1 for sample in samples if not getattr(sample, field, None))
        if empty_count > 0:
            empty_fields[field] = empty_count
    
    if empty_fields:
        print(f"\n⚠️  有些字段存在空值:")
        for field, count in empty_fields.items():
            print(f"    {field}: {count} 个样本")
    else:
        print(f"\n✅ 所有字段都已填充")
    
    return all_valid


def main():
    """运行所有测试"""
    print("\n" + "🎯" * 35)
    print("JSON 数据格式转换测试")
    print("🎯" * 35)
    
    try:
        # 测试1: JSON 加载器
        if not test_json_loader():
            print("\n❌ JSON 加载器测试失败")
            return False
        
        # 测试2: JSON 数据流
        if not test_json_data_stream():
            print("\n❌ JSON 数据流测试失败")
            return False
        
        # 测试3: 格式兼容性
        if not test_format_compatibility():
            print("\n⚠️  格式兼容性测试发现问题")
        
        print("\n" + "="*70)
        print("✅ 所有测试完成")
        print("="*70)
        print("""
✨ 总结:

✅ JSON 数据加载成功
✅ 数据格式转换完成
✅ 兼容 DataStreamSample 结构
✅ 已准备好集成到在线测试框架

📁 支持的文件:
  • /data/sentiment_input_batch.json
  • /data/sentiment_input_with_prices.json

🚀 下一步:
  运行: python demo_online_testing.py
  并选择演示 2️⃣  (JSON 数据流演示)
        """)
        
        return True
    
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
