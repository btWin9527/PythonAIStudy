"""
================================================================================
  智能客服系统 - 自洽性检查（Self-Consistency）
================================================================================

  基于 LangChain 框架实现客服质量检查，使用 Self-Consistency 策略：
  对同一问题多次调用 LLM（5次），统计 Y/N 投票结果，给出最终判断。

  整体流程分为以下几步：
  ─────────────────────────────────────────────
  第1步：导入依赖包（含公共配置 config.py）
  第2步：覆写本地配置
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
import re
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
# 第2步：覆写本地配置
# ==============================================================================
# 关闭 LangSmith 追踪
config.setup_langsmith(enable=False)

# 初始化日志
logger = config.setup_logging(__name__)


# ==============================================================================
# 第3步：定义应用生命周期管理（lifespan）
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, prompt, chain

    try:
        logger.info("正在初始化模型、提取prompt模版、定义chain（Self-Consistency）...")

        # ── 初始化 LLM 模型（temperature=0.8 提高多样性，利于投票统计） ──
        model = config.create_model(temperature=0.8)

        # ── 加载 Prompt 模板 ──
        prompt = config.build_prompt()

        # ── 构建 Chain（不含 getPrompt，直接 prompt | model） ──
        chain = prompt | model

        # 同步到全局
        config.model = model
        config.prompt = prompt
        config.chain = chain

        logger.info("初始化完成（Self-Consistency 模式）")
    except Exception as e:
        logger.error(f"初始化过程中出错: {str(e)}")
        raise

    yield
    logger.info("正在关闭...")


app = FastAPI(lifespan=lifespan)


# ==============================================================================
# 第4步：定义 API 接口
# ==============================================================================
# Self-Consistency 核心逻辑：连续调用 5 次，统计 Y/N 投票结果。

@app.post("/v1/chat/completions")
async def chat_completions(request: config.ChatCompletionRequest):
    if not config.model or not config.prompt or not config.chain:
        logger.error("服务未初始化")
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"收到聊天完成请求: {request}")
        query_prompt = request.messages[-1].content
        logger.info(f"用户问题是: {query_prompt}")

        # ── Self-Consistency：连续 5 次推理，统计 Y/N ──
        total_y_count = 0
        total_n_count = 0

        for i in range(5):
            result = config.chain.invoke({"query": query_prompt})
            formatted_response = str(config.format_response(result.content))

            # 提取输出结果中的 Y/N
            results = re.findall(r'输出：(Y|N)', formatted_response)
            y_count = results.count('Y')
            n_count = results.count('N')

            total_y_count += y_count
            total_n_count += n_count
            logger.info(f"LLM第{i + 1}次的结果回复: {formatted_response}")

        # ── 比较投票结果，给出最终判断 ──
        if total_y_count > total_n_count:
            final_result = "结论：客服介绍的产品信息准确无误。输出：Y"
        elif total_n_count > total_y_count:
            final_result = "结论：客服介绍的产品信息错误。输出：N"
        else:
            final_result = "结论：客服介绍的产品信息准确无误。输出：Y"

        logger.info(f"最终Y={total_y_count}, N={total_n_count} → {final_result}")

        # ── 响应处理 ──
        if request.stream:
            async def generate_stream():
                chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
                lines = final_result.split('\n')
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
                        message=config.Message(role="assistant", content=final_result),
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
    logger.info(f"在端口 {config.PORT} 上启动服务器（Self-Consistency 模式）")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
