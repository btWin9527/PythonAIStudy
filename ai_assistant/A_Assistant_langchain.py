#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - 基于LangChain的智能文档问答系统（LangChain 重写版）

LangChain 内置组件：
  PDF 解析   → PyPDFLoader
  文档切割   → RecursiveCharacterTextSplitter
  向量存储   → FAISS
  嵌入       → DashScopeEmbeddings（适配 DashScope 原生 API）
  LLM       → ChatOpenAI（DashScope qwen-max）
  记忆       → SimpleMemory（working + episodic，嵌入相似度搜索）

使用方法：
    from A_Assistant_langchain import PDFLearningAssistant

    assistant = PDFLearningAssistant(user_id="my_user")
    assistant.load_document("/path/to/doc.pdf")
    answer = assistant.ask("这个文档讲了什么？")
"""

# ======================== 环境初始化 ========================

import os

from dotenv import load_dotenv

# 优先从当前文件所在目录加载 .env
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()

import time
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

# LangChain 核心
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.embeddings import Embeddings

# DashScope 嵌入 SDK（原生 API 启动时检查，缺依赖立即报错）
import dashscope
from dashscope import TextEmbedding


# ======================== DashScope 嵌入适配器 ========================

class DashScopeEmbeddings(Embeddings):
    """
    DashScope 原生嵌入 API 适配器（实现 LangChain Embeddings 接口）
    """

    def __init__(self, model: str = "text-embedding-v3", api_key: str = ""):
        self.model = model
        dashscope.api_key = api_key

    def embed_query(self, text: str) -> List[float]:
        """嵌入单条查询文本"""
        resp = TextEmbedding.call(model=self.model, input=text, text_type="query")
        if resp.status_code != 200:
            raise RuntimeError(f"嵌入失败: {resp.message}")
        return resp.output["embeddings"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档文本"""
        embeddings = []
        for i in range(0, len(texts), 25):
            batch = texts[i:i + 25]
            resp = TextEmbedding.call(model=self.model, input=batch, text_type="document")
            if resp.status_code != 200:
                raise RuntimeError(f"批量嵌入失败: {resp.message}")
            for item in resp.output["embeddings"]:
                embeddings.append(item["embedding"])
        return embeddings


# ======================== 自定义内存（替代 HelloAgents MemoryTool） ========================

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
        self._embeddings = DashScopeEmbeddings(
            model=os.getenv("EMBED_MODEL_NAME", "text-embedding-v3"),
            api_key=os.getenv("EMBED_API_KEY", ""),
        )

    def add(self, content: str, memory_type: str, importance: float = 0.5,
            event_type: str = "", session_id: str = "", concept: str = ""):
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

    def search(self, query: str, limit: int = 5) -> str:
        """搜索记忆（嵌入相似度）"""
        if not self._memories:
            return "暂无记忆记录。"

        try:
            query_embedding = self._embeddings.embed_query(query)
        except Exception:
            return self._keyword_search(query, limit)

        scored = []
        for mem in self._memories:
            try:
                mem_embedding = self._embeddings.embed_query(mem["content"])
                dot = sum(a * b for a, b in zip(query_embedding, mem_embedding))
                norm_q = sum(a ** 2 for a in query_embedding) ** 0.5
                norm_m = sum(b ** 2 for b in mem_embedding) ** 0.5
                score = dot / (norm_q * norm_m + 1e-10)
                scored.append((score, mem))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        if not top:
            return "未找到相关记忆。"

        lines = []
        for i, (score, mem) in enumerate(top, 1):
            mem_type = "📋 工作" if mem["memory_type"] == "working" else "📖 情景"
            lines.append(f"{i}. [{mem_type}] {mem['content']}")
            lines.append(f"   重要性: {mem['importance']:.1f} | 时间: {mem['timestamp'][:19]}")

        return "\n".join(lines)

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

        lines = []
        for i, (score, mem) in enumerate(top, 1):
            mem_type = "📋 工作" if mem["memory_type"] == "working" else "📖 情景"
            lines.append(f"{i}. [{mem_type}] {mem['content']}")
            lines.append(f"   重要性: {mem['importance']:.1f} | 时间: {mem['timestamp'][:19]}")

        return "\n".join(lines)

    def summary(self, limit: int = 10) -> str:
        """获取记忆摘要"""
        sorted_memories = sorted(
            self._memories,
            key=lambda m: m["importance"],
            reverse=True
        )[:limit]

        if not sorted_memories:
            return "暂无记忆。"

        lines = [f"共 {len(self._memories)} 条记忆，以下为最重要的 {len(sorted_memories)} 条："]
        for i, mem in enumerate(sorted_memories, 1):
            lines.append(f"{i}. [{mem['memory_type']}] {mem['content']}")

        return "\n".join(lines)


