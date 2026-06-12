"""
================================================================================
  智能客服系统 - 推荐手机流量套餐
================================================================================

  本文件是项目的核心入口，实现了一个基于 LangChain + FastAPI 的智能客服服务。

  整体流程分为以下几步：
  ─────────────────────────────────────────────
  第1步：导入依赖包
  第2步：配置环境变量与全局参数
  第3步：定义请求/响应的数据模型（Pydantic）
  第4步：定义辅助工具函数（getPrompt、format_response）
  第5步：定义应用生命周期管理（lifespan）—— 启动时初始化模型、Prompt、Chain
  第6步：定义 API 接口（/v1/chat/completions）—— 接收请求、调用 Chain、返回结果
  第7步：启动服务（uvicorn）
  ─────────────────────────────────────────────

  核心架构图：

    用户请求 → FastAPI接口 → Chain执行 → LLM推理 → 格式化输出 → 响应返回

    其中 Chain = prompt | getPrompt | model
      · prompt：将用户输入填入模板，生成完整提示词
      · getPrompt：中间环节，记录日志（方便调试）
      · model：调用大语言模型，获取推理结果

================================================================================
"""


# ==============================================================================
# 第1步：导入依赖包
# ==============================================================================
# 各导入的作用说明：
#   os / re / json / asyncio / uuid / time / logging —— Python 标准库
#   asynccontextmanager —— 用于创建异步上下文管理器（管理应用生命周期）
#   pydantic —— 数据模型定义与校验（定义请求/响应的 JSON 结构）
#   langchain_openai.ChatOpenAI —— LangChain 封装的 OpenAI 兼容客户端
#   langchain_core.prompts —— Prompt 模板（将 system/user 提示词结构化）
#   fastapi —— Web 框架（提供 REST API）
#   uvicorn —— ASGI 服务器（运行 FastAPI 应用）

import os
import re
import json
import asyncio
import uuid
import time
import logging
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import PromptTemplate
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn


# ==============================================================================
# 第2步：配置环境变量与全局参数
# ==============================================================================
# 这一部分集中管理所有可调配置，方便根据实际环境修改

# ── 2.1 LangSmith 链路追踪配置 ──
# LangSmith 是 LangChain 官方的可观测性平台，开启后可在网页端查看每次 Chain 调用的
# 完整输入/输出/耗时，便于调试和优化 Prompt
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "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"

# ── 2.2 日志配置 ──
# 设置日志级别为 INFO，定义日志格式：时间 - 模块名 - 级别 - 消息
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 2.3 Prompt 模板文件路径 ──
# 将 Prompt 模板独立为文本文件，便于单独编辑和迭代，无需修改代码
PROMPT_TEMPLATE_TXT_SYS = "prompt_template_system.txt"   # 系统角色设定 + 套餐知识库
PROMPT_TEMPLATE_TXT_USER = "prompt_template_user.txt"    # 用户输入模板（含 {query} 占位符）

# ── 2.4 LLM 模型配置 ──
# API_TYPE 决定使用哪种模型服务，切换时只需修改此变量和对应配置即可
API_TYPE = "oneapi"  # 可选值：openai（GPT模型） | oneapi（通义千问等）

# OpenAI 官方 API 配置（当 API_TYPE = "openai" 时使用）
OPENAI_API_BASE = "https://api.wlai.vip/v1"
# OPENAI_CHAT_API_KEY = "sk-EhxvNWXkjzZJADfHA1Ac24Dd0f0b42B2B97f3725D3BcA378"
# OPENAI_CHAT_MODEL = "gpt-4o-mini"

# OneAPI 配置（当 API_TYPE = "oneapi" 时使用，以通义千问为例）
ONEAPI_API_BASE = "http://172.24.12.90:3000/v1"
ONEAPI_CHAT_API_KEY = "sk-xwu3pd0iSis9gpUX33F178F8D4824fFaA1D55f8e65Dc2dC1"
ONEAPI_CHAT_MODEL = "qwen-max"

# ── 2.5 API 服务端口 ──
PORT = 8012

# ── 2.6 全局变量声明 ──
# 这三个变量会在应用启动时（lifespan 函数中）被初始化，在请求处理时被使用
model = None   # ChatOpenAI 实例，用于调用 LLM
prompt = None  # ChatPromptTemplate 实例，用于组装提示词
chain = None   # LangChain Chain 实例，串联 prompt → getPrompt → model


# ==============================================================================
# 第3步：定义请求/响应的数据模型（Pydantic）
# ==============================================================================
# 这些模型定义了 API 接口的 JSON 结构，FastAPI 会自动完成：
#   · 请求校验：传入的 JSON 不符合结构时返回 422 错误
#   · 响应序列化：将模型实例转为标准 JSON 返回
# 整体兼容 OpenAI Chat Completions API 规范

