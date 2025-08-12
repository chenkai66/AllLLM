import os
import json
import re
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from chatbot.llm import invoke
from chatbot.utils.file_utils import read_file, write_file, ensure_directory_exists

logger = logging.getLogger(__name__)

class KnowledgeManager:
    """知识库管理器"""
    
    def __init__(self, knowledge_base_dir: str = "docs"):
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.ensure_directory_exists(self.knowledge_base_dir)
        
    def ensure_directory_exists(self, directory_path: Path):
        """确保目录存在"""
        directory_path.mkdir(parents=True, exist_ok=True)
        
    def collect_files_info(self) -> List[Dict]:
        """收集所有文件信息"""
        files_info = []
        
        # 遍历所有txt文件
        for file_path in self.knowledge_base_dir.rglob("*.txt"):
            try:
                content = read_file(file_path)
                files_info.append({
                    "path": file_path,
                    "relative_path": str(file_path.relative_to(self.knowledge_base_dir)),
                    "name": file_path.name,
                    "content": content,
                    "size": len(content),
                    "modified_time": file_path.stat().st_mtime
                })
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
        
        return files_info
    
    def determine_file_theme(self, filename: str, content_sample: str) -> str:
        """使用LLM确定文件主题"""
        try:
            prompt = f"""
            作为ck的智能知识库管理助手，您的专业职责是对知识库中的文件内容进行深度分析，确定最恰当的主题分类。

            请根据以下文件名和内容样本确定该文件的核心主题类别：
            
            文件名: {filename}
            内容样本: {content_sample}
            
            要求：
            1. 请从以下预定义的一级分类中选择最合适的分类：
               - 技术科学类：人工智能、机器学习、深度学习、自然语言处理、计算机视觉、数据分析、云计算、算法
               - 人文社科类：历史、地理、法律、哲学、文学、艺术
               - 生活百科类：生活、旅游、健康、教育、经济、管理
               - 其他：无法归入以上分类的内容
            2. 在选定的一级分类下，再确定一个更具体的二级分类（不超过8个汉字）
            3. 以"一级分类/二级分类"的格式返回，例如"技术科学类/机器学习"
            4. 如果内容质量较低、无实际价值或无法判断主题，请回复"其他/未分类"
            5. 绝对不要包含特殊字符、标点符号或文件格式信息
            6. 只回复分类结果，不要包含任何其他解释性文字
            
            请提供最准确的主题分类：
            """
            
            theme = invoke(prompt).strip()
            
            # 验证输出质量
            if not theme or len(theme) < 1 or len(theme) > 50:
                return "其他/未分类"
                
            # 标准化主题名称
            theme_mappings = {
                "技术科学类/世界模型与AI": "技术科学类/世界模型",
                "技术科学类/世界模型与AI应用": "技术科学类/世界模型",
                "技术科学类/人工智能与世界模型": "技术科学类/世界模型",
                "技术科学类/人工智能世界模型": "技术科学类/世界模型",
                "技术科学类/世界模型应用": "技术科学类/世界模型",
                "技术科学类/机器学习介绍": "技术科学类/机器学习",
                "技术科学类/机器学习简介": "技术科学类/机器学习",
                "技术科学类/机器学习基础": "技术科学类/机器学习",
                "技术科学类/深度学习介绍": "技术科学类/深度学习",
                "技术科学类/深度学习简介": "技术科学类/深度学习",
                "技术科学类/深度学习基础": "技术科学类/深度学习",
                "技术科学类/自然语言处理介绍": "技术科学类/自然语言处理",
                "技术科学类/自然语言处理简介": "技术科学类/自然语言处理",
                "技术科学类/自然语言处理基础": "技术科学类/自然语言处理",
                "技术科学类/nlp": "技术科学类/自然语言处理",
                "技术科学类/nlp基础": "技术科学类/自然语言处理",
                "技术科学类/计算机视觉介绍": "技术科学类/计算机视觉",
                "技术科学类/计算机视觉基础": "技术科学类/计算机视觉",
                "技术科学类/cv": "技术科学类/计算机视觉",
                "技术科学类/cv基础": "技术科学类/计算机视觉",
                "技术科学类/云计算概念": "技术科学类/云计算",
                "技术科学类/云计算基础": "技术科学类/云计算"
            }
            
            normalized_theme = theme_mappings.get(theme, theme)
            
            # 清理主题名称
            normalized_theme = re.sub(r'[^\w\u4e00-\u9fff\-_/]', '', normalized_theme)
            normalized_theme = normalized_theme.strip()
            
            # 验证格式
            if "/" not in normalized_theme:
                return "其他/未分类"
                
            parts = normalized_theme.split("/")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return "其他/未分类"
            
            # 如果清理后为空或无效，使用默认值
            if not normalized_theme or normalized_theme in ["无效", "无用", "垃圾", "未定义"]:
                return "其他/未分类"
                
            return normalized_theme
        except Exception as e:
            logger.error(f"确定文件主题失败: {e}")
            return "其他/未分类"
    
    def analyze_file_themes(self, files_info: List[Dict]) -> List[Tuple[str, str]]:
        """分析文件内容并确定主题"""
        file_themes = []
        
        for file_info in files_info:
            try:
                # 取文件内容的前2000个字符进行分析
                content_sample = file_info["content"][:2000]
                
                # 使用LLM分析文件主题
                theme = self.determine_file_theme(file_info["name"], content_sample)
                file_themes.append((file_info["relative_path"], theme))
            except Exception as e:
                logger.warning(f"分析文件主题失败 {file_info['relative_path']}: {e}")
                file_themes.append((file_info["relative_path"], "其他/未分类"))
        
        return file_themes
    
    def identify_problematic_files(self, files_info: List[Dict]) -> Tuple[List[str], List[str]]:
        """识别重复和无效文件"""
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
    
    def should_merge_files(self, file_contents: List[Dict]) -> bool:
        """判断是否应该合并文件"""
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
                - "世界模型"、"人工智能"、"机器学习"等相关概念的文件应视为高度相关
                - 技术概念的不同角度阐述应考虑合并
                - 基础概念与进阶应用的文件可以考虑合并为完整的知识体系
                - 如果文件主题完全不同（如"世界模型"与"自然语言处理"），不应合并
                
                请严格按以下格式回复：
                - 如果应该合并，只回复"yes"
                - 如果不应合并，只回复"no"
                
                基于以上专业分析，您的判断是：
                """
                
                result = invoke(prompt).strip().lower()
                return result == "yes"
            else:
                # 对于大量文件，先进行主题聚类
                themes = []
                for f in file_contents[:5]:  # 只分析前5个文件以提高效率
                    theme_prompt = f"""
                    请为以下文件内容确定一个核心主题标签（不超过6个字）：
                    
                    文件: {f['name']}
                    内容: {f['content'][:500]}
                    
                    只回复主题标签，不要包含其他内容：
                    """
                    theme = invoke(theme_prompt).strip()
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
    
    def merge_file_contents(self, file_contents: List[Dict]) -> str:
        """合并文件内容"""
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
    
    def generate_merged_filename(self, theme: str, file_contents: List[Dict]) -> str:
        """生成合并文件的文件名"""
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{theme}_综合_{timestamp}.txt"
    
    def generate_smart_filename(self, original_file_path: Path, content: str) -> str:
        """生成智能文件名"""
        try:
            file_info = {
                "path": str(original_file_path.relative_to(self.knowledge_base_dir)),
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
            4. 不要包含日期、时间戳等时间相关信息
            5. 长度不超过15个字
            6. 示例格式：世界模型核心概念、深度学习应用等
            7. 只回复文件名，不要包含其他内容
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
                    new_filename_base = "未命名文件"
                    
            return f"{new_filename_base}.txt"
        except Exception as e:
            logger.error(f"生成智能文件名失败 {original_file_path}: {e}")
            # 使用原文件名，但去除日期部分
            original_name = original_file_path.stem
            # 移除日期格式的部分（如_20250808_1）
            cleaned_name = re.sub(r'_\d{8}_?\d*$', '', original_name)
            if len(cleaned_name) < 2:
                cleaned_name = "未命名文件"
            return f"{cleaned_name}.txt"
    
    def reorganize_structure(self, file_themes: List[Tuple[str, str]], 
                            duplicates: List[str], invalid_files: List[str], 
                            merged_files: List[Dict]) -> Dict:
        """重新组织文件夹结构"""
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
                
            # 解析主题分类
            if "/" in theme:
                parts = theme.split("/")
                primary_category = parts[0]
                secondary_category = parts[1] if len(parts) > 1 else "其他"
            else:
                primary_category = "其他"
                secondary_category = theme if theme else "未分类"
            
            # 创建主分类文件夹
            if primary_category not in theme_directories:
                primary_path = self.knowledge_base_dir / primary_category
                self.ensure_directory_exists(primary_path)
                theme_directories[primary_category] = primary_path
            
            # 创建子分类文件夹
            category_key = f"{primary_category}/{secondary_category}"
            if category_key not in theme_directories:
                secondary_path = self.knowledge_base_dir / primary_category / secondary_category
                self.ensure_directory_exists(secondary_path)
                theme_directories[category_key] = secondary_path
            
            # 移动文件到主题文件夹并生成智能文件名
            original_file_path = self.knowledge_base_dir / file_path
            if original_file_path.exists():
                # 生成智能文件名
                try:
                    content = read_file(original_file_path)
                    new_filename = self.generate_smart_filename(original_file_path, content)
                except Exception as e:
                    logger.error(f"生成智能文件名失败 {original_file_path}: {e}")
                    # 使用原文件名
                    new_filename = original_file_path.name
                
                # 确保文件名唯一
                new_file_path = theme_directories[category_key] / new_filename
                counter = 1
                final_new_path = new_file_path
                while final_new_path.exists():
                    name_parts = new_filename.split('.')
                    if len(name_parts) > 1:
                        final_new_path = theme_directories[category_key] / f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        final_new_path = theme_directories[category_key] / f"{new_filename}_{counter}"
                    counter += 1
                
                try:
                    original_file_path.rename(final_new_path)
                    reorganized_structure[file_path] = {
                        "new_path": str(final_new_path.relative_to(self.knowledge_base_dir)),
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
            # 解析主题分类
            if "/" in theme:
                parts = theme.split("/")
                primary_category = parts[0]
                secondary_category = parts[1] if len(parts) > 1 else "其他"
            else:
                primary_category = "其他"
                secondary_category = theme if theme else "未分类"
            
            # 创建主分类文件夹
            if primary_category not in theme_directories:
                primary_path = self.knowledge_base_dir / primary_category
                self.ensure_directory_exists(primary_path)
                theme_directories[primary_category] = primary_path
            
            # 创建子分类文件夹
            category_key = f"{primary_category}/{secondary_category}"
            if category_key not in theme_directories:
                secondary_path = self.knowledge_base_dir / primary_category / secondary_category
                self.ensure_directory_exists(secondary_path)
                theme_directories[category_key] = secondary_path
            
            # 删除被合并的原始文件
            for file_path in merged_info["merged_files"]:
                try:
                    full_path = self.knowledge_base_dir / file_path
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
                full_path = self.knowledge_base_dir / file_path
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
        self.cleanup_empty_directories()
        
        return reorganized_structure
    
    def cleanup_empty_directories(self):
        """清理空文件夹"""
        try:
            for dir_path in self.knowledge_base_dir.rglob("*"):
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    logger.info(f"删除空文件夹: {dir_path}")
        except Exception as e:
            logger.error(f"清理空文件夹失败: {e}")
    
    def organize_knowledge_base(self) -> Dict:
        """一键整理知识库结构"""
        try:
            # 1. 收集所有文件信息
            files_info = self.collect_files_info()
            
            # 2. 分析文件内容并确定主题
            file_themes = self.analyze_file_themes(files_info)
            
            # 3. 识别重复和无效文件
            duplicates, invalid_files = self.identify_problematic_files(files_info)
            
            # 4. 智能合并相似主题的文件
            merged_files = self.merge_similar_files(file_themes)
            
            # 5. 重新组织文件夹结构
            reorganized_structure = self.reorganize_structure(file_themes, duplicates, invalid_files, merged_files)
            
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
    
    def merge_similar_files(self, file_themes: List[Tuple[str, str]]) -> List[Dict]:
        """智能合并相似主题的文件"""
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
                        full_path = self.knowledge_base_dir / file_path
                        if full_path.exists():
                            content = read_file(full_path)
                            file_contents.append({
                                "path": file_path,
                                "content": content,
                                "name": full_path.name
                            })
                    
                    # 如果内容足够相似，则合并
                    if self.should_merge_files(file_contents):
                        # 合并内容
                        merged_content = self.merge_file_contents(file_contents)
                        
                        # 解析主题分类
                        if "/" in theme:
                            parts = theme.split("/")
                            primary_category = parts[0]
                            secondary_category = parts[1] if len(parts) > 1 else "其他"
                        else:
                            primary_category = "其他"
                            secondary_category = theme if theme else "未分类"
                        
                        # 生成智能文件名
                        new_filename = self.generate_merged_filename(theme, file_contents)
                        new_file_path = self.knowledge_base_dir / primary_category / secondary_category / new_filename
                        
                        # 确保目录存在
                        self.ensure_directory_exists(new_file_path.parent)
                        
                        # 写入合并后的内容
                        write_file(new_file_path, merged_content)
                        
                        merged_files.append({
                            "theme": theme,
                            "merged_files": [f["path"] for f in file_contents],
                            "new_file": str(new_file_path.relative_to(self.knowledge_base_dir))
                        })
                except Exception as e:
                    logger.error(f"合并文件失败 {theme}: {e}")
        
        return merged_files

    def update_knowledge_base(self, user_input: str, model_response: str) -> Optional[str]:
        """
        根据对话内容更新知识库
        
        参数:
            user_input (str): 用户输入
            model_response (str): 模型回复
            
        返回:
            str: 更新的文件路径
        """
        try:
            # 1. 提取结构化知识
            knowledge_prompt = """请从以下对话中提取有价值的知识点，格式化为结构化的知识：

