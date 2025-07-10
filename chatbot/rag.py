# Import dependencies
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
from llama_index.llms.dashscope import DashScope
# These two lines of code are used to suppress WARNING messages to avoid interference with reading and learning. In production environments, it is recommended to set the log level as needed.
import logging
logging.basicConfig(level=logging.ERROR)
from llama_index.llms.openai_like import OpenAILike
from llama_index.core import PromptTemplate
import os

def indexing(document_path="./docs", persist_path="data/knowledge_base"):
    """
    Create an index and persistently store it
    Parameters
      path(str): Document path
    """
    index = create_index(document_path)
    # Persist the index, saving it as a local file
    index.storage_context.persist(persist_path)

def create_index(document_path="./docs"):
    """
    Create an index
    Parameters
      path(str): Document path
    """
    # Parse all documents in the ./docs directory
    documents = SimpleDirectoryReader(document_path).load_data()
    # Create an index
    index = VectorStoreIndex.from_documents(
        documents,
        # Specify the embedding model
        embed_model=DashScopeEmbedding(
            # You can also use other embedding models provided by Alibaba Cloud: https://help.aliyun.com/zh/model-studio/getting-started/models#3383780daf8hw
            model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2
        )
    )
    return index

def load_index(persist_path="knowledge_base/test"):
    """
    Load the index
    Parameters
      persist_path(str): Index file path
    Returns
      VectorStoreIndex: Index object
    """
    storage_context = StorageContext.from_defaults(persist_dir=persist_path)
    return load_index_from_storage(storage_context, embed_model=DashScopeEmbedding(
      model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2
    ))

def create_query_engine(index):
    """
    Create a query engine
    Parameters
      index(VectorStoreIndex): Index object
    Returns
      QueryEngine: Query engine object
    """
    
    query_engine = index.as_query_engine(
      # Set to streaming output
      streaming=True,
      # Here we use the qwen-plus-0919 model. You can also use other Qwen text generation models provided by Alibaba Cloud: https://help.aliyun.com/zh/model-studio/getting-started/models#9f8890ce29g5u
      llm=OpenAILike(
          model="qwen-plus-0919",
          api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
          api_key=os.getenv("DASHSCOPE_API_KEY"),
          is_chat_model=True
          ))
    return query_engine

def ask(question, query_engine, context_history=None):
    """
    问答函数，支持上下文历史
    
    参数:
        question (str): 问题
        query_engine (QueryEngine): 查询引擎对象
        context_history (list): 上下文历史
        
    返回:
        str: 回答内容
    """
    # 如果有上下文历史，构建完整查询
    full_query = question
    if context_history:
        context_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in context_history])
        full_query = f"上下文历史:\n{context_str}\n\n当前问题: {question}"
    
    streaming_response = query_engine.query(full_query)
    
    # 收集流式响应
    response_text = ""
    for text in streaming_response.response_gen:
        response_text += text
    
    return response_text

# 新增函数：加载用户偏好用于RAG
def load_user_preference(conversation_id):
    """加载用户偏好数据（简化实现）"""
    pass

def update_prompt_template(
        query_engine,
        qa_prompt_tmpl_str = (
        "You are a question-answering robot. You need to carefully read the reference information and then answer the questions raised by everyone."
        "Notes:\n"
        "1. Answer questions based on contextual information rather than prior knowledge.\n"
        "2. For tool consultation questions, be sure to provide download address links.\n"
        "3. For employee department queries, be sure to note that there may be multiple employees with the same name—there could be 2, 3, or even more people with the same name.\n"
        "The following is the reference information."
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "Question: {query_str}\n."
        "Answer: "
    )):
    """
    Modify the prompt template
    Input is the query_engine before prompt modification and the prompt template; output is the query_engine after prompt modification
    """
    qa_prompt_tmpl_str = qa_prompt_tmpl_str
    qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)
    query_engine.update_prompts(
        {"response_synthesizer:text_qa_template": qa_prompt_tmpl}
    )
    # print("Prompt template updated successfully")
    return query_engine