# ── 3.1 消息模型 ──
# 对应 OpenAI API 中的 message 对象
class Message(BaseModel):
    role: str       # 角色：user（用户）/ assistant（助手）/ system（系统）
    content: str    # 消息内容

# ── 3.2 请求模型 ──
# 对应客户端发送的请求体结构
class ChatCompletionRequest(BaseModel):
    messages: List[Message]       # 对话消息列表
    stream: Optional[bool] = False  # 是否流式输出，默认非流式

# ── 3.3 响应中的选项模型 ──
# 对应响应中 choices 数组里的单个元素
class ChatCompletionResponseChoice(BaseModel):
    index: int                          # 选项序号
    message: Message                    # 助手的回复消息
    finish_reason: Optional[str] = None # 结束原因：stop（正常结束）/ null（未结束）

# ── 3.4 完整响应模型 ──
# 对应服务端返回的完整响应体结构
class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")  # 唯一响应ID
    object: str = "chat.completion"       # 对象类型
    created: int = Field(default_factory=lambda: int(time.time()))  # 创建时间戳
    choices: List[ChatCompletionResponseChoice]  # 回复选项列表
    system_fingerprint: Optional[str] = None     # 系统指纹（可选）


# ==============================================================================
# 第4步：定义辅助工具函数
# ==============================================================================

def getPrompt(prompt):
    """
    Chain 的中间环节函数，作用：
      1. 拦截并记录 Chain 执行过程中最终发送给 LLM 的完整 Prompt
      2. 原样返回 prompt，不影响 Chain 的后续执行

    用途：调试时可以清楚看到模板渲染后的完整内容，方便排查 Prompt 问题。
    """
    logger.info(f"最后给到LLM的prompt的内容: {prompt}")
    return prompt


def format_response(response):
    """
    格式化 LLM 的输出文本，使其更具可读性，处理逻辑：
      1. 按连续空行分段（保留段落结构）
      2. 识别代码块（```...```），确保代码块格式正确
      3. 非代码块的普通文本中，在句点后添加换行（改善排版）

    参数：response —— LLM 返回的原始文本
    返回：格式化后的文本
    """
    # 第1步：按两个或更多连续换行符分割为段落
    paragraphs = re.split(r'\n{2,}', response)
    formatted_paragraphs = []

    for para in paragraphs:
        if '```' in para:
            # 第2步：处理包含代码块的段落
            # 按 ``` 分割，奇数索引部分为代码块，偶数索引部分为普通文本
            parts = para.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # 奇数索引 = 代码块内容
                    parts[i] = f"\n```\n{part.strip()}\n```\n"
            para = ''.join(parts)
        else:
            # 第3步：普通文本在句点后换行，改善可读性
            para = para.replace('. ', '.\n')

        formatted_paragraphs.append(para.strip())

    # 用双换行符重新连接所有段落
    return '\n\n'.join(formatted_paragraphs)


# ==============================================================================
# 第5步：定义应用生命周期管理（lifespan）
# ==============================================================================
# lifespan 是 FastAPI 的生命周期管理机制：
#   · yield 之前的代码 → 应用启动时执行（初始化模型、加载模板、构建 Chain）
#   · yield 之后的代码 → 应用关闭时执行（清理资源）
#
# 使用 @asynccontextmanager 装饰器声明为异步上下文管理器

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 声明全局变量，在函数内初始化后供整个应用使用 ──
    global model, prompt, chain, API_TYPE, PROMPT_TEMPLATE_TXT_SYS, PROMPT_TEMPLATE_TXT_USER
    global ONEAPI_API_BASE, ONEAPI_CHAT_API_KEY, ONEAPI_CHAT_MODEL
    global OPENAI_API_BASE, OPENAI_CHAT_API_KEY, OPENAI_CHAT_MODEL

    try:
        logger.info("正在初始化模型、提取prompt模版、定义chain...")

        # ── 5.1 初始化 LLM 模型 ──
        # 根据 API_TYPE 选择不同的模型服务，ChatOpenAI 统一封装了调用逻辑
        # temperature=0.3 表示模型输出会有少量随机性（0=确定性，1=高随机性）
        if API_TYPE == "oneapi":
            model = ChatOpenAI(
                base_url=ONEAPI_API_BASE,
                api_key=ONEAPI_CHAT_API_KEY,
                model=ONEAPI_CHAT_MODEL,
                temperature=0.3,
            )
        elif API_TYPE == "openai":
            model = ChatOpenAI(
                base_url=OPENAI_API_BASE,
                api_key=OPENAI_CHAT_API_KEY,
                model=OPENAI_CHAT_MODEL,
                temperature=0.3,
            )

        # ── 5.2 加载并组装 Prompt 模板 ──
        # 从外部文本文件读取模板，将 system（角色设定）和 human（用户输入）组合
        # system 模板定义了客服角色和套餐知识，human 模板定义了用户输入格式
        prompt_template_system = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_SYS)
        prompt_template_user = PromptTemplate.from_file(PROMPT_TEMPLATE_TXT_USER)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_template_system.template),  # 系统角色：你是客服NanGe
                ("human", prompt_template_user.template)      # 用户输入：用户问：{query}
            ]
        )

        # ── 5.3 构建 Chain（核心！） ──
        # 使用 LCEL（LangChain Expression Language）的管道语法串联三个环节：
        #   prompt  → 将 {query} 替换为实际用户输入，生成完整提示词
        #   getPrompt → 记录日志，原样传递（辅助调试，不影响逻辑）
        #   model  → 调用 LLM 推理，返回 AIMessage
        chain = prompt | getPrompt | model

        logger.info("初始化完成")
    except Exception as e:
        logger.error(f"初始化过程中出错: {str(e)}")
        raise

    # yield 将控制权交给 FastAPI，应用开始接收请求
    # yield 之前 = 启动逻辑，yield 之后 = 关闭逻辑
    yield

    # ── 应用关闭时的清理逻辑 ──
    logger.info("正在关闭...")


