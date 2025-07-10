from .conversation_log import load_recent_conversations
from .reflection import analyze_user_preference
from chatbot.llm import invoke

def process_user_input(user_input, conversation_id, max_context_length=10000):
    """
    处理用户输入的工作流
    
    参数:
        user_input (str): 用户输入
        conversation_id (str): 对话ID
        max_context_length (int): 最大上下文长度
        
    返回:
        tuple: (处理后的输入, 上下文历史)
    """
    # 1. 判断输入清晰度
    clarity = assess_input_clarity(user_input)
    
    if not clarity:
        # 如果不清晰，请求澄清
        return "您的输入不够清晰，请提供更多细节", []
    
    # 2. 加载最近对话
    recent_conversations = load_recent_conversations(conversation_id)
    
    # 3. 总结对话历史
    summary = summarize_conversation_history(recent_conversations)
    
    # 4. 判断是否需要详细上下文
    need_full_context = determine_context_need(user_input, summary)
    
    # 5. 构建上下文历史
    if need_full_context:
        context_history = truncate_conversations(recent_conversations, max_context_length)
    else:
        context_history = [{"role": "system", "content": summary}]
    
    # 6. 分析用户偏好
    analyze_user_preference(user_input, conversation_id)
    
    return user_input, context_history

def assess_input_clarity(user_input):
    """使用LLM评估输入清晰度"""
    prompt = f"""
    请判断以下用户输入是否清晰明确：
    "{user_input}"
    
    如果清晰请回复"clear"，否则回复"unclear"（不要包含任何其他文本）
    """
    return invoke(prompt).strip().lower() == "clear"

def summarize_conversation_history(conversations):
    """总结对话历史"""
    prompt = "请总结以下对话历史的关键信息:\n"
    for conv in conversations:
        prompt += f"用户: {conv['user_input']}\n助手: {conv['model_response']}\n"
    prompt += "\n总结:"
    return invoke(prompt)

def determine_context_need(user_input, summary):
    """判断是否需要详细上下文"""
    prompt = f"""
    基于以下对话总结和当前用户输入，判断是否需要加载完整对话上下文：
    对话总结: {summary}
    当前输入: {user_input}
    
    如果需要完整上下文请回复"yes"，否则回复"no"（不要包含任何其他文本）
    """
    return invoke(prompt).strip().lower() == "yes"

def truncate_conversations(conversations, max_length):
    """反向截断对话历史"""
    # 从最新对话开始反向添加，直到达到最大长度
    truncated = []
    current_length = 0
    
    for conv in reversed(conversations):
        conv_text = f"用户: {conv['user_input']}\n助手: {conv['model_response']}"
        if current_length + len(conv_text) > max_length:
            break
        truncated.insert(0, conv)
        current_length += len(conv_text)
    
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": conv['user_input' if i % 2 == 0 else 'model_response']} 
            for i, conv in enumerate(truncated)]