import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from chatbot.utils.file_utils import ensure_directory_exists

# 配置日志
logger = logging.getLogger(__name__)

def log_conversation(conversation_id: str, user_input: str, model_response: str, 
                   knowledge_updated: bool = False, knowledge_file: str = ""):
    """
    记录对话日志
    
    参数:
        conversation_id (str): 对话ID
        user_input (str): 用户输入
        model_response (str): 模型响应
        knowledge_updated (bool): 是否更新了知识库
        knowledge_file (str): 知识库文件路径
    """
    try:
        log_dir = Path("data/log")
        ensure_directory_exists(log_dir)
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"{today}.csv"
        
        # 如果文件不存在，创建并写入表头
        if not log_file.exists():
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("timestamp,conversation_id,user_input,model_response,knowledge_updated,knowledge_file\n")
        
        # 追加日志
        with open(log_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().isoformat()
            # 转义CSV特殊字符
            user_input_escaped = user_input.replace('"', '""')
            model_response_escaped = model_response.replace('"', '""')
            f.write(f'{timestamp},"{conversation_id}","{user_input_escaped}","{model_response_escaped}",{knowledge_updated},"{knowledge_file}"\n')
    except Exception as e:
        logger.error(f"记录对话日志失败: {e}")