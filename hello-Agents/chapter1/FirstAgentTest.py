# 1. agent的指令模版
AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具：
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。

# 输出格式要求：
你的每次回复必须严格遵循以下格式，包含一对Thought和Action:

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示：

- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够的信息可以回答用户问题时，必须使用Action: Finish[最终答案] 格式结束

请开始吧！
"""

# 2. 查询真实天气
import requests


def get_weather(city: str) -> str:
    """
    通过调用wttr.in API获取真实天气信息
    :param city:
    :return:
    """
    url = f"https://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # 提取当天天气状态
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        return f"{city} current weather：{weather_desc}，temperature{temp_c} degree Celsius"
    except requests.exceptions.RequestException as e:
        return f"Error：Network problem encountered when querying weather- {e}"
    except(KeyError, IndexError) as e:
        return f"Error：Failed to parse weather data, city name may be invalid-{e}"


# 3. 搜索并推荐旅游景点
import os
from tavily import TavilyClient


def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气，使用Tavily Search API搜索并返回优化后的景点推荐
    :param city:
    :param weather:
    :return:
    """
    # 从环境变量中读取API密钥
    api_key = os.environ.get('TAVILY_API_KEY')
    if not api_key:
        return "Error：TAVILY_API_KEY environment variable not configured."

    # 初始化Tavily客户端
    tavily = TavilyClient(api_key=api_key)
    # 构造一个精确的查询
    query = f"'{city} most worthwhile tourist attractions and reasons in {weather}' weather"

    try:
        # 调用API，include_answer-True会返回一个综合性的回答
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        # Tavily return results are already very clean and can be used directly
        # response['answer'] is a summary answer based on all search results
        if response.get('answer'):
            return response["answer"]
        # If there's no comprehensive answer, format raw results
        formatted_results = []
        for result in response.get('results', []):
            formatted_results.append(f"-{result['title']}:{result['content']}")
        if not formatted_results:
            return "Sorry, no relevant tourist attractions found for the given city and weather."
        return "based on search, found the following information for you:\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"Problem occurred when excuting Tavily search - {e}"


# Put all tool functions into a dictionary for easy subsequent calling
available_tools = {
    'get_weather': get_weather,
    'get_attraction': get_attraction,
}

# 4. Connecting to Large Language Models
from openai import OpenAI


class OpenAICompatibleClient:
    """
    A client for calling any LLM service compatible with the OpenAI interface.
    """

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Call LLM API to generate response."""
        print("Calling large language model...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt},
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer = response.choices[0].message.content
            print("Large language model responded successfully.")
            return answer
        except Exception as e:
            print(f"Error occurred when calling LLM PI: {e}")
            return "Error: Error occurred when calling language model service."

# 5. Executing the Action Loop
import re

# --- 1. 配置LLM客户端 ---
# 请根据您使用的服务，将这里替换成对应的凭证和地址
API_KEY = "sk-f92f3376b228495ead811aa7f2e33021"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_ID = "qwen-max"
os.environ['TAVILY_API_KEY'] = "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"

llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

# --- 2. 初始化 ---
user_prompt = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
prompt_history = [f"用户请求: {user_prompt}"]

print(f"用户输入: {user_prompt}\n" + "=" * 40)

# --- 3. 运行主循环 ---
for i in range(5):  # 设置最大循环次数
    print(f"--- 循环 {i + 1} ---\n")

    # 3.1. 构建Prompt
    full_prompt = "\n".join(prompt_history)

    # 3.2. 调用LLM进行思考
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    # 模型可能会输出多余的Thought-Action，需要截断
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余的 Thought-Action 对")
    print(f"模型输出:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 3.3. 解析并执行行动
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)
        continue
    action_str = action_match.group(1).strip()

    if action_str.startswith("Finish"):
        final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
        print(f"任务完成，最终答案: {final_answer}")
        break

    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误：未定义的工具 '{tool_name}'"

    # 3.4. 记录观察结果
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "=" * 40)
    prompt_history.append(observation_str)