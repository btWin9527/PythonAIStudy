# 智能文档问答助手

基于 **LangChain + FastAPI + DashScope** 的 RAG 文档问答系统，支持两种前端 UI。

---

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| **LLM** | `ChatOpenAI` → DashScope `qwen-max` | LangChain 统一接口调用阿里云模型 |
| **Embedding** | `DashScopeEmbeddings` → `text-embedding-v3` | 自定义适配器实现 LangChain `Embeddings` 接口 |
| **文档解析** | `PyPDFLoader` | LangChain 内置 PDF 加载器 |
| **文档切割** | `RecursiveCharacterTextSplitter` | chunk_size=1000, overlap=200, 中文分隔符 |
| **向量存储** | `FAISS` | 纯内存索引 + 磁盘缓存，无外部依赖 |
| **记忆系统** | `SimpleMemory` | 自实现 working + episodic 双记忆，嵌入相似度检索 |
| **后端框架** | **FastAPI** | REST + SSE 流式端点 |
| **Python UI** | Gradio 6 | 一键启动，自动初始化 |
| **Vue UI** | Vue 3 + TypeScript + `@ai-sdk/vue` | SPA 前端，打字机流式效果 |
| **构建工具** | Vite 5 | 前端开发服务器 + API 代理 |

---

### 快速启动（Shell 脚本，推荐）

```bash
cd ai_assistant

# 一键交互式启动（自动检查依赖 + 安装）
./run.sh
#   1) py   → Gradio UI → http://localhost:7860
#   2) vue  → Vue 3 UI   → http://localhost:5173（自动启动后端 + 前端）

# 直接指定模式
./run.sh py              # Gradio UI
./run.sh vue             # Vue UI（后端 8000 + 前端 5173）
./run.sh vue-api         # 仅后端 API
./run.sh vue-client      # 仅前端
```

### Python 启动（传统方式）

---

## 目录结构

```
ai_assistant/
├── run.py                          # 统一启动入口
├── .env                            # API 密钥 / 模型配置
├── A_Assistant_langchain.py        # ★ LangChain 版核心（主要学习目标）
├── A_Assistant.py                  # HelloAgents 版（对照参考）
├── pdf/
│   ├── test.pdf                    # 默认文档 (46KB)
│   └── Happy-LLM-0727.pdf          # 大文档 (20MB)
├── ui/
│   ├── gradio_ui.py                # Gradio Web UI
│   ├── vue_api.py                  # ★ FastAPI 后端
│   └── vue_client/                 # Vue 3 前端
│       └── src/
│           ├── api/index.ts         # API 客户端 + SSE 读取
│           ├── composables/
│           │   └── useStreamChat.ts  # 流式聊天 Hook
│           └── components/          # ChatView / TokenBar / Sidebar ...
├── _chat_history.json              # 对话历史持久化
└── _faiss_cache/                   # FAISS 索引缓存
```

---

## 核心数据流：文档上传 → 问答

### 整体架构

```
┌─ 文档上传 ───────────────────────────────────────────────────┐
│                                                               │
│  PDF 文件                                                      │
│    │                                                          │
│    ▼                                                          │
│  PyPDFLoader           ← LangChain: 解析 PDF 文本              │
│    │                                                          │
│    ▼                                                          │
│  RecursiveCharacterTextSplitter  ← LangChain: 按规则切片       │
│    │  chunk_size=1000, overlap=200                             │
│    ▼                                                          │
│  DashScopeEmbeddings.embed_documents()  ← 调用 Embedding API  │
│    │  text-embedding-v3 → 1024 维向量                          │
│    ▼                                                          │
│  FAISS.from_documents()   ← LangChain: 构建内存索引            │
│    │  → 保存 _faiss_cache/ 磁盘缓存（二次加载秒级）             │
│    ▼                                                          │
│  ✅ 知识库就绪                                                 │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌─ 问答（非流式）───────────────────────────────────────────────┐
│                                                               │
│  用户提问 "有哪些矿山类型？"                                    │
│    │                                                          │
│    ▼                                                          │
│  vectorstore.similarity_search(question, k=5)                 │
│    │  DashScopeEmbeddings.embed_query(question)  ← 问题向量化  │
│    │  FAISS 余弦相似度 → Top-5 相关文档块                       │
│    ▼                                                          │
│  ChatPromptTemplate(system + context + question)               │
│    │  system: "你是一个专业学习助手，仅基于文档回答..."          │
│    │  context: [文档1]...[文档2]...（拼接 Top-5 块）            │
│    ▼                                                          │
│  ChatOpenAI.invoke() → qwen-max → AIMessage                    │
│    │  HTTP POST → DashScope API → 返回回答                     │
│    ▼                                                          │
│  提取 AIMessage.content + usage_metadata                       │
│    │  _record_tokens(usage) → 累加 prompt/completion/total     │
│    ▼                                                          │
│  ✅ 纯文本 answer → 前端渲染                                    │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌─ 问答（流式 / Vue）───────────────────────────────────────────┐
│                                                               │
│  Vue useChat → POST /api/ai-chat                              │
│    │  Body: { messages: [{role:"user", content:"..."}] }      │
│    ▼                                                          │
│  FastAPI ask_stream() → 检索 + LLM.stream()                   │
│    │  LangChain ChatOpenAI.stream() → 逐 chunk yield           │
│    ▼                                                          │
│  StreamingResponse → AI SDK v4 wire format                    │
│    │  0:"文" 0:"本" 0:"块" 4:{完整消息}                        │
│    ▼                                                          │
│  @ai-sdk/vue → messages 自动追加 → 打字机渲染                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### LangChain 链式调用拆解

`A_Assistant_langchain.py` 中 RAG 链的核心构建（`_build_rag_chain`）：

```python
# 1. 定义 Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的学习助手...\n参考文档内容：\n{context}"),
    ("human", "{question}")
])

