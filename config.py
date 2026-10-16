"""
================================================================================
  公共配置文件 —— 集中管理项目的所有可调配置、数据模型和工具函数
================================================================================

  本文件被以下子目录的 main.py 共同引用，避免重复代码：
    · basic / basicWebUI / cot / selfConsistency / withMemoryTest / tot

  包含以下模块：
    1. 导入依赖包
    2. LangSmith 链路追踪配置
    3. 日志配置
    4. Prompt 模板文件路径
    5. LLM 模型配置（OpenAI / OneAPI）
    6. API 服务端口
    7. 全局变量声明
    8. Pydantic 数据模型（请求/响应）
    9. 工具函数（getPrompt / format_response）
   10. 初始化函数（create_model / build_prompt / build_chain）

  使用方式：
    import config
    # 可按需覆写配置值
    config.ONEAPI_API_BASE = "http://your-server:3000/v1"
    config.PORT = 8080
    # 然后调用初始化函数
================================================================================
"""


# ==============================================================================
# 第1部分：导入依赖包
# ==============================================================================
import os
import re
import uuid
import time
import logging
from pathlib import Path
from pydantic import BaseModel, Field, SecretStr
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate


# ==============================================================================
# 第2部分：LangSmith 链路追踪配置
# ==============================================================================
# LangSmith 是 LangChain 官方的可观测性平台，开启后可在网页端查看每次 Chain 调用
# 的完整输入/输出/耗时，便于调试和优化 Prompt。

def setup_langsmith(enable: bool = True):
    """配置 LangSmith 链路追踪。

    Args:
        enable: True 开启追踪，False 关闭追踪。
    """
    if enable:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = "输出你的LangSmith_api_key"
    else:
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        os.environ.pop("LANGCHAIN_API_KEY", None)


# ==============================================================================
# 第3部分：日志配置
# ==============================================================================

def setup_logging(name: str = __name__) -> logging.Logger:
    """初始化日志配置并返回 logger 对象。

    Args:
        name: logger 名称，通常传 __name__。

    Returns:
        配置好的 logging.Logger 实例。
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    return logging.getLogger(name)


# ==============================================================================
# 第4部分：Prompt 模板文件路径
# ==============================================================================
# 将 Prompt 模板独立为文本文件，便于单独编辑和迭代，无需修改代码。
# 各子目录下均应存在这两个同名文件。

PROMPT_TEMPLATE_TXT_SYS = "prompt_template_system.txt"   # 系统角色设定 + 套餐知识库
PROMPT_TEMPLATE_TXT_USER = "prompt_template_user.txt"    # 用户输入模板（含 {query} 占位符）


# ==============================================================================
# 第5部分：LLM 模型配置
# ==============================================================================
# API_TYPE 决定使用哪种模型服务，切换时只需修改此变量即可。
# 各子目录的 main.py 可在导入后覆写以下变量以适配不同环境。

API_TYPE = "oneapi"  # 可选值：openai（GPT模型）| oneapi（通义千问等）

# OpenAI 官方 API 配置（当 API_TYPE = "openai" 时使用）
OPENAI_API_BASE = "https://api.wlai.vip/v1"
OPENAI_CHAT_API_KEY = "输出你的OpenAI_api_key"
OPENAI_CHAT_MODEL = "gpt-4o-mini"

# OneAPI 配置（当 API_TYPE = "oneapi" 时使用，以通义千问为例）
ONEAPI_API_BASE = "http://localhost:3000/v1"
ONEAPI_CHAT_API_KEY = "输出你的OneAPI_api_key"
ONEAPI_CHAT_MODEL = "qwen-max"


# ==============================================================================
# 第6部分：API 服务端口
# ==============================================================================
PORT = 8012


# ==============================================================================
# 第7部分：全局变量声明
# ==============================================================================
# 这些变量在应用启动时（lifespan 函数中）被初始化，在请求处理时被使用。
# 模块级别声明，供各 main.py 通过 import config 后访问。

model = None   # ChatOpenAI 实例，用于调用 LLM
prompt = None  # ChatPromptTemplate 实例，用于组装提示词
chain = None   # LangChain Chain 实例，串联 prompt → getPrompt → model


# ==============================================================================
# 第8部分：Pydantic 数据模型（请求/响应结构）
# ==============================================================================
# 这些模型定义了 API 接口的 JSON 结构，兼容 OpenAI Chat Completions API 规范。
# FastAPI 会自动完成请求校验和响应序列化。

class Message(BaseModel):
    """对应 OpenAI API 中的 message 对象。"""
    role: str       # 角色：user / assistant / system
    content: str    # 消息内容


class ChatCompletionRequest(BaseModel):
    """对应客户端发送的请求体结构。"""
    messages: List[Message]         # 对话消息列表
    stream: Optional[bool] = False   # 是否流式输出，默认非流式


class ChatCompletionResponseChoice(BaseModel):
    """对应响应中 choices 数组里的单个元素。"""
    index: int                          # 选项序号
    message: Message                    # 助手的回复消息
    finish_reason: Optional[str] = None  # 结束原因：stop / null


class ChatCompletionResponse(BaseModel):
    """对应服务端返回的完整响应体结构。"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    choices: List[ChatCompletionResponseChoice]
    system_fingerprint: Optional[str] = None


