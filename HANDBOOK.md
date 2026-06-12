# 智能客服项目手册

## 一、项目概述

本项目基于 **LangChain** 框架，实现了一个推荐手机流量套餐的智能客服系统。系统通过 FastAPI 提供 REST API 服务，支持流式（SSE）和非流式两种响应方式，调用大语言模型（LLM）完成用户意图理解与套餐推荐。

---

## 二、项目结构

```
pythonProject/
├── basic/
│   ├── main.py                    # 主程序：FastAPI 服务 + LangChain 链
│   ├── apiTest.py                 # API 测试客户端
│   ├── prompt_template_system.txt # 系统角色 Prompt 模板
│   └── prompt_template_user.txt   # 用户输入 Prompt 模板
└── requirements.txt               # Python 依赖清单
```

---

## 三、文件说明

### 3.1 `basic/main.py` — 主程序

核心服务文件，负责模型初始化、Prompt 加载、Chain 构建、API 接口暴露。

**主要功能模块：**

| 模块 | 说明 |
|------|------|
| 全局配置 | 设置 API 类型（openai/oneapi）、API Key、模型名称、服务端口等 |
| LangSmith 追踪 | 通过环境变量 `LANGCHAIN_TRACING_V2` 开启 LangSmith 链路追踪 |
| 数据模型（Pydantic） | 定义 `Message`、`ChatCompletionRequest`、`ChatCompletionResponse` 等请求/响应结构 |
| `getPrompt()` | 中间函数，用于在 Chain 执行时打印/记录最终发送给 LLM 的 Prompt |
| `format_response()` | 对 LLM 返回的文本进行格式化处理（段落分隔、代码块标记、换行优化） |
| `lifespan()` | FastAPI 生命周期管理，在应用启动时完成模型实例化、Prompt 模板加载、Chain 定义 |
| `chat_completions()` | POST `/v1/chat/completions` 接口，接收用户消息并调用 Chain 获取回复，支持流式/非流式返回 |
| `uvicorn.run()` | 启动 ASGI 服务器，默认端口 `8012` |

**Chain 定义：**

```python
chain = prompt | getPrompt | model
```

- `prompt`：由系统模板 + 用户模板组合而成的 `ChatPromptTemplate`
- `getPrompt`：中间处理函数，用于日志记录
- `model`：`ChatOpenAI` 实例，根据 `API_TYPE` 配置选择 OpenAI 或 OneAPI

**支持的 API 类型：**

| API_TYPE | 说明 | 默认模型 |
|----------|------|----------|
| `openai` | 调用 OpenAI GPT 系列模型 | `gpt-4o-mini` |
| `oneapi` | 调用 OneAPI 方案支持的模型 | `qwen-max`（通义千问） |

---

### 3.2 `basic/apiTest.py` — API 测试客户端

用于对主服务进行接口测试的脚本，支持流式和非流式两种模式。

**功能说明：**

| 功能 | 说明 |
|------|------|
| 请求地址 | `http://localhost:8012/v1/chat/completions` |
| 流式开关 | 通过 `stream_flag` 控制流式（`True`）/ 非流式（`False`）输出 |
| 测试用例 | 内置多个测试问题，如"有没有土豪套餐"、"200元以下，流量大的套餐有啥"等 |
| 流式处理 | 使用 `requests.post(stream=True)` 逐行读取 SSE 数据，解析 JSON 片段 |
| 非流式处理 | 直接发送 POST 请求，从响应 JSON 中提取 `choices[0].message.content` |

---

### 3.3 `basic/prompt_template_system.txt` — 系统角色 Prompt

定义了智能客服的角色设定和业务知识，内容包括：

- **角色定位**：推荐手机流量套餐的客服代表，名叫"南哥"
- **可选套餐**：

| 套餐名称 | 月费 | 流量 | 备注 |
|----------|------|------|------|
| 经济套餐 | 50 元 | 10G | — |
| 畅游套餐 | 180 元 | 100G | — |
| 无限套餐 | 300 元 | 1000G | — |
| 校园套餐 | 150 元 | 200G | 仅限在校生 |

