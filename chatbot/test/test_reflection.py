from chatbot.workflow.reflection import analyze_user_preference, perform_self_reflection
import os
import shutil
import csv

def test_reflection():
    """测试反思功能"""
    # 准备测试环境
    test_dir = "test_user_data"
    os.makedirs(test_dir, exist_ok=True)
    
    # 测试用户偏好分析
    analyze_user_preference("如何提高团队效率？", "test_conv_456")
    
    # 验证文件创建
    assert os.path.exists("data/user_data/user_preference.csv")
    
    # 测试自我反思
    perform_self_reflection("这个问题不清楚", "请提供更多细节")
    
    # 验证文件创建
    assert os.path.exists("data/user_data/self_reflection.csv")
    
    print("✅ 反思功能测试通过")

if __name__ == "__main__":
    test_reflection()