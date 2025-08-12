import logging
import json
from typing import Tuple, List, Dict, Optional, Union

from chatbot.workflow.conversation_log import load_recent_conversations
from chatbot.workflow.reflection import analyze_user_preference
from chatbot.llm import invoke
from chatbot.utils.file_utils import read_file

# 配置日志
logger = logging.getLogger(__name__)

def process_user_input(user_input: str, conversation_id: str, max_context_length: int = 10000) -> Tuple[str, List[Dict]]:
    """
    处理用户输入的工作流
    
    参数:
        user_input (str): 用户输入
        conversation_id (str): 对话ID
        max_context_length (int): 最大上下文长度
        
    返回:
        tuple: (处理后的输入, 上下文历史)
    """
    try:
        # 1. 判断输入清晰度
        clarity = assess_input_clarity(user_input)
        
        if not clarity:
            # 如果不清晰，进行意图澄清
            intent_clarification = clarify_user_intent(user_input)
            # 返回意图澄清结果，让前端处理
            return json.dumps(intent_clarification), []
        
        # 2. 加载最近对话
        recent_conversations = load_recent_conversations(conversation_id)
        
        # 3. 总结对话历史
        summary = summarize_conversation_history(recent_conversations)
        
        # 4. 判断是否需要详细上下文
        need_full_context = determine_context_need(user_input, summary, recent_conversations)
        
        # 5. 构建上下文历史
        if need_full_context:
            context_history = truncate_conversations(recent_conversations, max_context_length)
        else:
            context_history = [{"role": "system", "content": summary}]
        
        # 6. 分析用户偏好
        analyze_user_preference(user_input, conversation_id)
        
        return user_input, context_history
    except Exception as e:
        logger.error(f"处理用户输入时出错: {e}")
        return "抱歉，处理您的输入时出现了错误", []

def assess_input_clarity(user_input: str) -> bool:
    """使用LLM评估输入清晰度"""
    try:
        # 读取提示词模板
        prompt_template = read_file("chatbot/prompt/input_clarity.txt")
        if not prompt_template:
            prompt_template = """请判断以下用户输入是否清晰明确："{user_input}"\n\n如果清晰请回复"clear"，否则回复"unclear"（不要包含任何其他文本）"""
        
        prompt = prompt_template.format(user_input=user_input)
        return invoke(prompt).strip().lower() == "clear"
    except Exception as e:
        logger.warning(f"评估输入清晰度时出错，默认认为输入是清晰的: {e}")
        # 默认认为输入是清晰的
        return True

def clarify_user_intent(user_input: str) -> Dict:
    """
    使用LLM生成可能的用户意图方向
    
    参数:
        user_input (str): 用户输入
        
    返回:
        Dict: 包含可能意图方向的字典
    """
    try:
        # 读取提示词模板
        prompt_template = read_file("chatbot/prompt/intent_clarification.txt")
        if not prompt_template:
            prompt_template = """
作为ck的智能助理，您的任务是分析用户输入并提供可能的意图方向，让用户选择或补充信息。

用户输入: {user_input}

请按照以下步骤分析：

1. 识别用户输入中的核心主题和关键词
2. 基于核心主题，生成3-5个可能的用户意图方向
3. 为每个意图方向提供简短的描述
4. 如果用户输入不够清晰，请提供一个"需要更多信息"的选项

请严格按照以下JSON格式回复：

{
  "intents": [
    {
      "id": 1,
      "title": "意图方向1的简短标题",
      "description": "该意图方向的详细描述"
    },
    {
      "id": 2,
      "title": "意图方向2的简短标题",
      "description": "该意图方向的详细描述"
    }
  ],
  "need_more_info": {
    "title": "需要更多信息",
    "description": "您的问题不够清晰，请提供更多细节"
  }
}
"""
        
        prompt = prompt_template.format(user_input=user_input)
        response = invoke(prompt)
        
        # 解析JSON响应
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"解析意图澄清响应失败: {response}")
            # 返回默认结构
            return {
                "intents": [
                    {
                        "id": 1,
                        "title": "技术咨询",
                        "description": "用户希望了解某项技术的原理、应用或最新发展"
                    },
                    {
                        "id": 2,
                        "title": "操作指南",
                        "description": "用户需要关于如何使用某个工具或完成某项任务的指导"
                    }
                ],
                "need_more_info": {
                    "title": "需要更多信息",
                    "description": "您的问题不够清晰，请提供更多细节"
                }
            }
    except Exception as e:
        logger.error(f"澄清用户意图时出错: {e}")
        # 返回默认结构
        return {
            "intents": [
                {
                    "id": 1,
                    "title": "技术咨询",
                    "description": "用户希望了解某项技术的原理、应用或最新发展"
                },
                {
                    "id": 2,
                    "title": "操作指南",
                    "description": "用户需要关于如何使用某个工具或完成某项任务的指导"
                }
            ],
            "need_more_info": {
                "title": "需要更多信息",
                "description": "您的问题不够清晰，请提供更多细节"
            }
        }

