"""
文本分析模块 - 预处理
功能：清洗、分词、实体识别、文本切分
"""

import re
import jieba
import jieba.posseg as pseg
from typing import List, Dict, Any, Tuple
import hashlib
from dataclasses import dataclass
from datetime import datetime

from models import RawText, ProcessedChunk, TextSource


class TextPreprocessor:
    """
    文本预处理器
    职责：将原始文本转化为标准化的、适合LLM处理的文本块
    """
    
    def __init__(self):
        # 加载金融词典优化分词
        self._load_financial_dict()
        # 编译正则表达式
        self._compile_patterns()
    
    def _load_financial_dict(self):
        """加载金融领域专有词典"""
        # 港股特定术语
        hk_terms = [
            "港股通", "恒生指数", "红筹股", "蓝筹股", "供股", "配股",
            "闪崩", "北水", "南水", "窝轮", "牛熊证", "沽空", "好仓", "淡仓",
            "业绩公告", "内幕消息", "须予披露交易", "关连交易", "主要交易",
            "腾讯控股", "阿里巴巴", "美团", "小米集团", "比亚迪", "港交所"
        ]
        for term in hk_terms:
            jieba.add_word(term, freq=1000, tag='n')
    
    def _compile_patterns(self):
        """编译清洗用的正则表达式"""
        self.patterns = {
            # 去除HTML标签
            'html': re.compile(r'<[^>]+>'),
            # 去除URL
            'url': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
            # 去除多余空白
            'whitespace': re.compile(r'\s+'),
            # 去除特殊符号但保留中英文标点
            'special_chars': re.compile(r'[^\w\s\u4e00-\u9fff.,;:!?，。；：！？\"\"''（）【】《》]'),
            # 识别股票代码
            'stock_code': re.compile(r'(\d{4,5})\s*(?:HK|\.HK)?'),
            # 识别金额数字
            'money': re.compile(r'(\d+\.?\d*)\s*(?:亿|万|千|百万|千万|billion|million|mln|bln)'),
        }
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本
        输入：原始文本（可能包含HTML、URL、特殊符号）
        输出：清洗后的纯文本
        """
        if not text:
            return ""
        
        # 步骤1：去除HTML
        text = self.patterns['html'].sub(' ', text)
        
        # 步骤2：去除URL
        text = self.patterns['url'].sub(' ', text)
        
        # 步骤3：规范化空白字符
        text = self.patterns['whitespace'].sub(' ', text)
        
        # 步骤4：去除无意义特殊符号（保留金融相关符号）
        text = self.patterns['special_chars'].sub('', text)
        
        # 步骤5：统一中英文标点
        text = text.replace('，', ',').replace('。', '.').replace('；', ';')
        text = text.replace('：', ':').replace('！', '!').replace('？', '?')
        text = text.replace('（', '(').replace('）', ')')
        text = text.replace('【', '[').replace('】', ']')
        
        return text.strip()
    
    def extract_entities(self, text: str, stock_codes: List[str], stock_names: List[str]) -> List[Dict[str, Any]]:
        """
        命名实体识别
        输入：清洗后的文本，已知的股票代码和名称列表
        输出：识别的实体列表
        """
        entities = []
        
        # 1. 识别股票代码和名称
        for code in stock_codes:
            # 匹配各种格式：00700, 00700.HK, 腾讯
            patterns = [
                rf'\b{code.replace(".HK", "")}\b',
                rf'\b{code}\b',
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entities.append({
                        "text": match.group(),
                        "type": "STOCK_CODE",
                        "start": match.start(),
                        "end": match.end(),
                        "normalized": code
                    })
        
        # 2. 识别公司名称（使用jieba分词+匹配）
        words = pseg.cut(text)
        for word, flag in words:
            for name in stock_names:
                if name in word or word in name:
                    entities.append({
                        "text": word,
                        "type": "COMPANY_NAME",
                        "start": text.find(word),
                        "end": text.find(word) + len(word),
                        "normalized": name
                    })
        
        # 3. 识别人名（高管）
        person_pattern = re.compile(r'(?:CEO|主席|总裁|总监|经理|Chief|President)\s*[:：]?\s*([^\s,，.]{2,4})')
        for match in person_pattern.finditer(text):
            entities.append({
                "text": match.group(1),
                "type": "PERSON",
                "start": match.start(1),
                "end": match.end(1),
                "role": match.group(0).split()[0] if match.group(0).split() else "高管"
            })
        
        # 4. 识别时间表达式
        time_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}-\d{2}-\d{2}',
            r'(?:上|下|本|前|去)个?(?:年|月|季度|周)',
            r'(?:今日|昨日|明日|近日|早前)'
        ]
        for pattern in time_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "type": "TIME",
                    "start": match.start(),
                    "end": match.end()
                })
        
        # 5. 识别金额数字
        for match in self.patterns['money'].finditer(text):
            entities.append({
                "text": match.group(),
                "type": "MONEY",
                "start": match.start(),
                "end": match.end(),
                "value": match.group(1)
            })
        
        # 去重和排序
        seen = set()
        unique_entities = []
        for e in sorted(entities, key=lambda x: x['start']):
            key = (e['start'], e['end'], e['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(e)
        
        return unique_entities
    
    def split_into_chunks(self, text: str, stock_code: str, max_length: int = 800, overlap: int = 100) -> List[ProcessedChunk]:
        """
        将长文本切分为适合LLM处理的块
        策略：按语义边界（段落、句子）切分，保持上下文重叠
        
        输入：清洗后的长文本，主要股票代码
        输出：文本块列表
        """
        chunks = []
        
        # 如果文本较短，无需切分
        if len(text) <= max_length:
            chunk_id = hashlib.md5(f"{text}_{stock_code}_0".encode()).hexdigest()[:16]
            return [ProcessedChunk(
                chunk_id=chunk_id,
                parent_text_id="",  # 由调用者填充
                stock_code=stock_code,
                content=text,
                start_idx=0,
                end_idx=len(text),
                is_relevant=True
            )]
        
        # 按段落初步分割
        paragraphs = re.split(r'\n+', text)
        
        current_chunk = ""
        current_start = 0
        chunk_idx = 0
        
        for para in paragraphs:
            # 如果当前段落加入后不超过限制，直接加入
            if len(current_chunk) + len(para) < max_length:
                current_chunk += para + "\n"
            else:
                # 保存当前块
                if current_chunk.strip():
                    chunk_id = hashlib.md5(f"{text}_{stock_code}_{chunk_idx}".encode()).hexdigest()[:16]
                    chunks.append(ProcessedChunk(
                        chunk_id=chunk_id,
                        parent_text_id="",
                        stock_code=stock_code,
                        content=current_chunk.strip(),
                        start_idx=current_start,
                        end_idx=current_start + len(current_chunk),
                        is_relevant=True
                    ))
                    chunk_idx += 1
                
                # 处理长段落：按句子切分
                if len(para) > max_length:
                    sentences = re.split(r'([。！？.!?])', para)
                    current_chunk = ""
                    for i in range(0, len(sentences)-1, 2):
                        sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                        if len(current_chunk) + len(sentence) < max_length:
                            current_chunk += sentence
                        else:
                            if current_chunk.strip():
                                chunk_id = hashlib.md5(f"{text}_{stock_code}_{chunk_idx}".encode()).hexdigest()[:16]
                                chunks.append(ProcessedChunk(
                                    chunk_id=chunk_id,
                                    parent_text_id="",
                                    stock_code=stock_code,
                                    content=current_chunk.strip(),
                                    start_idx=current_start,
                                    end_idx=current_start + len(current_chunk),
                                    is_relevant=True
                                ))
                                chunk_idx += 1
                            # 保留重叠部分
                            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                            current_chunk = overlap_text + sentence
                            current_start += len(current_chunk) - len(sentence)
                else:
                    current_chunk = para + "\n"
                    current_start += len(current_chunk)
        
        # 处理最后一个块
        if current_chunk.strip():
            chunk_id = hashlib.md5(f"{text}_{stock_code}_{chunk_idx}".encode()).hexdigest()[:16]
            chunks.append(ProcessedChunk(
                chunk_id=chunk_id,
                parent_text_id="",
                stock_code=stock_code,
                content=current_chunk.strip(),
                start_idx=current_start,
                end_idx=current_start + len(current_chunk),
                is_relevant=True
            ))
        
        return chunks
    
    def process(self, raw_text: RawText) -> List[ProcessedChunk]:
        """
        主处理流程
        输入：RawText对象
        输出：按股票分离的ProcessedChunk列表
        """
        all_chunks = []
        
        # 1. 清洗全文
        cleaned_title = self.clean_text(raw_text.title)
        cleaned_content = self.clean_text(raw_text.content)
        full_text = f"{cleaned_title}\n{cleaned_content}"
        
        # 2. 为每只股票分别处理
        for i, stock_code in enumerate(raw_text.stock_codes):
            stock_name = raw_text.stock_names[i] if i < len(raw_text.stock_names) else ""
            
            # 3. 实体识别
            entities = self.extract_entities(
                full_text, 
                [stock_code], 
                [stock_name] if stock_name else []
            )
            
            # 4. 切分文本块
            chunks = self.split_into_chunks(full_text, stock_code)
            
            # 5. 填充元数据
            for chunk in chunks:
                chunk.parent_text_id = raw_text.text_id
                chunk.entities = [e for e in entities if chunk.start_idx <= e['start'] < chunk.end_idx]
                
                # 简单关键词提取（基于TF或规则）
                chunk.keywords = self._extract_keywords(chunk.content)
                
                # 相关性判断：如果块中未提及该股票，标记为低相关
                if not any(e['normalized'] == stock_code or e.get('normalized') == stock_name 
                          for e in chunk.entities):
                    chunk.is_relevant = False
            
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def _extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """简单关键词提取（基于词频和词性）"""
        words = pseg.cut(text)
        # 筛选名词、动词，过滤停用词
        keywords = []
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        word_freq = {}
        for word, flag in words:
            if len(word) > 1 and word not in stop_words and flag.startswith(('n', 'v')):
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:top_k]]


# 使用示例
if __name__ == "__main__":
    # 创建测试数据
    raw = RawText(
        text_id="test-001",
        title="腾讯控股发布Q1财报，净利润同比增长54%",
        content="腾讯控股(00700.HK)今日公布2024年第一季度业绩。收入同比增长6%至人民币1,595亿元。净利润同比增长54%至人民币418亿元。董事会主席兼CEO马化腾表示：\"本季度我们的游戏业务表现强劲。\"",
        stock_codes=["00700.HK"],
        stock_names=["腾讯控股"],
        source=TextSource(
            source_type="announcement",
            source_name="披露易",
            publish_time=datetime.now()
        )
    )
    
    # 预处理
    preprocessor = TextPreprocessor()
    chunks = preprocessor.process(raw)
    
    print(f"生成 {len(chunks)} 个文本块")
    for chunk in chunks:
        print(f"\n块ID: {chunk.chunk_id}")
        print(f"股票: {chunk.stock_code}")
        print(f"内容: {chunk.content[:100]}...")
        print(f"实体: {chunk.entities}")
        print(f"关键词: {chunk.keywords}")
        print(f"相关性: {chunk.is_relevant}")