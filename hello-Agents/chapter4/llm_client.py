import os
from openai import OpenAI, Stream  # Stream: 流式响应的类型
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam  # ChatCompletionMessageParam: 消息参数的标准类型
from dotenv import load_dotenv  # 从 .env 文件加载环境变量，避免密钥硬编码
from typing import cast  # cast: 用于向类型检查器断言变量类型

# 加载环境变量（指定同目录下的 .env 文件，确保无论从哪里执行脚本都能正确加载）
_ = load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

class HelloAgentsLLM:
    """
    为本书 "Hello Agents" 定制的 LLM 客户端。
    封装了 OpenAI 兼容接口的调用逻辑，默认使用流式响应（stream=True）。

    使用方式:
        # 方式1: 通过 .env 文件配置（推荐）
        client = HelloAgentsLLM()

        # 方式2: 通过代码传参（优先级高于 .env）
        client = HelloAgentsLLM(
            model="gpt-4",
            apiKey="sk-xxx",
            baseUrl="https://api.openai.com/v1"
        )
    """

    # ---- 类属性类型注解（方便 IDE 和类型检查器识别） ----
    model: str | None
    apiKey: str | None
    baseUrl: str | None
    timeout: int
    client: OpenAI

    def __init__(self, model: str | None = None, apiKey: str | None = None,
                 baseUrl: str | None = None, timeout: int | None = None):
        """
        初始化 LLM 客户端。

        参数优先级: 代码传参 > 环境变量(.env) > 默认值

        :param model:   模型名称，如 "qwen-max"、"gpt-4" 等。不传则读取 LLM_MODEL_ID 环境变量
        :param apiKey:  API 密钥。不传则读取 LLM_API_KEY 环境变量
        :param baseUrl: API 服务地址，兼容 OpenAI 接口协议。不传则读取 LLM_BASE_URL 环境变量
                       常见地址:
                         - 阿里百炼: https://dashscope.aliyuncs.com/compatible-mode/v1
                         - OpenAI:   https://api.openai.com/v1
                         - DeepSeek: https://api.deepseek.com
        :param timeout: 请求超时时间（秒）。不传则读取 LLM_TIMEOUT 环境变量，默认为 60 秒
        """
        # 使用 "or" 运算符实现回退逻辑：优先用传入参数，没有则从环境变量读取
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.apiKey = apiKey or os.getenv("LLM_API_KEY")
        self.baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        # timeout 需要转为 int 类型，默认 60 秒
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))

        # 校验三个必要参数是否都已提供
        if not all([self.model, self.apiKey, self.baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        # 创建 OpenAI 客户端实例（注意：参数名使用 snake_case 风格）
        self.client = OpenAI(api_key=self.apiKey, base_url=self.baseUrl, timeout=self.timeout)

    def think(self, messages: list[ChatCompletionMessageParam], temperature: float = 0) -> str | None:
        """
        调用大语言模型，以流式方式获取响应并实时打印。

        :param messages:    对话消息列表，格式为:
                            [
                                {"role": "system", "content": "系统提示词"},
                                {"role": "user",   "content": "用户输入"}
                            ]
        :param temperature: 生成温度(0-2)，0 表示最确定性的输出，值越高随机性越强
        :return:            模型返回的完整文本；出错时返回 None
        """
        print(f"🧠 正在调用 {self.model} 模型...")
        try:
            # 发起流式请求（stream=True），边生成边返回，提升用户体验
            # cast: 告知类型检查器经过 __init__ 校验后 self.model 一定不是 None
            # Stream[ChatCompletionChunk]: 明确流式响应的类型，避免级联的类型未知警告
            response: Stream[ChatCompletionChunk] = self.client.chat.completions.create(
                model=cast(str, self.model),
                messages=messages,
                temperature=temperature,
                stream=True
            )

            # 逐个接收流式数据块并实时打印
            print("✅ 大语言模型响应成功:")
            collected_content: list[str] = []
            for chunk in response:
                # 每个 chunk 包含一小段生成的文本
                content = chunk.choices[0].delta.content or ""
                # end="" 不换行，flush=True 立即刷新到终端
                print(content, end="", flush=True)
                collected_content.append(content)
            print()  # 流式输出结束后换行
            # 将所有片段拼接成完整响应
            return "".join(collected_content)
        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            return None


# ======================================================================
# 客户端使用示例
# 直接运行本文件(python llm_client.py)即可测试 LLM 是否连通
# ======================================================================
if __name__ == '__main__':
    try:
        # 步骤1: 实例化客户端（自动从 .env 文件读取配置）
        llmClient = HelloAgentsLLM()

        # 步骤2: 构建对话消息（标准的 OpenAI Chat 格式）
        # ChatCompletionMessageParam 是 OpenAI SDK 定义的标准消息类型
        exampleMessage: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "You are a helpful assistant that writes Python code."
            },
            {
                "role": "user",
                "content": "写一个快速排序的算法"
            }
        ]

        # 步骤3: 调用 think() 方法发起请求（流式输出，实时打印）
        print("--调用LLM--")
        responseText = llmClient.think(exampleMessage)

        # 步骤4: 处理返回的完整文本
        if responseText:
            print("\n\n--- 完整模型响应 ---")
            print(responseText)
    except ValueError as e:
        # 配置缺失时的友好提示
        print(e)
