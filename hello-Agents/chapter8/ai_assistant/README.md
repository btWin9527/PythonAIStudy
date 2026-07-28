# 智能文档问答助手 — LangChain 版

## HelloAgents vs LangChain 对比

| 功能 | HelloAgents 版 | LangChain 版 |
|------|:---:|:---:|
| **文件** | `A_Assistant.py` | `A_Assistant_langchain.py` |
| **LLM 调用** | 框架自动检测 Provider | `ChatOpenAI` 显式配置 |
| **PDF 解析** | `RAGTool.run(action="add_document")` | `PyPDFLoader(pdf_path).load()` |
| **文档切割** | `RAGTool` 内置 (chunk_size/overlap) | `RecursiveCharacterTextSplitter` |
| **向量存储** | `Qdrant`（外部云服务） | `FAISS`（纯内存） |
| **Embedding** | `RAGTool` 内置 DASHSCOPE | `DashScopeEmbeddings`（自定义适配器） |
| **RAG 检索** | `RAGTool.run(action="ask")` 一行完成 | 手动构建链：检索 → prompt → LLM |
| **高级检索** | 支持 MQE + HyDE | 暂未实现（保留参数兼容） |
| **工作记忆** | `MemoryTool(working)` | `SimpleMemory.add(working)` |
| **情景记忆** | `MemoryTool(episodic)` | `SimpleMemory.add(episodic)` |
| **记忆搜索** | `MemoryTool.run(action="search")` | `SimpleMemory.search()` 嵌入相似度 |
| **API 调用风格** | 统一 `tool.run({action, ...})` | LangChain 链式调用 `|` |
| **外部依赖** | Qdrant 云数据库 | 无需外部服务（纯内存） |

### 关键差异详解

```
HelloAgents 方式：封装黑盒，一行搞定                LangChain 方式：组合积木，流程可见

# 文档加载 + 检索 + 回答（HelloAgents）              # 文档加载（LangChain）
rag_tool.run({                                       loader = PyPDFLoader(path)
    "action": "add_document",                        pages = loader.load()
    "file_path": "doc.pdf",                          chunks = text_splitter.split(pages)
})                                                   
                                                     # 向量化（LangChain）
answer = rag_tool.run({                              vectorstore = FAISS.from_documents(
    "action": "ask",                                     chunks, embeddings)
    "question": "什么是RAG?"                         
})                                                   # 检索 + 回答（LangChain）
                                                     chain = (
# 记忆记录（HelloAgents）                               检索函数 
memory_tool.run({                                    | prompt模板
    "action": "add",                                 | llm
    "content": "log...",                             | 输出解析器
})                                                   )
                                                     answer = chain.invoke(问题)
```

**HelloAgents 优势**：API 极简，不需要关心内部实现；框架自动管理 Qdrant 连接、Memory 持久化。

**LangChain 优势**：流程完全可控、可定制；每个环节可替换（换 Embedding 只需换一个对象）；不依赖外部数据库。

---

## 目录结构

```
ai_assistant/
├── .env                          # 环境变量（API 密钥、模型配置）
├── run.py                        # ★ 统一启动入口（交互式选择模式）
├── A_Assistant.py                # HelloAgents 版
├── A_Assistant_langchain.py      # LangChain 版
├── pdf/
│   ├── test.pdf                  # 默认文档（46KB）
│   └── Happy-LLM-0727.pdf        # 大文档（20MB）
├── ui/
│   ├── gradio_ui.py              # Python Gradio Web UI
│   ├── vue_api.py                # ★ FastAPI 后端（Vue 3 接口）
│   └── vue_client/               # ★ Vue 3 前端项目
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       ├── index.html
│       └── src/
│           ├── main.ts
│           ├── App.vue
│           ├── style.css
│           ├── api/
│           │   └── index.ts       # API 客户端 + SSE 流式读取
│           ├── composables/
│           │   └── useStreamChat.ts # 流式聊天 composable
│           └── components/
│               ├── TokenBar.vue    # Token 用量显示
│               ├── Sidebar.vue     # 导航侧栏
│               ├── HomeView.vue    # 开始使用（PDF上传/状态）
│               ├── ChatView.vue    # ★ 智能问答（@ai-sdk/vue 流式）
│               ├── NotesView.vue   # 学习笔记
│               └── StatsView.vue   # 学习统计 / 报告
├── _chat_history.json            # 对话历史持久化（运行时生成）
└── _faiss_cache/                 # FAISS 向量索引缓存
```

