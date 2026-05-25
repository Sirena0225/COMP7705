"""
多语言文本预处理模块
支持中文和英文的文本处理
"""

import re
import jieba
import jieba.posseg as pseg
from typing import List, Dict, Any, Tuple
import hashlib
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag

from models import RawText, ProcessedChunk, TextSource

# 下载必要的NLTK数据
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class LanguageProcessor(ABC):
    """
    语言处理器抽象基类
    支持不同语言的文本处理
    """
    
    @abstractmethod
    def tokenize_words(self, text: str) -> List[Tuple[str, str]]:
        """
        分词并进行词性标注
        返回 [(词, 词性), ...] 的列表
        """
        pass
    
    @abstractmethod
    def tokenize_sentences(self, text: str) -> List[str]:
        """将文本分句"""
        pass
    
    @abstractmethod
    def extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """提取关键词"""
        pass
    
    @abstractmethod
    def get_stopwords(self) -> set:
        """获取停用词集合"""
        pass


class ChineseProcessor(LanguageProcessor):
    """中文文本处理器"""
    
    def __init__(self):
        self._load_financial_dict()
        self.stopwords = self._get_chinese_stopwords()
    
    def _load_financial_dict(self):
        """加载金融领域专有词典"""
        hk_terms = [
            "港股通", "恒生指数", "红筹股", "蓝筹股", "供股", "配股",
            "闪崩", "北水", "南水", "窝轮", "牛熊证", "沽空", "好仓", "淡仓",
            "业绩公告", "内幕消息", "须予披露交易", "关连交易", "主要交易",
            "腾讯控股", "阿里巴巴", "美团", "小米集团", "比亚迪", "港交所",
            "IPO", "IPO融资", "发行价", "破发", "上市首日", "定增", "融资融券",
            "做空", "做多", "牛市", "熊市", "震荡", "跳空", "缺口"
        ]
        for term in hk_terms:
            jieba.add_word(term, freq=1000, tag='n')
    
    def _get_chinese_stopwords(self) -> set:
        """获取中文停用词"""
        stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '样', '因为', '所以', '但', '如果', '那么',
            '其中', '其他', '已', '它', '他', '她', '们', '为', '被', '与', '之',
            '等', '及', '或', '从', '对', '对于', '按', '通过', '比', '比如', '比较'
        }
        return stopwords
    
    def tokenize_words(self, text: str) -> List[Tuple[str, str]]:
        """使用jieba进行中文分词和词性标注"""
        words = pseg.cut(text)
        return [(word, flag) for word, flag in words]
    
    def tokenize_sentences(self, text: str) -> List[str]:
        """中文分句（按标点符号）"""
        sentences = re.split(r'[。！？\.\!\?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """提取中文关键词"""
        words = self.tokenize_words(text)
        word_freq = {}
        
        for word, flag in words:
            # 筛选名词、动词、形容词，过滤停用词
            if len(word) > 1 and word not in self.stopwords and flag.startswith(('n', 'v', 'a')):
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:top_k]]
    
    def get_stopwords(self) -> set:
        """返回停用词集合"""
        return self.stopwords


