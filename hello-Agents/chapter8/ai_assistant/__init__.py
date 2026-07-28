#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - ai_assistant 模块

模块结构：
├── __init__.py                   # 包入口（本文件）
├── .env                          # 环境变量配置（LLM API密钥、数据库等）
├── A_Assistant.py                # HelloAgents 版本的 PDFLearningAssistant
├── A_Assistant_langchain.py      # LangChain 版本的 PDFLearningAssistant
├── pdf/
│   └── Happy-LLM-0727.pdf       # 默认文档（未上传时自动加载）
└── ui/
    ├── __init__.py
    └── gradio_ui.py              # Gradio Web UI（可切换 HelloAgents/LangChain）

使用方式：

    # 方式1: 代码调用
    from ai_assistant.A_Assistant import PDFLearningAssistant
    assistant = PDFLearningAssistant(user_id="my_user")
    assistant.load_document("path/to/doc.pdf")
    answer = assistant.ask("这个文档讲了什么？")

    # 方式2: 启动 Web UI
    cd ai_assistant && python ui/gradio_ui.py

    # 方式3: 切换 LangChain 版本
    from ai_assistant.A_Assistant_langchain import PDFLearningAssistant
"""

from .A_Assistant import PDFLearningAssistant as HelloAgentsAssistant
from .A_Assistant_langchain import PDFLearningAssistant as LangChainAssistant

__all__ = ["HelloAgentsAssistant", "LangChainAssistant"]
