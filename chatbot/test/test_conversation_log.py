from chatbot.workflow.conversation_log import save_conversation_log, load_recent_conversations
import os
import shutil
from datetime import datetime, timedelta

def test_conversation_log():
    """测试对话日志功能"""
    # 准备测试环境
    test_dir = "test_logs"
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试数据
    test_data = {
        "timestamp": datetime.now().isoformat(),
        "conversation_id": "test_conv_123",
        "user_input": "测试问题",
        "model_response": "测试回答",
        "knowledge_updated": True,
        "knowledge_file": "test_knowledge.txt"
    }
    
    # 保存日志
    save_conversation_log(test_data)
    
    # 加载日志
    logs = load_recent_conversations("test_conv_123")
    
    # 验证结果
    assert len(logs) > 0
    assert logs[0]['user_input'] == "测试问题"
    assert logs[0]['model_response'] == "测试回答"
    
    print("✅ 对话日志测试通过")

if __name__ == "__main__":
    test_conversation_log()