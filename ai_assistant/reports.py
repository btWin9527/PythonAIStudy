#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据报表模块 - 统计信息与学习报告的组装

职责单一：将 PDFLearningAssistant 的运行数据组装为报表/统计视图。
"""

import json
from datetime import datetime
from typing import Any, Dict

try:
    from . import config
except ImportError:
    import config


def build_stats(assistant) -> Dict[str, Any]:
    """
    构建当前会话的学习统计视图

    Args:
        assistant: PDFLearningAssistant 实例

    Returns:
        统计信息字典
    """
    duration = (datetime.now() - assistant.stats["session_start"]).total_seconds()

    return {
        "会话时长": f"{duration:.0f}秒",
        "加载文档": assistant.stats["documents_loaded"],
        "提问次数": assistant.stats["questions_asked"],
        "学习笔记": assistant.stats["concepts_learned"],
        "当前文档": assistant.current_document or "未加载",
        "使用模型": config.LLM_MODEL_ID,
        "总记忆数": len(assistant.memory._memories),
        "框架版本": "LangChain",
        "本次会话累计": (
            f"输入 {assistant.token_usage['prompt_tokens']} / "
            f"输出 {assistant.token_usage['completion_tokens']}"
        ),
        "LLM 调用次数": assistant.token_usage["calls"],
        "对话轮数": len(assistant._conversation_history) // 2,
    }


def build_rag_status(assistant) -> Dict[str, Any]:
    """构建 RAG 状态视图"""
    if not assistant.vectorstore:
        return {"has_vectorstore": False}
    return {
        "has_vectorstore": True,
        "current_document": assistant.current_document,
        "chunks_loaded": assistant._chunk_count,
    }


def build_report(assistant, save_to_file: bool = True) -> Dict[str, Any]:
    """
    构建完整学习报告

    Args:
        assistant: PDFLearningAssistant 实例
        save_to_file: 是否保存为 JSON 文件

    Returns:
        学习报告字典
    """
    memory_summary = assistant.memory.summary(limit=10)
    rag_stats = build_rag_status(assistant)
    duration = (datetime.now() - assistant.stats["session_start"]).total_seconds()

    report = {
        "framework": "LangChain",
        "session_info": {
            "session_id": assistant.session_id,
            "user_id": assistant.user_id,
            "start_time": assistant.stats["session_start"].isoformat(),
            "duration_seconds": duration,
        },
        "learning_metrics": {
            "documents_loaded": assistant.stats["documents_loaded"],
            "questions_asked": assistant.stats["questions_asked"],
            "concepts_learned": assistant.stats["concepts_learned"],
            "total_memories": len(assistant.memory._memories),
            "conversation_turns": len(assistant._conversation_history) // 2,
        },
        "memory_summary": memory_summary,
        "rag_status": rag_stats,
    }

    if save_to_file:
        _save_report_json(report, assistant.session_id)

    return report


def _save_report_json(report: Dict, session_id: str):
    """将报告保存为 JSON 文件"""
    report_file = f"learning_report_langchain_{session_id}.json"
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        report["report_file"] = report_file
    except Exception as e:
        report["save_error"] = str(e)