- **多轮对话示例**：4 个参考对话，覆盖价格查询、套餐对比、超出范围等场景
- **回复风格要求**：口语化、亲切、不说"抱歉"、不加前缀

---

### 3.4 `basic/prompt_template_user.txt` — 用户输入 Prompt

定义用户消息的模板格式：

```
用户问：
{query}
```

其中 `{query}` 为占位符，运行时由用户实际输入替换。

---

### 3.5 `requirements.txt` — 依赖清单

| 包名 | 版本 | 用途 |
|------|------|------|
| `langchain` | 0.2.15 | LangChain 核心框架 |
| `langchain-openai` | 0.1.22 | LangChain 的 OpenAI 集成 |
| `langchain-community` | 0.2.15 | LangChain 社区扩展 |
| `fastapi` | 0.112.0 | Web 框架，提供 REST API |
| `uvicorn` | 0.30.6 | ASGI 服务器，运行 FastAPI 应用 |

> 测试脚本 `apiTest.py` 还依赖 `requests`，需额外安装。

---

## 四、实现流程

### 4.1 实现目标

构建一个**手机流量套餐推荐的智能客服系统**，用户通过 HTTP 接口发送自然语言问题（如"有没有土豪套餐"），系统调用大语言模型（LLM）理解用户意图，结合预设的套餐知识库，以口语化、亲切的风格返回推荐结果。系统需满足以下要求：

- 兼容 OpenAI Chat Completions API 规范，方便对接各类前端/客户端
- 支持流式（SSE）和非流式两种响应模式
- 通过 Prompt Engineering 控制模型的回复风格和知识边界
- 具备链路追踪能力，便于调试和优化

### 4.2 技术栈及作用

| 技术 | 在本项目中的作用 |
|------|------------------|
| **LangChain** | 核心编排框架，负责将 Prompt 模板、中间处理函数、LLM 模型串联成可执行的 Chain（`prompt \| getPrompt \| model`），实现声明式的调用链定义 |
| **ChatOpenAI（langchain-openai）** | LLM 调用层，统一封装 OpenAI 兼容接口的调用逻辑，支持通过 `base_url` 切换不同模型服务商（OpenAI / 通义千问等） |
| **PromptTemplate / ChatPromptTemplate** | Prompt 模板管理，将 system 角色设定和 user 输入模板从代码中解耦为独立文本文件，便于维护和迭代优化 |
| **FastAPI** | Web 服务框架，提供高性能异步 HTTP 接口，自动生成 API 文档，支持请求体校验（Pydantic）和异步处理 |
| **Pydantic** | 数据模型定义与校验，定义请求/响应的 JSON 结构（`ChatCompletionRequest`、`ChatCompletionResponse` 等），确保接口规范 |
| **Uvicorn** | ASGI 服务器，承载 FastAPI 应用的运行，支持异步并发处理 |
| **SSE（Server-Sent Events）** | 流式响应协议，通过 `StreamingResponse` 逐行推送模型生成内容，提升用户等待体验 |
| **LangSmith** | 链路追踪工具，通过 `LANGCHAIN_TRACING_V2` 环境变量开启，可在线查看每次 Chain 调用的完整输入/输出，便于调试 |

### 4.3 具体实现流程