## 启动方式

### 统一入口（推荐）

```bash
cd ai_assistant
python run.py
# 交互式选择：
#   1) py   — Gradio Web UI（Python 原生界面）
#   2) vue  — Vue 3 UI（API + 前端分离）

# 或直接指定模式：
python run.py py     # 启动 Gradio UI → http://localhost:7860
python run.py vue    # 启动 FastAPI  → http://localhost:8000
```

### 快速启动（传统方式）

```bash
# Python UI 模式
python ui/gradio_ui.py    # → http://localhost:7860

# Vue UI 模式
python run.py vue         # 启动后端 API
cd ui/vue_client && npm install && npm run dev  # 启动前端 → http://localhost:5173
```

## 组件总览

```
┌──────────────────────────────────────────────────────────────┐
│                      ui/gradio_ui.py                         │
│  demo.load(auto_init) → 页面加载时自动初始化                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │🏠 开始使用│  │💬 智能问答│  │📝 学习笔记│  │📊 学习统计│    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │              │             │             │           │
└───────┼──────────────┼─────────────┼─────────────┼───────────┘
        │              │             │             │
        ▼              ▼             ▼             ▼
┌──────────────────────────────────────────────────────────────┐
│                 A_Assistant_langchain.py                     │
│                                                              │
│  PDFLearningAssistant                                        │
│  ├── llm: ChatOpenAI(qwen-max)                               │
│  ├── embeddings: DashScopeEmbeddings(text-embedding-v3)      │
│  ├── vectorstore: FAISS                                      │
│  ├── memory: SimpleMemory(working + episodic)                │
│  └── text_splitter: RecursiveCharacterTextSplitter            │
└──────────────────────────────────────────────────────────────┘
```

## 核心流程

### 流程 1：启动与自动初始化

```
gradio_ui.main()
  │
  ├─→ create_gradio_ui()
  │     ├─→ from A_Assistant_langchain import PDFLearningAssistant
  │     ├─→ 构建 4 个 Tab 界面 + 绑定事件回调
  │     └─→ demo.load(fn=auto_init, outputs=[init_output])  ← 页面加载触发
  │
  └─→ demo.launch() → http://localhost:7860

页面加载 → auto_init():
  ├─→ 创建 PDFLearningAssistant 实例
  ├─→ ChatOpenAI + DashScopeEmbeddings + SimpleMemory
  ├─→ load_document(DEFAULT_PDF_PATH)  ← 自动加载默认文档
  │     └─→ PyPDFLoader → RecursiveTextSplitter → FAISS.from_documents()
  ├─→ 恢复上次对话历史 (_chat_history.json)
  └─→ 显示 "✅ 助手已就绪"
```

---

### 流程 2a：默认文档自动加载（页面加载时触发）

```
auto_init() → load_document("pdf/test.pdf")
  │
  ├─ 1. PyPDFLoader("pdf/test.pdf")          ← LangChain: 解析 PDF
  │     └─→ pages[0].page_content = "地下矿山照片..."
  │
  ├─ 2. RecursiveCharacterTextSplitter        ← LangChain: 按规则切块
  │     └─→ chunks = [Document(page_content="...")]
  │
  ├─ 3. FAISS.from_documents(chunks, embeddings)  ← LangChain: 向量化 + 索引
  │     ├─→ DashScopeEmbeddings.embed_documents()  ← DashScope 原生 API
  │     │     └─→ TextEmbedding.call(model="text-embedding-v3", input=[...])
  │     │           HTTP POST → DashScope → 返回 1024 维向量
  │     └─→ FAISS 内存索引（余弦相似度检索）
  │
  ├─ 4. _build_rag_chain(llm, vectorstore)
  │     ├─→ ChatPromptTemplate(system + context + human)
  │     └─→ retrieve_and_format | prompt | llm | StrOutputParser
  │
  ├─ 5. memory.add("加载了文档...", episodic, importance=0.9)
  │
  └─ 6. 返回 {"success": True, "message": "加载成功！(耗时: 0.5秒, 1页, 1块)"}
```

