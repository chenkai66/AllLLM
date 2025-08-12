import sys
import os
import logging
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chatbot.llm import invoke
from chatbot.workflow.input_processing import process_user_input
from chatbot.update_knowledge import update_knowledge_base
from chatbot.rag import ensure_index_exists, create_query_engine

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_full_workflow():
    """测试完整工作流（带错误处理）"""
    try:
        # 确保索引存在
        logger.info("检查索引...")
        index = ensure_index_exists("data/knowledge_base")
        
        # 创建查询引擎
        logger.info("创建查询引擎...")
        query_engine = create_query_engine(index)
        conversation_id = "test_conv_789"
        
        # 处理用户输入
        logger.info("处理用户输入...")
        user_input = "如何提高团队协作效率？"
        processed_input, context_history = process_user_input(
            user_input, 
            conversation_id
        )
        
        # 获取回答
        logger.info("获取模型回答...")
        response = invoke(processed_input, conversation_id=conversation_id, context_history=context_history)
        
        # 更新知识库
        logger.info("更新知识库...")
        knowledge_file = update_knowledge_base(user_input, response)
        
        # 打印结果
        print(f"用户输入: {user_input}")
        print(f"模型回答: {response}")
        print(f"知识库更新到: {knowledge_file}")
        print("✅ 完整工作流测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        print(f"❌ 测试失败: {str(e)}")
        # 提供有用的调试建议
        print("\n调试建议:")
        print("1. 检查 .env 文件中的 DASHSCOPE_API_KEY 是否正确")
        print("2. 确保网络连接正常，可以访问 https://dashscope.aliyuncs.com")
        print("3. 运行 `python -m chatbot.rag indexing` 手动创建索引")
        print("4. 检查文档目录 ./docs 是否包含有效文档")

if __name__ == "__main__":
    test_full_workflow()