# ==============================================================================
# 第5步续：创建 FastAPI 应用实例
# ==============================================================================
# 将 lifespan 绑定到应用，启动/关闭时自动执行对应逻辑
app = FastAPI(lifespan=lifespan)


# ==============================================================================
# 第6步：定义 API 接口
# ==============================================================================
# 提供兼容 OpenAI Chat Completions 规范的 POST 接口
# 支持流式（SSE）和非流式两种响应模式

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    核心接口：接收用户消息，调用 Chain 推理，返回 LLM 回复

    请求流程：
      1. 校验服务是否已初始化
      2. 提取用户最后一条消息
      3. 调用 Chain 执行推理（prompt渲染 → 日志记录 → LLM推理）
      4. 格式化 LLM 输出
      5. 根据 stream 参数返回流式或非流式响应
    """

    # ── 6.1 校验服务状态 ──
    # 如果 model/prompt/chain 未初始化（启动失败），返回 500 错误
    if not model or not prompt or not chain:
        logger.error("服务未初始化")
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"收到聊天完成请求: {request}")

        # ── 6.2 提取用户输入 ──
        # 取消息列表的最后一条作为当前问题（兼容多轮对话传入）
        query_prompt = request.messages[-1].content
        logger.info(f"用户问题是: {query_prompt}")

        # ── 6.3 调用 Chain 执行推理 ──
        # invoke 会依次执行：prompt渲染 → getPrompt日志 → model推理
        # {"query": query_prompt} 中的 query 对应模板中的 {query} 占位符
        result = chain.invoke(
            {"query": query_prompt}
        )

        # ── 6.4 格式化 LLM 输出 ──
        # result.content 是 LLM 返回的原始文本，format_response 优化排版
        formatted_response = str(format_response(result.content))
        logger.info(f"格式化的搜索结果: {formatted_response}")

        # ── 6.5 根据 stream 参数选择响应方式 ──
        if request.stream:
            # ====== 流式响应（SSE） ======
            # 逐行推送内容，客户端可以实时看到生成过程
            async def generate_stream():
                # 生成唯一的 chunk_id，同一流式响应的所有片段共享此 ID
                chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
                # 将完整响应按行分割，逐行推送
                lines = formatted_response.split('\n')
                for i, line in enumerate(lines):
                    # 构造单个 SSE 数据片段，兼容 OpenAI chunk 格式
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": line + '\n'},
                                "finish_reason": None  # 未结束
                            }
                        ]
                    }
                    # 转为 JSON 字符串并发送
                    yield f"{json.dumps(chunk)}\n"
                    # 每行间隔 0.5 秒，模拟逐字生成效果
                    await asyncio.sleep(0.5)

                # 发送结束标记片段
                final_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},              # 空内容
                            "finish_reason": "stop"   # 标记结束
                        }
                    ]
                }
                yield f"{json.dumps(final_chunk)}\n"

            # 返回流式响应，media_type 为 SSE 标准格式
            return StreamingResponse(generate_stream(), media_type="text/event-stream")

        else:
            # ====== 非流式响应 ======
            # 一次性返回完整的 JSON 结果
            response = ChatCompletionResponse(
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=Message(role="assistant", content=formatted_response),
                        finish_reason="stop"
                    )
                ]
            )
            logger.info(f"发送响应内容: \n{response}")
            # model_dump() 将 Pydantic 模型转为标准字典，再由 JSONResponse 序列化
            return JSONResponse(content=response.model_dump())

    except Exception as e:
        logger.error(f"处理聊天完成时出错:\n\n {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# 第7步：启动服务
# ==============================================================================
# uvicorn 是轻量级 ASGI 服务器，用于部署 FastAPI 异步应用
# host="0.0.0.0" 表示监听所有网络接口（允许外部访问）

if __name__ == "__main__":
    logger.info(f"在端口 {PORT} 上启动服务器")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