用户输入: {user_input}
模型回复: {model_response}

请按照以下格式提取知识：
## 主题
[简要描述对话的核心主题]

## 关键信息
- [关键信息点1]
- [关键信息点2]
- ...

## 详细内容
[详细的内容描述]

## 应用场景
[该知识的可能应用场景]
"""
            full_prompt = knowledge_prompt.format(user_input=user_input, model_response=model_response)
            structured_knowledge = invoke(full_prompt)
            
            # 2. 确定知识类别
            category = self.determine_knowledge_category(user_input, structured_knowledge)
            
            # 解析主题分类
            if "/" in category:
                parts = category.split("/")
                primary_category = parts[0]
                secondary_category = parts[1] if len(parts) > 1 else "其他"
            else:
                primary_category = "其他"
                secondary_category = category if category else "未分类"
            
            category_dir = self.knowledge_base_dir / primary_category / secondary_category
            self.ensure_directory_exists(category_dir)
            
            # 3. 生成文件名
            filename = self.generate_smart_filename(Path("temp.txt"), structured_knowledge)
            filepath = category_dir / filename
            
            # 4. 写入文件
            write_file(filepath, structured_knowledge)
            
            logger.info(f"知识库更新完成: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"更新知识库失败: {e}")
            raise

    def determine_knowledge_category(self, user_input: str, knowledge: str) -> str:
        """
        使用LLM确定知识类别
        
        参数:
            user_input (str): 用户输入
            knowledge (str): 提取的知识
            
        返回:
            str: 知识类别
        """
        try:
            # 获取现有类别
            existing_categories = []
            if self.knowledge_base_dir.exists():
                for item in self.knowledge_base_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):  # 忽略隐藏目录
                        existing_categories.append(item.name)
            
            # 构建更详细的提示
            prompt = f"""
            作为ck的智能知识管理助手，您的任务是根据以下用户输入和提取的知识确定最相关的知识类别：

            现有类别: {', '.join(existing_categories) if existing_categories else '无'}
            
            用户输入: {user_input}
            提取的知识: {knowledge}
            
            要求：
            1. 请从以下预定义的一级分类中选择最合适的分类：
               - 技术科学类：人工智能、机器学习、深度学习、自然语言处理、计算机视觉、数据分析、云计算、算法
               - 人文社科类：历史、地理、法律、哲学、文学、艺术
               - 生活百科类：生活、旅游、健康、教育、经济、管理
               - 其他：无法归入以上分类的内容
            2. 在选定的一级分类下，再确定一个更具体的二级分类（不超过8个汉字）
            3. 以"一级分类/二级分类"的格式返回，例如"技术科学类/机器学习"
            4. 如果内容质量较低或无实际价值，回复"其他/未分类"
            5. 绝对不要包含特殊字符、标点符号或文件格式信息
            6. 只回复分类结果，不要包含任何其他解释性文字
            
            请提供最恰当的类别名称：
            """
            
            category = invoke(prompt).strip()
            
            # 验证和清理类别名称
            if not category or category == "无效内容":
                return "其他/未分类"
                
            # 确保类别名称是有效的目录名
            category = re.sub(r'[^\w\u4e00-\u9fff\-_/]', '_', category)
            category = re.sub(r'_+', '_', category)  # 合并多个下划线
            category = category.strip('_')  # 去除首尾下划线
            
            # 验证格式
            if "/" not in category:
                return "其他/未分类"
                
            parts = category.split("/")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return "其他/未分类"
            
            # 如果处理后的类别名为空或过短，使用默认值
            if len(category) < 1:
                return "其他/未分类"
            elif len(category) > 50:  # 限制长度
                category = category[:50]
                
            return category
        except Exception as e:
            logger.error(f"确定知识类别失败: {e}")
            return "其他/未分类"