#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DashScope 嵌入适配器 - 实现 LangChain Embeddings 接口
"""

from typing import List

from langchain_core.embeddings import Embeddings

import dashscope
from dashscope import TextEmbedding

try:
    from ..config import EMBED_MODEL_NAME, EMBED_API_KEY
    from ..constants import EmbedTextType
except ImportError:
    from config import EMBED_MODEL_NAME, EMBED_API_KEY
    from constants import EmbedTextType


class DashScopeEmbeddings(Embeddings):
    """
    DashScope 原生嵌入 API 适配器（实现 LangChain Embeddings 接口）

    用途：将文本转换为向量，用于 FAISS 相似度搜索。
    """

    def __init__(self, model: str = "", api_key: str = ""):
        self.model = model or EMBED_MODEL_NAME
        dashscope.api_key = api_key or EMBED_API_KEY

    def embed_query(self, text: str) -> List[float]:
        """嵌入单条查询文本"""
        resp = TextEmbedding.call(model=self.model, input=text, text_type=EmbedTextType.QUERY)
        if resp.status_code != 200:
            raise RuntimeError(f"嵌入失败: {resp.message}")
        return resp.output["embeddings"][0]["embedding"]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档文本（每批最多 25 条）"""
        embeddings = []
        for i in range(0, len(texts), 25):
            batch = texts[i:i + 25]
            resp = TextEmbedding.call(model=self.model, input=batch, text_type=EmbedTextType.DOCUMENT)
            if resp.status_code != 200:
                raise RuntimeError(f"批量嵌入失败: {resp.message}")
            for item in resp.output["embeddings"]:
                embeddings.append(item["embedding"])
        return embeddings
