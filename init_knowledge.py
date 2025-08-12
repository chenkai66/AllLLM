import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chatbot.rag import indexing

if __name__ == "__main__":
    indexing()