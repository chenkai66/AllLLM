import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from chatbot.llm import invoke
from chatbot.utils.file_utils import read_file, write_file, ensure_directory_exists

logger = logging.getLogger(__name__)

def organize_knowledge_base_structure(knowledge_base_dir: str) -> Dict:
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
        
        # 1. 收集所有文件信息
        files_info = collect_files_info(base_path)
        
        # 2. 分析文件内容并确定主题
        file_themes = analyze_file_themes(files_info)
        
        # 3. 识别重复和无效文件
        duplicates, invalid_files = identify_problematic_files(files_info)
        
        # 4. 智能合并相似主题的文件
        merged_files = merge_similar_files(base_path, file_themes)
        
        # 5. 重新组织文件夹结构
        reorganized_structure = reorganize_structure(base_path, file_themes, duplicates, invalid_files, merged_files)
        
        # 6. 返回整理结果
        return {
            "success": True,
            "files_analyzed": len(files_info),
            "themes_identified": len(set(theme for _, theme in file_themes)),
            "duplicates_removed": len(duplicates),
            "invalid_files_removed": len(invalid_files),
            "files_merged": len(merged_files),
            "reorganized_files": len(reorganized_structure),
            "details": reorganized_structure
        }
    except Exception as e:
        logger.error(f"整理知识库失败: {e}")
        return {"error": f"整理知识库失败: {str(e)}"}

def collect_files_info(base_path: Path) -> List[Dict]:
    """
    收集所有文件信息
    
    参数:
        base_path (Path): 知识库根目录路径
        
    返回:
        List[Dict]: 文件信息列表
    """
    files_info = []
    
    # 遍历所有txt文件
    for file_path in base_path.rglob("*.txt"):
        try:
            content = read_file(file_path)
            files_info.append({
                "path": file_path,
                "relative_path": str(file_path.relative_to(base_path)),
                "name": file_path.name,
                "content": content,
                "size": len(content),
                "modified_time": file_path.stat().st_mtime
            })
        except Exception as e:
            logger.warning(f"读取文件失败 {file_path}: {e}")
    
    return files_info

def analyze_file_themes(files_info: List[Dict]) -> List[Tuple[str, str]]:
    """
    分析文件内容并确定主题
    
    参数:
        files_info (List[Dict]): 文件信息列表
        
    返回:
        List[Tuple[str, str]]: 文件路径和主题的元组列表
    """
    file_themes = []
    
    for file_info in files_info:
        try:
            # 取文件内容的前2000个字符进行分析
            content_sample = file_info["content"][:2000]
            
            # 使用LLM分析文件主题
            theme = determine_file_theme(file_info["name"], content_sample)
            file_themes.append((file_info["relative_path"], theme))
        except Exception as e:
            logger.warning(f"分析文件主题失败 {file_info['relative_path']}: {e}")
            file_themes.append((file_info["relative_path"], "未分类"))
    
    return file_themes

