#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文档问答助手 - Gradio Web UI

特性：
- 页面加载时自动初始化助手并加载默认 PDF
- 对话历史持久化（归一化格式保存，不受 Gradio 内部转换影响）
- 顶部显示 Token 用量 / 剩余 Token
- 4 个 Tab 页签：开始使用 / 智能问答 / 学习笔记 / 学习统计
"""

import sys
import os
import json

# 确保能导入父目录（ai_assistant/）中的模块
_AI_ASSISTANT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _AI_ASSISTANT_DIR)

from typing import List, Tuple
import gradio as gr

# ======================== 框架切换开关（改这一行即可切换） ========================
USE_LANGCHAIN = True
# ===============================================================================

DEFAULT_PDF_PATH = os.path.join(_AI_ASSISTANT_DIR, "pdf", "test.pdf")
_HISTORY_FILE = os.path.join(_AI_ASSISTANT_DIR, "_chat_history.json")


# ======================== 历史持久化（归一化格式） ========================

def _save_pairs(pairs: list):
    """保存对话历史（自有格式：[{user, assistant}, ...]）"""
    try:
        with open(_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(pairs, f, ensure_ascii=False)
    except Exception:
        pass


def _load_pairs() -> list:
    """加载对话历史（自有格式）"""
    try:
        if os.path.exists(_HISTORY_FILE):
            with open(_HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧格式（纯 message 列表）
                if data and isinstance(data[0], dict) and 'role' in data[0]:
                    return _convert_old_format(data)
                return data
    except Exception:
        pass
    return []


def _convert_old_format(messages: list) -> list:
    """兼容旧版 Gradio 格式 [role, content]，转换为 pairs"""
    pairs = []
    pending_user = None
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content', '')
        # content 可能是字符串或 [{text, type}]
        if isinstance(content, list) and content:
            content = content[0].get('text', '')
        if role == 'user':
            pending_user = content
        elif role == 'assistant' and pending_user is not None:
            pairs.append({"user": pending_user, "assistant": content})
            pending_user = None
    return pairs


def _pairs_to_gradio(pairs: list) -> list:
    """自有格式 → Gradio Chatbot 格式"""
    messages = []
    for pair in pairs:
        messages.append({"role": "user", "content": pair.get("user", "")})
        messages.append({"role": "assistant", "content": pair.get("assistant", "")})
    return messages


def _gradio_to_pairs(messages: list) -> list:
    """Gradio Chatbot 格式 → 自有格式（提取纯文本）"""
    pairs = []
    pending_user = None
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content', '')
        if isinstance(content, list) and content:
            content = content[0].get('text', '')
        if role == 'user':
            pending_user = content
        elif role == 'assistant' and pending_user is not None:
            pairs.append({"user": pending_user, "assistant": content})
            pending_user = None
    return pairs


# ======================== UI 构建 ========================

def create_gradio_ui(AssistantClass=None):
    """创建 Gradio Web 交互界面"""
    if AssistantClass is None:
        if USE_LANGCHAIN:
            from A_Assistant_langchain import PDFLearningAssistant as AssistantClass
        else:
            from A_Assistant import PDFLearningAssistant as AssistantClass

    assistant_state = {"assistant": None, "document_loaded": False}

    # ===== 事件处理函数 =====

    def auto_init() -> Tuple[str, str]:
        """页面加载时自动初始化助手并加载默认 PDF"""
        print("[auto_init] 正在初始化助手...")
        output = ["⏳ 正在初始化助手..."]

        assistant_state["assistant"] = AssistantClass(user_id="web_user")
        output.append("✅ 助手已初始化")

        if os.path.exists(DEFAULT_PDF_PATH):
            print(f"[auto_init] 加载文档: {DEFAULT_PDF_PATH}")
            result = assistant_state["assistant"].load_document(DEFAULT_PDF_PATH)
            if result["success"]:
                assistant_state["document_loaded"] = True
                output.append(f"📄 默认文档已加载: {result['document']}")
            else:
                output.append(f"⚠️ 文档加载失败: {result['message']}")
        else:
            output.append(f"⚠️ 默认文档未找到")

        pairs = _load_pairs()
        if pairs:
            output.append(f"💬 已恢复 {len(pairs)} 条历史对话")

        return "\n".join(output), _format_token_bar()

    def load_pdf(pdf_file) -> Tuple[str, str]:
        """加载用户上传的 PDF 文件"""
        if assistant_state["assistant"] is None:
            return "❌ 助手尚未就绪", _format_token_bar()
        if pdf_file is None:
            if os.path.exists(DEFAULT_PDF_PATH):
                result = assistant_state["assistant"].load_document(DEFAULT_PDF_PATH)
                if result["success"]:
                    assistant_state["document_loaded"] = True
                    return f"✅ {result['message']}", _format_token_bar()
            return "❌ 请上传PDF文件", _format_token_bar()

        result = assistant_state["assistant"].load_document(pdf_file.name)
        if result["success"]:
            assistant_state["document_loaded"] = True
            return f"✅ {result['message']}", _format_token_bar()
        return f"❌ {result['message']}", _format_token_bar()

    def chat(message: str, history: List) -> Tuple[str, List, str]:
        """聊天核心函数"""
        if assistant_state["assistant"] is None:
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": "⏳ 助手正在初始化..."})
            return "", history, _format_token_bar()

        if not message.strip():
            return "", history, _format_token_bar()

        if any(keyword in message for keyword in ["之前", "学过", "回顾", "历史", "记得"]):
            response = assistant_state["assistant"].recall(message)
            response = f"🧠 **学习回顾**\n\n{response}"
        else:
            response = assistant_state["assistant"].ask(message)
            response = f"💡 **回答**\n\n{response}"

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})
        _save_pairs(_gradio_to_pairs(history))  # 持久化（归一化格式）
        return "", history, _format_token_bar()

    def clear_history() -> Tuple[list, str, str]:
        """清空对话历史"""
        _save_pairs([])
        return [], "✅ 对话历史已清空", _format_token_bar()

    def add_note_ui(note_content: str, concept: str) -> Tuple[str, str]:
        """添加笔记"""
        if assistant_state["assistant"] is None:
            return "❌ 助手尚未就绪", _format_token_bar()
        if not note_content.strip():
            return "❌ 笔记内容不能为空", _format_token_bar()
        assistant_state["assistant"].add_note(note_content, concept or None)
        return f"✅ 笔记已保存: {note_content[:50]}...", _format_token_bar()

    def get_stats_ui() -> str:
        """获取学习统计"""
        if assistant_state["assistant"] is None:
            return "❌ 助手尚未就绪"
        stats = assistant_state["assistant"].get_stats()
        result = "📊 **学习统计**\n\n"
        for key, value in stats.items():
            result += f"- **{key}**: {value}\n"
        return result

    def generate_report_ui() -> str:
        """生成学习报告"""
        if assistant_state["assistant"] is None:
            return "❌ 助手尚未就绪"
        report = assistant_state["assistant"].generate_report(save_to_file=True)
        result = "✅ 学习报告已生成\n\n**会话信息**\n"
        result += f"- 会话时长: {report['session_info']['duration_seconds']:.0f}秒\n"
        result += f"- 加载文档: {report['learning_metrics']['documents_loaded']}\n"
        result += f"- 提问次数: {report['learning_metrics']['questions_asked']}\n"
        result += f"- 学习笔记: {report['learning_metrics']['concepts_learned']}\n"
        if "report_file" in report:
            result += f"\n💾 报告已保存至: {report['report_file']}"
        return result

    def _format_token_bar() -> str:
        """格式化 Token 用量条"""
        if assistant_state["assistant"] is None:
            return "⏳ 助手初始化中..."
        usage = assistant_state["assistant"].token_usage
        import config
        ctx = config.LLM_CONTEXT_WINDOW
        model = config.LLM_MODEL_ID
        remaining = max(0, ctx - usage["total_tokens"])
        return (
            f"📊 **Token 用量** | 模型 **{model}** | "
            f"剩余 **{remaining}** | "
            f"输入 {usage['prompt_tokens']} / 输出 {usage['completion_tokens']} | "
            f"调用 {usage['calls']} 次"
        )

    # ============================== 新增：页面加载时恢复历史 ==============================
    def load_history_into_chatbot() -> list:
        """从磁盘 JSON 文件恢复对话历史，推送到 Chatbot"""
        pairs = _load_pairs()
        return _pairs_to_gradio(pairs)
    # ====================================================================================

    # ===== 构建 Gradio 界面 =====

    with gr.Blocks(title="智能文档问答助手") as demo:

        # ===== 页面标题 + Token 用量条 =====
        token_bar = gr.Markdown("⏳ 助手初始化中...")

        gr.Markdown("""
        # 📚 智能文档问答助手

        基于 LangChain 的智能文档问答系统，页面加载后自动初始化。
        - 📄 PDF 知识库构建（自动加载默认文档）
        - 💬 智能问答（RAG + DashScope qwen-max）
        - 📝 学习笔记记录
        - 🧠 学习历程回顾
        - 📊 学习报告生成
        """)

        # ===== Tab 1: 开始使用 =====
        with gr.Tab("🏠 开始使用"):
            init_output = gr.Textbox(
                label="初始化状态",
                value="⏳ 等待页面加载...",
                interactive=False
            )
            gr.Markdown("### 📄 加载PDF文档")
            gr.Markdown("> 💡 页面加载后会自动初始化并加载默认文档，也可手动上传PDF替换。")
            pdf_upload = gr.File(
                label="上传PDF文件（可选）",
                file_types=[".pdf"],
                type="filepath"
            )
            load_btn = gr.Button("加载文档", variant="primary")
            load_output = gr.Textbox(label="加载状态", interactive=False)
            load_btn.click(load_pdf, inputs=[pdf_upload], outputs=[load_output, token_bar])

        # ===== Tab 2: 智能问答 =====
        with gr.Tab("💬 智能问答"):
            gr.Markdown("### 向文档提问或回顾学习历程")
            chatbot = gr.Chatbot(
                label="对话历史",
                height=400
            )
            with gr.Row():
                msg_input = gr.Textbox(
                    label="输入问题",
                    placeholder="例如：有什么照片类型？ 或 我之前学过什么？",
                    scale=4
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)

            with gr.Row():
                clear_btn = gr.Button("清空历史", variant="secondary", size="sm")
                clear_output = gr.Textbox(value="", visible=False)

            gr.Examples(
                examples=[
                    "有哪些矿山类型？",
                    "地下矿山有哪些照片类型？",
                    "我之前学过什么内容？",
                    "回顾一下关于职称号的学习",
                ],
                inputs=msg_input
            )

            msg_input.submit(chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot, token_bar])
            send_btn.click(chat, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot, token_bar])
            clear_btn.click(clear_history, outputs=[chatbot, clear_output, token_bar])

        # ===== Tab 3: 学习笔记 =====
        with gr.Tab("📝 学习笔记"):
            gr.Markdown("### 记录学习心得和重要概念")
            note_content = gr.Textbox(label="笔记内容", placeholder="输入你的学习笔记...", lines=3)
            concept_input = gr.Textbox(label="相关概念（可选）", placeholder="例如：露天矿山, 尾矿库")
            note_btn = gr.Button("保存笔记", variant="primary")
            note_output = gr.Textbox(label="保存状态", interactive=False)
            note_btn.click(add_note_ui, inputs=[note_content, concept_input], outputs=[note_output, token_bar])

        # ===== Tab 4: 学习统计 =====
        with gr.Tab("📊 学习统计"):
            gr.Markdown("### 查看学习进度和统计信息")
            stats_btn = gr.Button("刷新统计", variant="primary")
            stats_output = gr.Markdown()
            stats_btn.click(get_stats_ui, outputs=[stats_output])
            gr.Markdown("### 生成学习报告")
            report_btn = gr.Button("生成报告", variant="primary")
            report_output = gr.Textbox(label="报告状态", interactive=False)
            report_btn.click(generate_report_ui, outputs=[report_output])

        # ===== 页面加载时自动初始化（同时初始化 token 栏、恢复历史对话）=====
        demo.load(fn=auto_init, outputs=[init_output, token_bar])
        demo.load(fn=load_history_into_chatbot, outputs=[chatbot])

    return demo


def main():
    """主函数 - 启动 Gradio Web UI"""
    framework = "LangChain" if USE_LANGCHAIN else "HelloAgents"
    print("\n" + "=" * 60)
    print(f"智能文档问答助手 - {framework} 模式")
    print("=" * 60)
    print(f"默认文档: {DEFAULT_PDF_PATH}")
    print(f"对话历史: {_HISTORY_FILE}")
    print(f"访问地址: http://localhost:7860")
    print("正在启动Web界面（页面加载时自动初始化）...\n")

    demo = create_gradio_ui()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft()
    )


if __name__ == "__main__":
    main()