# 2. 检索函数（从 FAISS 取 Top-5 文档块，拼接为上下文）
def retrieve_and_format(inputs):
    docs = vectorstore.similarity_search(inputs["question"], k=5)
    context = "\n\n".join([doc.page_content for doc in docs])
    return {"context": context, "question": inputs["question"]}

# 3. LangChain 链式组合（LCEL 管道语法）
chain = (
    retrieve_and_format     # RunnableLambda: 输入 → {context, question}
    | prompt                # 填充模板 → [SystemMessage, HumanMessage]
    | llm                   # ChatOpenAI.invoke() → AIMessage
    | extract_answer_and_usage  # 提取 content + usage_metadata
)

# 4. 调用
answer, usage = chain.invoke({"question": "有哪些矿山类型？"})
```

---

## LangChain vs HelloAgents 对照

> 项目同时提供两个版本的 `PDFLearningAssistant`，通过 `USE_LANGCHAIN` 开关切换，
> 所有公共方法签名一致（`load_document` / `ask` / `recall` / `add_note` / `get_stats` / `generate_report`）。

| 功能 | HelloAgents 版 | LangChain 版 |
|------|------|------|
| **文件** | `A_Assistant.py` | `A_Assistant_langchain.py` |
| **LLM 调用** | 框架自动检测 Provider | `ChatOpenAI` 显式配置 |
| **PDF 解析** | `RAGTool.run(action="add_document")` | `PyPDFLoader(path).load()` |
| **文档切割** | `RAGTool` 内置 | `RecursiveCharacterTextSplitter` |
| **向量存储** | `Qdrant`（外部云服务） | `FAISS`（纯内存 + 磁盘缓存） |
| **Embedding** | `RAGTool` 内置 DASHSCOPE | `DashScopeEmbeddings`（自定义适配器） |
| **RAG 检索** | `RAGTool.run(action="ask")` 一行 | 手动构建链：检索 → Prompt → LLM |
| **记忆搜索** | `MemoryTool.run(action="search")` | `SimpleMemory.search()` 自实现嵌入相似度 |
| **API 风格** | 统一 `tool.run({action, ...})` | LangChain 链式调用 `\|` |

```
HelloAgents：封装黑盒                           LangChain：组合积木

rag_tool.run({                                  loader = PyPDFLoader(path)
    "action": "add_document",                   pages = loader.load()
    "file_path": "doc.pdf",                     chunks = text_splitter.split(pages)
})                                              vectorstore = FAISS.from_documents(
                                                    chunks, embeddings)
answer = rag_tool.run({                         
    "action": "ask",                            chain = (
    "question": "什么是RAG?"                        检索函数 | prompt | llm
})                                              )
                                                answer = chain.invoke(问题)
```

---

## FastAPI 后端设计（`ui/vue_api.py`）

### 设计要点

```python
# 单例模式：整个服务生命周期共享一个 Assistant 实例
_assistant = None

def get_assistant():
    global _assistant
    if _assistant is not None:
        return _assistant                         # ← 已初始化，直接返回
    _assistant = PDFLearningAssistant(user_id="vue_user")
    _assistant.load_document(DEFAULT_PDF_PATH)    # ← 首次调用时自动加载文档
    return _assistant
```

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/init` | GET | 初始化助手 + 返回历史 |
| `/api/ai-chat` | POST | ★ 流式问答（AI SDK v4 wire format） |
| `/api/chat` | POST | 同步问答 |
| `/api/upload-pdf` | POST | 上传新 PDF |
| `/api/token` | GET | Token 用量 |
| `/api/history` | GET | 对话历史 |
| `/api/clear-history` | POST | 清空历史 |
| `/api/add-note` | POST | 添加笔记 |
| `/api/stats` | GET | 学习统计 |
| `/api/report` | GET | 生成报告 |

### 流式协议

后端 `/api/ai-chat` 输出 AI SDK v4 wire format（单字符前缀 + JSON 值）：

```
5:{"threadId":"...","messageId":"..."}     ← 控制帧
0:"回答"                                   ← 文本增量
0:"内容"
4:{"id":"...","role":"assistant","content":[...]}  ← 消息完成帧
```

`@ai-sdk/vue` 的 `useChat` 自动解析此格式，前端 `messages` 响应式数组实时追加，产生打字机效果。

---

## 其他功能（笔记 / 统计 / 报告）

| 功能 | 调用方法 | 说明 |
|------|---------|------|
| 添加笔记 | `assistant.add_note(content, concept)` | 存入 episodic 记忆，importance=0.8 |
| 学习统计 | `assistant.get_stats()` | 会话时长 / 文档数 / 提问数 / Token 用量 |
| 生成报告 | `assistant.generate_report()` | 记忆摘要 + RAG 状态，可选存 JSON |

---

## 关键设计

**USE_LANGCHAIN 开关**：`ui/gradio_ui.py` 和 `ui/vue_api.py` 第 25 行各有一个，一行切换底层实现。

```python
USE_LANGCHAIN = True   # LangChain 版
USE_LANGCHAIN = False  # HelloAgents 版
```

**FAISS 缓存**：首次加载 PDF → 嵌入 + 保存索引到 `_faiss_cache/` → 二次加载直接读磁盘（1-2 秒），不再消耗 Embedding token。

**Token 统计**：非流式通过 AIMessage 的 `usage_metadata` 精确累计；流式按字符数估算（中文 ~1.5 chars/token）。
