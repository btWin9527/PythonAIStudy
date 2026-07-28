#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 链构建模块 - 负责检索增强生成管线的组装

职责单一：构建 LLM + 检索器 + Prompt 的 RAG 链 + 消息构建。
"""

from typing import Dict, List, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

try:
    from .constants import Role
except ImportError:
    from constants import Role

try:
    from . import config
except ImportError:
    import config

# ======================== System Prompt ========================

SYSTEM_PROMPT_BASE = """你是一个专业的学习助手，基于提供的文档内容回答问题。

请遵循以下原则：
1. 仅基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，诚实告知用户
3. 回答要准确、简洁、有条理
4. 可以引用文档中的关键段落支持你的回答
5. 用中文回答"""

SYSTEM_PROMPT_TEMPLATE = SYSTEM_PROMPT_BASE + """

参考文档内容：
{context}"""

SYSTEM_PROMPT_WITH_HISTORY = SYSTEM_PROMPT_BASE + """
6. 如果有历史对话上下文，请参考上下文理解用户的指代和延续性问题

参考文档内容：
{context}"""

# ======================== RAG 消息构建（ask / ask_stream 共用） ========================


def build_rag_messages(
    vectorstore,
    question: str,
    history_context: str = "",
) -> Optional[List[Dict]]:
    """
    构建 RAG 消息列表（检索 + 上下文 + Prompt）

    ask() 和 ask_stream() 共用本函数，确保行为一致。

    Args:
        vectorstore: FAISS 向量存储
        question: 用户问题
        history_context: 对话历史上下文文本（空字符串则不注入）

    Returns:
        messages 列表，供 LLM 调用；vectorstore 未初始化时返回 None
    """
    if not vectorstore:
        return None

    docs = vectorstore.similarity_search(question, k=config.RETRIEVAL_K)
    context = "\n\n---\n\n".join([
        f"[文档{i+1}] {doc.page_content}" for i, doc in enumerate(docs)
    ])

    template = SYSTEM_PROMPT_WITH_HISTORY if history_context else SYSTEM_PROMPT_TEMPLATE
    system_content = template.format(context=context)

    messages: List[Dict] = [{"role": Role.SYSTEM, "content": system_content}]

    if history_context:
        messages.append({
            "role": Role.SYSTEM,
            "content": f"历史对话上下文（用于理解指代和延续性问题）：\n{history_context}",
        })

    messages.append({"role": Role.USER, "content": question})
    return messages


# ======================== LCEL RAG 链（向后兼容） ========================


def build_rag_prompt() -> ChatPromptTemplate:
    """构建 RAG 问答的 ChatPromptTemplate"""
    return ChatPromptTemplate.from_messages([
        (Role.SYSTEM, SYSTEM_PROMPT_TEMPLATE),
        ("human", "{question}"),
    ])


def build_rag_prompt_with_history() -> ChatPromptTemplate:
    """构建带对话历史的 RAG 问答 ChatPromptTemplate"""
    return ChatPromptTemplate.from_messages([
        (Role.SYSTEM, SYSTEM_PROMPT_TEMPLATE),
        ("placeholder", "{conversation_history}"),
        ("human", "{question}"),
    ])


def build_retrieve_fn(vectorstore):
    """构建检索函数（闭包形式，捕获 vectorstore）"""

    def retrieve_and_format(inputs: Dict) -> Dict:
        question = inputs["question"]
        docs = vectorstore.similarity_search(question, k=5)
        context = "\n\n---\n\n".join([
            f"[文档{i+1}] {doc.page_content}" for i, doc in enumerate(docs)
        ])
        return {"context": context, "question": question}

    return retrieve_and_format


def extract_answer_and_usage(message) -> Tuple[str, Dict]:
    """从 AIMessage 提取 (content, usage_dict)"""
    usage = {}
    if hasattr(message, 'usage_metadata') and message.usage_metadata:
        usage = dict(message.usage_metadata)
    elif hasattr(message, 'response_metadata') and message.response_metadata:
        usage = message.response_metadata.get('token_usage', {})
    return message.content, usage


def build_rag_chain(llm, vectorstore):
    """构建 RAG 问答链，返回 (答案文本, usage) 元组"""
    retrieve_fn = build_retrieve_fn(vectorstore)
    prompt = build_rag_prompt()

    base_chain = retrieve_fn | prompt | llm
    return base_chain | RunnableLambda(extract_answer_and_usage)