def rewrite_user_input(user_input: str) -> Dict:
    """
    使用LLM改写用户输入，使其更加清晰和具体
    
    参数:
        user_input (str): 原始用户输入
        
    返回:
        Dict: 包含改写结果的字典
    """
    try:
        # 读取提示词模板
        prompt_template = read_file("chatbot/prompt/input_rewrite.txt")
        if not prompt_template:
            prompt_template = """请严格按照以下JSON格式回复：

{
  "rewritten_input": "改写后的用户输入",
  "changes": [
    "修改点1的简短描述",
    "修改点2的简短描述"
  ],
  "reasoning": "改写的原因和逻辑"
}"""
        
        prompt = prompt_template + f"\n\n原始用户输入: {user_input}"
        response = invoke(prompt)
        
        # 确保response不是None
        if response is None:
            logger.error("改写用户输入时LLM返回None")
            # 返回默认结构
            return {
                "rewritten_input": user_input,
                "changes": [],
                "reasoning": "LLM返回空响应"
            }
        
        # 解析JSON响应
        try:
            result = json.loads(response)
            # 验证必要的字段是否存在
            if not isinstance(result, dict) or "rewritten_input" not in result:
                logger.error(f"解析输入改写响应失败，缺少必要字段: {response}")
                # 返回默认结构
                return {
                    "rewritten_input": user_input,
                    "changes": [],
                    "reasoning": "响应格式不正确"
                }
            return result
        except json.JSONDecodeError:
            logger.error(f"解析输入改写响应失败: {response}")
            # 返回默认结构
            return {
                "rewritten_input": user_input,
                "changes": [],
                "reasoning": "无法改写输入"
            }
    except Exception as e:
        logger.error(f"改写用户输入时出错: {e}")
        # 返回默认结构
        return {
            "rewritten_input": user_input,
            "changes": [],
            "reasoning": "改写输入时出现错误"
        }

def summarize_conversation_history(conversations: List[Dict]) -> str:
    """总结对话历史"""
    try:
        if not conversations:
            return "这是新对话"
        
        prompt = "请总结以下对话历史的关键信息:\n"
        for conv in conversations:
            prompt += f"用户: {conv['user_input']}\n助手: {conv['model_response']}\n"
        prompt += "\n总结:"
        return invoke(prompt)
    except Exception as e:
        logger.warning(f"总结对话历史时出错，使用默认摘要: {e}")
        return "对话历史摘要"

def determine_context_need(user_input: str, summary: str, recent_conversations: List[Dict]) -> bool:
    """判断是否需要详细上下文"""
    try:
        # 检查是否与最近的问题重复
        if recent_conversations:
            last_entry = recent_conversations[-1]
            if isinstance(last_entry, dict):
                last_user_input = last_entry.get('user_input', '')
                # 确保last_user_input不是None
                if last_user_input is not None:
                    # 如果当前输入与最近的用户输入相同或非常相似，则需要上下文
                    if user_input.strip().lower() == last_user_input.strip().lower():
                        return True
        
        # 如果有对话历史，即使不是重复问题，也默认需要上下文
        if recent_conversations:
            return True
            
        prompt = f"""
        基于以下对话总结和当前用户输入，判断是否需要加载完整对话上下文：
        对话总结: {summary}
        当前输入: {user_input}
        
        如果需要完整上下文请回复"yes"，否则回复"no"（不要包含任何其他文本）
        """
        result = invoke(prompt)
        if result is not None:
            return result.strip().lower() == "yes"
        else:
            # 如果LLM返回None，默认需要上下文
            return True
    except Exception as e:
        logger.warning(f"判断上下文需求时出错，默认需要上下文: {e}")
        # 默认需要上下文
        return True

def truncate_conversations(conversations: List[Dict], max_length: int) -> List[Dict]:
    """反向截断对话历史"""
    try:
        # 从最新对话开始反向添加，直到达到最大长度
        truncated = []
        current_length = 0
        
        for conv in reversed(conversations):
            conv_text = f"用户: {conv['user_input']}\n助手: {conv['model_response']}"
            if current_length + len(conv_text) > max_length:
                break
            truncated.insert(0, conv)
            current_length += len(conv_text)
        
        # 转换为标准格式
        result = []
        for conv in truncated:
            result.append({"role": "user", "content": conv['user_input']})
            result.append({"role": "assistant", "content": conv['model_response']})
        
        return result
    except Exception as e:
        logger.error(f"截断对话历史时出错，返回空列表: {e}")
        # 如果截断失败，返回空列表
        return []