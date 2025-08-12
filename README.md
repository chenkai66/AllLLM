# Allllm - 本地网页版大模型调用应用

Allllm 是一个结合各种知识库以及记忆流的本地网页版大模型调用应用。它使用通义千问模型，支持检索增强生成（RAG），能够自动管理知识库，并提供美观的网页界面。

## 功能特性

- **大模型交互**：基于通义千问模型的智能问答
- **检索增强生成（RAG）**：结合本地知识库提供更准确的回答
- **自动知识库管理**：自动从对话中提取和更新知识
- **记忆流**：支持多轮对话和上下文理解
- **用户偏好分析**：分析用户偏好并优化回答策略
- **自我反思机制**：持续改进回答质量
- **现代化网页界面**：美观、响应式的聊天界面
- **对话日志**：记录所有对话历史用于分析和审计

## 安装教程

### 1. 克隆仓库
```bash
git clone https://github.com/yourusername/Allllm.git
cd Allllm
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
创建 `.env` 文件并添加您的 DashScope API 密钥列表：
```bash
echo 'DASHSCOPE_API_KEYS=["your_api_key_1", "your_api_key_2"]' > .env
```

### 4. 初始化知识库
```bash
python -m chatbot.rag indexing
```

### 5. 启动系统
```bash
python app.py
```

打开浏览器访问：http://localhost:5000

## 使用教程

### 网页界面功能
1. **问答区域**：在输入框中输入问题并获取回答
2. **系统设置**：
   - ☑️ 实时更新知识库
   - ☑️ 启用上下文分析
   - 📏 上下文长度限制 (默认 10000 字符)
3. **对话历史**：显示当前会话的所有对话记录

### 命令行测试
```bash
# 测试完整工作流
python chatbot/test/test_workflows.py

# 测试知识更新功能
python chatbot/test/test_knowledge_update.py

# 测试对话日志
python chatbot/test/test_conversation_log.py
```

## 模块详细说明

### 1. LLM 交互模块 (`llm.py`)
- **功能**：与大模型交互的核心接口
- **输入**：
  - `user_message`: 用户输入文本
  - `model_name`: 模型名称 (默认 qwen-plus-0919)
  - `conversation_id`: 对话ID (用于多轮对话)
  - `context_history`: 上下文历史
- **输出**：模型生成的回复文本
- **关键函数**：
  - `invoke()`: 标准调用
  - `invoke_with_stream_log()`: 流式输出调用

### 2. RAG 核心模块 (`rag.py`)
- **功能**：实现检索增强生成的核心逻辑
- **输入**：
  - `document_path`: 文档路径
  - `persist_path`: 知识库存储路径
- **输出**：查询引擎对象
- **关键函数**：
  - `indexing()`: 创建索引并持久化
  - `create_query_engine()`: 创建查询引擎
  - `ask()`: 执行问答

### 3. 知识库管理 (`update_knowledge.py`)
- **功能**：自动管理知识库的创建和更新
- **输入**：
  - `user_input`: 用户输入
  - `model_response`: 模型回复
  - `knowledge_base_dir`: 知识库目录
- **输出**：更新后的知识文件路径
- **工作流程**：
  1. 从对话中提取结构化知识
  2. 确定知识类别
  3. 创建/更新知识文件

### 4. 工作流模块 (`workflow/`)
- **对话日志 (`conversation_log.py`)**:
  - 记录每日对话到CSV文件
  - 加载最近对话历史
- **输入处理 (`input_processing.py`)**:
  - 评估输入清晰度
  - 总结对话历史
  - 构建上下文
- **用户分析 (`reflection.py`)**:
  - 分析用户偏好
  - 执行自我反思
  - 更新用户偏好表

### 5. 网页界面 (`app.py`)
- **路由**:
  - `/`: 主页面
  - `/ask`: 问答API接口
- **功能**:
  - 支持多轮对话
  - 实时更新知识库
  - 可配置参数设置

## 项目结构详细说明

| 模块 | 文件 | 功能描述 |
|------|------|----------|
| **核心功能** | `llm.py` | 大模型交互接口 |
|  | `rag.py` | RAG 实现 |
|  | `update_knowledge.py` | 知识库管理 |
| **工作流** | `conversation_log.py` | 对话日志管理 |
|  | `input_processing.py` | 用户输入处理 |
|  | `reflection.py` | 用户偏好分析 |
| **工具函数** | `file_utils.py` | 文件操作工具 |
|  | `logging_utils.py` | 日志记录工具 |
|  | `vector_utils.py` | 向量计算工具 |
| **网页界面** | `app.py` | Flask 主应用 |
|  | `index.html` | 网页界面模板 |
|  | `styles.css` | 样式表 |
| **配置** | `config.py` | 系统配置 |
|  | `.env` | 环境变量 |

## 配置说明

### 环境变量
在 `.env` 文件中配置以下变量：
```bash
DASHSCOPE_API_KEYS=["your_dashscope_api_key_1", "your_dashscope_api_key_2"]
```

### 系统配置
在 `config.py` 中可以调整以下配置：
- 模型配置（默认模型、嵌入模型）
- 路径配置（文档路径、知识库路径等）
- 对话配置（最大上下文长度、最大历史对话条数）

## 开发指南

### 代码结构
```
Allllm/
├── app.py                 # Flask 主应用
├── config.py              # 系统配置
├── requirements.txt       # Python 依赖
├── package.json           # 项目信息和脚本
├── .env                   # 环境变量
├── templates/             # HTML 模板
├── static/                # 静态资源（CSS, JS等）
├── docs/                  # 文档目录
├── data/                  # 数据目录
│   ├── knowledge_base/    # 知识库
│   ├── log/               # 对话日志
│   └── user_data/         # 用户数据
└── chatbot/               # 核心功能模块
    ├── llm.py             # 大模型交互
    ├── rag.py             # RAG 实现
    ├── prompt/            # 提示词模板
    ├── workflow/          # 工作流模块
    │   ├── knowledge_manager.py  # 知识库管理器
    │   ├── input_processing.py   # 输入处理
    │   ├── reflection.py         # 用户偏好分析和自我反思
    │   └── conversation_log.py   # 对话日志
    └── utils/             # 工具函数
        ├── file_utils.py         # 文件操作工具
        └── logging_utils.py      # 日志记录工具
