import os
import csv
import json
from datetime import datetime
from pathlib import Path
from chatbot.utils.file_utils import ensure_directory_exists
from chatbot.llm import invoke

USER_PREFERENCE_FILE = "data/user_data/user_preference.csv"
SELF_REFLECTION_FILE = "data/user_data/self_reflection.csv"

def analyze_user_preference(user_input, conversation_id):
    """
    分析用户偏好并更新表格
    
    参数:
        user_input (str): 用户输入
        conversation_id (str): 对话ID
    """
    ensure_directory_exists(Path(USER_PREFERENCE_FILE).parent)
    
    # 创建文件并写入表头（如果不存在）
    if not Path(USER_PREFERENCE_FILE).exists():
        with open(USER_PREFERENCE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "conversation_id", "user_intent", 
                "user_requirements", "analysis_insufficiency", 
                "summary", "embedding_vector"
            ])
    
    # 使用LLM分析用户意图
    prompt = f"""
    请分析以下用户输入的意图和需求：
    用户输入: {user_input}
    
    请按以下JSON格式回复：
    {{
        "intent": "用户意图的简短描述",
        "requirements": "用户详细需求的描述",
        "insufficiency": "分析不足的原因总结",
        "summary": "整体总结"
    }}
    """
    analysis = invoke(prompt)
    
    try:
        analysis_data = json.loads(analysis)
    except json.JSONDecodeError:
        analysis_data = {
            "intent": "未知",
            "requirements": user_input,
            "insufficiency": "分析失败",
            "summary": "无法解析分析结果"
        }
    
    # 追加到用户偏好文件
    with open(USER_PREFERENCE_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            conversation_id,
            analysis_data.get("intent", ""),
            analysis_data.get("requirements", ""),
            analysis_data.get("insufficiency", ""),
            analysis_data.get("summary", ""),
            ""  # 预留向量列（实际实现中应存储向量）
        ])

def perform_self_reflection(user_input, model_response):
    """
    执行自我反思并更新表格
    
    参数:
        user_input (str): 用户输入
        model_response (str): 模型响应
    """
    ensure_directory_exists(Path(SELF_REFLECTION_FILE).parent)
    
    # 创建文件并写入表头（如果不存在）
    if not Path(SELF_REFLECTION_FILE).exists():
        with open(SELF_REFLECTION_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "user_input", "model_response", 
                "improvement_strategy", "summary"
            ])
    
    # 使用LLM进行自我反思
    prompt = f"""
    基于以下对话交互，请反思回答策略需要改进的地方：
    用户输入: {user_input}
    模型响应: {model_response}
    
    请按以下JSON格式回复：
    {{
        "improvement_strategy": "需要改进的策略描述",
        "summary": "整体反思总结"
    }}
    """
    reflection = invoke(prompt)
    
    try:
        reflection_data = json.loads(reflection)
    except json.JSONDecodeError:
        reflection_data = {
            "improvement_strategy": "需要更好的理解用户意图",
            "summary": "反思失败"
        }
    
    # 追加到自我反思文件
    with open(SELF_REFLECTION_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            user_input,
            model_response,
            reflection_data.get("improvement_strategy", ""),
            reflection_data.get("summary", "")
        ])