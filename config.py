import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 模型配置
    DEFAULT_MODEL = "qwen-plus-0919"
    EMBEDDING_MODEL = "text-embedding-v2"
    
    # 路径配置
    DOCUMENT_PATH = "./docs"
    KNOWLEDGE_BASE_PATH = "data/knowledge_base"
    LOG_PATH = "data/log"
    USER_DATA_PATH = "data/user_data"
    
    # 对话配置
    MAX_CONTEXT_LENGTH = 10000  # 最大上下文长度
    MAX_CONVERSATION_HISTORY = 5  # 最大历史对话条数
    
    # 获取API密钥
    @property
    def DASHSCOPE_API_KEY(self):
        return os.getenv("DASHSCOPE_API_KEY")

# 全局配置对象
config = Config()