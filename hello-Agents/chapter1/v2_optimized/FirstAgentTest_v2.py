"""
============================================================================
  FirstAgentTest_v2.py —— 智能旅行助手（LangChain Agent + MCP 优化版）
============================================================================

  相比 v1 的改进点：
    1. 使用 LangChain ChatOpenAI 替代原始 openai.OpenAI（与项目 config.py 统一）
    2. 使用 LangChain Agent 框架（create_tool_calling_agent + AgentExecutor）替代手动 for 循环
    3. 工具通过 @tool 装饰器定义，替代手动正则解析 Action
    4. Prompt 从外部 .txt 文件加载，与项目其他模块风格一致
    5. API 密钥从环境变量读取，不再硬编码
    6. 引入 MCP 客户端模式，演示如何接入 MCP 工具

  运行前请设置环境变量：
    export OPENAI_API_KEY="your-api-key"
    export OPENAI_BASE_URL="your-base-url"
    export MODEL_ID="your-model-id"
    export TAVILY_API_KEY="your-tavily-key"

============================================================================
"""

import os
import logging
from typing import Optional

# ============================================================================
# 第1部分：LangChain 核心导入
# ============================================================================
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent

# ============================================================================
# 第2部分：日志配置
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


# ============================================================================
# 第3部分：LLM 客户端封装（复用项目 config.py 模式）
# ============================================================================
def create_model(
    model_id: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.3,
) -> ChatOpenAI:
    """
    创建 ChatOpenAI 实例，兼容 OpenAI 及各类代理服务（如 OneAPI）。

    优先级：参数 > 环境变量 > 默认值
    """
    _model = model_id or os.environ.get("MODEL_ID", "gpt-4o-mini")
    _base_url = base_url or os.environ.get("OPENAI_BASE_URL")
    _api_key = api_key or os.environ.get("OPENAI_API_KEY")

    if not _api_key:
        raise ValueError("请设置环境变量 OPENAI_API_KEY 或传入 api_key 参数")

    kwargs = dict(model=_model, api_key=_api_key, temperature=temperature)
    if _base_url:
        kwargs["base_url"] = _base_url

    logger.info(f"LLM 模型: {_model} @ {_base_url or 'OpenAI 官方'}")
    return ChatOpenAI(**kwargs)


# ============================================================================
# 第4部分：加载 System Prompt（外部 .txt 文件）
# ============================================================================
def load_system_prompt(path: Optional[str] = None) -> str:
    """从外部文件读取 system prompt 文本。"""
    _base = os.path.dirname(os.path.abspath(__file__))
    path = path or os.path.join(_base, "prompt_agent_system.txt")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ============================================================================
# 第5部分：工具定义（使用 @tool 装饰器，LangChain 原生方式）
# ============================================================================
import requests
from datetime import datetime, timedelta


@tool
def get_weather(city: str, date: str = "today") -> str:
    """
    查询指定城市在指定日期的天气信息。
    参数 city: 城市英文名，如 Beijing、Shanghai、Tokyo、Taiyuan。
    参数 date: 日期，可选 "today"（今天）、"tomorrow"（明天）或具体日期 "YYYY-MM-DD"。
    """
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # 确定目标日期
        if date == "today":
            target_date = datetime.now().strftime("%Y-%m-%d")
        elif date == "tomorrow":
            target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            target_date = date  # 支持直接传 "YYYY-MM-DD"

        # 从多日预报中匹配目标日期
        for day in data.get("weather", []):
            if day["date"] == target_date:
                weather_desc = day["hourly"][4]["weatherDesc"][0]["value"]
                temp_min = day["mintempC"]
                temp_max = day["maxtempC"]
                result = f"{city} {target_date} 天气：{weather_desc}，温度 {temp_min}°C ~ {temp_max}°C"
                logger.info(f"[get_weather] {result}")
                return result

        # 没匹配到目标日期，回退到当前天气
        current = data["current_condition"][0]
        weather_desc = current["weatherDesc"][0]["value"]
        temp_c = current["temp_C"]
        result = f"{city} 当前天气：{weather_desc}，温度 {temp_c}°C（未找到'{target_date}'的预报）"
        logger.info(f"[get_weather] {result}")
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"[get_weather] 网络错误: {e}")
        return f"查询天气失败（网络问题）：{e}"
    except (KeyError, IndexError) as e:
        logger.error(f"[get_weather] 解析错误: {e}")
        return f"查询天气失败（数据解析问题），请检查城市名是否正确。"


@tool
def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气搜索推荐旅游景点。
    参数 city: 城市名。参数 weather: 当前天气描述。
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "TAVILY_API_KEY 环境变量未配置，无法搜索景点。"

    try:
        from tavily import TavilyClient
        tavily = TavilyClient(api_key=api_key)
        query = f"'{city}' 在'{weather}'天气下最值得去的旅游景点及理由"
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
    except ImportError:
        return "tavily-python 库未安装，请执行: pip install tavily-python"
    except Exception as e:
        logger.error(f"[get_attraction] 搜索失败: {e}")
        return f"景点搜索失败：{e}"

    if response.get("answer"):
        result = response["answer"]
        logger.info(f"[get_attraction] 综合回答: {result[:100]}...")
        return result

    formatted = []
    for r in response.get("results", []):
        formatted.append(f"- {r['title']}: {r['content']}")
    if not formatted:
        return "抱歉，未找到该城市在指定天气下的景点信息。"
    result = "根据搜索结果，以下信息供参考：\n" + "\n".join(formatted)
    logger.info(f"[get_attraction] 返回 {len(formatted)} 条结果")
    return result


