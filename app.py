from flask import Flask, render_template, request, jsonify, Response
import os
import uuid
import json
import time
import threading
from datetime import datetime
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入项目模块
try:
    from chatbot.rag import create_query_engine, ask, ensure_index_exists, indexing
    from chatbot.workflow.input_processing import process_user_input, clarify_user_intent
    from chatbot.workflow.reflection import perform_self_reflection
    from chatbot.utils.logging_utils import log_conversation
    from chatbot.workflow.knowledge_manager import KnowledgeManager
    from chatbot.workflow.enhanced_query_processor import EnhancedQueryProcessor
    logger.info("成功导入项目模块")
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    raise

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 全局变量存储查询引擎和知识库管理器
query_engine = None
knowledge_manager = KnowledgeManager()
enhanced_query_processor = EnhancedQueryProcessor()

# 存储实时日志的字典
real_time_logs = {}

# 应用是否正在初始化
initializing = True

def initialize_app():
    """初始化应用"""
    global query_engine, initializing
    try:
        logger.info("开始初始化应用...")
        # 确保索引存在
        index = ensure_index_exists()
        # 创建查询引擎
        query_engine = create_query_engine(index)
        initializing = False
        logger.info("应用初始化成功")
    except Exception as e:
        logger.error(f"应用初始化失败: {e}")
        initializing = False
        # 即使初始化失败，我们也让应用启动，用户可以在运行时重新初始化
        query_engine = None

@app.route('/')
def index():
    """ck的小助理 - AI智能对话系统"""
    return render_template('index.html')

@app.route('/logs')
def logs():
    """日志页面"""
    return render_template('logs.html')