```
┌──────────────────────────────────────────────────────────────────┐
│                     第一阶段：应用启动初始化                        │
│                                                                  │
│  1. 加载环境变量                                                  │
│     └─ 设置 LangSmith 追踪配置（LANGCHAIN_TRACING_V2、API_KEY）  │
│                                                                  │
│  2. 初始化 LLM 模型                                              │
│     ├─ API_TYPE = "oneapi" → 使用 OneAPI 代理调用通义千问         │
│     └─ API_TYPE = "openai" → 直接调用 OpenAI GPT 模型            │
│     （ChatOpenAI 统一封装，切换只需改配置，无需改代码）             │
│                                                                  │
│  3. 加载 Prompt 模板                                              │
│     ├─ prompt_template_system.txt → 系统角色设定 + 套餐知识库     │
│     └─ prompt_template_user.txt  → 用户输入模板（{query}占位符）  │
│                                                                  │
│  4. 组合 ChatPromptTemplate                                       │
│     └─ 将 system 和 user 模板合并为多轮对话结构                   │
│                                                                  │
│  5. 构建 Chain（LCEL 管道）                                       │
│     └─ chain = prompt | getPrompt | model                        │
│         ├─ prompt：渲染模板，将 {query} 替换为实际用户输入         │
│         ├─ getPrompt：中间处理函数，记录最终发送给 LLM 的内容      │
│         └─ model：调用 LLM 进行推理，返回生成结果                 │
│                                                                  │
│  6. 启动 FastAPI + Uvicorn 服务                                   │
│     └─ 监听 0.0.0.0:8012，等待客户端请求                         │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                     第二阶段：请求处理与响应                        │
│                                                                  │
│  用户发送 POST /v1/chat/completions                               │
│         │                                                        │
│         ▼                                                        │
│  1. 解析请求体                                                    │
│     └─ FastAPI 自动将 JSON 映射为 ChatCompletionRequest 模型      │
│                                                                  │
│  2. 提取用户输入                                                  │
│     └─ 取 messages 列表最后一条消息的 content 作为 query           │
│                                                                  │
│  3. 调用 Chain 执行推理                                           │
│     chain.invoke({"query": "有没有土豪套餐"})                     │
│         │                                                        │
│         ▼                                                        │
│     Chain 内部执行流程：                                          │
│     ┌─────────────────────────────────────────────┐              │
│     │ prompt 渲染                                 │              │
│     │   system: "你是一个推荐手机流量套餐的客服..." │              │
│     │   human:  "用户问：有没有土豪套餐"           │              │
│     │          ↓                                   │              │
│     │ getPrompt 记录日志                           │              │
│     │          ↓                                   │              │
│     │ model 调用 LLM 推理，返回 AIMessage          │              │
│     └─────────────────────────────────────────────┘              │
│         │                                                        │
│         ▼                                                        │
│  4. 格式化 LLM 输出                                              │
│     └─ format_response() 处理段落分隔、代码块标记、换行优化       │
│                                                                  │
│  5. 根据 stream 参数选择响应方式                                   │
│     ├─ stream=True  → SSE 流式推送                               │
│     │   └─ 逐行生成 JSON chunk，每行间隔 0.5s，最后发送 stop 信号 │
│     └─ stream=False → 一次性返回完整 JSON                        │
│         └─ 构造 ChatCompletionResponse，包含完整的回复内容         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 五、接口说明

### POST `/v1/chat/completions`

**请求体：**

```json
{
  "messages": [
    {"role": "user", "content": "有没有土豪套餐"}
  ],
  "stream": false
}
```

**非流式响应：**

```json
{
  "id": "chatcmpl-xxxx",
  "object": "chat.completion",
  "created": 1717814400,
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "我们这里有无限套餐..."},
      "finish_reason": "stop"
    }
  ]
}
```

**流式响应：** 以 `text/event-stream` 格式逐行推送 JSON 片段，每个片段包含 `delta.content`，最后以 `finish_reason: "stop"` 结束。

---

## 六、运行指南

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install requests  # 测试脚本额外依赖
```

### 2. 修改配置

编辑 `basic/main.py` 中的以下配置项（根据实际情况调整）：

- `API_TYPE`：选择 `openai` 或 `oneapi`
- 对应的 API Base / API Key / 模型名称
- `PORT`：服务端口（默认 `8012`）

### 3. 启动服务

```bash
cd basic
python main.py
```

### 4. 测试接口

```bash
cd basic
python apiTest.py
```
