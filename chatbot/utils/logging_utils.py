import os
from datetime import datetime
from pathlib import Path
from chatbot.utils.file_utils import ensure_directory_exists

def log_conversation(conversation_id, user_input, model_response, knowledge_updated=False, knowledge_file=""):
    """
    记录对话日志
    
    参数:
        conversation_id (str): 对话ID
        user_input (str): 用户输入
        model_response (str): 模型响应
        knowledge_updated (bool): 是否更新了知识库
        knowledge_file (str): 知识库文件路径
    """
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
        f.write(f"{timestamp},{conversation_id},{user_input},{model_response},{knowledge_updated},{knowledge_file}\n")