---

### 流程 2b：手动上传文档

用户在 Tab 1 上传 PDF → 点击"加载文档" → `load_pdf()`：

```
gradio_ui.load_pdf(pdf_file)
  │
  ├─→ pdf_file.name  ← Gradio 临时文件路径
  │
  └─→ assistant.load_document(pdf_file.name)  → 同流程 2a
```

---

### 流程 3：用户提问 — RAG 问答

用户在 Tab 2 输入问题 → 点击"发送" → `chat()`：

```
chat(message, history)
  │
  ├─→ 关键词检测: "之前/学过/回顾/历史/记得" → 学习回顾
  │
  └─→ assistant.ask(message)
        │
        ├─ 1. memory.add("提问: ...", working)
        │
        ├─ 2. _rag_chain.invoke({"question": message})
        │     │
        │     ├─→ retrieve_and_format()
        │     │     ├─→ vectorstore.similarity_search(message, k=5)
        │     │     │     ├─→ DashScopeEmbeddings.embed_query(message)
        │     │     │     └─→ FAISS 余弦相似度 → Top-5 文本块
        │     │     └─→ "[文档1]...\n---\n[文档2]..."
        │     │
        │     ├─→ ChatPromptTemplate(system + context + question)
        │     │
        │     ├─→ ChatOpenAI.invoke() → qwen-max → 生成回答
        │     │
        │     └─→ StrOutputParser() → 纯文本 answer
        │
        ├─ 3. memory.add("关于'...'的学习", episodic)
        │
        └─ 4. 返回 answer → history → 渲染 + 持久化到 _chat_history.json
```

---

### 流程 3b：学习回顾（智能路由）

当用户输入含 "之前/学过/回顾/历史/记得" 关键词时：

```
chat(message, history) → assistant.recall(message)
  └─→ memory.search(query, limit=5)
        ├─→ embed_query → 余弦相似度匹配
        └─→ _keyword_search → 关键词匹配（降级）
```

---

## 对话历史持久化

```
每次发消息 → _save_history(history) → _chat_history.json
页面加载   → _load_history()       → Chatbot.value = saved_history
点击清空   → _save_history([])     → history = []
```

刷新页面或切换 Tab 后，对话历史从 `_chat_history.json` 恢复。

---

## 附：学习笔记 & 学习统计

| Tab | 触发 | 调用方法 | 说明 |
|-----|------|---------|------|
| 📝 学习笔记 | 点击"保存笔记" | `assistant.add_note(content, concept)` | 存入 episodic，importance=0.8 |
| 📊 学习统计 | 点击"刷新统计" | `assistant.get_stats()` | 会话时长/文档数/提问数 |
| 📊 生成报告 | 点击"生成报告" | `assistant.generate_report()` | 记忆摘要 + RAG 状态，可选存 JSON |

---

## 关键设计点

### 自动初始化

`demo.load(fn=auto_init)` 在页面加载时触发，用户无需手动点击"初始化助手"：

```python
# gradio_ui.py
demo.load(fn=auto_init, outputs=[init_output])

def auto_init():
    assistant = AssistantClass(user_id="web_user")
    assistant.load_document(DEFAULT_PDF_PATH)
    return "✅ 助手已就绪\n📄 默认文档已加载"
```

### USE_LANGCHAIN 开关

`ui/gradio_ui.py` 第 25 行 / `ui/vue_api.py` 第 25 行：一行切换框架