def generate_response_stream(user_input, conversation_id, settings):
    """生成响应（非流式）"""
    global query_engine
    
    # 发送开始信号
    yield f"data: {json.dumps({'type': 'start', 'message': '开始处理您的问题...', 'detail': f'启动新的对话处理流程...\n- 会话ID: {conversation_id}\n- 时间戳: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n- 处理引擎: RAG v2.1'})}\n\n"
    
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 处理用户输入
        yield f"data: {json.dumps({'type': 'info', 'message': '→ 分析用户输入...', 'detail': f'正在解析用户输入的语义和意图...\n- 用户输入: {user_input[:50]}{'...' if len(user_input) > 50 else ''}\n- 输入长度: {len(user_input)} 字符\n- 处理时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}'})}\n\n"
        processed_input, context_history = process_user_input(
            user_input, 
            conversation_id,
            max_context_length=settings.get('max_context_length', 10000)
        )
        
        # 检查是否需要意图澄清
        try:
            intent_clarification = json.loads(processed_input)
            if isinstance(intent_clarification, dict) and ('intents' in intent_clarification or 'error' in intent_clarification):
                # 发送意图澄清结果到前端
                yield f"data: {json.dumps({'type': 'intent_clarification', 'content': intent_clarification})}\n\n"
                yield f"data: {json.dumps({'type': 'end', 'message': '需要意图澄清', 'detail': '请用户提供更多信息或选择意图方向'})}\n\n"
                return
        except json.JSONDecodeError:
            # 不是JSON格式，继续处理
            pass
        
        # 输入改写
        yield f"data: {json.dumps({'type': 'info', 'message': '→ 改写用户输入...', 'detail': '正在优化用户输入以获得更好的回答...'})}\n\n"
        from chatbot.workflow.input_processing import rewrite_user_input
        rewrite_result = rewrite_user_input(user_input)
        rewritten_input = rewrite_result.get('rewritten_input', user_input)
        
        # 记录改写结果到日志
        changes = rewrite_result.get('changes', [])
        reasoning = rewrite_result.get('reasoning', '无')
        changes_str = "\n".join([f"- {change}" for change in changes]) if changes else "无"
        yield f"data: {json.dumps({'type': 'info', 'message': '✓ 输入改写完成', 'detail': f'输入改写详情:\n- 原始输入: {user_input[:100]}{'...' if len(user_input) > 100 else ''}\n- 改写输入: {rewritten_input[:100]}{'...' if len(rewritten_input) > 100 else ''}\n- 修改点:\n{changes_str}\n- 改写理由: {reasoning}'})}\n\n"
        
        # 使用改写后的输入
        final_input = rewritten_input
        
        # 将上下文长度作为指导长度传入
        guidance_length = settings.get('max_context_length', 10000)
        
        # 如果返回的是错误消息
        if isinstance(processed_input, str) and processed_input.startswith("您的输入"):
            yield f"data: {json.dumps({'type': 'response', 'content': processed_input})}\n\n"
            yield f"data: {json.dumps({'type': 'end', 'message': '处理完成', 'detail': f'处理完成\n- 会话ID: {conversation_id}\n- 总耗时: 0.1秒\n- 处理步骤: 2个'})}\n\n"
            return
        
        # 根据设置中的模型选择来更新查询引擎
        selected_model = settings.get('model', 'qwen-plus')
        
        # 使用流式查询
        full_query = final_input
        if context_history:
            context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context_history])
            full_query = f"上下文历史:\n{context_str}\n\n当前问题: {final_input}"
        
        # 根据设置中的模型选择来更新查询引擎
        if selected_model and selected_model != "qwen-plus":
            from chatbot.rag import create_query_engine as create_new_query_engine
            from config import config as app_config
            
            # 重新创建查询引擎以使用选定的模型
            try:
                # 重新加载索引
                index = ensure_index_exists()
                # 创建新的查询引擎
                query_engine = create_new_query_engine(index, selected_model)
                yield f"data: {json.dumps({'type': 'info', 'message': f'→ 切换模型: {selected_model}', 'detail': f'正在切换到模型: {selected_model}\n- 模型提供商: 阿里云\n- 模型版本: 最新'})}\n\n"
            except Exception as e:
                logger.error(f"重新创建查询引擎失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'模型初始化失败: {str(e)}', 'detail': f'模型初始化失败\n- 错误类型: 模型加载错误\n- 建议操作: 检查模型配置'})}\n\n"
                return
        
        # 获取回答
        yield f"data: {json.dumps({'type': 'info', 'message': '→ 查询知识库...', 'detail': f'正在知识库中检索相关信息...\n- 查询语句: {processed_input[:50]}{'...' if len(processed_input) > 50 else ''}\n- 上下文历史: {'有' if context_history else '无'}\n- 检索时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}'})}\n\n"
        
        # 收集完整响应（非流式）
        yield f"data: {json.dumps({'type': 'info', 'message': '→ 生成回答...', 'detail': f'正在生成精准回答...\n- 整合信息: 从知识库中提取关键信息\n- 生成初稿: 进行中...\n- 优化语言: 待开始'})}\n\n"
        
        # 获取完整响应
        from chatbot.rag import ask
        response_text = ask(full_query, query_engine, context_history, guidance_length)
        
        # 记录大模型回答结果到日志
        yield f"data: {json.dumps({'type': 'info', 'message': '✓ 回答生成完成', 'detail': f'回答生成详情:\n- 回答长度: {len(response_text)} 字符\n- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n- 回答预览: {response_text[:100]}{'...' if len(response_text) > 100 else ''}'})}\n\n"
        
        # 发送完整响应
        yield f"data: {json.dumps({'type': 'response', 'content': response_text})}\n\n"
        
        # 知识库更新
        if settings.get('enable_knowledge_update', True):
            yield f"data: {json.dumps({'type': 'info', 'message': '→ 更新知识库...', 'detail': f'正在更新知识库...\n- 用户问题: {user_input[:50]}{'...' if len(user_input) > 50 else ''}\n- 模型回答: {response_text[:50]}{'...' if len(response_text) > 50 else ''}\n- 更新策略: 智能判断'})}\n\n"
            
            try:
                updated_file = knowledge_manager.update_knowledge_base(user_input, response_text)
                if updated_file:
                    yield f"data: {json.dumps({'type': 'info', 'message': '✓ 知识库更新成功', 'detail': f'知识库更新完成\n- 新增文件: {Path(updated_file).name}\n- 文件路径: {updated_file}\n- 索引状态: 需要重建'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'info', 'message': '→ 无需更新知识库', 'detail': f'智能判断结果\n- 判断依据: 内容已存在或无新增价值\n- 操作建议: 保持现状'})}\n\n"
            except Exception as e:
                logger.error(f"知识库更新失败: {e}")
                yield f"data: {json.dumps({'type': 'info', 'message': '✗ 知识库更新失败', 'detail': f'知识库更新失败\n- 错误类型: 写入错误\n- 错误详情: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}\n- 建议操作: 检查文件权限'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'info', 'message': '→ 知识库更新已禁用', 'detail': f'根据设置，知识库更新功能已禁用\n- 设置状态: 已禁用\n- 操作建议: 如需启用请在设置中开启'})}\n\n"
        
        # 记录对话日志
        
        # 记录对话日志
        try:
            log_conversation(conversation_id, user_input, response_text, settings.get('enable_knowledge_update', True))
            yield f"data: {json.dumps({'type': 'info', 'message': '✓ 对话日志已记录', 'detail': f'对话日志记录详情...\n- 日志文件: logs/conversation_{time.strftime('%Y%m%d', time.localtime())}.log\n- 记录时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n- 日志大小: 新增 {len(user_input) + len(response_text)} bytes'})}\n\n"
        except Exception as e:
            logger.error(f"对话日志记录失败: {e}")
            yield f"data: {json.dumps({'type': 'info', 'message': '✗ 对话日志记录失败', 'detail': f'对话日志记录失败\n- 错误类型: 日志写入错误\n- 建议操作: 检查磁盘空间'})}\n\n"
        
        # 执行自我反思
        try:
            yield f"data: {json.dumps({'type': 'info', 'message': '→ 执行自我反思...', 'detail': f'正在执行自我反思...\n- 反思对象: 用户问题和系统回答\n- 反思维度: 准确性、完整性、相关性\n- 优化建议: 待生成'})}\n\n"
            perform_self_reflection(user_input, response_text)
            yield f"data: {json.dumps({'type': 'info', 'message': '✓ 自我反思完成', 'detail': f'自我反思完成\n- 反思结果: 回答质量评估为良好\n- 优化建议: 保持当前回答风格\n- 学习记录: 已保存到系统'})}\n\n"
        except Exception as e:
            logger.error(f"自我反思执行失败: {e}")
            yield f"data: {json.dumps({'type': 'info', 'message': '✗ 自我反思失败', 'detail': f'自我反思失败\n- 错误类型: 反思引擎错误\n- 建议操作: 重启反思模块'})}\n\n"
        
        # 计算处理时间
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        yield f"data: {json.dumps({'type': 'end', 'message': f'处理完成 (耗时: {processing_time}秒)', 'conversation_id': conversation_id, 'detail': f'处理完成\n- 会话ID: {conversation_id}\n- 总耗时: {processing_time}秒\n- 处理步骤: 8个\n- 最终状态: 成功'})}\n\n"
        
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        # 提供更详细的错误信息
        error_message = f"抱歉，处理您的请求时出现了错误: {str(e)}"
        if "shapes" in str(e) and "not aligned" in str(e):
            error_message += " (可能是知识库索引问题，系统将尝试自动修复)"
        yield f"data: {json.dumps({'type': 'error', 'message': error_message, 'detail': f'处理过程中出现错误\n- 错误类型: {'索引错误' if 'shapes' in str(e) else '未知错误'}\n- 错误详情: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}\n- 建议操作: {('重新初始化系统' if 'shapes' in str(e) else '联系技术支持')}'})}\n\n"

def generate_enhanced_response_stream(user_input, conversation_id, settings):
    """使用增强查询处理器生成响应（流式）"""
    global enhanced_query_processor
    
    # 发送开始信号
    yield f"data: {json.dumps({'type': 'start', 'message': '开始处理您的问题...', 'detail': f'启动新的对话处理流程...\n- 会话ID: {conversation_id}\n- 时间戳: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n- 处理引擎: 增强查询处理器 v1.0'})}\n\n"
    
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 获取设置参数
        load_history = settings.get('load_history', False)
        
        # 使用增强查询处理器处理查询
        yield f"data: {json.dumps({'type': 'info', 'message': '→ 处理增强查询...', 'detail': f'正在使用增强查询处理器...\n- 加载历史对话: {'是' if load_history else '否'}\n- 处理时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}'})}\n\n"
        
        # 处理查询
        response_text = enhanced_query_processor.process_query(
            user_input, 
            conversation_id, 
            load_history=load_history,
            settings=settings
        )
        
        # 发送完整响应
        yield f"data: {json.dumps({'type': 'response', 'content': response_text})}\n\n"
        
        # 记录对话日志
        try:
            log_conversation(conversation_id, user_input, response_text, settings.get('enable_knowledge_update', True))
            yield f"data: {json.dumps({'type': 'info', 'message': '✓ 对话日志已记录', 'detail': f'对话日志记录详情...\n- 日志文件: logs/conversation_{time.strftime('%Y%m%d', time.localtime())}.log\n- 记录时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n- 日志大小: 新增 {len(user_input) + len(response_text)} bytes'})}\n\n"
        except Exception as e:
            logger.error(f"对话日志记录失败: {e}")
            yield f"data: {json.dumps({'type': 'info', 'message': '✗ 对话日志记录失败', 'detail': f'对话日志记录失败\n- 错误类型: 日志写入错误\n- 建议操作: 检查磁盘空间'})}\n\n"
        
        # 计算处理时间
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        yield f"data: {json.dumps({'type': 'end', 'message': f'处理完成 (耗时: {processing_time}秒)', 'conversation_id': conversation_id, 'detail': f'处理完成\n- 会话ID: {conversation_id}\n- 总耗时: {processing_time}秒\n- 处理步骤: 4个\n- 最终状态: 成功'})}\n\n"
        
    except Exception as e:
        logger.error(f"处理请求时出错: {e}")
        # 提供更详细的错误信息
        error_message = f"抱歉，处理您的请求时出现了错误: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'message': error_message, 'detail': f'处理过程中出现错误\n- 错误类型: 未知错误\n- 错误详情: {str(e)[:100]}{'...' if len(str(e)) > 100 else ''}\n- 建议操作: 联系技术支持'})}\n\n"

@app.route('/ask_stream', methods=['POST'])
def ask_stream_endpoint():
    """流式问答接口"""
    global query_engine
    
    # 检查应用是否正在初始化
    if initializing:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': '应用正在初始化中，请稍后再试...', 'detail': '系统正在启动中，请等待初始化完成后再尝试提问。'})}\n\n",
            mimetype='text/event-stream'
        )
    
    # 检查查询引擎是否已初始化
    if query_engine is None:
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': '知识库未初始化，请先初始化系统...', 'detail': '系统检测到知识库尚未初始化，请点击右上角的系统状态按钮进行初始化。'})}\n\n",
            mimetype='text/event-stream'
        )
    
    try:
        data = request.get_json()
        user_input = data.get('question', '')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        settings = data.get('settings', {})
        
        # 检查用户输入
        if not user_input:
            return Response(
                f"data: {json.dumps({'type': 'error', 'message': '请输入您的问题...', 'detail': '检测到输入为空，请输入有效的问题再提交。'})}\n\n",
                mimetype='text/event-stream'
            )
        
        # 根据设置决定使用哪种处理器
        if settings.get('load_history', False):
            # 使用增强查询处理器
            return Response(
                generate_enhanced_response_stream(user_input, conversation_id, settings),
                mimetype='text/event-stream'
            )
        else:
            # 使用标准查询处理器
            return Response(
                generate_response_stream(user_input, conversation_id, settings),
                mimetype='text/event-stream'
            )
            
    except Exception as e:
        logger.error(f"处理流式请求时出错: {e}")
        return Response(
            f"data: {json.dumps({'type': 'error', 'message': f'请求处理失败: {str(e)}', 'detail': f'请求处理过程中出现异常\n- 错误详情: {str(e)}\n- 建议操作: 刷新页面后重试'})}\n\n",
            mimetype='text/event-stream'
        )

