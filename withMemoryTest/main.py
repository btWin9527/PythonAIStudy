"""
================================================================================
  智能客服系统（带记忆） - 推荐手机流量套餐
================================================================================

  与 basic/main.py 的核心区别在于引入了 **对话历史记忆** 功能：
  通过 RunnableWithMessageHistory + SQLChatMessageHistory，将用户的历史对话
  存储到 SQLite 数据库中，实现多轮对话上下文理解。

  整体流程分为以下几步：
  ─────────────────────────────────────────────
  第1步：导入依赖包（含公共配置 config.py + 记忆相关模块）
  第2步：覆写本地配置
  第3步：定义带记忆的请求数据模型
  第4步：定义对话历史管理函数（get_session_history）
  第5步：定义应用生命周期管理（lifespan）—— 初始化模型、Prompt、带记忆的 Chain
  第6步：定义 API 接口（/v1/chat/completions）—— 注入历史，调用 Chain
  第7步：启动服务（uvicorn）
  ─────────────────────────────────────────────

  核心架构图：

    用户请求 → FastAPI接口
                  │
                  ├── 提取 userId + conversationId
                  ├── 从 SQLite 加载历史对话（最近10条）
                  ├── 历史注入 Prompt 模板（MessagesPlaceholder）
                  ├── Chain 执行（prompt | getPrompt | model）
                  ├── LLM 推理（带上下文历史）
                  ├── 保存本轮对话到 SQLite
                  └── 格式化输出 → 响应返回

================================================================================
"""


# ==============================================================================
# 第1步：导入依赖包
# ==============================================================================
import sys
import os
import json
import asyncio
import uuid
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional

# 将项目根目录加入 sys.path，确保子目录运行时可导入 config.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

# 记忆相关导入
from pathlib import Path
from langchain_core.runnables import ConfigurableFieldSpec
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import HumanMessage


# ==============================================================================
# 第2步：覆写本地配置
# ==============================================================================
config.setup_langsmith(enable=True)
logger = config.setup_logging(__name__)


# ==============================================================================
# 第3步：定义带记忆的请求数据模型
# ==============================================================================
# 相比公共配置中的 ChatCompletionRequest，增加了 userId 和 conversationId，
# 用于在对话历史管理中区分不同用户和不同会话。

class MemoryChatCompletionRequest(config.ChatCompletionRequest):
    """带用户/会话标识的请求模型。"""
    userId: Optional[str] = None       # 用户唯一标识
    conversationId: Optional[str] = None  # 会话唯一标识


# ==============================================================================
# 第4步：定义对话历史管理函数
# ==============================================================================
# RunnableWithMessageHistory 会在每次请求时自动调用此函数，根据
# userId + conversationId 从 SQLite 加载历史记录并注入 Prompt。

def get_session_history(user_id: str, conversation_id: str):
    """根据用户ID和会话ID获取 SQLite 数据库中的聊天历史。

    处理逻辑：
        1. 以 "userId--conversationId" 为表名连接 SQLite
        2. 读取所有历史，只保留最近 10 条
        3. 清空原表后重新写入精简记录（防止历史无限增长）
    """
    history = SQLChatMessageHistory(
        f"{user_id}--{conversation_id}", "sqlite:///memory.db"
    )

    all_messages = history.messages
    recent_messages_content = [message.content for message in all_messages[-10:]]

    history.clear()

    for content in recent_messages_content:
        message = HumanMessage(content=content)
        history.add_message(message)

    logger.info(f"历史对话记忆内容: {history}\n")
    return history


# ==============================================================================
# 第5步：定义应用生命周期管理（lifespan）
# ==============================================================================
# 与 basic 版本的区别：Prompt 中增加了 MessagesPlaceholder("history")，
# 并在 Chain 外层包裹了 RunnableWithMessageHistory。

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, chain, with_message_history

    try:
        logger.info("正在初始化模型、提取prompt模版、定义chain（含历史记忆）...")

        # ── 5.1 初始化 LLM 模型（temperature=0 确保客服回答一致性） ──
        model = config.create_model(temperature=0)

        # ── 5.2 加载 Prompt 模板（含历史占位符） ──
        from langchain_core.prompts import PromptTemplate
        prompt_template_system = PromptTemplate.from_template(Path(config.PROMPT_TEMPLATE_TXT_SYS).read_text(encoding="utf-8"))
        prompt_template_user = PromptTemplate.from_template(Path(config.PROMPT_TEMPLATE_TXT_USER).read_text(encoding="utf-8"))
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_template_system.template),
                MessagesPlaceholder(variable_name="history"),   # 历史对话占位符
                ("human", prompt_template_user.template),
            ]
        )

        # ── 5.3 构建基础 Chain ──
        chain = prompt | config.getPrompt | model

        # ── 5.4 构建带历史记忆的 Chain ──
        with_message_history = RunnableWithMessageHistory(
            chain,
            get_session_history,
            input_messages_key="query",
            history_messages_key="history",
            history_factory_config=[
                ConfigurableFieldSpec(
                    id="user_id",
                    annotation=str,
                    name="User ID",
                    description="Unique identifier for the user.",
                    default="",
                    is_shared=True,
                ),
                ConfigurableFieldSpec(
                    id="conversation_id",
                    annotation=str,
                    name="Conversation ID",
                    description="Unique identifier for the conversation.",
                    default="",
                    is_shared=True,
                ),
            ],
        )

        # 同步到全局
        config.model = model
        config.prompt = prompt
        config.chain = chain

        logger.info("初始化完成（含历史记忆功能）")
    except Exception as e:
        logger.error(f"初始化过程中出错: {str(e)}")
        raise

    yield
    logger.info("正在关闭...")


app = FastAPI(lifespan=lifespan)


# ==============================================================================
# 第6步：定义 API 接口
# ==============================================================================
# 使用 with_message_history.invoke 替代 chain.invoke，自动注入历史对话。

@app.post("/v1/chat/completions")
async def chat_completions(request: MemoryChatCompletionRequest):
    if not config.model or not config.prompt or not config.chain:
        logger.error("服务未初始化")
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"收到聊天完成请求: {request}")
        query_prompt = request.messages[-1].content
        logger.info(f"用户问题是: {query_prompt}")

        # ── 调用带记忆的 Chain ──
        result = with_message_history.invoke(
            {"query": query_prompt},
            config={
                "configurable": {
                    "user_id": request.userId,
                    "conversation_id": request.conversationId,
                }
            },
        )

        formatted_response = str(config.format_response(result.content))
        logger.info(f"格式化的搜索结果: {formatted_response}")

        if request.stream:
            async def generate_stream():
                chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
                lines = formatted_response.split('\n')
                for i, line in enumerate(lines):
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": line + '\n'},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"{json.dumps(chunk)}\n"
                    await asyncio.sleep(0.5)

                final_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [
                        {"index": 0, "delta": {}, "finish_reason": "stop"}
                    ],
                }
                yield f"{json.dumps(final_chunk)}\n"

            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            response = config.ChatCompletionResponse(
                choices=[
                    config.ChatCompletionResponseChoice(
                        index=0,
                        message=config.Message(role="assistant", content=formatted_response),
                        finish_reason="stop",
                    )
                ]
            )
            logger.info(f"发送响应内容: \n{response}")
            return JSONResponse(content=response.model_dump())

    except Exception as e:
        logger.error(f"处理聊天完成时出错:\n\n {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# 第7步：启动服务
# ==============================================================================
if __name__ == "__main__":
    logger.info(f"在端口 {config.PORT} 上启动服务器（含历史对话记忆功能）")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