# ======================== RAG 链构建 ========================

def _build_rag_chain(llm, vectorstore):
    """构建 RAG 问答链，返回 (答案文本, usage) 元组"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的学习助手，基于提供的文档内容回答问题。

请遵循以下原则：
1. 仅基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，诚实告知用户
3. 回答要准确、简洁、有条理
4. 可以引用文档中的关键段落支持你的回答
5. 用中文回答

参考文档内容：
{context}"""),
        ("human", "{question}")
    ])

    def retrieve_and_format(inputs: Dict) -> Dict:
        question = inputs["question"]
        docs = vectorstore.similarity_search(question, k=5)
        context = "\n\n---\n\n".join([
            f"[文档{i+1}] {doc.page_content}" for i, doc in enumerate(docs)
        ])
        return {"context": context, "question": question}

    # 不使用 StrOutputParser，保留 AIMessage 以读取 token 用量
    base_chain = retrieve_and_format | prompt | llm

    def extract_answer_and_usage(message):
        """从 AIMessage 提取 (content, usage_dict)"""
        usage = {}
        if hasattr(message, 'usage_metadata') and message.usage_metadata:
            usage = dict(message.usage_metadata)
        elif hasattr(message, 'response_metadata') and message.response_metadata:
            usage = message.response_metadata.get('token_usage', {})
        return message.content, usage

    return base_chain | RunnableLambda(extract_answer_and_usage)


# ======================== 核心业务类（LangChain 版） ========================

