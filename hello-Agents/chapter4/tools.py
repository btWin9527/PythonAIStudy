from ddgs import DDGS  # DDGS: DuckDuckGo 搜索引擎客户端，免费无需 API Key
from typing import Dict, Any, Callable, Optional  # 类型注解: Dict 工具字典, Any 通用值, Callable 可调用对象, Optional 可选返回


# ======================================================================
# 搜索工具函数
# 基于 DuckDuckGo 的免费网页搜索，替代原 SerpApi 方案，无需注册和 API Key
# ======================================================================


def search(query: str) -> str:
    """
    一个基于 DuckDuckGo 的免费网页搜索引擎工具（无需 API Key）。
    它会智能地解析搜索结果，返回前三个搜索结果的摘要。

    使用方式:
        result = search("今天天气怎么样")
        print(result)

    :param query: 搜索关键词，支持中英文，建议使用关键词而非完整问句以提高搜索命中率
    :return: 格式化的搜索结果文本，包含标题和摘要；未找到结果或出错时返回提示信息
    """
    print(f"🔍 正在执行 [DuckDuckGo] 网页搜索: {query}")
    try:
        # 创建 DDGS 客户端并发起搜索（timeout=30 避免中文查询超时）
        # ddgs.text() 返回一个生成器，用 list() 一次性获取所有结果
        with DDGS(timeout=30) as ddgs:
            results = list(ddgs.text(query, max_results=5))

        # 无结果时的友好提示
        if not results:
            return f"对不起，没有找到关于 '{query}' 的信息。"

        # 取前三个搜索结果，格式化为 [序号] 标题 + 摘要 的形式
        snippets = [
            f"[{i + 1}] {r.get('title', '')}\n{r.get('body', '')}"
            for i, r in enumerate(results[:3])
        ]
        # 用两个换行分隔不同结果，方便阅读
        return "\n\n".join(snippets)

    except Exception as e:
        # 捕获网络超时、解析失败等所有异常，确保工具调用不会中断智能体主流程
        return f"搜索时发生错误: {e}"


# ======================================================================
# 工具执行器（ToolExecutor）
# 负责注册、管理和调用智能体可用的全部工具
# ======================================================================


class ToolExecutor:
    """
    一个通用的工具执行器，负责管理和执行工具。

    功能:
        - 注册工具: 将工具名称、描述和执行函数绑定在一起
        - 获取工具: 根据名称取出工具的执行函数
        - 列出工具: 生成供 LLM 阅读的可用工具描述列表

    使用方式:
        executor = ToolExecutor()
        executor.registerTool("search", "搜索引擎工具", search)
        tool_func = executor.getTool("search")
        result = tool_func("查询内容")
    """

    # ---- 类属性类型注解（方便 IDE 和类型检查器识别） ----
    tools: Dict[str, Dict[str, Any]]

    def __init__(self):
        """
        初始化工具执行器，创建一个空的工具字典。

        tools 结构:
            {
                "工具名": {
                    "description": "工具的功能描述",
                    "func": <可执行函数>
                }
            }
        """
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: Callable[..., Any]) -> None:
        """
        向工具箱中注册一个新工具。

        :param name:        工具的唯一名称（如 "search"），用于后续查找和调用
        :param description: 工具的功能描述文本，会展示给 LLM 帮助其决定是否调用
        :param func:        工具的实际执行函数，必须可调用且接受一个字符串参数
        :return:            无返回值
        """
        # 检查是否存在同名工具，存在则给出警告（覆盖旧工具）
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        # 将工具的元信息（描述 + 函数）存入字典
        self.tools[name] = {"description": description, "func": func}
        print(f"工具'{name}'已注册。")

    def getTool(self, name: str) -> Optional[Callable[..., Any]]:
        """
        根据名称获取一个工具的执行函数。

        :param name: 工具名称（与注册时一致）
        :return:     工具的执行函数；未找到时返回 None
        """
        # self.tools.get(name, {}) 确保 name 不存在时返回空字典，避免 KeyError
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具的格式化描述字符串，供 LLM 理解有哪些工具可用。

        :return: 格式为 "- 工具名: 描述" 的多行字符串
        """
        return "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.tools.items()
        ])


# ======================================================================
# 工具执行器使用示例
# 直接运行本文件(python tools.py)即可测试搜索引擎工具是否正常工作
# ======================================================================
if __name__ == "__main__":
    # 步骤1: 初始化工具执行器
    toolExecutor = ToolExecutor()

    # 步骤2: 注册搜索工具（绑定工具名、功能描述和执行函数）
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("search", search_description, search)

    # 步骤3: 获取并打印可用工具列表
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 步骤4: 模拟智能体的 action 调用，通过工具名获取函数并执行
    print("\n--- 执行 Action: Search['英伟达最新的GPU型号是什么'] ---")
    tool_name = "search"
    tool_input = "英伟达最新的GPU型号是什么"

    tool_function = toolExecutor.getTool(tool_name)
    if tool_function:
        # 执行搜索，获取观察结果（Observation）
        observation = tool_function(tool_input)
        print("--- 观察 (Observation) ---")
        print(observation)
    else:
        print(f"错误：未找到工具 '{tool_name}'")
