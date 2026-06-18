# FirstAgentTest 优化方案

## 对比总览

| 对比维度 | v1（原始版） | v2（优化版） |
|---------|------------|------------|
| LLM 接入 | 原生 `openai.OpenAI` | LangChain `ChatOpenAI`（与项目 config.py 统一） |
| Agent 循环 | `for i in range(5)` 手动循环 + 正则解析 | `AgentExecutor` 自动管理循环和工具调度 |
| 工具定义 | 普通 dict + 手动正则提取 `Thought/Action` | `@tool` 装饰器，带 docstring 的语义化描述 |
| Prompt 管理 | 代码内硬编码长字符串 | 外部 `.txt` 文件加载（`PromptTemplate.from_file()`） |
| API 密钥 | 代码中明文硬编码 | 环境变量读取 |
| MCP 接入 | 无 | 引入 `langchain_mcp_adapters`，支持动态加载 MCP 工具 |
| 错误处理 | 基础 try/except | Agent 内置 `handle_parsing_errors` 自动重试 + 详细日志 |
| 交互方式 | 单次执行固定 query | 交互式对话循环 |

---

## 优化步骤详解

### 步骤 1：统一 LLM 接入层（原生 OpenAI → LangChain ChatOpenAI）

**问题**：`FirstAgentTest.py` 直接使用 `openai.OpenAI` 客户端，定义了自定义 `OpenAICompatibleClient` 类封装。这与项目中 `config.py` 使用的 `langchain_openai.ChatOpenAI` 不一致，无法复用项目的模型配置和链路追踪能力。

**方案**：使用 `langchain_openai.ChatOpenAI`，支持通过 `base_url` 切换不同服务商。

```python
# v1: 自定义封装
from openai import OpenAI
class OpenAICompatibleClient:
    def __init__(self, model, api_key, base_url):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    def generate(self, prompt, system_prompt):
        response = self.client.chat.completions.create(...)
        return response.choices[0].message.content

# v2: LangChain 标准方式
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ.get("OPENAI_BASE_URL"),  # 可选，切换代理服务
    temperature=0.3,
)
```

**收益**：与项目 `config.py` 模式一致，后续可直接复用 LangChain 生态能力。

---

### 步骤 2：Agent 循环机制升级（手动 for 循环 → AgentExecutor）

**问题**：v1 使用 `for i in range(5)` 硬编码最大 5 次循环，用正则 `re.search(r"Action: (.*)")` 手动解析 LLM 输出的 `Thought/Action` 格式。这种方式存在以下缺陷：
- LLM 输出格式不稳定时容易解析失败
- 无法判断何时该停止（只能依赖 LLM 输出 `Finish[...]`）
- 每一轮都要手动构建 `prompt_history` 拼接上下文

**方案**：使用 LangChain 的 `create_tool_calling_agent` + `AgentExecutor`，Agent 框架自动处理：
- 工具调用决策（LLM 判断何时调用哪个工具）
- 工具执行和结果反馈
- 循环终止条件（达到答案或超过最大迭代次数）
- 解析错误自动重试

```python
# v1: 手动循环
for i in range(5):
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    action_match = re.search(r"Action: (.*)", llm_output)
    # 手动解析、执行工具、拼接 observation...

# v2: AgentExecutor 自动管理
from langchain.agents import create_tool_calling_agent, AgentExecutor

agent = create_tool_calling_agent(llm=model, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(
    agent=agent, tools=tools,
    max_iterations=5,           # 最大迭代次数
    handle_parsing_errors=True,  # 解析错误自动重试
    verbose=True,                # 打印执行过程
)
result = agent_executor.invoke({"query": user_input})
```

**收益**：代码量减少 ~60%，不再需要手动写 Thought/Action 解析逻辑和 prompt 历史拼接。

---

### 步骤 3：工具定义方式升级（dict + 正则 → @tool 装饰器）

