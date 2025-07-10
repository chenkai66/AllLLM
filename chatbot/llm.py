import os
import json
from datetime import datetime
from openai import OpenAI
from chatbot.utils.logging_utils import log_conversation  # 修复导入
from chatbot.workflow.conversation_log import save_conversation_log

client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

def invoke(user_message, model_name="qwen-plus-0919", conversation_id=None, context_history=None):
    """
    扩展的LLM调用函数，支持多轮对话和日志记录
    
    参数:
        user_message (str): 用户输入消息
        model_name (str): 模型名称，默认为"qwen-plus-0919"
        conversation_id (str): 对话ID，用于关联多轮对话
        context_history (list): 历史对话上下文
        
    返回:
        str: 模型生成的回复内容
    """
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
    
    # 记录对话日志
    if conversation_id:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "user_input": user_message,
            "model_response": response
        }
        log_conversation(conversation_id, user_message, response)  # 使用正确的函数
    
    return response

def invoke_with_stream_log(user_message, model_name="qwen-plus-0919", conversation_id=None):
    """流式输出版本，支持日志记录"""
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
    
    # 记录对话日志
    if conversation_id:
        log_conversation(conversation_id, user_message, result)
    
    return result