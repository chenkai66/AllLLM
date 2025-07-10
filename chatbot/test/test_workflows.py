import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chatbot.llm import invoke
from chatbot.workflow.input_processing import process_user_input
from chatbot.update_knowledge import update_knowledge_base
from chatbot.rag import create_query_engine, load_index

def test_full_workflow():
    """测试完整工作流"""
    # 初始化
    index = load_index("data/knowledge_base")
    query_engine = create_query_engine(index)
    conversation_id = "test_conv_789"
    
    # 处理用户输入
    user_input = "如何提高团队协作效率？"
    processed_input, context_history = process_user_input(
        user_input, 
        conversation_id
    )
    
    # 获取回答
    response = invoke(processed_input, conversation_id=conversation_id, context_history=context_history)
    
    # 更新知识库
    knowledge_file = update_knowledge_base(user_input, response)
    
    # 打印结果
    print(f"用户输入: {user_input}")
    print(f"模型回答: {response}")
    print(f"知识库更新到: {knowledge_file}")
    print("✅ 完整工作流测试完成")

if __name__ == "__main__":
    test_full_workflow()