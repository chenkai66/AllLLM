import os
import csv
from datetime import datetime
from pathlib import Path
from chatbot.utils.file_utils import ensure_directory_exists

LOG_DIR = "data/log"

def save_conversation_log(log_data):
    """
    保存对话日志到CSV文件
    每天创建一个新的日志文件，格式为YYYY-MM-DD.csv
    
    参数:
        log_data (dict): 包含对话数据的字典
    """
    ensure_directory_exists(LOG_DIR)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = Path(LOG_DIR) / f"{today}.csv"
    
    # 文件不存在时创建并写入表头
    if not log_file.exists():
        with open(log_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "conversation_id", "user_input", 
                "model_response", "knowledge_updated", "knowledge_file"
            ])
    
    # 追加日志
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            log_data.get("timestamp", datetime.now().isoformat()),
            log_data.get("conversation_id", ""),
            log_data.get("user_input", ""),
            log_data.get("model_response", ""),
            log_data.get("knowledge_updated", False),
            log_data.get("knowledge_file", "")
        ])

def load_recent_conversations(conversation_id, max_entries=10):
    """
    加载最近的对话历史
    
    参数:
        conversation_id (str): 对话ID
        max_entries (int): 最大加载条目数
        
    返回:
        list: 对话历史列表
    """
    conversations = []
    log_dir = Path(LOG_DIR)
    
    # 按日期倒序查找日志文件
    log_files = sorted(log_dir.glob('*.csv'), reverse=True)
    
    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['conversation_id'] == conversation_id:
                    conversations.append({
                        "timestamp": row['timestamp'],
                        "user_input": row['user_input'],
                        "model_response": row['model_response']
                    })
                    if len(conversations) >= max_entries:
                        return conversations
    return conversations