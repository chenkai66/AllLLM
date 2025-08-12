import os
import json
import re
from pathlib import Path
from chatbot.llm import invoke
from chatbot.utils.file_utils import read_file, write_file, ensure_directory_exists

def organize_knowledge_base_structure(knowledge_base_dir):
    """
    一键整理知识库结构
    
    参数:
        knowledge_base_dir (str): 知识库目录路径
        
    返回:
        dict: 整理结果详情
    """
    try:
        base_path = Path(knowledge_base_dir)
        if not base_path.exists():
            return {"error": "知识库目录不存在"}
        
        # 1. 收集所有文件夹和文件信息
        folders_info = collect_folders_info(base_path)
        
        # 2. 分析每个文件夹的内容并确定主题
        folder_themes = analyze_folder_themes(folders_info)
        
        # 3. 重新组织文件夹结构，限制层级为两层
        reorganized_structure = reorganize_folders(base_path, folder_themes)
        
        # 4. 返回整理结果
        return {
            "success": True,
            "folders_analyzed": len(folder_themes),
            "reorganized_folders": len(reorganized_structure),
            "details": reorganized_structure
        }
    except Exception as e:
        return {"error": f"整理知识库失败: {str(e)}"}

def collect_folders_info(base_path):
    """
    收集所有文件夹和文件信息
    
    参数:
        base_path (Path): 知识库根目录路径
        
    返回:
        dict: 文件夹信息
    """
    folders_info = {}
    
    # 遍历所有文件夹
    for folder_path in base_path.iterdir():
        if folder_path.is_dir():
            folder_name = folder_path.name
            folder_files = []
            
            # 收集文件夹中的所有文件
            for file_path in folder_path.rglob('*'):
                if file_path.is_file() and file_path.suffix == '.txt':
                    try:
                        content = read_file(file_path)
                        folder_files.append({
                            "name": file_path.name,
                            "path": str(file_path.relative_to(base_path)),
                            "content": content,
                            "size": len(content)
                        })
                    except Exception as e:
                        print(f"读取文件失败 {file_path}: {e}")
            
            folders_info[folder_name] = {
                "path": str(folder_path.relative_to(base_path)),
                "files": folder_files
            }
    
    return folders_info

def analyze_folder_themes(folders_info):
    """
    分析每个文件夹的内容并确定主题
    
    参数:
        folders_info (dict): 文件夹信息
        
    返回:
        dict: 文件夹主题分析结果
    """
    folder_themes = {}
    
    for folder_name, folder_data in folders_info.items():
        try:
            # 收集文件夹中的内容摘要
            content_samples = []
            total_size = 0
            
            # 为避免内容过长，我们只取前几个文件或限制总字符数
            for file_info in folder_data["files"]:
                if total_size > 5000:  # 限制总字符数
                    break
                # 取文件内容的前1000个字符
                sample = file_info["content"][:1000]
                content_samples.append(sample)
                total_size += len(sample)
            
            # 如果内容太多，进一步简化
            if total_size > 5000:
                content_samples = [sample[:500] for sample in content_samples]
            
            content_summary = "\n\n".join(content_samples)
            
            # 使用LLM分析文件夹主题
            theme = determine_folder_theme(folder_name, content_summary)
            folder_themes[folder_name] = {
                "theme": theme,
                "file_count": len(folder_data["files"]),
                "total_size": sum(f["size"] for f in folder_data["files"])
            }
        except Exception as e:
            print(f"分析文件夹主题失败 {folder_name}: {e}")
            folder_themes[folder_name] = {
                "theme": "未分类",
                "file_count": len(folder_data["files"]),
                "total_size": sum(f["size"] for f in folder_data["files"])
            }
    
    return folder_themes

