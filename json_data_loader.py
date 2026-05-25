"""
JSON 数据加载器 - 从 /data 目录下的 JSON 文件加载数据并转换为 DataStreamSample 格式
支持 sentiment_input_batch.json 和 sentiment_input_with_prices.json
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from data_stream_sampler import DataStreamSample


class JSONDataLoader:
    """JSON 数据加载器"""
    
    def __init__(self, data_dir: str = "/Users/mac/sandbox/HKU/COMP7705/data"):
        """
        初始化加载器
        
        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
    
    @staticmethod
    def convert_to_sample(raw_data: dict, index: int = 0) -> DataStreamSample:
        """
        将原始 JSON 数据转换为 DataStreamSample
        
        Args:
            raw_data: 原始 JSON 对象
            index: 样本索引（用于生成 sample_id）
        
        Returns:
            DataStreamSample 对象
        """
        # 提取必要字段
        text_id = raw_data.get("text_id", f"doc-{index}")
        language = raw_data.get("language", "en")
        
        # 合并 title 和 content 作为 text
        title = raw_data.get("title", "")
        content = raw_data.get("content", "")
        text = f"{title}\n{content}".strip() if title else content
        
        # 股票代码处理 (可能是列表)
        stock_codes = raw_data.get("stock_codes", [])
        stock_code = stock_codes[0] if isinstance(stock_codes, list) and stock_codes else ""
        
        # 来源类型转换
        source_type = raw_data.get("source_type", "announcement")
        source_name = raw_data.get("source_name", "unknown")
        published_at = raw_data.get("published_at", datetime.now().isoformat())
        
        # 创建 DataStreamSample
        sample = DataStreamSample(
            sample_id=f"{text_id}-{index}",
            raw_text_id=text_id,
            text=text,
            language=language,
            stock_code=stock_code,
            source=source_type,
            source_name=source_name,
            timestamp=published_at,
            confidence=0.0,  # 默认值
            priority=0  # 默认值
        )
        
        return sample
    
    def load_batch_json(self, filename: str = "sentiment_input_batch.json") -> List[DataStreamSample]:
        """
        加载批量 JSON 文件并转换为 DataStreamSample 列表
        
        Args:
            filename: JSON 文件名 (默认: sentiment_input_batch.json)
        
        Returns:
            DataStreamSample 列表
        """
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return []
        
        print(f"📂 加载文件: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            if not isinstance(raw_data, list):
                print(f"⚠️  预期 JSON 数组，但得到 {type(raw_data)}")
                return []
            
            # 转换所有数据
            samples = []
            for idx, item in enumerate(raw_data):
                sample = self.convert_to_sample(item, idx)
                samples.append(sample)
            
            print(f"✅ 加载完成: {len(samples)} 个样本")
            return samples
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析错误: {e}")
            return []
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return []
    
    def load_with_prices(self, filename: str = "sentiment_input_with_prices.json") -> List[dict]:
        """
        加载包含价格信息的 JSON 文件
        
        Args:
            filename: JSON 文件名 (默认: sentiment_input_with_prices.json)
        
        Returns:
            包含 sample 和 price 信息的字典列表
        """
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return []
        
        print(f"📂 加载文件: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            if not isinstance(raw_data, list):
                print(f"⚠️  预期 JSON 数组，但得到 {type(raw_data)}")
                return []
            
            # 转换并保留价格信息
            results = []
            for idx, item in enumerate(raw_data):
                sample = self.convert_to_sample(item, idx)
                
                # 提取价格信息
                price_on_publish = item.get("price_on_publish_date", {})
                previous_price = item.get("previous_trading_day_price", {})
                
                results.append({
                    "sample": sample,
                    "price_on_publish_date": price_on_publish,
                    "previous_trading_day_price": previous_price
                })
            
            print(f"✅ 加载完成: {len(results)} 个样本 (含价格信息)")
            return results
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析错误: {e}")
            return []
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return []
    
    def save_converted_data(
        self,
        samples: List[DataStreamSample],
        output_filename: str = "sentiment_input_for_sampler.json"
    ) -> bool:
        """
        将转换后的数据保存为 JSON 文件
        
        Args:
            samples: DataStreamSample 列表
            output_filename: 输出文件名
        
        Returns:
            是否成功保存
        """
        output_path = self.data_dir / output_filename
        
        try:
            # 转换为字典列表
            data = []
            for sample in samples:
                data.append({
                    "sample_id": sample.sample_id,
                    "raw_text_id": sample.raw_text_id,
                    "text": sample.text,
                    "language": sample.language,
                    "stock_code": sample.stock_code,
                    "source": sample.source,
                    "source_name": sample.source_name,
                    "timestamp": sample.timestamp,
                    "sampled_at": sample.sampled_at,
                    "confidence": sample.confidence,
                    "priority": sample.priority
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 转换后的数据已保存: {output_path}")
            return True
        
        except Exception as e:
            print(f"❌ 保存失败: {e}")
            return False


def load_data_for_sampling(
    filename: str = "sentiment_input_batch.json",
    data_dir: str = "/Users/mac/sandbox/HKU/COMP7705/data"
) -> List[DataStreamSample]:
    """
    快速加载数据的便利函数
    
    Args:
        filename: JSON 文件名
        data_dir: 数据目录
    
    Returns:
        DataStreamSample 列表
    """
    loader = JSONDataLoader(data_dir)
    return loader.load_batch_json(filename)


def load_data_with_prices(
    filename: str = "sentiment_input_with_prices.json",
    data_dir: str = "/Users/mac/sandbox/HKU/COMP7705/data"
) -> List[dict]:
    """
    快速加载包含价格数据的便利函数
    
    Args:
        filename: JSON 文件名
        data_dir: 数据目录
    
    Returns:
        包含 sample 和价格信息的字典列表
    """
    loader = JSONDataLoader(data_dir)
    return loader.load_with_prices(filename)


# 演示和测试
if __name__ == "__main__":
    print("=" * 70)
    print("JSON 数据加载器 - 测试")
    print("=" * 70)
    
    loader = JSONDataLoader()
    
    # 测试1: 加载基础 JSON
    print("\n🧪 测试1: 加载基础 JSON")
    samples = loader.load_batch_json("sentiment_input_batch.json")
    if samples:
        print(f"\n第一个样本:")
        sample = samples[0]
        print(f"  ID: {sample.sample_id}")
        print(f"  文本长度: {len(sample.text)} 字符")
        print(f"  语言: {sample.language}")
        print(f"  股票代码: {sample.stock_code}")
        print(f"  来源: {sample.source} ({sample.source_name})")
        print(f"  时间戳: {sample.timestamp}")
    
    # 测试2: 加载包含价格的 JSON
    print("\n🧪 测试2: 加载包含价格的 JSON")
    price_data = loader.load_with_prices("sentiment_input_with_prices.json")
    if price_data:
        print(f"\n第一个样本 (含价格):")
        item = price_data[0]
        print(f"  ID: {item['sample'].sample_id}")
        if item['price_on_publish_date']:
            print(f"  发布日期价格: ¥{item['price_on_publish_date'].get('close_price', 'N/A')}")
        if item['previous_trading_day_price']:
            print(f"  前一交易日价格: ¥{item['previous_trading_day_price'].get('close_price', 'N/A')}")
    
    # 测试3: 保存转换后的数据
    if samples:
        print("\n🧪 测试3: 保存转换后的数据")
        loader.save_converted_data(samples, "sentiment_input_for_sampler.json")
    
    print("\n" + "=" * 70)
    print("✅ 所有测试完成")
    print("=" * 70)