class EnglishProcessor(LanguageProcessor):
    """英文文本处理器"""
    
    def __init__(self):
        self.stopwords = set(stopwords.words('english'))
        self._add_financial_stopwords()
    
    def _add_financial_stopwords(self):
        """添加金融领域特定的停用词"""
        financial_stopwords = {
            'get', 'has', 'have', 'being', 'would', 'could', 'should',
            'also', 'such', 'each', 'which', 'because', 'make', 'made'
        }
        self.stopwords.update(financial_stopwords)
    
    def tokenize_words(self, text: str) -> List[Tuple[str, str]]:
        """使用NLTK进行英文分词和词性标注"""
        # 先分句，再分词，最后标注词性
        sentences = sent_tokenize(text)
        words = []
        for sentence in sentences:
            tokens = word_tokenize(sentence.lower())
            tagged = pos_tag(tokens)
            words.extend(tagged)
        return words
    
    def tokenize_sentences(self, text: str) -> List[str]:
        """使用NLTK进行英文分句"""
        sentences = sent_tokenize(text)
        return [s.strip() for s in sentences if s.strip()]
    
    def extract_keywords(self, text: str, top_k: int = 5) -> List[str]:
        """提取英文关键词"""
        words = self.tokenize_words(text)
        word_freq = {}
        
        for word, pos in words:
            # 筛选名词、动词、形容词，过滤停用词和短词
            if (len(word) > 2 and word not in self.stopwords and 
                pos in ['NN', 'NNS', 'NNP', 'NNPS', 'VB', 'VBD', 'VBG', 'VBN', 'VBZ', 'VBP',
                        'JJ', 'JJR', 'JJS']):
                word_freq[word] = word_freq.get(word, 0) + 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w[0] for w in sorted_words[:top_k]]
    
    def get_stopwords(self) -> set:
        """返回停用词集合"""
        return self.stopwords


