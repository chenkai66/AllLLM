import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
from chatbot.llm import invoke
from chatbot.utils.file_utils import read_file, write_file, ensure_directory_exists

logger = logging.getLogger(__name__)

def search_knowledge_base(query: str, knowledge_base_dir: str = "docs") -> List[Dict]:
    """
    在知识库中搜索相关信息
    
    参数:
        query (str): 查询内容
        knowledge_base_dir (str): 知识库目录路径
        
    返回:
        List[Dict]: 匹配的文件信息列表
    """
    try:
        base_path = Path(knowledge_base_dir)
        if not base_path.exists():
            return []
        
        matched_files = []
        
        # 遍历所有txt文件
        for file_path in base_path.rglob("*.txt"):
            try:
                content = read_file(file_path)
                # 简单的关键词匹配（实际应用中应该使用更复杂的相似度计算）
                if query.lower() in content.lower():
                    matched_files.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "content": content,
                        "relevance": calculate_relevance(query, content)
                    })
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
        
        # 按相关性排序
        matched_files.sort(key=lambda x: x["relevance"], reverse=True)
        
        return matched_files[:5]  # 返回前5个最相关的文件
    except Exception as e:
        logger.error(f"搜索知识库失败: {e}")
        return []

def calculate_relevance(query: str, content: str) -> float:
    """
    计算查询与内容的相关性
    
    参数:
        query (str): 查询内容
        content (str): 内容
        
    返回:
        float: 相关性分数
    """
    # 简单的关键词匹配分数计算
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    
    if not query_words:
        return 0.0
    
    # 计算交集
    common_words = query_words.intersection(content_words)
    return len(common_words) / len(query_words)

def should_update_knowledge_base(user_input: str, model_response: str, knowledge_base_dir: str = "docs") -> bool:
    """
    判断是否应该更新知识库
    
    参数:
        user_input (str): 用户输入
        model_response (str): 模型回复
        knowledge_base_dir (str): 知识库目录路径
        
    返回:
        bool: 是否应该更新知识库
    """
    try:
        # 搜索相关知识
        matched_files = search_knowledge_base(user_input, knowledge_base_dir)
        
        # 如果没有找到相关知识，则应该更新
        if not matched_files:
            return True
        
        # 使用LLM判断是否需要更新
        prompt = f"""
        请判断是否需要将以下对话内容添加到知识库中：

        用户输入: {user_input}
        模型回复: {model_response}
        
        知识库中已有的相关信息:
        {chr(10).join([f"- {f['name']}: {f['content'][:200]}..." for f in matched_files[:3]])}
        
        判断标准：
        1. 如果模型回复包含新的、有价值的信息，则应该更新
        2. 如果模型回复只是重复已有信息，则不需要更新
        3. 如果模型回复是通用的、无特定价值的信息，则不需要更新
        
        请回答"yes"或"no"，不要包含其他内容。
        """
        
        result = invoke(prompt).strip().lower()
        return result == "yes"
    except Exception as e:
        logger.error(f"判断是否更新知识库失败: {e}")
        # 默认情况下，如果出现错误，我们仍然更新知识库以确保不丢失信息
        return True

def update_knowledge_base(user_input: str, model_response: str, knowledge_base_dir: str = "docs"):
    """
    根据对话内容更新知识库
    
    参数:
        user_input (str): 用户输入
        model_response (str): 模型回复
        knowledge_base_dir (str): 知识库目录路径
        
    返回:
        str: 更新的文件路径
    """
    try:
        # 首先判断是否需要更新
        if not should_update_knowledge_base(user_input, model_response, knowledge_base_dir):
            logger.info("判断无需更新知识库")
            return None
        
        # 1. 提取结构化知识
        knowledge_prompt = """请从以下对话中提取有价值的知识点，格式化为结构化的知识：

用户输入: {user_input}
模型回复: {model_response}

请按照以下格式提取知识：
## 主题
[简要描述对话的核心主题]

## 关键信息
- [关键信息点1]
- [关键信息点2]
- ...

## 详细内容
[详细的内容描述]

## 应用场景
[该知识的可能应用场景]
"""
        full_prompt = knowledge_prompt.format(user_input=user_input, model_response=model_response)
        structured_knowledge = invoke(full_prompt)
        
        # 2. 确定知识类别
        category = determine_knowledge_category(user_input, structured_knowledge, knowledge_base_dir)
        category_dir = Path(knowledge_base_dir) / category
        ensure_directory_exists(category_dir)
        
        # 3. 生成文件名
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{category}_{timestamp}.txt"
        filepath = category_dir / filename
        
        # 4. 写入文件
        write_file(filepath, structured_knowledge)
        
        logger.info(f"知识库更新完成: {filepath}")
        return str(filepath)
    except Exception as e:
        logger.error(f"更新知识库失败: {e}")
        raise

def determine_knowledge_category(user_input: str, knowledge: str, knowledge_base_dir: str) -> str:
    """
    使用LLM确定知识类别
    
    参数:
        user_input (str): 用户输入
        knowledge (str): 提取的知识
        knowledge_base_dir (str): 知识库目录路径
        
    返回:
        str: 知识类别
    """
    try:
        # 获取现有类别
        base_path = Path(knowledge_base_dir)
        existing_categories = []
        if base_path.exists():
            for item in base_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):  # 忽略隐藏目录
                    existing_categories.append(item.name)
        
        # 构建更详细的提示
        prompt = f"""
        作为ck的智能知识管理助手，您的任务是根据以下用户输入和提取的知识确定最相关的知识类别：

        现有类别: {', '.join(existing_categories) if existing_categories else '无'}
        
        用户输入: {user_input}
        提取的知识: {knowledge}
        
        要求：
        1. 如果现有类别中有合适的，请选择一个最匹配的
        2. 如果没有合适的，请创建一个新的类别（使用简洁的中文词语）
        3. 类别名称应准确反映知识内容的核心主题
        4. 优先使用标准化的专业术语
        5. 类别名称长度不超过10个汉字
        6. 只回复类别名称，不要包含任何其他解释性文字
        7. 如果内容质量较低或无实际价值，回复"无效内容"
        
        请提供最恰当的类别名称：
        """
        
        category = invoke(prompt, max_tokens=50).strip()
        
        # 验证和清理类别名称
        if not category or category == "无效内容":
            return "未分类"
            
        # 确保类别名称是有效的目录名
        import re
        category = re.sub(r'[^\w\u4e00-\u9fff\-_]', '_', category)
        category = re.sub(r'_+', '_', category)  # 合并多个下划线
        category = category.strip('_')  # 去除首尾下划线
        
        # 如果处理后的类别名为空或过短，使用默认值
        if len(category) < 1:
            return "未分类"
        elif len(category) > 20:  # 限制长度
            category = category[:20]
            
        return category
    except Exception as e:
        logger.error(f"确定知识类别失败: {e}")
        return "未分类"