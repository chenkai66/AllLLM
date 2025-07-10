import os
import re
from datetime import datetime
from pathlib import Path
from chatbot.llm import invoke
from chatbot.utils.file_utils import ensure_directory_exists, read_file, write_file

def update_knowledge_base(user_input, model_response, knowledge_base_dir="data/knowledge_base"):
    """
    根据对话内容更新知识库
    
    参数:
        user_input (str): 用户输入
        model_response (str): 模型回复
        knowledge_base_dir (str): 知识库目录路径
    """
    # 1. 提取结构化知识
    knowledge_prompt = read_file("chatbot/prompt/knowledge_extract.txt")
    full_prompt = f"{knowledge_prompt}\n\n用户输入: {user_input}\n模型回复: {model_response}"
    structured_knowledge = invoke(full_prompt)
    
    # 2. 确定知识类别
    category = determine_knowledge_category(user_input, structured_knowledge)
    category_dir = Path(knowledge_base_dir) / category
    ensure_directory_exists(category_dir)
    
    # 3. 查找或创建知识文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{category}_knowledge_{timestamp}.txt"
    filepath = category_dir / filename
    
    # 4. 检查是否已有类似知识
    existing_knowledge = check_existing_knowledge(category_dir, structured_knowledge)
    
    if existing_knowledge:
        # 更新现有文件
        updated_content = update_existing_knowledge(existing_knowledge, structured_knowledge)
        write_file(existing_knowledge, updated_content)
        return str(existing_knowledge)
    else:
        # 创建新文件
        write_file(filepath, structured_knowledge)
        return str(filepath)

def determine_knowledge_category(user_input, knowledge):
    """使用LLM确定知识类别"""
    prompt = f"""
    请根据以下用户输入和提取的知识确定最相关的知识类别：
    用户输入: {user_input}
    提取的知识: {knowledge}
    
    请用单个英文单词或短语回复类别名称（不要包含任何其他文本）
    """
    return invoke(prompt).strip().lower()

def check_existing_knowledge(category_dir, new_knowledge):
    """检查是否存在类似知识文件"""
    # 简化实现：检查目录中是否有文件包含类似主题
    # 实际实现应使用向量相似度或LLM判断
    for file in category_dir.iterdir():
        if file.is_file():
            content = read_file(file)
            if is_related(content, new_knowledge):
                return file
    return None

def is_related(existing_content, new_content):
    """使用LLM判断知识是否相关"""
    prompt = f"""
    请判断以下两段知识是否相关：
    现有知识: {existing_content}
    新知识: {new_content}
    
    如果相关请回复"yes"，否则回复"no"（不要包含任何其他文本）
    """
    return invoke(prompt).strip().lower() == "yes"

def update_existing_knowledge(filepath, new_knowledge):
    """更新现有知识文件"""
    existing_content = read_file(filepath)
    prompt = f"""
    请将新知识合并到现有知识中，确保内容简洁且不重复：
    现有知识: {existing_content}
    新知识: {new_content}
    
    请返回合并后的完整知识内容（不要包含任何其他文本）
    """
    return invoke(prompt)