class MultilingualTextPreprocessor:
    """
    多语言文本预处理器
    自动检测文本语言并使用相应的处理器
    """
    
    def __init__(self):
        self.chinese_processor = ChineseProcessor()
        self.english_processor = EnglishProcessor()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译清洗用的正则表达式"""
        self.patterns = {
            'html': re.compile(r'<[^>]+>'),
            'url': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
            'whitespace': re.compile(r'\s+'),
            'special_chars': re.compile(r'[^\w\s\u4e00-\u9fff.,;:!?，。；：！？\"\"''（）【】《》\-]'),
            'stock_code': re.compile(r'(\d{4,5})\s*(?:HK|\.HK)?'),
            'money': re.compile(r'(\d+\.?\d*)\s*(?:亿|万|千|百万|千万|billion|million|mln|bln)'),
        }
    
    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        返回 'zh'（中文）、'en'（英文）或 'mixed'（混合）
        """
        # 计算中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        total_chars = len(text)
        
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_words / (total_chars / 5) if total_chars > 0 else 0  # 平均每个词5个字符
        
        if chinese_ratio > 0.3:
            return 'zh' if english_ratio < 0.2 else 'mixed'
        elif english_ratio > 0.3:
            return 'en'
        else:
            return 'mixed'
    
    def get_processor(self, language: str) -> LanguageProcessor:
        """根据语言获取相应的处理器"""
        if language == 'zh':
            return self.chinese_processor
        elif language == 'en':
            return self.english_processor
        else:
            # 混合语言默认使用中文处理器，因为港股市场主要是中文
            return self.chinese_processor
    
    def clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        # 去除HTML标签
        text = self.patterns['html'].sub(' ', text)
        
        # 去除URL
        text = self.patterns['url'].sub(' ', text)
        
        # 规范化空白字符
        text = self.patterns['whitespace'].sub(' ', text)
        
        # 去除特殊符号
        text = self.patterns['special_chars'].sub('', text)
        
        # 统一标点符号
        text = text.replace('，', ',').replace('。', '.').replace('；', ';')
        text = text.replace('：', ':').replace('！', '!').replace('？', '?')
        text = text.replace('（', '(').replace('）', ')')
        text = text.replace('【', '[').replace('】', ']')
        
        return text.strip()
    
    def extract_entities(self, text: str, stock_codes: List[str], stock_names: List[str],
                        language: str = 'zh') -> List[Dict[str, Any]]:
        """
        命名实体识别
        支持多语言
        """
        entities = []
        
        # 识别股票代码和名称
        for code in stock_codes:
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
        
        # 识别公司名称
        processor = self.get_processor(language)
        words = processor.tokenize_words(text)
        
        for word, flag in words:
            for name in stock_names:
                if name.lower() in word.lower() or word.lower() in name.lower():
                    start_pos = text.find(word)
                    if start_pos >= 0:
                        entities.append({
                            "text": word,
                            "type": "COMPANY_NAME",
                            "start": start_pos,
                            "end": start_pos + len(word),
                            "normalized": name
                        })
        
        # 识别时间表达式
        time_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{4}-\d{2}-\d{2}',
            r'(?:上|下|本|前|去)个?(?:年|月|季度|周)',
            r'(?:今日|昨日|明日|近日|早前)',
            r'\d{4}年\d{1,2}月',
            r'[Jj]an(?:uary)?|[Ff]eb(?:ruary)?|[Mm]ar(?:ch)?|[Aa]pr(?:il)?|[Mm]ay|[Jj]un(?:e)?|[Jj]ul(?:y)?|[Aa]ug(?:ust)?|[Ss]ep(?:tember)?|[Oo]ct(?:ober)?|[Nn]ov(?:ember)?|[Dd]ec(?:ember)?',
            r'(?:today|yesterday|tomorrow|recently|last\s+(?:week|month|year))',
        ]
        
        for pattern in time_patterns:
            for match in re.finditer(pattern, text):
                entities.append({
                    "text": match.group(),
                    "type": "TIME",
                    "start": match.start(),
                    "end": match.end()
                })
        
        # 识别金额
        for match in self.patterns['money'].finditer(text):
            entities.append({
                "text": match.group(),
                "type": "MONEY",
                "start": match.start(),
                "end": match.end(),
                "value": match.group(1)
            })
        
        # 去重
        seen = set()
        unique_entities = []
        for e in sorted(entities, key=lambda x: x['start']):
            key = (e['start'], e['end'], e['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(e)
        
        return unique_entities
    
    def split_into_chunks(self, text: str, stock_code: str, language: str = 'zh',
                         max_length: int = 800, overlap: int = 100) -> List[ProcessedChunk]:
        """
        将文本切分为适合LLM处理的块
        支持多语言
        """
        chunks = []
        processor = self.get_processor(language)
        
        if len(text) <= max_length:
            chunk_id = hashlib.md5(f"{text}_{stock_code}_0".encode()).hexdigest()[:16]
            return [ProcessedChunk(
                chunk_id=chunk_id,
                parent_text_id="",
                stock_code=stock_code,
                content=text,
                start_idx=0,
                end_idx=len(text),
                is_relevant=True
            )]
        
        # 使用语言特定的分句方法
        sentences = processor.tokenize_sentences(text)
        
        current_chunk = ""
        current_start = 0
        chunk_idx = 0
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + " "
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
                    current_start += len(current_chunk)
                
                current_chunk = sentence + " "
        
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
        支持中文、英文和混合文本
        """
        all_chunks = []
        
        # 检查语言（使用给定的或自动检测）
        if raw_text.language == 'mixed':
            detected_language = self.detect_language(raw_text.full_text)
        else:
            detected_language = raw_text.language
        
        # 清洗文本
        cleaned_title = self.clean_text(raw_text.title)
        cleaned_content = self.clean_text(raw_text.content)
        full_text = f"{cleaned_title}\n{cleaned_content}"
        
        # 为每只股票处理
        for i, stock_code in enumerate(raw_text.stock_codes):
            stock_name = raw_text.stock_names[i] if i < len(raw_text.stock_names) else ""
            
            # 实体识别
            entities = self.extract_entities(
                full_text,
                [stock_code],
                [stock_name] if stock_name else [],
                language=detected_language
            )
            
            # 切分文本块
            chunks = self.split_into_chunks(
                full_text,
                stock_code,
                language=detected_language
            )
            
            # 填充元数据
            processor = self.get_processor(detected_language)
            for chunk in chunks:
                chunk.parent_text_id = raw_text.text_id
                chunk.entities = [e for e in entities if chunk.start_idx <= e['start'] < chunk.end_idx]
                chunk.keywords = processor.extract_keywords(chunk.content)
                
                # 相关性判断
                if not any(e['normalized'] == stock_code or e.get('normalized') == stock_name 
                          for e in chunk.entities):
                    chunk.is_relevant = False
            
            all_chunks.extend(chunks)
        
        return all_chunks
