"""
人工标注接口 - Streamlit mini-app
用于专家复核低置信度样本和模型一致性差的样本
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass
class AnnotationTask:
    """标注任务"""
    task_id: str
    text: str
    text_id: str
    language: str
    stock_code: str
    source: str
    
    production_result: Dict  # 生产模型结果
    candidate_result: Dict   # 候选模型结果
    
    priority: int            # 优先级 (0-2, 越高越紧急)
    reason: str             # 为什么需要标注


@dataclass
class AnnotationResult:
    """标注结果"""
    task_id: str
    annotator_id: str
    timestamp: str
    
    # 标注内容
    gold_standard_polarity: str     # 真实极性
    gold_standard_risk_level: str   # 真实风险等级
    confidence: float               # 标注者置信度 (0-1)
    
    # 可选字段
    notes: str = ""                 # 标注备注
    corrections: Dict = None        # 需要修正的模型输出
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "annotator_id": self.annotator_id,
            "timestamp": self.timestamp,
            "gold_standard_polarity": self.gold_standard_polarity,
            "gold_standard_risk_level": self.gold_standard_risk_level,
            "confidence": self.confidence,
            "notes": self.notes,
            "corrections": self.corrections or {}
        }


class AnnotationInterface:
    """人工标注接口管理器"""
    
    def __init__(self, db_path: str = "/Users/mac/sandbox/HKU/COMP7705/annotations.jsonl"):
        """
        初始化标注接口
        
        Args:
            db_path: 标注结果存储路径
        """
        self.db_path = db_path
        self.pending_tasks: List[AnnotationTask] = []
        self.completed_results: List[AnnotationResult] = []
        
        # 加载已有结果
        self._load_results()
    
    def _load_results(self):
        """从磁盘加载已有的标注结果"""
        path = Path(self.db_path)
        
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # 这里可以转换回AnnotationResult对象
                        self.completed_results.append(data)
    
    def add_task(self, task: AnnotationTask):
        """添加标注任务"""
        self.pending_tasks.append(task)
    
    def add_batch_tasks(self, tasks: List[AnnotationTask]):
        """批量添加标注任务"""
        self.pending_tasks.extend(tasks)
    
    def get_next_task(self, annotator_id: str) -> Optional[AnnotationTask]:
        """
        获取下一个待标注任务
        
        优先级：
        1. 高风险 (priority=2)
        2. 中等风险 (priority=1)
        3. 低优先级 (priority=0)
        """
        if not self.pending_tasks:
            return None
        
        # 按优先级排序
        sorted_tasks = sorted(self.pending_tasks, key=lambda x: -x.priority)
        task = sorted_tasks[0]
        self.pending_tasks.remove(task)
        
        return task
    
    def submit_annotation(self, result: AnnotationResult) -> bool:
        """
        提交标注结果
        
        Args:
            result: 标注结果
        
        Returns:
            是否成功
        """
        try:
            self.completed_results.append(result)
            
            # 追加到文件
            with open(self.db_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + '\n')
            
            return True
        except Exception as e:
            print(f"❌ 提交标注结果失败: {e}")
            return False
    
    def get_gold_standard(self, text_id: str) -> Optional[AnnotationResult]:
        """获取文本的黄金标准标注"""
        for result in self.completed_results:
            if result["task_id"] == text_id:
                return result
        return None
    
    def get_pending_count(self) -> int:
        """获取待标注任务数"""
        return len(self.pending_tasks)
    
    def get_annotation_stats(self) -> Dict:
        """获取标注统计"""
        stats = {
            "total_completed": len(self.completed_results),
            "pending_tasks": len(self.pending_tasks),
            "by_language": {},
            "by_annotator": {},
            "avg_annotator_confidence": 0,
        }
        
        # 按语言统计
        for result in self.completed_results:
            # 需要从原始数据中获取语言信息
            # 这里假设已有该信息
            pass
        
        # 按标注者统计
        annotators = {}
        confidences = []
        
        for result in self.completed_results:
            annotator = result.get("annotator_id", "unknown")
            annotators[annotator] = annotators.get(annotator, 0) + 1
            confidences.append(result.get("confidence", 0))
        
        stats["by_annotator"] = annotators
        stats["avg_annotator_confidence"] = (
            sum(confidences) / len(confidences) if confidences else 0
        )
        
        return stats


class AnnotationStreamlit:
    """Streamlit界面代码生成器"""
    
    @staticmethod
    def generate_annotation_app_code() -> str:
        """生成Streamlit标注应用代码"""
        code = '''
import streamlit as st
import json
from annotation_interface import AnnotationInterface, AnnotationResult, AnnotationTask
from datetime import datetime

# 页面配置
st.set_page_config(page_title="港股舆情标注系统", layout="wide")

# 初始化
if "annotation_interface" not in st.session_state:
    st.session_state.annotation_interface = AnnotationInterface()

# 侧边栏
st.sidebar.title("📝 人工标注系统")
annotator_id = st.sidebar.text_input("标注者ID", value="annotator_001")
mode = st.sidebar.radio(
    "选择模式",
    ["标注任务", "查看统计", "管理任务"]
)

interface = st.session_state.annotation_interface

# 主界面
if mode == "标注任务":
    st.title("🎯 人工标注 - 待标注样本")
    
    # 显示待标注任务数
    pending_count = interface.get_pending_count()
    col1, col2, col3 = st.columns(3)
    col1.metric("待标注任务", pending_count)
    col2.metric("已完成", len(interface.completed_results))
    
    if pending_count > 0:
        # 获取下一个任务
        task = interface.get_next_task(annotator_id)
        
        if task:
            st.markdown(f"### 任务: {task.task_id}")
            st.markdown(f"**优先级**: {'🔴' if task.priority == 2 else '🟡' if task.priority == 1 else '🟢'}")
            st.markdown(f"**原因**: {task.reason}")
            
            # 显示原始文本
            st.markdown("#### 📄 原始文本")
            st.text_area("文本内容", value=task.text, height=150, disabled=True)
            
            st.markdown(f"**股票代码**: {task.stock_code} | **语言**: {task.language} | **来源**: {task.source}")
            
            # 显示两个模型的结果对比
            st.markdown("#### 🤖 模型结果对比")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**生产模型**")
                st.json(task.production_result)
            
            with col2:
                st.markdown("**候选模型**")
                st.json(task.candidate_result)
            
            # 标注表单
            st.markdown("#### ✅ 标注结果")
            
            col1, col2 = st.columns(2)
            
            with col1:
                polarity = st.radio(
                    "真实情绪极性",
                    ["positive", "neutral", "negative"],
                    horizontal=True
                )
            
            with col2:
                risk_level = st.radio(
                    "真实风险等级",
                    ["green", "yellow", "red"],
                    horizontal=True
                )
            
            confidence = st.slider(
                "标注者置信度",
                min_value=0.0,
                max_value=1.0,
                value=0.9,
                step=0.05
            )
            
            notes = st.text_area(
                "标注备注 (可选)",
                value="",
                height=100
            )
            
            # 模型需要的修正
            need_correction = st.checkbox("模型需要修正")
            
            corrections = None
            if need_correction:
                corrections = {
                    "production": st.text_input("生产模型需要修正的地方"),
                    "candidate": st.text_input("候选模型需要修正的地方")
                }
            
            # 提交按钮
            if st.button("✅ 提交标注", type="primary", use_container_width=True):
                result = AnnotationResult(
                    task_id=task.task_id,
                    annotator_id=annotator_id,
                    timestamp=datetime.now().isoformat(),
                    gold_standard_polarity=polarity,
                    gold_standard_risk_level=risk_level,
                    confidence=confidence,
                    notes=notes,
                    corrections=corrections
                )
                
                if interface.submit_annotation(result):
                    st.success("✅ 标注已提交！")
                    st.rerun()
                else:
                    st.error("❌ 提交失败，请重试")
        else:
            st.info("没有更多任务了")
    else:
        st.success("🎉 所有任务已完成！")

elif mode == "查看统计":
    st.title("📊 标注统计")
    
    stats = interface.get_annotation_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("已完成", stats["total_completed"])
    col2.metric("待标注", stats["pending_tasks"])
    col3.metric("标注者数", len(stats["by_annotator"]))
    col4.metric("平均置信度", f"{stats['avg_annotator_confidence']:.2%}")
    
    st.markdown("### 标注者工作量")
    st.json(stats["by_annotator"])

elif mode == "管理任务":
    st.title("⚙️ 任务管理")
    
    st.markdown("### 批量导入任务")
    uploaded_file = st.file_uploader(
        "上传JSON格式的任务文件",
        type=["json", "jsonl"]
    )
    
    if uploaded_file:
        try:
            content = json.loads(uploaded_file.read())
            st.json(content)
            
            if st.button("导入任务", type="primary"):
                # 解析并导入
                st.success("✅ 任务已导入")
        except Exception as e:
            st.error(f"❌ 文件解析失败: {e}")

# 页脚
st.divider()
st.caption("港股舆情分析系统 - 人工标注模块 v1.0")
'''
        return code
    
    @staticmethod
    def save_app_code(output_file: str = "/Users/mac/sandbox/HKU/COMP7705/annotation_app.py"):
        """保存Streamlit应用代码"""
        code = AnnotationStreamlit.generate_annotation_app_code()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"✅ 标注应用代码已保存到: {output_file}")
        print(f"\n运行命令: streamlit run {output_file}")


# 便利函数
def create_annotation_tasks_from_comparisons(
    comparisons: List[Dict],
    consistency_threshold: float = 0.7
) -> List[AnnotationTask]:
    """
    从A/B对比结果创建标注任务
    
    Args:
        comparisons: 对比结果列表
        consistency_threshold: 一致性阈值，低于此值的需要标注
    
    Returns:
        标注任务列表
    """
    tasks = []
    
    for idx, comp in enumerate(comparisons):
        # 只标注一致性低的样本
        if comp.get("consistency_score", 100) < consistency_threshold * 100:
            task = AnnotationTask(
                task_id=f"annotation-{idx}",
                text=comp.get("text", ""),
                text_id=comp.get("text_id", ""),
                language=comp.get("language", "unknown"),
                stock_code=comp.get("stock_code", ""),
                source=comp.get("source", ""),
                
                production_result=comp.get("production_result", {}),
                candidate_result=comp.get("candidate_result", {}),
                
                priority=2 if comp.get("consistency_score", 100) < 50 else 1,
                reason=f"低一致性样本 ({comp.get('consistency_score', 0):.1f}%)"
            )
            tasks.append(task)
    
    return tasks
