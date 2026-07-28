#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Assistant 统一配置文件

所有环境变量、模型参数、路径配置集中管理。
支持通过 .env 文件覆盖默认值。
"""

import os

from dotenv import load_dotenv

# -------- 加载 .env --------
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()

# ======================== LLM 大模型配置 ========================

LLM_MODEL_ID = os.getenv("LLM_MODEL_ID", "qwen-max")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "32768"))

# ======================== Embedding 嵌入模型配置 ========================

EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "text-embedding-v3")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")

# ======================== 文档处理配置 ========================

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "5"))

# ======================== 对话上下文配置 ========================

MAX_CONVERSATION_TURNS = int(os.getenv("MAX_CONVERSATION_TURNS", "10"))

# ======================== 路径配置 ========================

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_CACHE_DIR = os.path.join(_BASE_DIR, "_faiss_cache")
