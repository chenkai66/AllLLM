import os
import json
from datetime import datetime
import logging
from openai import OpenAI
from config import config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API密钥索引和客户端列表
_api_key_index = 0
_clients = []

# 初始化客户端列表
def _initialize_clients():
    global _clients
    _clients = []
    for i, api_key in enumerate(config.DASHSCOPE_API_KEYS):
        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            _clients.append(client)
            logger.info(f"DashScope客户端 {i} 初始化成功")
        except Exception as e:
            logger.error(f"DashScope客户端 {i} 初始化失败: {e}")

# 在模块加载时初始化客户端
_initialize_clients()

# 更新配置中的当前API密钥索引
def _update_config_api_key_index(index):
    """更新配置中的当前API密钥索引，用于日志记录"""
    config.DASHSCOPE_API_KEY_INDEX = index

def _get_current_client():
    """获取当前使用的客户端"""
    global _api_key_index
    if not _clients:
        raise RuntimeError("没有可用的DashScope客户端")
    return _clients[_api_key_index]

def _rotate_api_key():
    """切换到下一个API密钥"""
    global _api_key_index
    if not _clients:
        raise RuntimeError("没有可用的DashScope客户端")
    
    _api_key_index = (_api_key_index + 1) % len(_clients)
    _update_config_api_key_index(_api_key_index)
    logger.info(f"切换到API密钥索引 {_api_key_index}")

def invoke(user_message, model_name="qwen-plus-0919", conversation_id=None, context_history=None):
    """
    扩展的LLM调用函数，支持多轮对话、API密钥轮询和日志记录
    
    参数:
        user_message (str): 用户输入消息
        model_name (str): 模型名称，默认为"qwen-plus-0919"
        conversation_id (str): 对话ID，用于关联多轮对话
        context_history (list): 历史对话上下文
        
    返回:
        str: 模型生成的回复内容
    """
    global _api_key_index
    max_retries = len(config.DASHSCOPE_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            client = _get_current_client()
            messages = [{"role": "system", "content": "你是一个乐于助人的助手"}]
            
            # 添加上下文历史
            if context_history:
                messages.extend(context_history)
            
            messages.append({"role": "user", "content": user_message})
            
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages
            )
            
            response = completion.choices[0].message.content
            
            return response
        except Exception as e:
            logger.error(f"调用LLM时出错 (API密钥索引 {_api_key_index}): {e}")
            # 如果是最后一次尝试，直接抛出异常
            if attempt == max_retries - 1:
                raise RuntimeError(f"调用LLM失败，所有API密钥都已尝试: {str(e)}")
            
            # 切换到下一个API密钥
            _rotate_api_key()

def invoke_with_stream_log(user_message, model_name="qwen-plus-0919", conversation_id=None):
    """流式输出版本，支持API密钥轮询和日志记录"""
    global _api_key_index
    max_retries = len(config.DASHSCOPE_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            client = _get_current_client()
            messages = [{"role": "system", "content": "你是一个乐于助人的助手"}]
            messages.append({"role": "user", "content": user_message})
            
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True
            )
            
            result = ""
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    result += content
                    print(content, end="")
            
            return result
        except Exception as e:
            logger.error(f"流式调用LLM时出错 (API密钥索引 {_api_key_index}): {e}")
            # 如果是最后一次尝试，直接抛出异常
            if attempt == max_retries - 1:
                raise RuntimeError(f"流式调用LLM失败，所有API密钥都已尝试: {str(e)}")
            
            # 切换到下一个API密钥
            _rotate_api_key()