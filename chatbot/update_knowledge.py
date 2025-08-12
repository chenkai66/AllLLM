import os
import json
import re
from datetime import datetime
from pathlib import Path
from chatbot.llm import invoke
from chatbot.utils.file_utils import ensure_directory_exists, read_file, write_file

def update_knowledge_base(user_input, model_response, knowledge_base_dir="docs"):
    """
    根据对话内容更新知识库
    
    参数:
        user_input (str): 用户输入
        model_response (str): 模型回复
        knowledge_base_dir (str): 知识库目录路径
    """
    try:
        # 1. 提取结构化知识
        knowledge_prompt = read_file("chatbot/prompt/knowledge_extract.txt")
        if not knowledge_prompt:
            knowledge_prompt = "请从以下对话中提取结构化知识：\n用户输入: {user_input}\n模型回复: {model_response}\n\n提取要求：\n1. 提取关键事实、概念或方法\n2. 用简洁的语言总结（不超过3句话）\n3. 避免包含对话上下文或情感内容\n4. 格式为纯文本，不要使用列表或项目符号\n\n提取的知识："
        
        full_prompt = f"{knowledge_prompt}\n\n用户输入: {user_input}\n模型回复: {model_response}"
        structured_knowledge = invoke(full_prompt)
        
        # 2. 确定知识类别和子类别
        category, subcategory = determine_knowledge_category_and_subcategory(user_input, structured_knowledge)
        
        # 3. 确保层级不超过两层
        # 如果子类别与类别相同或相似，则不使用子类别
        if category.lower() == subcategory.lower() or subcategory.lower() == "general":
            subcategory = None
        
        # 4. 查找最相关的文件夹
        target_dir = find_or_create_best_matching_folder(knowledge_base_dir, category, subcategory)
        
        # 5. 查找或创建知识文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if subcategory:
            filename = f"{category}_{subcategory}_knowledge_{timestamp}.txt"
        else:
            filename = f"{category}_knowledge_{timestamp}.txt"
        filepath = Path(target_dir) / filename
        
        # 6. 检查是否已有类似知识
        existing_knowledge_file = check_existing_knowledge(target_dir, structured_knowledge)
        
        if existing_knowledge_file:
            # 更新现有文件
            updated_content = update_existing_knowledge(existing_knowledge_file, structured_knowledge)
            write_file(existing_knowledge_file, updated_content)
        else:
            # 创建新文件
            write_file(filepath, structured_knowledge)
            
    except Exception as e:
        print(f"知识库更新失败: {e}")
        # 不抛出异常，因为知识库更新失败不应影响主要功能

def determine_knowledge_category_and_subcategory(user_input, knowledge):
    """使用LLM确定知识类别和子类别"""
    try:
        prompt = f"""
        请根据以下用户输入和提取的知识确定最相关的知识类别和子类别：
        用户输入: {user_input}
        提取的知识: {knowledge}
        
        请按以下JSON格式回复：
        {{
            "category": "主要类别（英文单词或短语，不超过2个单词）",
            "subcategory": "子类别（英文单词或短语，不超过2个单词，如果没有请写'general'）"
        }}
        
        要求：
        1. 类别和子类别都应该是通用的技术或业务领域名称
        2. 类别和子类别应该简洁明了
        3. 如果子类别与类别相同或非常相似，请使用'general'
        """
        response = invoke(prompt).strip()
        # 尝试解析JSON
        try:
            result = json.loads(response)
            category = result.get("category", "general")
            subcategory = result.get("subcategory", "general")
        except json.JSONDecodeError:
            # 如果解析失败，使用简单方法提取
            lines = response.split('\n')
            category = lines[0] if len(lines) > 0 else "general"
            subcategory = lines[1] if len(lines) > 1 else "general"
        
        # 确保类别名称是有效的目录名
        category = re.sub(r'[^\w\-_]', '_', category.lower())
        subcategory = re.sub(r'[^\w\-_]', '_', subcategory.lower())
        
        return category if category else "general", subcategory if subcategory else "general"
    except Exception:
        return "general", "general"

def find_or_create_best_matching_folder(knowledge_base_dir, category, subcategory):
    """查找或创建最匹配的文件夹，确保层级不超过两层"""
    base_path = Path(knowledge_base_dir)
    
    # 使用类别作为主文件夹
    category_path = base_path / category
    ensure_directory_exists(category_path)
    
    # 如果有子类别且不为general，则在类别文件夹下创建子类别文件夹
    if subcategory and subcategory.lower() != "general":
        # 确保子类别文件夹路径不超过两层
        subcategory_path = category_path / subcategory
        ensure_directory_exists(subcategory_path)
        return subcategory_path
    else:
        # 只使用类别文件夹
        return category_path

def check_existing_knowledge(target_dir, new_knowledge):
    """检查是否存在类似知识文件"""
    # 检查目录中是否有文件包含类似主题
    for file in Path(target_dir).iterdir():
        if file.is_file() and file.suffix == '.txt':
            content = read_file(file)
            if is_related(content, new_knowledge):
                return file
    return None

def is_related(existing_content, new_content):
    """使用LLM判断知识是否相关"""
    try:
        prompt = f"""
        请判断以下两段知识是否相关：
        现有知识: {existing_content}
        新知识: {new_content}
        
        如果相关请回复"yes"，否则回复"no"（不要包含任何其他文本）
        """
        return invoke(prompt).strip().lower() == "yes"
    except Exception:
        return False

def update_existing_knowledge(filepath, new_knowledge):
    """更新现有知识文件"""
    try:
        existing_content = read_file(filepath)
        prompt = f"""
        请将新知识合并到现有知识中，确保内容简洁且不重复：
        现有知识: {existing_content}
        新知识: {new_knowledge}
        
        请按以下步骤操作：
        1. 识别现有知识和新知识中的重复内容
        2. 保留现有知识中的有价值信息
        3. 添加新知识中的补充信息
        4. 删除过时或错误的信息
        5. 确保最终内容结构清晰，没有重复
        
        请返回合并后的完整知识内容（不要包含任何其他文本）
        """
        return invoke(prompt)
    except Exception:
        # 如果更新失败，返回新知识
        return new_knowledge