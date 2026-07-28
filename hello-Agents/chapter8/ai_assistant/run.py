#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - 统一启动入口

Usage:
    python run.py          # 交互式选择模式
    python run.py py       # 直接启动 Gradio UI
    python run.py vue      # 直接启动 Vue UI（API + 前端）
"""

import sys
import os
import subprocess

_AI_ASSISTANT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AI_ASSISTANT_DIR)

PORT_VUE_API = 8000
PORT_GRADIO = 7860


def start_gradio():
    """启动 Gradio Web UI"""
    print("\n" + "=" * 60)
    print("  启动模式: Gradio Web UI")
    print("=" * 60)
    print(f"  访问地址: http://localhost:{PORT_GRADIO}")
    print("=" * 60 + "\n")

    from ui.gradio_ui import main
    main()


def start_vue():
    """启动 Vue 3 模式（FastAPI 后端）"""
    import uvicorn

    print("\n" + "=" * 60)
    print("  启动模式: Vue 3 UI")
    print("=" * 60)
    print(f"  API 服务:  http://localhost:{PORT_VUE_API}")
    print(f"  API 文档:  http://localhost:{PORT_VUE_API}/docs")
    print(f"  前端页面:  cd ui/vue_client && npm run dev")
    print("=" * 60 + "\n")

    uvicorn.run(
        "ui.vue_api:app",
        host="127.0.0.1",
        port=PORT_VUE_API,
        reload=True,
    )


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else None

    if mode == "py":
        start_gradio()
    elif mode == "vue":
        start_vue()
    else:
        print("\n" + "=" * 60)
        print("  智能文档问答助手 - 启动模式选择")
        print("=" * 60)
        print("  1) py   - Gradio Web UI（Python 原生界面）")
        print("  2) vue  - Vue 3 UI（API + 前端分离）")
        print("=" * 60)
        choice = input("\n  请选择模式 (1/2): ").strip()

        if choice == "1" or choice.lower() == "py":
            start_gradio()
        elif choice == "2" or choice.lower() == "vue":
            start_vue()
        else:
            print("无效选择，默认启动 Gradio UI")
            start_gradio()


if __name__ == "__main__":
    main()