class PDFLearningAssistant:
    """
    智能文档问答助手（LangChain 版本）

    使用示例：
        assistant = PDFLearningAssistant(user_id="zhangsan")
        assistant.load_document("机器学习入门.pdf")
        answer = assistant.ask("什么是监督学习？")
    """

    def __init__(self, user_id: str = "default_user"):
        """初始化学习助手（LangChain 版）"""
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # LLM 配置（DashScope qwen-max）
        self.model_name = os.getenv("LLM_MODEL_ID", "qwen-max")
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL"),
            temperature=0.3,
        )

        # Embedding 配置（DashScope 原生 API）
        self.embeddings = DashScopeEmbeddings(
            model=os.getenv("EMBED_MODEL_NAME", "text-embedding-v3"),
            api_key=os.getenv("EMBED_API_KEY", ""),
        )

        # 向量存储（延后初始化，FAISS 是 LangChain 内置的）
        self.vectorstore: Optional[FAISS] = None
        self._chunk_count: int = 0

        # RAG 链（延后构建）
        self._rag_chain = None

        # 记忆系统
        self.memory = SimpleMemory()

        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", ".", " ", ""],
            length_function=len,
        )

        # 学习统计
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "concepts_learned": 0
        }

        # Token 用量统计
        self.token_usage = {
            "prompt_tokens": 0,      # 累计输入 token
            "completion_tokens": 0,   # 累计输出 token
            "total_tokens": 0,        # 累计总 token
            "calls": 0,               # 累计调用次数
        }

        # 模型上下文窗口（内部计算剩余 token 用，可选 .env 覆盖）
        self.context_window = int(os.getenv("CONTEXT_WINDOW", "32768"))

        self.current_document = None

    # ======================== 文档加载 ========================

    def load_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        加载PDF文档到知识库（带 FAISS 持久化缓存）

        首次加载 → 切块 + 嵌入 + 保存索引到磁盘（慢，仅一次）
        再次加载 → 直接读取磁盘缓存（快，1-2 秒）
        """
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"文件不存在: {pdf_path}"}

        # 缓存目录：基于文件路径 + 修改时间的 hash
        cache_key = hashlib.md5(
            f"{os.path.abspath(pdf_path)}_{os.path.getmtime(pdf_path)}".encode()
        ).hexdigest()[:16]
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_faiss_cache", cache_key)

        start_time = time.time()

        try:
            # ==== 尝试从缓存加载 ====
            if os.path.exists(os.path.join(cache_dir, "index.faiss")):
                print(f"[load] 命中缓存: {cache_key}")
                self.vectorstore = FAISS.load_local(
                    cache_dir, self.embeddings, allow_dangerous_deserialization=True
                )
                pages = ["(cached)"]  # 占位
                self._chunk_count = self.vectorstore.index.ntotal

            else:
                # ==== 首次加载：切块 + 嵌入 + 保存 ====
                print(f"[load] 未命中缓存，正在嵌入...")
                loader = PyPDFLoader(pdf_path)
                pages = loader.load()

                if not pages:
                    return {"success": False, "message": "PDF 文件为空或无法解析"}

                chunks = self.text_splitter.split_documents(pages)
                self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
                self._chunk_count = len(chunks)

                # 持久化到磁盘
                os.makedirs(cache_dir, exist_ok=True)
                self.vectorstore.save_local(cache_dir)
                print(f"[load] 索引已缓存: {cache_dir}")

            # ==== 构建 RAG 链 ====
            self._rag_chain = _build_rag_chain(self.llm, self.vectorstore)

            process_time = time.time() - start_time

            self.current_document = os.path.basename(pdf_path)
            self.stats["documents_loaded"] += 1

            page_count = len(pages) if not isinstance(pages[0], str) else "?"
            self.memory.add(
                content=f"加载了文档《{self.current_document}》（{page_count} 页，{self._chunk_count} 块）",
                memory_type="episodic", importance=0.9,
                event_type="document_loaded", session_id=self.session_id
            )

            return {
                "success": True,
                "message": f"加载成功（耗时 {process_time:.1f}s，{self._chunk_count} 块）",
                "document": self.current_document,
                "chunk_count": self._chunk_count,
                "cached": page_count == "?"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"加载失败: {str(e)}"
            }

    # ======================== 智能问答 ========================

    def _get_rag_messages(self, question: str) -> list:
        """构建 RAG 消息列表（供 ask 和 ask_stream 共用）"""
        if not self.vectorstore:
            return None

        docs = self.vectorstore.similarity_search(question, k=5)
        context = "\n\n---\n\n".join([
            f"[文档{i+1}] {doc.page_content}" for i, doc in enumerate(docs)
        ])

        return [
            {"role": "system", "content": f"""你是一个专业的学习助手，基于提供的文档内容回答问题。

请遵循以下原则：
1. 仅基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，诚实告知用户
3. 回答要准确、简洁、有条理
4. 可以引用文档中的关键段落支持你的回答
5. 用中文回答