def determine_file_theme(filename: str, content_sample: str) -> str:
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
        作为ck的智能知识库管理助手，您的专业职责是对知识库中的文件内容进行深度分析，确定最恰当的主题分类。

        请根据以下文件名和内容样本确定该文件的核心主题类别：
        
        文件名: {filename}
        内容样本: {content_sample}
        
        要求：
        1. 用简洁的中文描述该文件的核心主题（不超过8个汉字）
        2. 主题应能准确反映文件的核心内容和专业领域
        3. 使用标准化的专业术语和通用分类名称
        4. 以下是一些标准主题示例供参考：
           - 世界模型
           - 机器学习
           - 深度学习
           - 自然语言处理
           - 人工智能基础
           - 强化学习
           - 计算机视觉
           - 数据分析
           - 技术架构
           - 项目管理
        5. 如果内容质量较低、无实际价值或无法判断主题，请回复"未分类"
        6. 绝对不要包含特殊字符、标点符号或文件格式信息
        7. 只回复主题名称，不要包含任何其他解释性文字
        
        请提供最准确的主题分类：
        """
        
        theme = invoke(prompt, max_tokens=30).strip()
        
        # 验证输出质量
        if not theme or len(theme) < 1 or len(theme) > 20:
            return "未分类"
            
        # 标准化主题名称
        theme_mappings = {
            "世界模型与AI": "世界模型",
            "世界模型与AI应用": "世界模型",
            "人工智能与世界模型": "世界模型",
            "人工智能世界模型": "世界模型",
            "世界模型应用": "世界模型",
            "机器学习介绍": "机器学习",
            "机器学习简介": "机器学习",
            "机器学习基础": "机器学习",
            "深度学习介绍": "深度学习",
            "深度学习简介": "深度学习",
            "深度学习基础": "深度学习",
            "自然语言处理介绍": "自然语言处理",
            "自然语言处理简介": "自然语言处理",
            "自然语言处理基础": "自然语言处理",
            "nlp": "自然语言处理",
            "nlp基础": "自然语言处理",
            "计算机视觉介绍": "计算机视觉",
            "计算机视觉基础": "计算机视觉",
            "cv": "计算机视觉",
            "cv基础": "计算机视觉"
        }
        
        normalized_theme = theme_mappings.get(theme, theme)
        
        # 清理主题名称
        import re
        normalized_theme = re.sub(r'[^\w\u4e00-\u9fff\-_]', '', normalized_theme)
        normalized_theme = normalized_theme.strip()
        
        # 如果清理后为空或无效，使用默认值
        if not normalized_theme or normalized_theme in ["无效", "无用", "垃圾", "未定义"]:
            return "未分类"
            
        return normalized_theme
    except Exception as e:
        logger.error(f"确定文件主题失败: {e}")
        return "未分类"

def identify_problematic_files(files_info: List[Dict]) -> Tuple[List[str], List[str]]:
    """
    识别重复和无效文件
    
    参数:
        files_info (List[Dict]): 文件信息列表
        
    返回:
        Tuple[List[str], List[str]]: 重复文件路径列表和无效文件路径列表
    """
    duplicates = []
    invalid_files = []
    
    # 按内容分组以识别重复文件
    content_groups = {}
    for file_info in files_info:
        content_hash = hash(file_info["content"][:1000])  # 使用前1000个字符计算哈希
        if content_hash not in content_groups:
            content_groups[content_hash] = []
        content_groups[content_hash].append(file_info["relative_path"])
    
    # 识别重复文件（相同内容的文件保留一个）
    for paths in content_groups.values():
        if len(paths) > 1:
            duplicates.extend(paths[1:])  # 保留第一个，其余标记为重复
    
    # 识别无效文件（内容过少或无意义）
    for file_info in files_info:
        if file_info["size"] < 50:  # 小于50字符的文件视为无效
            invalid_files.append(file_info["relative_path"])
        elif "默认的文档内容" in file_info["content"] or "示例文档" in file_info["content"]:
            invalid_files.append(file_info["relative_path"])
    
    return duplicates, invalid_files

def merge_similar_files(base_path: Path, file_themes: List[Tuple[str, str]]) -> List[Dict]:
    """
    智能合并相似主题的文件
    
    参数:
        base_path (Path): 知识库根目录路径
        file_themes (List[Tuple[str, str]]): 文件路径和主题的元组列表
        
    返回:
        List[Dict]: 合并文件信息列表
    """
    merged_files = []
    
    # 按主题分组文件
    theme_groups = {}
    for file_path, theme in file_themes:
        if theme not in theme_groups:
            theme_groups[theme] = []
        theme_groups[theme].append(file_path)
    
    # 对于每个主题组，如果文件数量大于1，则考虑合并
    for theme, files in theme_groups.items():
        if len(files) > 1:
            try:
                # 收集同主题文件的内容
                file_contents = []
                for file_path in files:
                    full_path = base_path / file_path
                    if full_path.exists():
                        content = read_file(full_path)
                        file_contents.append({
                            "path": file_path,
                            "content": content,
                            "name": full_path.name
                        })
                
                # 如果内容足够相似，则合并
                if should_merge_files(file_contents):
                    # 合并内容
                    merged_content = merge_file_contents(file_contents)
                    
                    # 生成智能文件名
                    new_filename = generate_merged_filename(theme, file_contents)
                    new_file_path = base_path / theme / new_filename
                    
                    # 写入合并后的内容
                    ensure_directory_exists(new_file_path.parent)
                    write_file(new_file_path, merged_content)
                    
                    merged_files.append({
                        "theme": theme,
                        "merged_files": [f["path"] for f in file_contents],
                        "new_file": str(new_file_path.relative_to(base_path))
                    })
            except Exception as e:
                logger.error(f"合并文件失败 {theme}: {e}")
    
    return merged_files

def should_merge_files(file_contents: List[Dict]) -> bool:
    """
    判断是否应该合并文件
    
    参数:
        file_contents (List[Dict]): 文件内容列表
        
    返回:
        bool: 是否应该合并
    """
    try:
        if len(file_contents) < 2:
            return False
        
        # 对于少量文件，直接进行详细分析
        if len(file_contents) <= 3:
            # 使用LLM判断文件内容是否相似到可以合并的程度
            contents_summary = "\n".join([f"文件: {f['name']}\n内容: {f['content'][:800]}" for f in file_contents[:3]])
            
            prompt = f"""
            作为ck的智能知识管理助手，您的任务是专业判断以下文件内容是否相似到可以智能合并的程度：
            
            {contents_summary}
            
            判断标准：
            1. 核心主题一致性：文件是否围绕完全相同或高度相关的主题展开
            2. 内容互补性：文件间是否存在明显的互补关系，合并后能形成更完整的知识体系
            3. 重复度评估：文件内容是否存在大量重复表述或可合并的相似观点
            4. 知识价值提升：合并后是否能显著提升知识的完整性、准确性和实用性
            5. 专业领域匹配：文件是否属于相同的专业技术领域
            
            特别注意：
            - \"世界模型\"、\"人工智能\"、\"机器学习\"等相关概念的文件应视为高度相关
            - 技术概念的不同角度阐述应考虑合并
            - 基础概念与进阶应用的文件可以考虑合并为完整的知识体系
            - 如果文件主题完全不同（如\"世界模型\"与\"自然语言处理\"），不应合并
            
            请严格按以下格式回复：
            - 如果应该合并，只回复\"yes\"
            - 如果不应合并，只回复\"no\"
            
            基于以上专业分析，您的判断是：
            """
            
            result = invoke(prompt, max_tokens=20).strip().lower()
            return result == "yes"
        else:
            # 对于大量文件，先进行主题聚类
            themes = [
            for f in file_contents[:5]:  # 只分析前5个文件以提高效率
                theme_prompt = f"""
                请为以下文件内容确定一个核心主题标签（不超过6个字）：
                
                文件: {f['name']}
                内容: {f['content'][:500]}
                
                只回复主题标签，不要包含其他内容：
                """
                theme = invoke(theme_prompt, max_tokens=20).strip()
                themes.append(theme)
            
            # 如果大多数文件主题相同或高度相关，则考虑合并
            if len(themes) > 0:
                primary_theme = themes[0]
                similar_count = sum(1 for theme in themes if theme == primary_theme or 
                                  primary_theme in theme or theme in primary_theme)
                return similar_count >= len(themes) * 0.6  # 60%以上相似则合并
            
            return False
            
    except Exception as e:
        logger.error(f"判断是否合并文件失败: {e}")
        # 如果出现错误，默认不合并，确保数据安全
        return False

def merge_file_contents(file_contents: List[Dict]) -> str:
    """
    合并文件内容
    
    参数:
        file_contents (List[Dict]): 文件内容列表
        
    返回:
        str: 合并后的内容
    """
    try:
        # 构建合并提示
        contents_list = "\n".join([f"## {f['name']}\n{f['content']}" for f in file_contents])
        
        prompt = f"""
        请将以下多个文件内容合并为一个连贯的知识文档：
        
        {contents_list}
        
        合并要求：
        1. 保留所有有价值的信息
        2. 消除重复内容
        3. 组织成逻辑清晰的结构
        4. 添加适当的标题和小标题
        5. 确保语言流畅自然
        6. 按照以下结构组织：
           # 主题名称
           ## 核心概念
           ## 主要应用
           ## 技术细节
           ## 发展趋势
        7. 如果某些信息不适用某个章节，可以跳过
        """
        
        merged_content = invoke(prompt)
        return merged_content
    except Exception as e:
        logger.error(f"合并文件内容失败: {e}")
        # 如果合并失败，简单连接内容并添加分隔符
        return "\n\n---\n\n".join([f["content"] for f in file_contents])

def generate_merged_filename(theme: str, file_contents: List[Dict]) -> str:
    """
    生成合并文件的文件名
    
    参数:
        theme (str): 主题
        file_contents (List[Dict]): 文件内容列表
        
    返回:
        str: 生成的文件名
    """
    try:
        # 提取文件内容的关键信息来生成文件名
        contents_summary = "\n".join([f"文件: {f['name']}\n内容: {f['content'][:300]}" for f in file_contents[:2]])
        
        prompt = f"""
        请根据以下文件内容为主题"{theme}"生成一个恰当的文件名：
        
        {contents_summary}
        
        要求：
        1. 文件名应简洁明了，能准确反映文件内容核心
        2. 使用中文命名
        3. 不要包含特殊字符，只能使用中文、英文、数字、下划线
        4. 长度不超过20个字
        5. 示例格式：世界模型核心概念、深度学习应用指南等
        6. 只回复文件名，不要包含其他内容
        """
        
        filename = invoke(prompt).strip()
        # 清理文件名
        filename = re.sub(r'[^\w\u4e00-\u9fff]', '_', filename)
        filename = re.sub(r'_+', '_', filename)  # 合并多个下划线
        filename = filename.strip('_')  # 去除首尾下划线
        
        # 如果生成的文件名太短或为空，使用默认命名
        if len(filename) < 2:
            filename = f"{theme}_综合指南"
            
        return f"{filename}.txt"
    except Exception as e:
        logger.error(f"生成合并文件名失败: {e}")
        # 使用默认命名
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{theme}_综合_{timestamp}.txt"

def reorganize_structure(base_path: Path, file_themes: List[Tuple[str, str]], 
                        duplicates: List[str], invalid_files: List[str], 
                        merged_files: List[Dict]) -> Dict:
    """
    重新组织文件夹结构
    
    参数:
        base_path (Path): 知识库根目录路径
        file_themes (List[Tuple[str, str]]): 文件路径和主题的元组列表
        duplicates (List[str]): 重复文件路径列表
        invalid_files (List[str]): 无效文件路径列表
        merged_files (List[Dict]): 合并文件信息列表
        
    返回:
        Dict: 重新组织的结构信息
    """
    reorganized_structure = {}
    
    # 1. 创建主题分类文件夹
    theme_directories = {}
    for file_path, theme in file_themes:
        # 跳过已处理的文件（重复、无效或已合并）
        if file_path in duplicates or file_path in invalid_files:
            continue
            
        # 检查是否是已合并的文件
        is_merged = False
        for merged_info in merged_files:
            if file_path in merged_info["merged_files"]:
                is_merged = True
                break
        
        if is_merged:
            continue
            
        if theme not in theme_directories:
            theme_path = base_path / theme
            ensure_directory_exists(theme_path)
            theme_directories[theme] = theme_path
        
        # 移动文件到主题文件夹并生成智能文件名
        original_file_path = base_path / file_path
        if original_file_path.exists():
            # 生成智能文件名
            try:
                content = read_file(original_file_path)
                file_info = {
                    "path": file_path,
                    "content": content,
                    "name": original_file_path.name
                }
                
                # 使用LLM生成恰当的文件名
                prompt = f"""
                请根据以下文件内容生成一个恰当的文件名：
                
                文件名: {original_file_path.name}
                内容: {content[:500]}
                
                要求：
                1. 文件名应简洁明了，能准确反映文件内容核心
                2. 使用中文命名
                3. 不要包含特殊字符，只能使用中文、英文、数字、下划线
                4. 长度不超过15个字
                5. 示例格式：世界模型核心概念、深度学习应用等
                6. 只回复文件名，不要包含其他内容
                """
                
                new_filename_base = invoke(prompt).strip()
                # 清理文件名
                new_filename_base = re.sub(r'[^\w\u4e00-\u9fff]', '_', new_filename_base)
                new_filename_base = re.sub(r'_+', '_', new_filename_base)  # 合并多个下划线
                new_filename_base = new_filename_base.strip('_')  # 去除首尾下划线
                
                # 如果生成的文件名太短或为空，使用默认命名
                if len(new_filename_base) < 2:
                    # 从原文件名中提取关键词
                    name_parts = original_file_path.stem.split('_')
                    if len(name_parts) > 1:
                        new_filename_base = name_parts[0]
                    else:
                        new_filename_base = theme
                    
                new_filename = f"{new_filename_base}.txt"
            except Exception as e:
                logger.error(f"生成智能文件名失败 {original_file_path}: {e}")
                # 使用原文件名
                new_filename = original_file_path.name
            
            # 确保文件名唯一
            new_file_path = theme_directories[theme] / new_filename
            counter = 1
            final_new_path = new_file_path
            while final_new_path.exists():
                name_parts = new_filename.split('.')
                if len(name_parts) > 1:
                    final_new_path = theme_directories[theme] / f"{name_parts[0]}_{counter}.{name_parts[1]}"
                else:
                    final_new_path = theme_directories[theme] / f"{new_filename}_{counter}"
                counter += 1
            
            try:
                original_file_path.rename(final_new_path)
                reorganized_structure[file_path] = {
                    "new_path": str(final_new_path.relative_to(base_path)),
                    "theme": theme,
                    "status": "moved"
                }
            except Exception as e:
                logger.error(f"移动文件失败 {original_file_path}: {e}")
                reorganized_structure[file_path] = {
                    "error": f"移动失败: {str(e)}",
                    "theme": theme,
                    "status": "error"
                }
    
    # 2. 处理合并的文件
    for merged_info in merged_files:
        theme = merged_info["theme"]
        if theme not in theme_directories:
            theme_path = base_path / theme
            ensure_directory_exists(theme_path)
            theme_directories[theme] = theme_path
        
        # 删除被合并的原始文件
        for file_path in merged_info["merged_files"]:
            try:
                full_path = base_path / file_path
                if full_path.exists():
                    full_path.unlink()
                    reorganized_structure[file_path] = {
                        "status": "deleted",
                        "reason": "merged",
                        "merged_to": merged_info["new_file"]
                    }
            except Exception as e:
                logger.error(f"删除合并文件失败 {file_path}: {e}")
                reorganized_structure[file_path] = {
                    "error": f"删除失败: {str(e)}",
                    "status": "error"
                }
        
        # 记录新创建的合并文件
        reorganized_structure[merged_info["new_file"]] = {
            "status": "created",
            "source_files": merged_info["merged_files"],
            "theme": theme
        }
    
    # 3. 删除重复和无效文件
    for file_path in duplicates + invalid_files:
        # 检查是否已经处理过
        if file_path in reorganized_structure:
            continue
            
        try:
            full_path = base_path / file_path
            if full_path.exists():
                full_path.unlink()
                reorganized_structure[file_path] = {
                    "status": "deleted",
                    "reason": "duplicate" if file_path in duplicates else "invalid"
                }
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {e}")
            reorganized_structure[file_path] = {
                "error": f"删除失败: {str(e)}",
                "status": "error"
            }
    
    # 4. 清理空文件夹
    cleanup_empty_directories(base_path)
    
    return reorganized_structure

def cleanup_empty_directories(base_path: Path):
    """
    清理空文件夹
    
    参数:
        base_path (Path): 知识库根目录路径
    """
    try:
        for dir_path in base_path.rglob("*"):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                logger.info(f"删除空文件夹: {dir_path}")
    except Exception as e:
        logger.error(f"清理空文件夹失败: {e}")