from flask import Flask, render_template, request, jsonify
from chatbot.rag import create_query_engine, ask
from chatbot.update_knowledge import update_knowledge_base
from chatbot.workflow.input_processing import process_user_input
import uuid
import os

app = Flask(__name__)

# 初始化查询引擎
index = load_index("data/knowledge_base")
query_engine = create_query_engine(index)

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_endpoint():
    """问答接口"""
    data = request.json
    user_input = data.get('question')
    conversation_id = data.get('conversation_id', str(uuid.uuid4()))
    settings = data.get('settings', {})
    
    # 处理用户输入
    processed_input, context_history = process_user_input(
        user_input, 
        conversation_id,
        max_context_length=settings.get('max_context_length', 10000)
    )
    
    # 如果返回的是错误消息
    if isinstance(processed_input, str) and processed_input.startswith("您的输入"):
        return jsonify({
            "response": processed_input,
            "conversation_id": conversation_id
        })
    
    # 获取回答
    response = ask(processed_input, query_engine, context_history=context_history)
    
    # 知识库更新
    if settings.get('enable_knowledge_update', True):
        update_knowledge_base(user_input, response)
    
    return jsonify({
        "response": response,
        "conversation_id": conversation_id
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)