def determine_folder_theme(folder_name, content_summary):
    """
    使用LLM确定文件夹主题
    
    参数:
        folder_name (str): 文件夹名称
        content_summary (str): 内容摘要
        
    返回:
        str: 文件夹主题
    """
    try:
        # 读取提示模板
        prompt_template = read_file("chatbot/prompt/folder_theme_analysis.txt")
        if not prompt_template:
            prompt_template = """你是一个专业的知识库管理助手，你的任务是分析文件夹的主题。

请根据文件夹名称和内容摘要确定该文件夹的主题类别：

文件夹名称: {folder_name}
内容摘要: {content_summary}

请按照以下要求回复：
1. 用简洁的中文描述该文件夹的主题（不超过10个字）
2. 只回复主题名称，不要包含其他内容
"""
        
        prompt = prompt_template.format(folder_name=folder_name, content_summary=content_summary)
        
        theme = invoke(prompt).strip()
        # 确保主题名称是有效的目录名
        theme = re.sub(r'[^\w\-_]', '_', theme)
        return theme if theme else "未分类"
    except Exception:
        return "未分类"

def reorganize_folders(base_path, folder_themes):
    """
    重新组织文件夹结构，限制层级为两层
    
    参数:
        base_path (Path): 知识库根目录路径
        folder_themes (dict): 文件夹主题分析结果
        
    返回:
        dict: 重新组织的结构信息
    """
    reorganized_structure = {}
    
    # 1. 创建主题分类文件夹
    theme_folders = {}
    for folder_name, theme_info in folder_themes.items():
        theme = theme_info["theme"]
        if theme not in theme_folders:
            theme_path = base_path / theme
            ensure_directory_exists(theme_path)
            theme_folders[theme] = theme_path
        else:
            theme_path = theme_folders[theme]
        
        # 移动原文件夹到主题分类文件夹中
        original_folder_path = base_path / folder_name
        if original_folder_path.exists() and original_folder_path.is_dir():
            # 新路径为 主题分类/原子文件夹名
            new_folder_path = theme_path / folder_name
            
            # 如果目标路径已存在，添加序号
            counter = 1
            final_new_path = new_folder_path
            while final_new_path.exists():
                final_new_path = theme_path / f"{folder_name}_{counter}"
                counter += 1
            
            # 移动文件夹
            try:
                original_folder_path.rename(final_new_path)
                reorganized_structure[folder_name] = {
                    "original_path": str(original_folder_path.relative_to(base_path)),
                    "new_path": str(final_new_path.relative_to(base_path)),
                    "theme": theme
                }
            except Exception as e:
                print(f"移动文件夹失败 {original_folder_path}: {e}")
                reorganized_structure[folder_name] = {
                    "original_path": str(original_folder_path.relative_to(base_path)),
                    "error": f"移动失败: {str(e)}",
                    "theme": theme
                }
    
    # 2. 处理根目录下的文件（不属于任何文件夹的文件）
    for item in base_path.iterdir():
        if item.is_file() and item.suffix == '.txt':
            try:
                # 读取文件内容以确定主题
                content = read_file(item)
                content_sample = content[:1000]  # 取前1000个字符
                
                # 确定文件主题
                theme = determine_file_theme(item.name, content_sample)
                
                # 创建主题文件夹
                if theme not in theme_folders:
                    theme_path = base_path / theme
                    ensure_directory_exists(theme_path)
                    theme_folders[theme] = theme_path
                
                # 移动文件到主题文件夹
                new_file_path = theme_folders[theme] / item.name
                item.rename(new_file_path)
                
                reorganized_structure[item.name] = {
                    "original_path": str(item.relative_to(base_path)),
                    "new_path": str(new_file_path.relative_to(base_path)),
                    "theme": theme,
                    "type": "file"
                }
            except Exception as e:
                print(f"处理文件失败 {item}: {e}")
    
    return reorganized_structure

def determine_file_theme(filename, content_sample):
    """
    使用LLM确定文件主题
    
    参数:
        filename (str): 文件名
        content_sample (str): 文件内容样本
        
    返回:
        str: 文件主题
    """
    try:
        prompt = f"""
        请根据以下文件名和内容样本确定该文件的主题类别：
        
        文件名: {filename}
        内容样本: {content_sample}
        
        请按照以下要求回复：
        1. 用简洁的中文描述该文件的主题（不超过10个字）
        2. 只回复主题名称，不要包含其他内容
        """
        
        theme = invoke(prompt).strip()
        # 确保主题名称是有效的目录名
        theme = re.sub(r'[^\w\-_]', '_', theme)
        return theme if theme else "未分类"
    except Exception:
        return "未分类"