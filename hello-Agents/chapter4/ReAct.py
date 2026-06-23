import re  # re: 正则表达式，用于解析 LLM 输出的 Thought/Action 格式
from llm_client import HelloAgentsLLM  # HelloAgentsLLM: 封装了 OpenAI 兼容接口的 LLM 客户端
from tools import ToolExecutor, search  # ToolExecutor: 工具执行器; search: DuckDuckGo 网页搜索工具


# ======================================================================
# ReAct Prompt 模板
# 定义智能体与 LLM 交互的提示词格式，指导 LLM 按 Thought → Action → Observation 循环推理
# ======================================================================

REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下：
{tools}

请严格按照以下格式进行回应：

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一：
- `{{tool_name}}[{{tool_input}}]`：调用一个可用工具。
- `Finish[最终答案]`：当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在`Action:`字段后使用 `Finish[最终答案]` 来输出最终答案。


现在，请开始解决以下问题：
Question: {question}
History: {history}
"""


# ======================================================================
# ReAct Agent（推理-行动循环智能体）
# 实现经典的 ReAct（Reasoning + Acting）模式，让 LLM 在思考与行动之间迭代，
# 通过调用外部工具获取信息，最终给出有依据的答案
# ======================================================================


class ReActAgent:
    """
    ReAct（Reasoning + Acting）智能体。

    核心思想: 让 LLM 在"思考（Thought）→ 行动（Action）→ 观察（Observation）"的循环中
    逐步解决问题。每一步 LLM 输出 Thought（推理过程）和 Action（调用工具或输出答案），
    程序执行 Action 后将结果作为 Observation 反馈给 LLM，形成闭环。

    循环流程:
        Step 1: LLM 输出 Thought + Action
        Step 2: 程序解析并执行 Action（调用工具或 Finish 结束）
        Step 3: 将 Observation 追加到历史记录
        Step 4: 回到 Step 1，直到得到最终答案或达到最大步数

    使用方式:
        llm = HelloAgentsLLM()
        executor = ToolExecutor()
        executor.registerTool("Search", search_desc, search)
        agent = ReActAgent(llm_client=llm, tool_executor=executor, max_steps=5)
        answer = agent.run("今天天气怎么样？")
    """

    # ---- 类属性类型注解（方便 IDE 和类型检查器识别） ----
    llm_client: HelloAgentsLLM
    tool_executor: ToolExecutor
    max_steps: int
    history: list[str]

    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        """
        初始化 ReAct 智能体。

        :param llm_client:    LLM 客户端实例，用于调用大语言模型进行推理
        :param tool_executor: 工具执行器实例，管理并执行外部工具
        :param max_steps:     最大推理步数，防止无限循环；默认 5 步
        """
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        # history: 存储每轮的 Action 和 Observation，作为 LLM 的上下文记忆
        self.history: list[str] = []

    def run(self, question: str) -> str | None:
        """
        启动 ReAct 循环，处理用户问题并返回最终答案。

        执行流程:
            1. 构建包含工具列表、问题、历史记录的 Prompt
            2. 调用 LLM 获取 Thought + Action
            3. 解析 Action: 如果是 Finish → 返回最终答案；否则调用工具
            4. 将 Observation 追加到历史，进入下一轮循环
            5. 达到 max_steps 仍未完成时终止

        :param question: 用户提出的问题
        :return:         最终的答案文本；如果未能得出答案则返回 None
        """
        # 每次运行前清空历史记录，确保每次问答独立
        self.history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            # 构建 Prompt: 注入工具列表 + 当前问题 + 历史记录
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 调用 LLM 进行推理（temperature=0 确保输出稳定可解析）
            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。")
                break

            # 从 LLM 输出中解析出 Thought 和 Action 两部分
            thought, action = self._parse_output(response_text)
            if thought:
                print(f"🤔 思考: {thought}")
            if not action:
                print("警告：未能解析出有效的Action，流程终止。")
                break

            # 如果是 Finish 指令，提取最终答案并结束循环
            if action.startswith("Finish"):
                final_answer = self._parse_action_input(action)
                print(f"🎉 最终答案: {final_answer}")
                return final_answer

            # 解析工具调用: tool_name[tool_input]
            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                self.history.append("Observation: 无效的Action格式，请检查。")
                continue

            # 执行工具调用，获取 Observation（观察结果）
            print(f"🎬 行动: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            observation = (
                tool_function(tool_input)
                if tool_function
                else f"错误：未找到名为 '{tool_name}' 的工具。"
            )

            # 将 Action 和 Observation 追加到历史记录，供下一轮 LLM 参考
            print(f"👀 观察: {observation}")
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        # 达到最大步数仍未给出最终答案
        print("已达到最大步数，流程终止。")
        return None

    # ---- 私有方法：解析 LLM 输出 ----

    def _parse_output(self, text: str) -> tuple[str | None, str | None]:
        """
        从 LLM 的原始输出中提取 Thought 和 Action。

        LLM 输出格式:
            Thought: 这里是思考内容...
            Action: Search[关键词]  或  Finish[最终答案]

        :param text: LLM 返回的原始文本
        :return:     (thought, action) 元组，解析失败时对应位置为 None
        """
        # 匹配 Thought: 从 "Thought:" 到 "Action:" 或文本末尾
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        # 匹配 Action: 从 "Action:" 到文本末尾
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str) -> tuple[str | None, str | None]:
        """
        解析 Action 文本，提取工具名称和输入参数。

        格式: tool_name[tool_input]
        示例: Search[英伟达最新GPU] → ("Search", "英伟达最新GPU")

        :param action_text: Action 字段的原始文本
        :return:            (tool_name, tool_input) 元组，格式不匹配时返回 (None, None)
        """
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        return (match.group(1), match.group(2)) if match else (None, None)

    def _parse_action_input(self, action_text: str) -> str:
        """
        从 Finish[xxx] 或 tool_name[xxx] 中提取方括号内的内容。

        示例: Finish[华为最新手机是 Mate 70 Pro] → "华为最新手机是 Mate 70 Pro"

        :param action_text: Action 字段的原始文本
        :return:            方括号内的内容字符串
        """
        match = re.match(r"\w+\[(.*)\]", action_text, re.DOTALL)
        return match.group(1) if match else ""


# ======================================================================
# ReAct Agent 使用示例
# 直接运行本文件(python ReAct.py)即可体验完整的 ReAct 推理-行动循环
# ======================================================================
if __name__ == '__main__':
    # 步骤1: 初始化 LLM 客户端（自动从 .env 文件读取配置）
    llm = HelloAgentsLLM()

    # 步骤2: 初始化工具执行器并注册搜索工具
    tool_executor = ToolExecutor()
    search_desc = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    tool_executor.registerTool("Search", search_desc, search)

    # 步骤3: 创建 ReAct 智能体（最多 5 步推理循环）
    agent = ReActAgent(llm_client=llm, tool_executor=tool_executor)

    # 步骤4: 提出问题，启动 ReAct 循环
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)
