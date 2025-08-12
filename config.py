import os
import json
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
    
    # 获取API密钥列表（带验证）
    @property
    def DASHSCOPE_API_KEYS(self):
        keys_str = os.getenv("DASHSCOPE_API_KEYS")
        if not keys_str:
            raise ValueError("DASHSCOPE_API_KEYS 未设置，请检查 .env 文件")
        
        try:
            keys = json.loads(keys_str)
        except json.JSONDecodeError:
            raise ValueError("DASHSCOPE_API_KEYS 格式无效，请检查 .env 文件")
        
        if not keys or not isinstance(keys, list):
            raise ValueError("DASHSCOPE_API_KEYS 必须是一个非空列表，请检查 .env 文件")
            
        return keys
    
    # 获取当前API密钥索引（用于日志记录）
    DASHSCOPE_API_KEY_INDEX = 0
    
    # 获取当前使用的API密钥（兼容旧代码）
    @property
    def DASHSCOPE_API_KEY(self):
        keys = self.DASHSCOPE_API_KEYS
        return keys[self.DASHSCOPE_API_KEY_INDEX]

# 全局配置对象
config = Config()