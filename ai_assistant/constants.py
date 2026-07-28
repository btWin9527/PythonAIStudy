#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目枚举常量定义

所有硬编码的枚举值集中管理，避免魔术字符串散落各处。
"""

from enum import Enum


# ======================== 记忆类型 ========================

class MemoryType(str, Enum):
    """记忆类型"""
    WORKING = "working"      # 工作记忆，当前会话的问题记录（短期）
    EPISODIC = "episodic"    # 情景记忆，重要事件和交互记录（长期）


MEMORY_LABEL_WORKING = "📋 工作"
MEMORY_LABEL_EPISODIC = "📖 情景"


# ======================== 事件类型 ========================

class EventType(str, Enum):
    """外界事件类型（用于情景记忆分类）"""
    DOCUMENT_LOADED = "document_loaded"
    QA_INTERACTION = "qa_interaction"


# ======================== 对话角色 ========================

class Role(str, Enum):
    """对话消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


ROLE_LABEL_USER = "👤 用户"
ROLE_LABEL_ASSISTANT = "🤖 助手"


# ======================== 嵌入文本类型 ========================

class EmbedTextType(str, Enum):
    """DashScope 嵌入 API 的文本类型参数"""
    QUERY = "query"
    DOCUMENT = "document"
