"""
================================================================================
  智能客服系统 - 推荐手机流量套餐（basicWebUI 后端）
================================================================================

  本文件是 basicWebUI 目录的后端入口，与 basic/main.py 功能相同，
  为 Gradio 前端（apiWebUI.py / gradioTest）提供 REST API 服务。

  整体流程分为以下几步：
  ─────────────────────────────────────────────
  第1步：导入依赖包（含公共配置 config.py）
  第2步：覆写本地配置（如需与公共配置不同）
  第3步：定义应用生命周期管理（lifespan）
  第4步：定义 API 接口（/v1/chat/completions）
  第5步：启动服务（uvicorn）
  ─────────────────────────────────────────────
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

# 将项目根目录加入 sys.path，确保子目录运行时可导入 config.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn


# ==============================================================================
# 第2步：覆写本地配置（如需与 config.py 中的默认值不同，可在此处覆写）
# ==============================================================================
# 当前使用公共默认配置（oneapi + localhost:3000），无需覆写。
# 如需调整，取消注释并修改：
# config.ONEAPI_API_BASE = "http://your-server:3000/v1"
# config.ONEAPI_CHAT_API_KEY = "your-key"
# config.PORT = 8080

# 启用 LangSmith 追踪
config.setup_langsmith(enable=True)

# 初始化日志
logger = config.setup_logging(__name__)


# ==============================================================================
# 第3步：定义应用生命周期管理（lifespan）
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, prompt, chain

    try:
        logger.info("正在初始化模型、提取prompt模版、定义chain...")

        # ── 初始化 LLM 模型 ──
        model = config.create_model(temperature=0.3)

        # ── 加载 Prompt 模板 ──
        prompt = config.build_prompt()

        # ── 构建 Chain ──
        chain = config.build_chain(prompt, model)

        # 同步到全局
        config.model = model
        config.prompt = prompt
        config.chain = chain

        logger.info("初始化完成")
    except Exception as e:
        logger.error(f"初始化过程中出错: {str(e)}")
        raise

    yield
    logger.info("正在关闭...")


app = FastAPI(lifespan=lifespan)


# ==============================================================================
# 第4步：定义 API 接口
# ==============================================================================

@app.post("/v1/chat/completions")
async def chat_completions(request: config.ChatCompletionRequest):
    """接收用户消息，调用 Chain 推理，返回 LLM 回复。"""
    if not config.model or not config.prompt or not config.chain:
        logger.error("服务未初始化")
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"收到聊天完成请求: {request}")
        query_prompt = request.messages[-1].content
        logger.info(f"用户问题是: {query_prompt}")

        result = config.chain.invoke({"query": query_prompt})
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
# 第5步：启动服务
# ==============================================================================
if __name__ == "__main__":
    logger.info(f"在端口 {config.PORT} 上启动服务器")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
