import logging
from typing import List, Dict, Optional
from chatbot.workflow.context_manager import ContextManager
from chatbot.workflow.history_processor import HistoryProcessor

logger = logging.getLogger(__name__)

class EnhancedQueryProcessor:
    """增强查询处理器，整合上下文、历史对话和知识库"""
    
    def __init__(self):
        """初始化增强查询处理器"""
        self.context_manager = ContextManager()
        self.history_processor = HistoryProcessor()
    
    def process_query(self, user_input: str, conversation_id: str, 
                     load_history: bool = False, settings: Optional[Dict] = None) -> str:
        """
        处理用户查询
        
        Args:
            user_input: 用户输入
            conversation_id: 会话ID
            load_history: 是否加载历史对话
            settings: 设置参数
            
        Returns:
            处理后的回答
        """
        try:
            # 1. 结合上下文重写查询
            rewritten_query = self.context_manager.rewrite_query_with_context(
                conversation_id, user_input
            )
            
            # 2. 如果需要加载历史对话
            relevant_history_info = ""
            if load_history:
                relevant_history_info = self._process_history_context(
                    conversation_id, rewritten_query
                )
            
            # 3. 获取知识库回答（简化实现）
            knowledge_response = self._get_knowledge_response(
                rewritten_query, settings
            )
            
            # 4. 综合所有信息生成最终回答
            final_response = self._generate_final_response(
                user_input, rewritten_query, relevant_history_info, 
                knowledge_response, settings
            )
            
            # 5. 添加当前对话到上下文管理器
            self.context_manager.add_to_context(conversation_id, user_input, final_response)
            
            return final_response
            
        except Exception as e:
            logger.error(f"处理查询时出错: {e}")
            return "抱歉，处理您的请求时出现了错误。"
    
    def _process_history_context(self, conversation_id: str, query: str) -> str:
        """
        处理历史对话上下文
        
        Args:
            conversation_id: 会话ID
            query: 查询
            
        Returns:
            相关历史信息字符串
        """
        try:
            # 1. 获取分类树
            category_tree = self.history_processor.get_category_tree()
            
            # 2. 选择要下探的一级分类（简化实现）
            primary_categories = list(category_tree.keys())[:3]  # 取前3个
            
            # 3. 选择要下探的二级分类（简化实现）
            all_secondary_categories = []
            for primary in primary_categories:
                if primary in category_tree:
                    all_secondary_categories.extend(category_tree[primary])
            
            secondary_categories = all_secondary_categories[:5]  # 取前5个
            
            # 4. 找到相关的历史对话
            relevant_history = self.history_processor.find_relevant_history(
                primary_categories, secondary_categories, query
            )
            
            # 5. 合并相关信息
            if relevant_history:
                history_info = "相关历史对话信息:\n" + "\n".join([
                    f"{conv_id}: {summary}" 
                    for conv_id, summary in relevant_history
                ])
                return history_info
            else:
                return ""
                
        except Exception as e:
            logger.error(f"处理历史上下文时出错: {e}")
            return ""
    
    def _get_knowledge_response(self, query: str, settings: Optional[Dict] = None) -> str:
        """
        获取知识库回答
        
        Args:
            query: 查询
            settings: 设置参数
            
        Returns:
            知识库回答
        """
        try:
            # 导入RAG模块来查询知识库
            from chatbot.rag import ask, ensure_index_exists, create_query_engine
            
            # 确保索引存在
            index = ensure_index_exists()
            # 创建查询引擎
            query_engine = create_query_engine(index)
            
            # 查询知识库
            response_text = ask(query, query_engine, None, settings.get('max_context_length', 10000) if settings else 10000)
            return response_text
        except Exception as e:
            logger.error(f"查询知识库时出错: {e}")
            return f"查询知识库时出现错误: {str(e)}"
    
    def _generate_final_response(self, original_query: str, rewritten_query: str,
                                history_info: str, knowledge_response: str,
                                settings: Optional[Dict] = None) -> str:
        """
        生成最终回答
        
        Args:
            original_query: 原始查询
            rewritten_query: 重写后的查询
            history_info: 历史信息
            knowledge_response: 知识库回答
            settings: 设置参数
            
        Returns:
            最终回答
        """
        # 构建综合信息
        comprehensive_info = ""
        
        if history_info:
            comprehensive_info += f"[历史对话信息]\n{history_info}\n\n"
        
        if knowledge_response:
            comprehensive_info += f"[知识库信息]\n{knowledge_response}\n\n"
        
        if not comprehensive_info:
            return "抱歉，我没有找到相关信息来回答您的问题。"
        
        # 简化实现，直接返回综合信息
        return f"基于以下信息回答您的问题：\n\n{comprehensive_info}"