**问题**：v1 将工具函数放入 `available_tools` 字典，运行时通过正则 `re.search(r"(\w+)\(")` 提取工具名和参数，再用 `dict(re.findall(r'(\w+)="([^"]*)"', args_str))` 解析参数。这种方式：
- 参数解析脆弱（复杂参数如 JSON、嵌套字符串无法处理）
- 工具描述在 Prompt 字符串中硬编码，容易不一致

**方案**：使用 `@tool` 装饰器，docstring 自动成为工具的 description 传给 LLM，LangChain 自动处理参数序列化。

```python
# v1: 手动字典 + 正则解析
available_tools = {"get_weather": get_weather, "get_attraction": get_attraction}
tool_name = re.search(r"(\w+)\(", action_str).group(1)
kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))
available_tools[tool_name](**kwargs)

# v2: @tool 装饰器
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """查询指定城市的实时天气信息。参数 city: 城市英文名。"""
    # ...实现...

# LangChain 自动生成 tool schema，无需手动解析参数
```

**收益**：工具定义即文档，参数类型安全，与 LangChain Agent 框架无缝集成。

---

### 步骤 4：Prompt 外部化（字符串硬编码 → .txt 文件加载）

**问题**：v1 的 `AGENT_SYSTEM_PROMPT` 直接在代码中硬编码（26 行字符串），不便于编辑、版本对比和 A/B 测试。

**方案**：将 Prompt 拆分为两个 `.txt` 文件，使用 `PromptTemplate.from_file()` 加载，与项目 `basic/`、`cot/`、`tot/` 等模块保持一致。

```
# 文件结构
chapter1/
├── prompt_agent_system.txt   # 系统角色 + 行为规则
├── prompt_agent_user.txt     # 用户输入模板 ({query} 占位符)
```

```python
# v1: 硬编码
AGENT_SYSTEM_PROMPT = """你是一个智能旅行助手..."""

# v2: 外部文件
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

prompt_sys = PromptTemplate.from_file("prompt_agent_system.txt")
prompt_user = PromptTemplate.from_file("prompt_agent_user.txt")
prompt = ChatPromptTemplate.from_messages([
    ("system", prompt_sys.template),
    ("human", prompt_user.template),
])
```

**收益**：Prompt 与代码解耦，非开发人员也能编辑优化，支持版本管理。

---

### 步骤 5：API 密钥安全管理（硬编码 → 环境变量）

**问题**：v1 将 `API_KEY`、`BASE_URL`、`MODEL_ID`、`TAVILY_API_KEY` 全部明文写在代码第 140-143 行，存在严重安全隐患。

**方案**：所有敏感信息从环境变量读取。

```python
# v1: 硬编码（危险！）
API_KEY = "YOUR_API_KEY"
BASE_URL = "YOUR_BASE_URL"
MODEL_ID = "YOUR_MODEL_ID"
os.environ['TAVILY_API_KEY'] = "YOUR_TAVILY_API_KEY"

# v2: 环境变量
# export OPENAI_API_KEY="sk-xxx"
# export OPENAI_BASE_URL="https://api.wlai.vip/v1"
# export MODEL_ID="gpt-4o-mini"
# export TAVILY_API_KEY="tvly-xxx"
```

**收益**：符合安全最佳实践，避免密钥泄露到代码仓库。

---

### 步骤 6：引入 MCP（Model Context Protocol）工具接入

**问题**：v1 的工具（`get_weather`、`get_attraction`）直接硬编码 HTTP API 调用，每个新数据源都需要手写请求逻辑、错误处理、数据解析代码。

**方案**：引入 MCP 协议，通过 `langchain_mcp_adapters` 将 MCP 服务器的工具自动转换为 LangChain Tool。MCP 是 Anthropic 提出的标准化协议，用于 AI 模型与外部工具/数据源的安全交互。

#### 6.1 安装依赖

```bash
pip install langchain-mcp-adapters
```