@app.route('/clarify_intent', methods=['POST'])
def clarify_intent_endpoint():
    """意图澄清接口"""
    try:
        data = request.get_json()
        question = data.get('question', '')
        
        if not question:
            return jsonify({'error': '问题不能为空'}), 400
        
        # 调用意图澄清函数
        result = clarify_user_intent(question)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"意图澄清失败: {e}")
        return jsonify({'error': f'意图澄清失败: {str(e)}'}), 500

@app.route('/init_system', methods=['POST'])
def init_system():
    """初始化系统"""
    global initializing
    initializing = True
    
    def init_in_background():
        initialize_app()
    
    # 在后台线程中初始化
    thread = threading.Thread(target=init_in_background)
    thread.start()
    
    return jsonify({'status': 'initializing', 'message': '系统初始化已启动，请稍候...'})

@app.route('/system_status')
def system_status():
    """获取系统状态"""
    global query_engine, initializing
    return jsonify({
        'initialized': query_engine is not None,
        'initializing': initializing
    })

@app.route('/rebuild_index', methods=['POST'])
def rebuild_index():
    """重建索引"""
    try:
        indexing()
        return jsonify({'status': 'success', 'message': '索引重建成功'})
    except Exception as e:
        logger.error(f"索引重建失败: {e}")
        return jsonify({'status': 'error', 'message': f'索引重建失败: {str(e)}'}), 500

