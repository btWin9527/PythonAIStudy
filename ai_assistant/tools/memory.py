#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
轻量级记忆系统 - 支持工作记忆和情景记忆
"""

import hashlib
import time
from datetime import datetime
from typing import Dict, List

try:
    from .embeddings import DashScopeEmbeddings
    from ..constants import MemoryType, MEMORY_LABEL_WORKING, MEMORY_LABEL_EPISODIC
except ImportError:
    from tools.embeddings import DashScopeEmbeddings
    from constants import MemoryType, MEMORY_LABEL_WORKING, MEMORY_LABEL_EPISODIC


class SimpleMemory:
    """
    轻量级记忆系统（替代 HelloAgents MemoryTool）

    支持两种记忆类型：
    - working:  工作记忆（当前会话的问题记录，短期）
    - episodic: 情景记忆（重要事件和交互记录，长期）

    存储方式：内存 List[Dict]，嵌入相似度搜索（带关键词降级）。
    """

    def __init__(self):
        self._memories: List[Dict] = []
        self._embeddings = DashScopeEmbeddings()

    # -------------------- 添加记忆 --------------------

    def add(
        self,
        content: str,
        memory_type: str,  # 推荐使用 MemoryType 枚举
        importance: float = 0.5,
        event_type: str = "",
        session_id: str = "",
        concept: str = "",
    ):
        """添加一条记忆"""
        entry = {
            "id": hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:12],
            "content": content,
            "memory_type": memory_type,
            "importance": importance,
            "event_type": event_type,
            "session_id": session_id,
            "concept": concept,
            "timestamp": datetime.now().isoformat(),
        }
        self._memories.append(entry)

    # -------------------- 搜索记忆 --------------------

    def search(self, query: str, limit: int = 5) -> str:
        """搜索记忆（嵌入相似度，带关键词降级）"""
        if not self._memories:
            return "暂无记忆记录。"

        try:
            return self._embedding_search(query, limit)
        except Exception:
            return self._keyword_search(query, limit)

    def _embedding_search(self, query: str, limit: int) -> str:
        """基于嵌入向量的相似度搜索"""
        query_embedding = self._embeddings.embed_query(query)
        scored = []

        for mem in self._memories:
            try:
                mem_embedding = self._embeddings.embed_query(mem["content"])
                score = self._cosine_similarity(query_embedding, mem_embedding)
                scored.append((score, mem))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        if not top:
            return "未找到相关记忆。"

        return self._format_search_results(top)

    def _keyword_search(self, query: str, limit: int) -> str:
        """简单关键词匹配搜索（降级方案）"""
        keywords = query.lower().split()
        matches = []

        for mem in self._memories:
            content_lower = mem["content"].lower()
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                matches.append((score * mem["importance"], mem))

        matches.sort(key=lambda x: x[0], reverse=True)
        top = matches[:limit]

        if not top:
            return "未找到相关记忆。"

        return self._format_search_results(top)

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a ** 2 for a in vec_a) ** 0.5
        norm_b = sum(b ** 2 for b in vec_b) ** 0.5
        return dot / (norm_a * norm_b + 1e-10)

    @staticmethod
    def _format_search_results(results: List) -> str:
        """格式化搜索结果"""
        lines = []
        for i, (score, mem) in enumerate(results, 1):
            mem_type = MEMORY_LABEL_WORKING if mem["memory_type"] == MemoryType.WORKING else MEMORY_LABEL_EPISODIC
            lines.append(f"{i}. [{mem_type}] {mem['content']}")
            lines.append(f"   重要性: {mem['importance']:.1f} | 时间: {mem['timestamp'][:19]}")
        return "\n".join(lines)

    # -------------------- 记忆摘要 --------------------

    def summary(self, limit: int = 10) -> str:
        """获取记忆摘要（按重要性排序）"""
        sorted_memories = sorted(
            self._memories, key=lambda m: m["importance"], reverse=True
        )[:limit]

        if not sorted_memories:
            return "暂无记忆。"

        lines = [f"共 {len(self._memories)} 条记忆，以下为最重要的 {len(sorted_memories)} 条："]
        for i, mem in enumerate(sorted_memories, 1):
            lines.append(f"{i}. [{mem['memory_type']}] {mem['content']}")

        return "\n".join(lines)
