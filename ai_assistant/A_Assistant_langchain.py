#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - LangChain 版核心

特性：上下文对话 / 配置分离 / 模块化（tools/ chains/ reports/）
快速使用：assistant = PDFLearningAssistant(); assistant.load_document("doc.pdf"); assistant.ask("问题")
"""

import hashlib
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# LangChain 核心
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 项目内部模块（兼容包导入和直接导入两种方式）
from . import config
from . import constants as const
from .chains import build_rag_messages
from .reports import build_report, build_stats
from .tools import (
    DashScopeEmbeddings,
    SimpleMemory,
    build_context_from_history,
    estimate_stream_tokens,
)


class PDFLearningAssistant:
    """智能文档问答助手：文档加载 → RAG 检索 → LLM 生成，支持多轮上下文对话。"""

    def __init__(self, user_id: str = "default_user"):
        """初始化组件：LLM、Embedding、文本分割器、向量存储、对话上下文、记忆系统"""
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # ---- 核心组件 ----
        self._llm = ChatOpenAI(
            model=config.LLM_MODEL_ID,
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            temperature=config.LLM_TEMPERATURE,
        )
        self._embeddings = DashScopeEmbeddings()
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", ".", " ", ""],
            length_function=len,
        )
        self.vectorstore: Optional[FAISS] = None
        self._chunk_count: int = 0

        self._conversation_history: List[Dict[str, str]] = []
        self._max_context_turns = config.MAX_CONVERSATION_TURNS

        self.memory = SimpleMemory()

        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "concepts_learned": 0,
        }
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "calls": 0,
        }
        self.current_document: Optional[str] = None

    # ======================== 文档加载 ========================

    def load_document(self, pdf_path: str) -> Dict[str, Any]:
        """加载 PDF → 切块 → 嵌入 → FAISS（带磁盘缓存，二次加载秒级）"""
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"文件不存在: {pdf_path}"}

        cache_dir = self._get_cache_path(pdf_path)
        start_time = time.time()

        try:
            if os.path.exists(os.path.join(cache_dir, "index.faiss")):
                self._load_from_cache(cache_dir)
                pages = ["(cached)"]
            else:
                pages = self._load_and_embed(pdf_path, cache_dir)

            self._update_document_state(pdf_path, pages, time.time() - start_time)
            return {
                "success": True,
                "message": f"加载成功（耗时 {time.time() - start_time:.1f}s，{self._chunk_count} 块）",
                "document": self.current_document,
                "chunk_count": self._chunk_count,
                "cached": isinstance(pages[0], str),
            }
        except Exception as e:
            return {"success": False, "message": f"加载失败: {str(e)}"}

    def _get_cache_path(self, pdf_path: str) -> str:
        cache_key = hashlib.md5(
            f"{os.path.abspath(pdf_path)}_{os.path.getmtime(pdf_path)}".encode()
        ).hexdigest()[:16]
        return os.path.join(config.FAISS_CACHE_DIR, cache_key)

    def _load_from_cache(self, cache_dir: str):
        print(f"[load] 命中缓存: {os.path.basename(cache_dir)}")
        self.vectorstore = FAISS.load_local(
            cache_dir, self._embeddings, allow_dangerous_deserialization=True
        )
        self._chunk_count = self.vectorstore.index.ntotal

    def _load_and_embed(self, pdf_path: str, cache_dir: str) -> List:
        print("[load] 未命中缓存，正在嵌入...")
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        if not pages:
            raise ValueError("PDF 文件为空或无法解析")

        chunks = self._text_splitter.split_documents(pages)
        self.vectorstore = FAISS.from_documents(chunks, self._embeddings)
        self._chunk_count = len(chunks)

        os.makedirs(cache_dir, exist_ok=True)
        self.vectorstore.save_local(cache_dir)
        print(f"[load] 索引已缓存: {os.path.basename(cache_dir)}")
        return pages

    def _update_document_state(self, pdf_path: str, pages: List, elapsed: float):
        self.current_document = os.path.basename(pdf_path)
        self.stats["documents_loaded"] += 1

        page_count = len(pages) if not isinstance(pages[0], str) else "?"
        self.memory.add(
            content=f"加载了文档《{self.current_document}》（{page_count} 页，{self._chunk_count} 块）",
            memory_type=const.MemoryType.EPISODIC,
            importance=0.9,
            event_type=const.EventType.DOCUMENT_LOADED,
            session_id=self.session_id,
        )

    # ======================== 问答（ask / ask_stream 共用消息构建） ========================

    def _get_history_context(self) -> str:
        if not self._conversation_history:
            return ""
        return build_context_from_history(self._conversation_history, self._max_context_turns)

    def _build_and_validate_messages(self, question: str, use_context: bool) -> Optional[List[Dict]]:
        """构建 RAG 消息 + 前置校验，校验失败返回 None"""
        if not self.current_document or self.vectorstore is None:
            return None
        history_context = self._get_history_context() if use_context else ""
        return build_rag_messages(self.vectorstore, question, history_context)

    def ask(self, question: str, use_context: bool = True) -> str:
        """RAG 问答，use_context=True 时携带对话历史上下文"""
        messages = self._build_and_validate_messages(question, use_context)
        if messages is None:
            return self._not_ready_message()

        self._record_question(question)

        try:
            response = self._llm.invoke(messages)
            answer = response.content if hasattr(response, 'content') else str(response)
            self._record_tokens_from_response(response)
        except Exception as e:
            answer = f"生成回答时出错: {str(e)}"

        if use_context:
            self._append_to_history(const.Role.USER, question)
            self._append_to_history(const.Role.ASSISTANT, answer)

        self._record_answer(question)
        self.stats["questions_asked"] += 1
        return answer

    def ask_stream(self, question: str, use_context: bool = True):
        """流式问答（生成器），与 ask() 共用 build_rag_messages()，行为一致"""
        messages = self._build_and_validate_messages(question, use_context)
        if messages is None:
            yield self._not_ready_message()
            return

        self._record_question(question)

        try:
            full_response = []
            for chunk in self._llm.stream(messages):
                chunk_text = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response.append(chunk_text)
                yield chunk_text

            # 流式 token 估算
            response_text = "".join(full_response)
            estimated = estimate_stream_tokens(question, messages, response_text)
            self.token_usage["prompt_tokens"] += estimated["prompt_tokens"]
            self.token_usage["completion_tokens"] += estimated["completion_tokens"]
            self.token_usage["total_tokens"] += estimated["total_tokens"]
            self.token_usage["calls"] += 1

            if use_context:
                self._append_to_history(const.Role.USER, question)
                self._append_to_history(const.Role.ASSISTANT, response_text)

        except Exception as e:
            yield f"\n\n生成回答时出错: {str(e)}"

        self._record_answer(question)
        self.stats["questions_asked"] += 1

    @staticmethod
    def _not_ready_message() -> str:
        return "⚠️ 请先加载文档！使用 load_document() 方法加载PDF文档。"

    # ======================== 上下文对话 ========================

    def chat(self, message: str) -> str:
        """多轮对话入口（始终启用上下文）"""
        return self.ask(message, use_context=True)

    def chat_stream(self, message: str):
        """多轮流式对话入口"""
        yield from self.ask_stream(message, use_context=True)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        return list(self._conversation_history)

    def clear_context(self):
        """清空对话历史，开始新话题"""
        self._conversation_history.clear()
        print("[context] 对话上下文已清空")

    # ======================== 内部辅助 ========================

    def _append_to_history(self, role: str, content: str):
        self._conversation_history.append({"role": role, "content": content})

    def _record_tokens_from_response(self, response):
        """从 LLM 响应提取 token 用量并累加"""
        usage = {}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = dict(response.usage_metadata)
        elif hasattr(response, 'response_metadata') and response.response_metadata:
            usage = response.response_metadata.get('token_usage', {})
        if usage:
            self.token_usage["prompt_tokens"] += (
                    usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
            )
            self.token_usage["completion_tokens"] += (
                    usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
            )
            self.token_usage["total_tokens"] += usage.get("total_tokens", 0)
            self.token_usage["calls"] += 1

    def _record_question(self, question: str):
        self.memory.add(
            content=f"提问: {question}",
            memory_type=const.MemoryType.WORKING,
            importance=0.6,
            session_id=self.session_id,
        )

    def _record_answer(self, question: str):
        short_q = question[:30] + ("..." if len(question) > 30 else "")
        self.memory.add(
            content=f"关于'{short_q}'的学习",
            memory_type=const.MemoryType.EPISODIC,
            importance=0.7,
            event_type=const.EventType.QA_INTERACTION,
            session_id=self.session_id,
        )

    # ======================== 笔记 & 回顾 ========================

    def add_note(self, content: str, concept: Optional[str] = None):
        """添加学习笔记到情景记忆"""
        self.memory.add(
            content=content,
            memory_type=const.MemoryType.EPISODIC,
            importance=0.8,
            concept=concept or "general",
            session_id=self.session_id,
        )
        self.stats["concepts_learned"] += 1

    def recall(self, query: str, limit: int = 5) -> str:
        """搜索学习记忆"""
        if not self.memory._memories:
            return "📭 暂无学习记录。开始提问或添加笔记来积累学习历程吧！"
        return self.memory.search(query, limit)

    # ======================== 统计 & 报告 ========================

    def get_stats(self) -> Dict[str, Any]:
        """获取学习统计（委托 reports.build_stats）"""
        return build_stats(self)

    def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """生成学习报告（委托 reports.build_report）"""
        return build_report(self, save_to_file)


# ======================== 测试入口 ========================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LangChain 版 PDFLearningAssistant 测试（重构版）")
    print("=" * 60)

    assistant = PDFLearningAssistant(user_id="test_user")
    print(f"✅ 助手已初始化 (session: {assistant.session_id})")
    print(f"   模型: {config.LLM_MODEL_ID}")
    print(f"   嵌入: {config.EMBED_MODEL_NAME}")
    print(f"   上下文轮数: {config.MAX_CONVERSATION_TURNS}")
