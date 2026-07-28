#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - 基于HelloAgents的智能文档问答系统（业务逻辑层）

这是一个完整的PDF学习助手核心类，支持：
- 加载PDF文档并构建知识库（RAGTool）
- 智能问答（基于RAG）
- 学习历程记录（基于MemoryTool）
- 学习回顾和报告生成

使用方法：
    # 代码直接调用
    from A_Assistant import PDFLearningAssistant

    assistant = PDFLearningAssistant(user_id="my_user")
    assistant.load_document("/path/to/doc.pdf")
    answer = assistant.ask("这个文档讲了什么？")
    print(answer)

    # 启动 Web UI
    python ui/gradio_ui.py
"""

# ======================== 环境初始化 ========================

import os

from dotenv import load_dotenv

# 优先从当前文件所在目录加载 .env，确保无论从哪里运行都能找到配置
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()  # 回退到默认行为

import time
import json
from datetime import datetime
from typing import Dict, Optional, Any

# HelloAgents 框架核心工具
from hello_agents.tools import MemoryTool, RAGTool


# ======================== 核心业务类 ========================

class PDFLearningAssistant:
    """
    智能文档问答助手（HelloAgents 版本）

    职责：
    1. 管理文档加载和知识库构建（通过 RAGTool）
    2. 处理用户提问并返回回答
    3. 记录学习历程（通过 MemoryTool）
    4. 提供学习统计和报告生成

    使用示例：
        assistant = PDFLearningAssistant(user_id="zhangsan")
        assistant.load_document("机器学习入门.pdf")
        answer = assistant.ask("什么是监督学习？")
        assistant.add_note("监督学习需要标注数据")
        report = assistant.generate_report()
    """

    def __init__(self, user_id: str = "default_user"):
        """
        初始化学习助手

        Args:
            user_id: 用户ID，用于隔离不同用户的记忆和知识库数据
        """
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 初始化 MemoryTool（工作记忆 + 情景记忆）
        self.memory_tool = MemoryTool(
            user_id=user_id,
            memory_types=["working", "episodic"]
        )

        # 初始化 RAGTool（文档知识库）
        self.rag_tool = RAGTool(rag_namespace=f"pdf_{user_id}")

        # 学习统计
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "concepts_learned": 0
        }

        self.current_document = None

    # ======================== 文档加载 ========================

    def load_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        加载PDF文档到知识库

        Args:
            pdf_path: PDF 文件的路径

        Returns:
            Dict: {success, message, document}
        """
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"文件不存在: {pdf_path}"}

        start_time = time.time()

        try:
            self.rag_tool.run({
                "action": "add_document",
                "file_path": pdf_path,
                "chunk_size": 1000,
                "chunk_overlap": 200
            })

            process_time = time.time() - start_time

            self.current_document = os.path.basename(pdf_path)
            self.stats["documents_loaded"] += 1

            # 记录到情景记忆
            self.memory_tool.run({
                "action": "add",
                "content": f"加载了文档《{self.current_document}》",
                "memory_type": "episodic",
                "importance": 0.9,
                "event_type": "document_loaded",
                "session_id": self.session_id
            })

            return {
                "success": True,
                "message": f"加载成功！(耗时: {process_time:.1f}秒)",
                "document": self.current_document
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"加载失败: {str(e)}"
            }

    # ======================== 智能问答 ========================

    def ask(self, question: str, use_advanced_search: bool = True) -> str:
        """
        向已加载的文档提问（RAG 问答）

        Args:
            question: 用户问题
            use_advanced_search: 是否启用高级检索（MQE + HyDE）

        Returns:
            str: LLM 生成的回答
        """
        if not self.current_document:
            return "⚠️ 请先加载文档！使用 load_document() 方法加载PDF文档。"

        # 记录到工作记忆
        self.memory_tool.run({
            "action": "add",
            "content": f"提问: {question}",
            "memory_type": "working",
            "importance": 0.6,
            "session_id": self.session_id
        })

        # RAG 检索 + 生成
        answer = self.rag_tool.run({
            "action": "ask",
            "question": question,
            "limit": 5,
            "enable_advanced_search": use_advanced_search,
            "enable_mqe": use_advanced_search,
            "enable_hyde": use_advanced_search
        })

        # 记录到情景记忆
        self.memory_tool.run({
            "action": "add",
            "content": f"关于'{question}'的学习",
            "memory_type": "episodic",
            "importance": 0.7,
            "event_type": "qa_interaction",
            "session_id": self.session_id
        })

        self.stats["questions_asked"] += 1
        return answer

    # ======================== 学习笔记 ========================

    def add_note(self, content: str, concept: Optional[str] = None):
        """
        添加学习笔记，记录到情景记忆

        Args:
            content: 笔记内容
            concept: 相关概念标签（可选）
        """
        self.memory_tool.run({
            "action": "add",
            "content": content,
            "memory_type": "episodic",
            "importance": 0.8,
            "concept": concept or "general",
            "session_id": self.session_id
        })

        self.stats["concepts_learned"] += 1

    # ======================== 学习回顾 ========================

    def recall(self, query: str, limit: int = 5) -> str:
        """
        回顾学习历程，从记忆中搜索相关内容

        Args:
            query: 搜索关键词
            limit: 返回结果数量上限

        Returns:
            str: 格式化的搜索结果
        """
        result = self.memory_tool.run({
            "action": "search",
            "query": query,
            "limit": limit
        })
        return result

    # ======================== 统计与报告 ========================

    def get_stats(self) -> Dict[str, Any]:
        """
        获取当前会话的学习统计

        Returns:
            Dict: 统计信息字典
        """
        duration = (datetime.now() - self.stats["session_start"]).total_seconds()

        return {
            "会话时长": f"{duration:.0f}秒",
            "加载文档": self.stats["documents_loaded"],
            "提问次数": self.stats["questions_asked"],
            "学习笔记": self.stats["concepts_learned"],
            "当前文档": self.current_document or "未加载"
        }

    def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """
        生成学习报告

        Args:
            save_to_file: 是否保存到 JSON 文件

        Returns:
            Dict: 完整的学习报告
        """
        memory_summary = self.memory_tool.run({"action": "summary", "limit": 10})
        rag_stats = self.rag_tool.run({"action": "stats"})

        duration = (datetime.now() - self.stats["session_start"]).total_seconds()

        report = {
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "start_time": self.stats["session_start"].isoformat(),
                "duration_seconds": duration
            },
            "learning_metrics": {
                "documents_loaded": self.stats["documents_loaded"],
                "questions_asked": self.stats["questions_asked"],
                "concepts_learned": self.stats["concepts_learned"]
            },
            "memory_summary": memory_summary,
            "rag_status": rag_stats
        }

        if save_to_file:
            report_file = f"learning_report_{self.session_id}.json"
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
                report["report_file"] = report_file
            except Exception as e:
                report["save_error"] = str(e)

        return report
