#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数 - 无状态纯函数集合
"""

from typing import Dict, List


def build_context_from_history(history: List[Dict[str, str]], max_turns: int) -> str:
    """
    从对话历史构建上下文字符串

    Args:
        history: 对话历史列表 [{"role": "user", "content": "..."}, ...]
        max_turns: 最大保留轮数

    Returns:
        格式化的上下文字符串
    """
    if not history:
        return ""

    recent = history[-(max_turns * 2):]
    lines = []
    for msg in recent:
        user_label = "👤 用户" if msg["role"] == "user" else "🤖 助手"
        lines.append(f"{user_label}: {msg['content']}")
    return "\n".join(lines)


def estimate_token_count(text: str) -> int:
    """中文文本 token 数估算（约 1.5 chars/token）"""
    return max(1, int(len(text) / 1.5))


def estimate_stream_tokens(question: str, messages: List[Dict], full_response: str) -> Dict[str, int]:
    """
    流式响应 token 用量估算

    Returns:
        {prompt_tokens, completion_tokens, total_tokens}
    """
    msg_text = "".join(m["content"] for m in messages)
    input_tokens = estimate_token_count(question) + estimate_token_count(msg_text)
    output_tokens = estimate_token_count(full_response)
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