```

### 核心模块API

#### KnowledgeManager (chatbot/workflow/knowledge_manager.py)
- `update_knowledge_base(user_input: str, model_response: str) -> Optional[str]`: 根据对话内容更新知识库
- `organize_knowledge_base() -> Dict`: 一键整理知识库结构
- `determine_file_theme(filename: str, content_sample: str) -> str`: 确定文件主题
- `merge_similar_files(file_themes: List[Tuple[str, str]]) -> List[Dict]`: 合并相似文件

#### RAG (chatbot/rag.py)
- `indexing(document_path: str = "./docs", persist_path: str = "data/knowledge_base") -> VectorStoreIndex`: 创建索引
- `load_index(persist_path: str = "data/knowledge_base") -> Optional[VectorStoreIndex]`: 加载索引
- `ensure_index_exists(persist_path: str = "data/knowledge_base") -> VectorStoreIndex`: 确保索引存在
- `create_query_engine(index: VectorStoreIndex, model_name: str = "qwen-plus") -> QueryEngine`: 创建查询引擎
- `ask(question: str, query_engine, context_history: Optional[list] = None) -> str`: 问答

#### Input Processing (chatbot/workflow/input_processing.py)
- `process_user_input(user_input: str, conversation_id: str, max_context_length: int = 10000) -> Tuple[str, List[Dict]]`: 处理用户输入
- `assess_input_clarity(user_input: str) -> bool`: 评估输入清晰度
- `summarize_conversation_history(conversations: List[Dict]) -> str`: 总结对话历史
- `determine_context_need(user_input: str, summary: str) -> bool`: 判断是否需要详细上下文
- `truncate_conversations(conversations: List[Dict], max_length: int) -> List[Dict]`: 截断对话历史

#### Reflection (chatbot/workflow/reflection.py)
- `analyze_user_preference(user_input: str, conversation_id: str)`: 分析用户偏好
- `perform_self_reflection(user_input: str, model_response: str)`: 执行自我反思

#### Conversation Log (chatbot/workflow/conversation_log.py)
- `save_conversation_log(log_data: Dict)`: 保存对话日志
- `load_recent_conversations(conversation_id: str, max_entries: int = 10) -> List[Dict]`: 加载最近对话

#### LLM (chatbot/llm.py)
- `invoke(user_message: str, model_name: str = "qwen-plus-0919", conversation_id: Optional[str] = None, context_history: Optional[list] = None) -> str`: 调用大模型
- `invoke_with_stream_log(user_message: str, model_name: str = "qwen-plus-0919", conversation_id: Optional[str] = None) -> str`: 流式调用大模型

### 添加新功能
1. 在 `chatbot/` 目录下创建新的模块文件
2. 在 `app.py` 中导入并集成新功能
3. 如果需要，更新 `templates/index.html` 和 `static/styles.css` 以支持新功能的UI
4. 添加相应的提示词模板到 `chatbot/prompt/` 目录

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest chatbot/test/test_workflows.py
```

## 未来规划 (TODO)

### 功能增强
1. **向量数据库集成**：
   - 使用 Milvus 或 ChromaDB 替代本地文件存储
   - 实现更高效的知识检索
   
2. **用户认证系统**：
   - 添加多用户支持
   - 个性化知识库和偏好设置

3. **实时监控面板**：
   - 添加系统状态监控
   - 知识库使用情况可视化

4. **多模型支持**：
   - 支持 OpenAI、Anthropic 等更多模型
   - 模型自动切换功能

### 性能优化
1. **知识检索优化**：
   - 实现增量索引更新
   - 添加知识去重机制

2. **对话压缩算法**：
   - 开发更高效的历史对话压缩方法
   - 自适应上下文长度管理

3. **分布式处理**：
   - 支持多节点部署
   - 负载均衡设计

## 贡献指南

欢迎贡献代码！请遵循以下流程：
1. Fork 本仓库
2. 创建新分支 (`git checkout -b feature/your-feature`)
3. 提交代码 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 [MIT 许可证](LICENSE)。