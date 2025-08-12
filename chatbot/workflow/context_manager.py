import logging
from typing import List, Dict, Optional
from collections import deque
import json

logger = logging.getLogger(__name__)

class ContextManager:
    """上下文管理器，负责维护和处理对话上下文"""
    
    def __init__(self, max_context_length: int = 30000):
        """
        初始化上下文管理器
        
        Args:
            max_context_length: 最大上下文长度（字符数）
        """
        self.max_context_length = max_context_length
        self.context_history = {}  # 每个会话ID对应一个上下文历史
    
    def add_to_context(self, conversation_id: str, user_input: str, model_response: str):
        """
        添加对话到上下文历史
        
        Args:
            conversation_id: 会话ID
            user_input: 用户输入
            model_response: 模型回复
        """
        if conversation_id not in self.context_history:
            self.context_history[conversation_id] = deque()
        
        # 添加新的对话到上下文历史
        self.context_history[conversation_id].append({
            "user_input": user_input,
            "model_response": model_response
        })
        
        # 限制上下文长度
        self._trim_context(conversation_id)
    
    def get_context(self, conversation_id: str) -> List[Dict]:
        """
        获取指定会话的上下文历史
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            上下文历史列表
        """
        return list(self.context_history.get(conversation_id, []))
    
    def _trim_context(self, conversation_id: str):
        """
        修剪上下文历史以保持在最大长度限制内
        
        Args:
            conversation_id: 会话ID
        """
        context = self.context_history[conversation_id]
        total_length = sum(
            len(item["user_input"]) + len(item["model_response"]) 
            for item in context
        )
        
        # 如果超过最大长度，从头部开始删除
        while total_length > self.max_context_length and len(context) > 1:
            removed_item = context.popleft()
            total_length -= len(removed_item["user_input"]) + len(removed_item["model_response"])
    
    def extract_relevant_context(self, conversation_id: str, current_query: str) -> str:
        """
        提取与当前查询相关的上下文信息
        
        Args:
            conversation_id: 会话ID
            current_query: 当前查询
            
        Returns:
            相关上下文信息字符串
        """
        context = self.get_context(conversation_id)
        if not context:
            return ""
        
        # 为简化实现，这里返回最近的几条上下文
        # 在实际应用中，应该使用大模型来判断相关性
        relevant_context = context[-3:]  # 获取最近3条
        
        context_str = "\n".join([
            f"用户: {item['user_input']}\n助手: {item['model_response']}"
            for item in relevant_context
        ])
        
        return context_str
    
    def rewrite_query_with_context(self, conversation_id: str, current_query: str) -> str:
        """
        结合上下文信息重写查询
        
        Args:
            conversation_id: 会话ID
            current_query: 当前查询
            
        Returns:
            重写后的查询
        """
        relevant_context = self.extract_relevant_context(conversation_id, current_query)
        if not relevant_context:
            return current_query
        
        # 为简化实现，这里直接返回原始查询
        # 在实际应用中，应该使用大模型来重写查询
        return current_query