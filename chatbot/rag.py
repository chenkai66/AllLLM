import os
import logging
import shutil
from pathlib import Path
from typing import Optional
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
from llama_index.llms.dashscope import DashScope
from llama_index.llms.openai_like import OpenAILike
from config import config
from chatbot.utils.file_utils import ensure_directory_exists
from chatbot.llm import _clients, _api_key_index, _rotate_api_key

# 设置日志
logger = logging.getLogger(__name__)

def _get_current_api_key():
    """获取当前使用的API密钥"""
    return config.DASHSCOPE_API_KEYS[_api_key_index]

def _get_current_client():
    """获取当前使用的客户端"""
    if not _clients:
        raise RuntimeError("没有可用的DashScope客户端")
    return _clients[_api_key_index]

def indexing(document_path="./docs", persist_path="data/knowledge_base"):
    """
    创建索引并持久化存储（带错误处理）
    """
    max_retries = len(config.DASHSCOPE_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            # 确保目录存在
            ensure_directory_exists(persist_path)
            
            # 如果文档目录不存在或为空，创建一个示例文档
            doc_path = Path(document_path)
            if not doc_path.exists() or not any(doc_path.iterdir()):
                doc_path.mkdir(parents=True, exist_ok=True)
                example_file = doc_path / "default.txt"
                with open(example_file, "w", encoding='utf-8') as f:
                    f.write("这是默认的文档内容，用于初始化知识库。")
                logger.info(f"创建了示例文档: {example_file}")
            
            # 使用递归方式加载所有文档
            documents = SimpleDirectoryReader(document_path, recursive=True).load_data()
            
            # 检查是否有文档
            if not documents:
                logger.warning("未找到任何文档，创建空索引")
                # 创建一个空文档
                documents = [SimpleDirectoryReader.load_data_from_text("这是一个空的知识库。")]
            
            # 使用配置中的API密钥
            embed_model = DashScopeEmbedding(
                api_key=_get_current_api_key(),
                model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2
            )
            
            index = VectorStoreIndex.from_documents(
                documents,
                embed_model=embed_model
            )
            
            # 持久化存储
            index.storage_context.persist(persist_path)
            logger.info("索引创建成功")
            return index
            
        except Exception as e:
            logger.error(f"索引创建失败 (API密钥索引 {_api_key_index}): {str(e)}")
            # 如果是最后一次尝试，直接抛出异常
            if attempt == max_retries - 1:
                # 如果是维度不匹配的错误，尝试清理并重新创建
                if "shapes" in str(e) and "not aligned" in str(e):
                    logger.info("检测到embedding维度不匹配错误，尝试清理旧索引...")
                    try:
                        if os.path.exists(persist_path):
                            shutil.rmtree(persist_path)
                            logger.info("已删除旧索引目录")
                        # 重新创建索引
                        return indexing(document_path=document_path, persist_path=persist_path)
                    except Exception as cleanup_error:
                        logger.error(f"清理旧索引失败: {str(cleanup_error)}")
                raise RuntimeError("索引创建失败，请检查API密钥和网络连接") from e
            
            # 切换到下一个API密钥
            _rotate_api_key()

def load_index(persist_path="data/knowledge_base") -> Optional[VectorStoreIndex]:
    """
    加载索引
    
    Args:
        persist_path (str): 索引持久化路径
        
    Returns:
        Optional[VectorStoreIndex]: 索引对象，如果加载失败则返回None
    """
    max_retries = len(config.DASHSCOPE_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            # 检查索引文件是否存在
            persist_dir = Path(persist_path)
            docstore_path = persist_dir / "docstore.json"
            if not docstore_path.exists():
                logger.warning(f"索引文件不存在: {docstore_path}")
                return None
                
            storage_context = StorageContext.from_defaults(persist_dir=persist_path)
            index = load_index_from_storage(storage_context, embed_model=DashScopeEmbedding(
                model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2,
                api_key=_get_current_api_key()
            ))
            logger.info("索引加载成功")
            return index
        except Exception as e:
            logger.error(f"索引加载失败 (API密钥索引 {_api_key_index}): {str(e)}")
            # 如果是最后一次尝试，处理错误
            if attempt == max_retries - 1:
                # 如果是维度不匹配的错误，删除旧索引并重新创建
                if "shapes" in str(e) and "not aligned" in str(e):
                    logger.info("检测到embedding维度不匹配错误，删除旧索引并重新创建...")
                else:
                    logger.info("尝试删除旧索引并重新创建...")
                try:
                    if os.path.exists(persist_path):
                        shutil.rmtree(persist_path)
                    return None
                except Exception as cleanup_error:
                    logger.error(f"清理旧索引失败: {str(cleanup_error)}")
                    raise RuntimeError("无法加载索引，请检查知识库路径") from e
            
            # 切换到下一个API密钥
            _rotate_api_key()

def ensure_index_exists(persist_path="data/knowledge_base") -> VectorStoreIndex:
    """
    确保索引存在，如果不存在则创建
    
    Args:
        persist_path (str): 索引持久化路径
        
    Returns:
        VectorStoreIndex: 索引对象
    """
    try:
        index = load_index(persist_path)
        if index is None:
            logger.info("索引不存在，正在创建初始索引...")
            return indexing(persist_path=persist_path)
        return index
    except Exception as e:
        logger.error(f"确保索引存在时出错: {str(e)}")
        raise RuntimeError("无法确保索引存在") from e

def create_query_engine(index: VectorStoreIndex, model_name: str = "qwen-plus"):
    """
    创建查询引擎
    
    Args:
        index (VectorStoreIndex): 索引对象
        model_name (str): 模型名称，默认为 "qwen-plus"
        
    Returns:
        QueryEngine: 查询引擎对象
    """
    max_retries = len(config.DASHSCOPE_API_KEYS)
    
    for attempt in range(max_retries):
        try:
            # 如果model_name为空，使用默认值
            if not model_name:
                model_name = "qwen-plus"
                
            query_engine = index.as_query_engine(
                streaming=True,
                llm=OpenAILike(
                    model=model_name,
                    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    api_key=_get_current_api_key(),
                    is_chat_model=True
                )
            )
            logger.info(f"查询引擎创建成功，使用模型: {model_name}")
            return query_engine
        except Exception as e:
            logger.error(f"查询引擎创建失败 (API密钥索引 {_api_key_index}): {str(e)}")
            # 如果是最后一次尝试，尝试备选方案
            if attempt == max_retries - 1:
                # 使用默认的 DashScope 模型作为备选方案
                try:
                    from llama_index.llms.dashscope import DashScope
                    
                    query_engine = index.as_query_engine(
                        streaming=True,
                        llm=DashScope(
                            model=model_name,
                            api_key=_get_current_api_key()
                        )
                    )
                    logger.info(f"使用 DashScope 查询引擎创建成功，使用模型: {model_name}")
                    return query_engine
                except Exception as e2:
                    logger.error(f"备选查询引擎创建也失败了: {str(e2)}")
                    raise RuntimeError("查询引擎创建失败") from e
            
            # 切换到下一个API密钥
            _rotate_api_key()

def ask(question: str, query_engine, context_history: Optional[list] = None, guidance_length: Optional[int] = None) -> str:
    """
    问答函数，支持上下文历史和指导长度
    
    参数:
        question (str): 问题
        query_engine (QueryEngine): 查询引擎对象
        context_history (list, optional): 上下文历史
        guidance_length (int, optional): 指导长度
        
    返回:
        str: 回答内容
    """
    try:
        # 检查输入参数
        if not question:
            raise ValueError("问题不能为空")
            
        # 构建查询指令
        query_instruction = ""
        if guidance_length:
            if guidance_length > 50000:
                query_instruction = "请提供非常详细和全面的回答，包含丰富的技术细节和示例。"
            elif guidance_length > 20000:
                query_instruction = "请提供详细和深入的回答，包含必要的技术细节。"
            elif guidance_length > 10000:
                query_instruction = "请提供清晰和完整的回答，包含关键信息。"
            else:
                query_instruction = "请提供简洁明了的回答，突出重点。"
        
        # 如果有上下文历史，构建完整查询
        full_query = question
        if query_instruction:
            full_query = f"{query_instruction}\n\n问题: {question}"
            
        # 检查是否需要使用上下文历史
        use_context = False
        if context_history:
            # 检查上下文历史中是否包含重复问题
            user_questions = []
            for msg in context_history:
                if isinstance(msg, dict) and msg.get('role') == 'user' and msg.get('content'):
                    user_questions.append(msg['content'])
            
            # 确保question不是None再进行比较
            if user_questions and question and user_questions[-1]:
                if question.strip().lower() == user_questions[-1].strip().lower():
                    # 如果是重复问题，需要使用上下文
                    use_context = True
                    # 添加提示让模型基于上下文回答
                    full_query = f"用户重复了相同的问题，请基于之前的对话历史提供更准确的回答。\n\n{full_query}"
        
        # 只有在需要使用上下文时才添加上下文历史
        if use_context and context_history:
            # 构建上下文字符串，确保所有内容都不是None
            context_parts = []
            for msg in context_history:
                if isinstance(msg, dict):
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role and content:
                        context_parts.append(f"{role}: {content}")
            
            if context_parts:
                context_str = "\n".join(context_parts)
                full_query = f"上下文历史:\n{context_str}\n\n{full_query}"
        
        streaming_response = query_engine.query(full_query)
        
        # 收集流式响应
        response_text = ""
        for text in streaming_response.response_gen:
            if text:  # 确保text不是None
                response_text += text
        
        return response_text
    except Exception as e:
        logger.error(f"问答处理失败: {str(e)}")
        raise RuntimeError("问答处理失败") from e

def main():
    """
    测试RAG功能的主函数
    """
    # 初始化日志
    logging.basicConfig(level=logging.INFO)
    logger.info("开始测试RAG功能...")
    
    try:
        # 确保索引存在（自动创建或加载）
        index = ensure_index_exists()
        logger.info("索引准备就绪")
        
        # 创建查询引擎
        query_engine = create_query_engine(index)
        logger.info("查询引擎创建成功")
        
        # 测试问答功能
        questions = [
            "你好，你能做什么？",
            "解释一下RAG是什么？",
            "如何创建知识库索引？"
        ]
        
        for q in questions:
            logger.info(f"提问: {q}")
            response = ask(q, query_engine)
            logger.info(f"回答: {response}")
            print(f"问题: {q}")
            print(f"回答: {response}\n")
    
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")

if __name__ == "__main__":
    main()