参考文档内容：
{context}"""},
            {"role": "user", "content": question}
        ]

    def ask_stream(self, question: str):
        """流式问答（生成器，逐块 yield 文本）"""
        if not self.current_document:
            yield "⚠️ 请先加载文档！使用 load_document() 方法加载PDF文档。"
            return

        if self._rag_chain is None:
            yield "⚠️ RAG 链尚未初始化，请重新加载文档。"
            return

        self.memory.add(
            content=f"提问: {question}",
            memory_type="working", importance=0.6,
            session_id=self.session_id
        )

        messages = self._get_rag_messages(question)
        if messages is None:
            yield "⚠️ 向量存储未初始化。"
            return

        try:
            full_response = []
            for chunk in self.llm.stream(messages):
                chunk_text = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response.append(chunk_text)
                yield chunk_text

            # 流式结束后非精确估算 token（中文约 1.5 chars/token）
            total_chars = sum(len(t) for t in full_response)
            estimated_output = max(1, int(total_chars / 1.5))
            estimated_input = max(1, int(len(question) / 1.5) + int(sum(len(m['content']) for m in messages) / 3))
            self.token_usage["prompt_tokens"] += estimated_input
            self.token_usage["completion_tokens"] += estimated_output
            self.token_usage["total_tokens"] += estimated_input + estimated_output
            self.token_usage["calls"] += 1

        except Exception as e:
            yield f"\n\n生成回答时出错: {str(e)}"

        self.memory.add(
            content=f"关于'{question[:30]}...'的学习",
            memory_type="episodic", importance=0.7,
            event_type="qa_interaction", session_id=self.session_id
        )
        self.stats["questions_asked"] += 1

    def ask(self, question: str, use_advanced_search: bool = True) -> str:
        """向已加载的文档提问（RAG 问答）"""
        if not self.current_document:
            return "⚠️ 请先加载文档！使用 load_document() 方法加载PDF文档。"

        if self._rag_chain is None:
            return "⚠️ RAG 链尚未初始化，请重新加载文档。"

        self.memory.add(
            content=f"提问: {question}",
            memory_type="working",
            importance=0.6,
            session_id=self.session_id
        )

        try:
            answer, usage = self._rag_chain.invoke({"question": question})
            self._record_tokens(usage)
        except Exception as e:
            answer = f"生成回答时出错: {str(e)}"

        self.memory.add(
            content=f"关于'{question[:30]}...'的学习",
            memory_type="episodic",
            importance=0.7,
            event_type="qa_interaction",
            session_id=self.session_id
        )

        self.stats["questions_asked"] += 1
        return answer

    def _record_tokens(self, usage: Dict):
        """累计 LLM 调用 token 用量"""
        if not usage:
            return
        self.token_usage["prompt_tokens"] += usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
        self.token_usage["completion_tokens"] += usage.get("output_tokens", 0) or usage.get("completion_tokens", 0)
        self.token_usage["total_tokens"] += usage.get("total_tokens", 0)
        self.token_usage["calls"] += 1

    # ======================== 学习笔记 ========================

    def add_note(self, content: str, concept: Optional[str] = None):
        """添加学习笔记"""
        self.memory.add(
            content=content,
            memory_type="episodic",
            importance=0.8,
            concept=concept or "general",
            session_id=self.session_id
        )

        self.stats["concepts_learned"] += 1

    # ======================== 学习回顾 ========================

    def recall(self, query: str, limit: int = 5) -> str:
        """回顾学习历程"""
        if not self.memory._memories:
            return "📭 暂无学习记录。开始提问或添加笔记来积累学习历程吧！"

        result = self.memory.search(query, limit)
        return result

    # ======================== 统计与报告 ========================

    def get_stats(self) -> Dict[str, Any]:
        """获取当前会话的学习统计"""
        duration = (datetime.now() - self.stats["session_start"]).total_seconds()

        return {
            "会话时长": f"{duration:.0f}秒",
            "加载文档": self.stats["documents_loaded"],
            "提问次数": self.stats["questions_asked"],
            "学习笔记": self.stats["concepts_learned"],
            "当前文档": self.current_document or "未加载",
            "使用模型": self.model_name,
            "总记忆数": len(self.memory._memories),
            "框架版本": "LangChain",
            "本次会话累计": f"输入 {self.token_usage['prompt_tokens']} / 输出 {self.token_usage['completion_tokens']}",
            "LLM 调用次数": self.token_usage["calls"],
        }

    def generate_report(self, save_to_file: bool = True) -> Dict[str, Any]:
        """生成学习报告"""
        memory_summary = self.memory.summary(limit=10)

        rag_stats = {
            "has_vectorstore": self.vectorstore is not None,
            "current_document": self.current_document,
            "chunks_loaded": self._chunk_count
        } if self.vectorstore else {"has_vectorstore": False}

        duration = (datetime.now() - self.stats["session_start"]).total_seconds()

        report = {
            "framework": "LangChain",
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "start_time": self.stats["session_start"].isoformat(),
                "duration_seconds": duration
            },
            "learning_metrics": {
                "documents_loaded": self.stats["documents_loaded"],
                "questions_asked": self.stats["questions_asked"],
                "concepts_learned": self.stats["concepts_learned"],
                "total_memories": len(self.memory._memories)
            },
            "memory_summary": memory_summary,
            "rag_status": rag_stats
        }

        if save_to_file:
            report_file = f"learning_report_langchain_{self.session_id}.json"
            try:
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
                report["report_file"] = report_file
            except Exception as e:
                report["save_error"] = str(e)

        return report


# ======================== 测试入口 ========================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LangChain 版 PDFLearningAssistant 测试")
    print("=" * 60)

    assistant = PDFLearningAssistant(user_id="test_user")
    print(f"✅ 助手已初始化 (session: {assistant.session_id})")