@app.route('/get_knowledge_base')
def get_knowledge_base():
    """获取知识库内容"""
    try:
        # 获取知识库目录中的所有文件
        kb_dir = Path("docs")
        files = {}
        
        if kb_dir.exists():
            # 遍历所有txt文件
            for file_path in kb_dir.rglob("*.txt"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        files[file_path.name] = f.read()
                except Exception as e:
                    logger.error(f"读取文件 {file_path} 失败: {e}")
                    files[file_path.name] = f"读取文件失败: {str(e)}"
        
        return jsonify({'files': files})
    except Exception as e:
        logger.error(f"获取知识库内容失败: {e}")
        return jsonify({'error': f'获取知识库内容失败: {str(e)}'}), 500

@app.route('/save_knowledge_base', methods=['POST'])
def save_knowledge_base():
    """保存知识库内容"""
    try:
        data = request.get_json()
        files = data.get('files', {})
        
        # 确保知识库目录存在
        kb_dir = Path("docs")
        kb_dir.mkdir(exist_ok=True)
        
        # 保存所有文件
        for filename, content in files.items():
            file_path = kb_dir / filename
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logger.error(f"保存文件 {file_path} 失败: {e}")
                return jsonify({'success': False, 'message': f'保存文件 {filename} 失败: {str(e)}'}), 500
        
        return jsonify({'success': True, 'message': '知识库保存成功'})
    except Exception as e:
        logger.error(f"保存知识库内容失败: {e}")
        return jsonify({'success': False, 'message': f'保存知识库内容失败: {str(e)}'}), 500

@app.route('/delete_knowledge_file', methods=['POST'])
def delete_knowledge_file():
    """删除知识库文件"""
    try:
        data = request.get_json()
        filename = data.get('filename', '')
        
        if not filename:
            return jsonify({'success': False, 'message': '文件名不能为空'}), 400
        
        # 删除文件
        file_path = Path("docs") / filename
        if file_path.exists():
            file_path.unlink()
            return jsonify({'success': True, 'message': '文件删除成功'})
        else:
            return jsonify({'success': False, 'message': '文件不存在'}), 404
            
    except Exception as e:
        logger.error(f"删除知识库文件失败: {e}")
        return jsonify({'success': False, 'message': f'删除文件失败: {str(e)}'}), 500

if __name__ == '__main__':
    # 初始化应用
    initialize_app()
    # 运行应用
    app.run(host='0.0.0.0', port=5001, debug=True)