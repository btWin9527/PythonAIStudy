"""
================================================================================
  体育人才分析系统 - 思维树策略（Tree of Thoughts）
================================================================================

  基于 LangChain 框架实现体育人才分析，使用 ToT（思维树）策略：
  通过多个 Chain 串联（分析 → 推荐 → 评估 → 报告），逐步推理并给出最终建议。

  整体流程分为以下几步：
  ─────────────────────────────────────────────
  第1步：导入依赖包（含公共配置 config.py）
  第2步：覆写本地配置
  第3步：定义本目录特有的数据模型（ToT 的 Message 需要额外字段）
  第4步：定义应用生命周期管理（lifespan）—— 初始化模型和多个 Chain
  第5步：定义 API 接口（/v1/chat/completions）—— ToT 核心逻辑
  第6步：启动服务（uvicorn）
  ─────────────────────────────────────────────

  核心架构图：

    用户请求 → FastAPI接口
                  │
                  ├── Chain1: 分析速度/耐力/力量分档
                  ├── Chain2: 获取可能适合的运动项目（剪枝）
                  ├── Chain3: 评估其他素质是否满足运动要求（剪枝）
                  ├── Chain4: 生成最终分析报告
                  └── 格式化输出 → 响应返回

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
from contextlib import asynccontextmanager
from typing import List, Optional

# 将项目根目录加入 sys.path，确保子目录运行时可导入 config.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from pathlib import Path
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
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
# 第3步：定义本目录特有的数据模型
# ==============================================================================
# ToT 的请求 Message 需要 name、performance、category 三个额外字段。

class ToTMessage(BaseModel):
    """ToT 专用的请求消息模型，包含候选人信息字段。"""
    role: str
    name: str           # 候选人姓名
    performance: str    # 候选人体测成绩
    category: str       # 目标运动类别（如"搏击"）


class ToTChatCompletionRequest(BaseModel):
    """ToT 专用的请求体结构。"""
    messages: List[ToTMessage]
    stream: Optional[bool] = False


# ==============================================================================
# 第4部分：全局变量（ToT 特有 4 组 Prompt + Chain）
# ==============================================================================
model = None
prompt_performanceAnalyser = None
performanceAnalyser_chain = None
prompt_possibleSports = None
possibleSports_chain = None
prompt_evaluate = None
evaluate_chain = None
prompt_report = None
report_chain = None

# Prompt 模板路径（ToT 特有）
PROMPT_PERFORMANCE_ANALYSER = "prompt_template_performanceAnalyser.txt"
PROMPT_POSSIBLE_SPORTS = "prompt_template_possibleSports.txt"
PROMPT_EVALUATE = "prompt_template_evaluate.txt"
PROMPT_REPORT = "prompt_template_reportGenerator.txt"


# ==============================================================================
# 第4步：定义应用生命周期管理（lifespan）
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    global prompt_performanceAnalyser, performanceAnalyser_chain
    global prompt_possibleSports, possibleSports_chain
    global prompt_evaluate, evaluate_chain
    global prompt_report, report_chain

    try:
        logger.info("正在初始化模型、提取prompt模版、定义Chain（ToT模式）...")

        # ── 初始化 LLM 模型（temperature=0.8 提高多样性） ──
        model = config.create_model(temperature=0.8)
        config.model = model

        # ── 加载 4 个 Prompt 模板 ──
        prompt_template_performanceAnalyser = PromptTemplate.from_template(Path(PROMPT_PERFORMANCE_ANALYSER).read_text(encoding="utf-8"))
        prompt_template_possibleSports = PromptTemplate.from_template(Path(PROMPT_POSSIBLE_SPORTS).read_text(encoding="utf-8"))
        prompt_template_evaluate = PromptTemplate.from_template(Path(PROMPT_EVALUATE).read_text(encoding="utf-8"))
        prompt_template_report = PromptTemplate.from_template(Path(PROMPT_REPORT).read_text(encoding="utf-8"))

        # 构建 ChatPromptTemplate
        prompt_performanceAnalyser = ChatPromptTemplate.from_messages([
            ("human", prompt_template_performanceAnalyser.template)
        ])
        prompt_possibleSports = ChatPromptTemplate.from_messages([
            ("human", prompt_template_possibleSports.template)
        ])
        prompt_evaluate = ChatPromptTemplate.from_messages([
            ("human", prompt_template_evaluate.template)
        ])
        prompt_report = ChatPromptTemplate.from_messages([
            ("human", prompt_template_report.template)
        ])

        # ── 构建 4 个 Chain ──
        performanceAnalyser_chain = prompt_performanceAnalyser | model
        possibleSports_chain = prompt_possibleSports | model
        evaluate_chain = prompt_evaluate | model
        report_chain = prompt_report | model

        logger.info("初始化完成（ToT 模式，4 Chain 就绪）")
    except Exception as e:
        logger.error(f"初始化过程中出错: {str(e)}")
        raise

    yield
    logger.info("正在关闭...")


app = FastAPI(lifespan=lifespan)


# ==============================================================================
# 第5步：定义 API 接口
# ==============================================================================
# ToT 核心逻辑：Chain1(分析分档) → Chain2(获取运动项目,剪枝) → Chain3(评估,剪枝) → Chain4(生成报告)

@app.post("/v1/chat/completions")
async def chat_completions(request: ToTChatCompletionRequest):
    if not model or not prompt_performanceAnalyser or not performanceAnalyser_chain:
        logger.error("服务未初始化")
        raise HTTPException(status_code=500, detail="服务未初始化")

    try:
        logger.info(f"收到聊天完成请求: {request}")

        name = request.messages[-1].name
        performance = request.messages[-1].performance
        category = request.messages[-1].category

        # ── 第一步：分析候选人在速度、耐力、力量三方面素质的分档分数 ──
        result = performanceAnalyser_chain.invoke({"text": name + performance})
        json_content = re.search(r'\{[^}]+\}', result.content, re.DOTALL).group()
        talents = json.loads(json_content)
        logger.info(f"talents: {talents}")

        # ── 第二、三、四步：遍历 → 剪枝 → 评估 → 生成报告 ──
        cache = set()
        finalContent = ''

        for k, v in talents.items():
            if v < 3:  # 剪枝：素质不合格则跳过
                continue

            # 第二步：获取该素质对应的运动项目
            result = possibleSports_chain.invoke({"talent": k, "category": category})
            json_content = re.search(r'\{[^}]+\}', result.content, re.DOTALL).group()
            leafs = json.loads(json_content)
            logger.info(f"leafs: {leafs}")

            sports_list = []
            for key, values in leafs.items():
                sports_list.extend(values)
            logger.info(f"sports_list: {sports_list}")

            # 第三步：对每个运动项目，检查其他素质是否达标
            for sports in sports_list:
                if sports in cache:
                    continue
                cache.add(sports)
                suitable = True

                for t, p in talents.items():
                    if t == k:
                        continue
                    result = evaluate_chain.invoke({"sports": sports, "talent": t})
                    val = int(result.content)
                    logger.info(f"evaluate_result:{sports}: {t} {val} {p >= val}")
                    if not p >= val:  # 剪枝
                        suitable = False
                        break
                logger.info(f"suitable: {suitable}")

                # 第四步：生成分析报告
                if suitable:
                    result = report_chain.invoke({
                        "name": name, "performance": performance,
                        "talents": talents, "sports": sports,
                    })
                    logger.info(f"report_result: {result.content}")
                    finalContent = finalContent + str(config.format_response(result.content))

        formatted_response = finalContent
        logger.info(f"格式化的搜索结果: {formatted_response}")

        # ── 响应处理 ──
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
# 第6步：启动服务
# ==============================================================================
if __name__ == "__main__":
    logger.info(f"在端口 {config.PORT} 上启动服务器（ToT 模式）")
    uvicorn.run(app, host="0.0.0.0", port=config.PORT)