# ============================================================================
# 第6部分：MCP 工具接入（演示模式）
# ============================================================================
def get_mcp_tools_if_available():
    """
    尝试从 MCP 服务器获取工具并转换为 LangChain Tool。

    使用 langchain_mcp_adapters 库（需要安装: pip install langchain-mcp-adapters）。

    MCP 连接说明：
      - apipost-mcp：API 管理平台工具（远程 HTTP，已配置 Token）  ✅ 可用
      - tavily-mcp：  搜索引擎（远程 HTTP，公网部署，用 TAVILY_API_KEY 认证）  ✅ 可用
      - weather-mcp： 天气查询（本地进程，需自行启动）  ⚠️ 注释中，按需启用

    优势：
      - MCP 工具由服务端提供，无需本地维护 API 调用代码
      - 支持动态发现工具、版本管理
      - 统一认证和参数校验
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        tavily_api_key = os.environ.get("TAVILY_API_KEY", "")

        # 构建 MCP 服务器配置
        servers = {
            # ---- 远程 MCP：API 管理平台（公网部署，直连即可） ----
            "apipost": {
                "url": "https://open.apipost.net/mcp",
                "transport": "streamable_http",
                "headers": {
                    "api-token": os.environ.get("APIPOST_MCP_TOKEN", "")
                }
            },
        }

        # ---- 远程 MCP：搜索引擎（公网部署，直连即可） ----
        if tavily_api_key:
            servers["tavily"] = {
                "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}",
                "transport": "streamable_http",
            }

        # ---- 本地 MCP：天气查询（需本地启动进程） ----
        # servers["weather"] = {
        #     "url": "http://localhost:8080/mcp",
        #     "transport": "streamable_http",
        # }

        import asyncio
        async def _load():
            client = MultiServerMCPClient(servers)
            tools = await client.get_tools()
            return tools, client

        tools, client = asyncio.run(_load())
        logger.info(f"[MCP] 成功加载 {len(tools)} 个 MCP 工具，来源: {list(servers.keys())}")
        return tools, client
    except ImportError:
        logger.warning(
            "[MCP] langchain-mcp-adapters 未安装，跳过 MCP 工具加载。"
            "安装命令: pip install langchain-mcp-adapters"
        )
        return [], None
    except Exception as e:
        logger.warning(f"[MCP] 连接 MCP 服务器失败: {e}")
        return [], None


# ============================================================================
# 第7部分：Agent 构建
# ============================================================================
def build_agent(
    model: ChatOpenAI,
    tools: list,
    system_prompt: str,
) -> "CompiledStateGraph":
    """
    构建 LangChain Agent（使用 langchain 1.x 的 create_agent API）。

    新 API 优势：
      - 基于 LangGraph 的 StateGraph，自动管理工具调用循环
      - system_prompt 直接传字符串，无需 ChatPromptTemplate
      - 内置解析错误处理和重试机制
    """
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )


# ============================================================================
# 第8部分：主流程
# ============================================================================
def main():
    # ---------- 8.1 配置（复用 FirstAgentTest.py 中的凭证 + MCP Token）----------
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "输出你的DashScope_api_key"
    if not os.environ.get("OPENAI_BASE_URL"):
        os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    if not os.environ.get("MODEL_ID"):
        os.environ["MODEL_ID"] = "qwen-max"
    if not os.environ.get("TAVILY_API_KEY"):
        os.environ["TAVILY_API_KEY"] = "输出你的Tavily_api_key"
    if not os.environ.get("APIPOST_MCP_TOKEN"):
        os.environ["APIPOST_MCP_TOKEN"] = "输出你的Apipost_MCP_token"

    # ---------- 8.2 创建 LLM ----------
    llm = create_model()

    # ---------- 8.3 构建本地工具列表 ----------
    local_tools = [get_weather, get_attraction]

    # ---------- 8.4 尝试加载 MCP 工具 ----------
    mcp_tools, mcp_client = get_mcp_tools_if_available()

    # ---------- 8.5 合并工具 ----------
    all_tools = local_tools + mcp_tools
    logger.info(f"工具总数: {len(all_tools)}（本地 {len(local_tools)} + MCP {len(mcp_tools)}）")

    # ---------- 8.6 加载 System Prompt ----------
    system_prompt = load_system_prompt()

    # ---------- 8.7 构建 Agent ----------
    agent = build_agent(model=llm, tools=all_tools, system_prompt=system_prompt)

    # ---------- 8.8 交互式对话 ----------
    print("\n" + "=" * 60)
    print("  智能旅行助手（LangChain Agent + MCP 版）")
    print("  输入 'quit' 或 'exit' 退出")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("请输入你的问题: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if not user_input:
            continue

        print(f"\n{'─' * 40}")
        try:
            result = agent.invoke({"messages": [{"role": "user", "content": user_input}]})
            # 提取最后一条 AI 消息作为回答
            last_msg = result["messages"][-1]
            print(f"\n🤖 助手回答:\n{last_msg.content}\n")
        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            print(f"\n❌ 处理请求时出错: {e}\n")

    # ---------- 8.9 清理 MCP 连接 ----------
    if mcp_client:
        try:
            mcp_client.close()
            logger.info("[MCP] 连接已关闭")
        except Exception:
            pass


# ============================================================================
# 第9部分：入口
# ============================================================================
if __name__ == "__main__":
    main()