# ==============================================================================
# 第9部分：工具函数
# ==============================================================================

def getPrompt(prompt_val):
    """Chain 的中间环节函数。

    拦截并记录最终发送给 LLM 的完整 Prompt，方便调试时查看模板渲染后的内容，
    然后原样返回，不影响 Chain 的后续执行。
    """
    _logger = logging.getLogger(__name__)
    _logger.info(f"最后给到LLM的prompt的内容: {prompt_val}")
    return prompt_val


def format_response(response: str) -> str:
    """格式化 LLM 输出文本，使其更具可读性。

    处理逻辑：
        1. 按连续空行分段，保留段落结构。
        2. 识别代码块（```...```），确保格式正确。
        3. 非代码块的普通文本在句点后添加换行，改善排版。
    """
    paragraphs = re.split(r'\n{2,}', response)
    formatted_paragraphs = []

    for para in paragraphs:
        if '```' in para:
            parts = para.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # 奇数索引 = 代码块
                    parts[i] = f"\n```\n{part.strip()}\n```\n"
            para = ''.join(parts)
        else:
            para = para.replace('. ', '.\n')

        formatted_paragraphs.append(para.strip())

    return '\n\n'.join(formatted_paragraphs)


# ==============================================================================
# 第10部分：初始化函数
# ==============================================================================
# 将模型创建、Prompt 加载、Chain 构建封装为独立函数，
# 各 main.py 可在 lifespan 中按需调用。

def create_model(temperature: float = 0.3) -> ChatOpenAI:
    """根据当前配置创建 ChatOpenAI 模型实例。

    Args:
        temperature: 模型发散程度，0 = 完全确定性，1 = 高随机性。

    Returns:
        ChatOpenAI 实例。
    """
    _logger = logging.getLogger(__name__)
    if API_TYPE == "oneapi":
        _logger.info(f"使用 OneAPI 模型: {ONEAPI_CHAT_MODEL} @ {ONEAPI_API_BASE}")
        return ChatOpenAI(
            base_url=ONEAPI_API_BASE,
            api_key=SecretStr(ONEAPI_CHAT_API_KEY),
            model=ONEAPI_CHAT_MODEL,
            temperature=temperature,
        )
    elif API_TYPE == "openai":
        _logger.info(f"使用 OpenAI 模型: {OPENAI_CHAT_MODEL} @ {OPENAI_API_BASE}")
        return ChatOpenAI(
            base_url=OPENAI_API_BASE,
            api_key=SecretStr(OPENAI_CHAT_API_KEY),
            model=OPENAI_CHAT_MODEL,
            temperature=temperature,
        )
    else:
        raise ValueError(f"不支持的 API_TYPE: {API_TYPE}，可选值：openai / oneapi")


def build_prompt(
    sys_path: Optional[str] = None,
    user_path: Optional[str] = None,
) -> ChatPromptTemplate:
    """加载 Prompt 模板文件并组装为 ChatPromptTemplate。

    Args:
        sys_path: system 模板文件路径，默认使用 PROMPT_TEMPLATE_TXT_SYS。
        user_path: user 模板文件路径，默认使用 PROMPT_TEMPLATE_TXT_USER。

    Returns:
        ChatPromptTemplate 实例。
    """
    sys_path = sys_path or PROMPT_TEMPLATE_TXT_SYS
    user_path = user_path or PROMPT_TEMPLATE_TXT_USER

    prompt_template_system = PromptTemplate.from_template(Path(sys_path).read_text(encoding="utf-8"))
    prompt_template_user = PromptTemplate.from_template(Path(user_path).read_text(encoding="utf-8"))

    return ChatPromptTemplate.from_messages(
        [
            ("system", prompt_template_system.template),
            ("human", prompt_template_user.template),
        ]
    )


def build_chain(prompt_obj: ChatPromptTemplate, model_obj: ChatOpenAI):
    """使用 LCEL 管道语法构建 Chain。

    Chain = prompt | getPrompt | model
        · prompt：将 {query} 替换为实际用户输入，生成完整提示词。
        · getPrompt：记录日志，原样传递（辅助调试）。
        · model：调用 LLM 推理，返回 AIMessage。

    Args:
        prompt_obj: ChatPromptTemplate 实例。
        model_obj: ChatOpenAI 实例。
    """
    return prompt_obj | getPrompt | model_obj