#### 6.2 配置 MCP 客户端连接

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    # ---- 当前已接入的 MCP 服务 ----
    "apipost": {
        "url": "https://open.apipost.net/mcp",
        "transport": "streamable_http",
        "headers": {"api-token": os.environ["APIPOST_MCP_TOKEN"]}
    },

    # ---- 可扩展的 MCP 服务（示例） ----
    # "weather": {
    #     "command": "npx",
    #     "args": ["-y", "@h1deya/mcp-server-weather"]
    # },
    # "brave-search": {
    #     "command": "npx",
    #     "args": ["-y", "@anthropic-ai/mcp-server-brave-search"],
    #     "env": {"BRAVE_API_KEY": os.environ["BRAVE_API_KEY"]}
    # }
})

# 自动获取所有 MCP 工具并转为 LangChain Tool
mcp_tools = client.get_tools()
```

#### 6.3 MCP 接入的架构优势

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LangChain  │────▶│  MCP Client      │────▶│  MCP Server A   │
│  Agent      │     │  (MultiServer)   │     │  (天气预报)      │
│             │     │                  │────▶│  MCP Server B   │
│  tools =    │     │  .get_tools()    │     │  (搜索服务)      │
│  local +    │     │  → LangChain     │────▶│  MCP Server C   │
│  mcp_tools  │     │    Tool 列表     │     │  (知识库)        │
└─────────────┘     └──────────────────┘     └─────────────────┘
```

相比直接在代码中写 HTTP 请求的**核心优势**：

| 维度 | 传统方式（v1） | MCP 方式（v2） |
|------|-------------|-------------|
| 工具定义 | 每个 API 手写函数 + 错误处理 | MCP Server 端定义，客户端自动发现 |
| 参数校验 | 手动正则提取，类型不安全 | MCP 提供 JSON Schema，自动校验 |
| 版本更新 | API 变更需修改代码重新部署 | Server 端更新，客户端无需改动 |
| 认证管理 | 每个工具单独配置 | 统一在 MCP Client 层管理 |
| 扩展性 | 新增工具 = 新增代码文件 | 新增工具 = 新增一条 MCP Server 配置 |

#### 6.4 当前可用的 MCP 工具示例

当前环境已接入 `apipost-mcp` 服务器，提供以下工具可供 Agent 使用：

| 工具名 | 功能 | 应用场景 |
|--------|------|---------|
| `get_project_tree` | 获取团队和项目列表 | 查询 API 项目结构 |
| `search_target` | 搜索 API 节点（接口/目录/文档） | 查找特定 API 定义 |
| `search_model` | 搜索数据模型详情 | 查询 API 请求/响应结构 |

这些工具可以作为 Agent 的"知识库查询"能力，拓展 Agent 的应用场景。

---

### 步骤 7：交互模式升级（单次执行 → 交互式对话）

**问题**：v1 是脚本式单次执行，`user_prompt` 写死在代码中。

**方案**：改为交互式 `while True` 循环，用户可以持续提问，输入 `quit` 退出。

---

## 运行方式

```bash
# 1. 设置环境变量
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.wlai.vip/v1"   # 可选
export MODEL_ID="gpt-4o-mini"
export TAVILY_API_KEY="your-tavily-key"

# 2. 可选：设置 MCP 凭证
export APIPOST_MCP_TOKEN="your-apipost-token"

# 3. 安装依赖
pip install langchain langchain-openai langchain-mcp-adapters tavily-python requests

# 4. 运行
cd hello-Agents/chapter1/v2_optimized/
python FirstAgentTest_v2.py
```

---

## 文件清单

```
hello-Agents/chapter1/
├── FirstAgentTest.py          # v1 原始版本
├── FirstAgentTest.ipynb
├── README.md                  # 本文档（优化方案说明）
└── v2_optimized/
    ├── FirstAgentTest_v2.py        # v2 优化版本
    ├── prompt_agent_system.txt     # 系统 Prompt 模板
    └── prompt_agent_user.txt       # 用户 Prompt 模板
```
