import os
import json
from pathlib import Path

import os
from pathlib import Path

def ensure_directory_exists(directory_path):
    """
    确保目录存在，如果不存在则创建
    
    参数:
        directory_path (str|Path): 目录路径
    """
    if isinstance(directory_path, str):
        directory_path = Path(directory_path)
    directory_path.mkdir(parents=True, exist_ok=True)

def read_file(file_path):
    """
    读取文件内容
    
    参数:
        file_path (str|Path): 文件路径
        
    返回:
        str: 文件内容
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
    if not file_path.exists():
        return ""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """
    写入文件内容
    
    参数:
        file_path (str|Path): 文件路径
        content (str): 要写入的内容
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)
    ensure_directory_exists(file_path.parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)