from chatbot.workflow.knowledge_update import update_knowledge_base
import os
import shutil

def test_knowledge_update():
    """测试知识更新功能"""
    # 准备测试环境
    test_dir = "test_knowledge"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 测试用例
    test_cases = [
        {
            "input": "如何提高团队协作效率？",
            "response": "可以使用Slack进行团队沟通，Trello进行任务管理，定期举行站会同步进度。"
        },
        {
            "input": "项目管理的最佳实践是什么？",
            "response": "敏捷开发方法如Scrum或Kanban是不错的选择，结合Jira等工具进行项目管理。"
        }
    ]
    
    # 执行测试
    for case in test_cases:
        result = update_knowledge_base(case["input"], case["response"], knowledge_base_dir=test_dir)
        print(f"知识更新到: {result}")
    
    # 检查结果
    assert os.path.exists(os.path.join(test_dir, "teamwork"))
    assert os.path.exists(os.path.join(test_dir, "management"))
    
    print("✅ 知识更新测试通过")

if __name__ == "__main__":
    test_knowledge_update()