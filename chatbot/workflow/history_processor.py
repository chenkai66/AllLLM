import logging
import json
import csv
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class HistoryProcessor:
    """历史对话处理器，负责处理和压缩历史对话"""
    
    def __init__(self, history_file_path: str = "data/history_processed.csv"):
        """
        初始化历史对话处理器
        
        Args:
            history_file_path: 处理后的历史对话存储文件路径
        """
        self.history_file_path = Path(history_file_path)
        self.processed_history = {}  # 已处理的历史对话缓存
        self._load_processed_history()
    
    def _load_processed_history(self):
        """加载已处理的历史对话"""
        if self.history_file_path.exists():
            try:
                with open(self.history_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.processed_history[row['conversation_id']] = {
                            'primary_category': row['primary_category'],
                            'secondary_category': row['secondary_category'],
                            'summary': row['summary']
                        }
            except Exception as e:
                logger.error(f"加载已处理历史对话时出错: {e}")
    
    def _save_processed_history(self):
        """保存已处理的历史对话"""
        try:
            # 确保目录存在
            self.history_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果文件不存在，先写入表头
            if not self.history_file_path.exists():
                with open(self.history_file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['conversation_id', 'primary_category', 'secondary_category', 'summary'])
            
            # 只写入新的对话记录（不在文件中的记录）
            existing_ids = self._get_existing_conversation_ids()
            new_records = {conv_id: data for conv_id, data in self.processed_history.items() 
                          if conv_id not in existing_ids}
            
            if new_records:
                # 追加新数据
                with open(self.history_file_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    for conv_id, data in new_records.items():
                        writer.writerow([conv_id, data['primary_category'], data['secondary_category'], data['summary']])
        except Exception as e:
            logger.error(f"保存已处理历史对话时出错: {e}")
    
    def _get_existing_conversation_ids(self) -> set:
        """获取已存在的对话ID集合"""
        existing_ids = set()
        if self.history_file_path.exists():
            try:
                with open(self.history_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        existing_ids.add(row['conversation_id'])
            except Exception as e:
                logger.error(f"读取现有对话ID时出错: {e}")
        return existing_ids
    
    def process_conversation_history(self, conversation_id: str, conversation_history: List[Dict]) -> Dict:
        """
        处理单个对话历史，生成分类和摘要
        
        Args:
            conversation_id: 对话ID
            conversation_history: 对话历史列表
            
        Returns:
            包含一级分类、二级分类和摘要的字典
        """
        # 如果已经处理过，直接返回缓存结果
        if conversation_id in self.processed_history:
            return self.processed_history[conversation_id]
        
        # 将对话历史转换为文本
        history_text = "\n".join([
            f"用户: {item['user_input']}\n助手: {item['model_response']}"
            for item in conversation_history
        ])
        
        # 为简化实现，这里使用固定的分类和摘要
        # 在实际应用中，应该使用大模型来进行分类和摘要
        result = {
            "primary_category": "技术科学类",
            "secondary_category": "人工智能",
            "summary": f"关于{conversation_id}的对话摘要"
        }
        
        # 缓存结果
        self.processed_history[conversation_id] = result
        
        # 只有在添加新记录时才保存
        existing_ids = self._get_existing_conversation_ids()
        if conversation_id not in existing_ids:
            self._save_processed_history()
        
        return result
    
    def get_category_tree(self) -> Dict[str, List[str]]:
        """
        获取分类树结构
        
        Returns:
            分类树结构字典
        """
        # 从已处理的历史对话中提取分类信息
        categories = defaultdict(list)
        for data in self.processed_history.values():
            primary = data['primary_category']
            secondary = data['secondary_category']
            
            if secondary not in categories[primary]:
                categories[primary].append(secondary)
        
        return dict(categories)
    
    def find_relevant_history(self, primary_categories: List[str], secondary_categories: List[str], 
                            current_query: str) -> List[Tuple[str, str]]:
        """
        根据分类和当前查询找到相关的历史对话
        
        Args:
            primary_categories: 一级分类列表
            secondary_categories: 二级分类列表
            current_query: 当前查询
            
        Returns:
            相关历史对话的ID和摘要列表
        """
        relevant_history = []
        
        # 筛选符合分类条件的历史对话
        for conv_id, data in self.processed_history.items():
            if (data['primary_category'] in primary_categories and 
                data['secondary_category'] in secondary_categories):
                relevant_history.append((conv_id, data['summary']))
        
        # 为简化实现，这里直接返回所有相关历史
        # 在实际应用中，应该使用大模型来评估相关性并排序
        return relevant_history[:5]  # 只返回前5个