```python
USE_LANGCHAIN = True   # LangChain 版
USE_LANGCHAIN = False  # HelloAgents 版
```

---

## Vue 3 前端（`ui/vue_client/`）

### 技术栈

| 层 | 技术 |
|----|------|
| 框架 | Vue 3 + TypeScript |
| 构建 | Vite 5 |
| AI 流式 | `@ai-sdk/vue`（`useChat`） |
| 后端协议 | AI SDK v4 wire format |
| CSS | scoped 暗色主题 |

### 架构

```
┌────────────────────────────────────────────────────────────────┐
│                        Vue 3 前端 :5173                        │
│  ┌──────────┐  ┌──────────────────────────────────────────┐   │
│  │ Sidebar  │  │  Main Area                                │   │
│  │          │  │  ┌──────────────────────────────────────┐ │   │
│  │ 🏠 开始  │  │  │ TokenBar  (模型 | 剩余 token | 调用) │ │   │
│  │ 💬 问答  │  │  └──────────────────────────────────────┘ │   │
│  │ 📝 笔记  │  │  ┌──────────────────────────────────────┐ │   │
│  │ 📊 统计  │  │  │ Content View                          │ │   │
│  │          │  │  │  HomeView / ChatView / Notes / Stats  │ │   │
│  └──────────┘  │  └──────────────────────────────────────┘ │   │
│                └──────────────────────────────────────────┘   │
└──────────────────────────┬─────────────────────────────────────┘
                           │ Vite proxy /api → :8000
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                  FastAPI 后端 :8000                             │
│  GET  /api/init          → 初始化助手 + 恢复历史                │
│  GET  /api/token         → Token 用量                          │
│  POST /api/upload-pdf    → 上传 PDF                            │
│  POST /api/ai-chat       → AI SDK v4 流式问答（SSE）            │
│  POST /api/chat          → 同步问答                             │
│  POST /api/add-note      → 添加笔记                             │
│  GET  /api/stats         → 学习统计                             │
│  GET  /api/report        → 生成报告                             │
│  GET  /api/history       → 对话历史                             │
│  POST /api/clear-history → 清空历史                             │
└────────────────────────────────────────────────────────────────┘
```

### 流式协议（AI SDK v4 wire format）

后端 `/api/ai-chat` 与 `@ai-sdk/vue` 的 `useChat` 对接，协议格式：

```
请求: POST /api/ai-chat
Body: { "messages": [{"role": "user", "content": "你好"}] }

响应: AI SDK v4 wire format (单字符前缀 + JSON)
  5:{"threadId":"...","messageId":"..."}  ← 控制帧（messageId）
  0:"这是"                                ← 增量文本（逐块流式）
  0:"回复内容"
  4:{"id":"...","role":"assistant",...}   ← 完整消息帧（流结束）
```

前端 `ChatView.vue` 中使用：

```ts
import { useChat } from '@ai-sdk/vue'

const { messages, input, handleSubmit, isLoading, setMessages } = useChat({
  api: '/api/ai-chat',
})
```

### 打字机效果

`@ai-sdk/vue` 原生支持流式渲染，`messages` 数组的最后一条 `assistant` 消息的 `content` 在每个 chunk 到达时自动追加，浏览器即时更新 DOM，产生逐字打印效果。消息末尾带闪烁光标 `▌` 标识流式进行中。

### 两种 UI 模式对比

| 特性 | py-ui（Gradio） | vue-ui（Vue 3） |
|------|:---:|:---:|
| 启动方式 | `python run.py py` | `python run.py vue` + `npm run dev` |
| 端口 | 7860 | 5173 (前端) / 8000 (API) |
| 界面风格 | Gradio 主题 | 自定义暗色主题 |
| 流式效果 | Gradio 默认 | `@ai-sdk/vue` 逐字打印 |
| 依赖 | 仅 Python | Python + Node.js |
| 跨域 | 无需处理 | CORS + Vite 代理 |
| API 文档 | 无 | `/docs` (Swagger) |
