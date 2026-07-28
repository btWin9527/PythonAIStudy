#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - Vue 3 前端 API 服务

提供 REST API + SSE 流式接口，供 Vue 3 + @ai-sdk/vue 前端调用。
"""

import sys
import os
import json
import time
import asyncio
from typing import Optional

# 确保能导入父目录中的模块
_AI_ASSISTANT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _AI_ASSISTANT_DIR)

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ======================== 框架切换开关 ========================
USE_LANGCHAIN = True
# ===========================================================

DEFAULT_PDF_PATH = os.path.join(_AI_ASSISTANT_DIR, "pdf", "test.pdf")
_HISTORY_FILE = os.path.join(_AI_ASSISTANT_DIR, "_chat_history.json")

app = FastAPI(title="智能文档问答助手 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_assistant = None


def get_assistant():
    """懒加载单例 Assistant"""
    global _assistant
    if _assistant is not None:
        return _assistant

    if USE_LANGCHAIN:
        from A_Assistant_langchain import PDFLearningAssistant
    else:
        from A_Assistant import PDFLearningAssistant

    _assistant = PDFLearningAssistant(user_id="vue_user")
    # 自动加载默认 PDF
    if os.path.exists(DEFAULT_PDF_PATH):
        result = _assistant.load_document(DEFAULT_PDF_PATH)
        print(f"[Vue API] 默认文档加载: {result['message']}")
    return _assistant


# ======================== 请求/响应模型 ========================

class ChatRequest(BaseModel):
    question: str


class NoteRequest(BaseModel):
    content: str
    concept: Optional[str] = None


# ======================== API 端点 ========================

@app.get("/api/init")
def init_assistant():
    """初始化助手 + 返回初始状态"""
    assistant = get_assistant()
    history = _load_history()
    return {
        "success": True,
        "message": "助手已就绪",
        "document": assistant.current_document or "未加载",
        "history": history,
        "token_usage": _get_token_info(assistant),
    }


@app.get("/api/token")
def token_info():
    """获取当前 Token 用量"""
    assistant = get_assistant()
    return _get_token_info(assistant)


@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """上传并加载 PDF"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")

    tmp_path = os.path.join(_AI_ASSISTANT_DIR, f"_upload_{file.filename}")
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        assistant = get_assistant()
        result = assistant.load_document(tmp_path)
        return result
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式问答（SSE 格式）"""
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "问题不能为空")

    assistant = get_assistant()

    async def event_generator():
        for chunk in assistant.ask_stream(question):
            data = json.dumps({"text": chunk, "type": "delta"}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            await asyncio.sleep(0)  # 让出控制权

        # 流式结束
        finish_data = json.dumps({"type": "finish"}, ensure_ascii=False)
        yield f"data: {finish_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/ai-chat")
async def ai_chat(req: dict):
    """
    AI SDK v4 wire format 兼容端点（@ai-sdk/vue useChat）

    接收 useChat 标准请求：{"messages": [{role, content}]}
    返回 AI SDK v4 流式格式（单字符前缀）：
      5:{"threadId":"...","messageId":"..."}   开始帧（control data）
      0:"文本内容"                            增量文本
      4:{"id":"...","role":"assistant",...}   完整消息（含 usage）
    """
    messages = req.get("messages", [])
    if not messages:
        raise HTTPException(400, "messages 不能为空")

    question = messages[-1].get("content", "")
    assistant = get_assistant()
    message_id = f"msg_{int(time.time() * 1000)}"
    thread_id = "thread_default"

    async def generator():
        # 开始帧（assistant_control_data）
        control = json.dumps({"threadId": thread_id, "messageId": message_id})
        yield f"5:{control}\n"

        # 流式文本（0:"..."）
        full_text = ""
        for chunk in assistant.ask_stream(question):
            full_text += chunk
            escaped = json.dumps(chunk, ensure_ascii=False)
            yield f"0:{escaped}\n"
            await asyncio.sleep(0)

        # 结束帧（4:assistant_message - 包含完整内容）
        finish_msg = json.dumps({
            "id": message_id,
            "role": "assistant",
            "content": [{
                "type": "text",
                "text": {"value": full_text}
            }]
        })
        yield f"4:{finish_msg}\n"

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat")
def chat_sync(req: ChatRequest):
    """同步问答（非流式）"""
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "问题不能为空")

    assistant = get_assistant()

    if any(keyword in question for keyword in ["之前", "学过", "回顾", "历史", "记得"]):
        answer = assistant.recall(question)
        answer = f"🧠 **学习回顾**\n\n{answer}"
    else:
        answer = assistant.ask(question)
        answer = f"💡 **回答**\n\n{answer}"

    # 持久化
    history = _load_history()
    history.append({"user": question, "assistant": answer})
    _save_history(history)

    return {
        "text": answer,
        "token_usage": _get_token_info(assistant),
    }


@app.post("/api/add-note")
def add_note(req: NoteRequest):
    """添加学习笔记"""
    assistant = get_assistant()
    assistant.add_note(req.content, req.concept)
    return {"success": True, "message": "笔记已保存"}


@app.get("/api/stats")
def get_stats():
    """获取学习统计"""
    assistant = get_assistant()
    return assistant.get_stats()


@app.get("/api/report")
def generate_report():
    """生成学习报告"""
    assistant = get_assistant()
    return assistant.generate_report(save_to_file=True)


@app.get("/api/history")
def get_history():
    """获取对话历史"""
    return {"history": _load_history()}


@app.post("/api/clear-history")
def clear_history():
    """清空对话历史"""
    _save_history([])
    return {"success": True, "message": "对话历史已清空"}


# ======================== 历史持久化 ========================

def _load_history() -> list:
    try:
        if os.path.exists(_HISTORY_FILE):
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_history(history: list):
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False)
    except Exception:
        pass


def _get_token_info(assistant) -> dict:
    usage = assistant.token_usage
    ctx = assistant.context_window
    return {
        "model": assistant.model_name,
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "remaining": max(0, ctx - usage["total_tokens"]),
        "calls": usage["calls"],
    }
