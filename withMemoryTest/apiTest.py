"""
================================================================================
  智能客服系统（带记忆） - API 测试客户端
================================================================================

  本文件用于测试 main.py 启动的智能客服服务接口（POST /v1/chat/completions）。
  与 basic 版本的区别：本版本支持携带 userId 和 conversationId，实现多轮对话
  上下文记忆（基于 SQLite 存储的历史对话）。

  整体流程分为以下几步：
  ─────────────────────────────────────────────
  第1步：导入依赖包
  第2步：配置请求参数（服务地址、请求头、流式开关、测试问题）
  第3步：构造请求体（兼容 OpenAI Chat Completions 规范，含用户/会话标识）
  第4步：发送请求并处理响应
         ├─ 流式模式：逐行读取 SSE 数据，实时输出每个片段
         └─ 非流式模式：一次性获取完整响应
  ─────────────────────────────────────────────

  使用方式：
    1. 先启动服务：python main.py
    2. 再运行测试：python apiTest.py
    3. 修改 stream_flag 切换流式/非流式输出体验
    4. 修改 input_text 测试不同的问题
    5. 修改 userId/conversationId 测试不同用户/会话的记忆隔离

================================================================================
"""


# ==============================================================================
# 第1步：导入依赖包
# ==============================================================================
#   requests —— HTTP 客户端库，用于发送 POST 请求到智能客服服务
#   json     —— JSON 序列化/反序列化，用于构造请求体和解析响应
#   logging  —— 日志模块，用于输出测试过程中的信息

import requests
import json
import logging


# ==============================================================================
# 第2步：配置请求参数
# ==============================================================================

# ── 2.1 日志配置 ──
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 2.2 服务地址与请求头 ──
# 对应 main.py 中 FastAPI 监听的地址和端口（默认 8012）
url = "http://localhost:8012/v1/chat/completions"
headers = {"Content-Type": "application/json"}  # 指定请求体为 JSON 格式

# ── 2.3 流式输出开关 ──
# True  → 流式输出（SSE），服务端逐行推送，客户端实时接收
# False → 非流式输出，服务端一次性返回完整结果
stream_flag = False

# ── 2.4 测试问题 ──
# 取消注释即可切换不同的测试场景，覆盖：
#   · 通用知识问答（LangChain是什么）
#   · 套餐咨询（有没有土豪套餐）
#   · 价格查询（这个套餐是多少钱）
#   · 套餐办理（办个200G的套餐）
#   · 上下文指代（就是刚刚问的那个套餐 —— 依赖历史记忆）
# input_text = "有没有土豪套餐"
# input_text = "这个套餐是多少钱"
# input_text = "办个200G的套餐"
# input_text = "这个套餐是多少钱"
# input_text = "就是刚刚问的那个套餐"
input_text = "LangChain是什么"


# ==============================================================================
# 第3步：构造请求体
# ==============================================================================
# 请求体结构兼容 OpenAI Chat Completions API 规范：
#   · messages       —— 对话消息列表，这里只发一条用户消息
#   · stream         —— 是否流式输出，与上面的 stream_flag 对应
#   · userId         —— 用户唯一标识，用于区分不同用户的历史记忆
#   · conversationId —— 会话唯一标识，用于区分同一用户的不同会话
#
# 与 basic 版本的核心区别：
#   main.py 会根据 userId + conversationId 从 SQLite 数据库中加载该用户/会话的
#   历史对话记录，并注入到 Prompt 中，实现"记住之前聊过什么"的效果。

data = {
    "messages": [{"role": "user", "content": input_text}],
    "stream": stream_flag,
    "userId": "123",
    "conversationId": "123"
}


# ==============================================================================
# 第4步：发送请求并处理响应
# ==============================================================================
# 根据 stream_flag 的值，走不同的响应处理逻辑

if stream_flag:
    # ======================================================================
    # 4A：流式响应处理
    # ======================================================================
    # 流式模式下，服务端通过 SSE（Server-Sent Events）逐行推送数据
    # 客户端使用 requests.post(stream=True) 逐行读取，实现实时输出
    #
    # 每个 SSE 片段的格式：
    #   {"id":"chatcmpl-xxx", "choices":[{"delta":{"content":"一行内容"}, "finish_reason":null}]}
    # 最后一个片段：
    #   {"id":"chatcmpl-xxx", "choices":[{"delta":{}, "finish_reason":"stop"}]}

    try:
        # stream=True 让 requests 不一次性下载全部内容，而是逐块读取
        with requests.post(url, stream=True, headers=headers, data=json.dumps(data)) as response:
            # iter_lines() 逐行迭代 SSE 数据流
            for line in response.iter_lines():
                if line:
                    # 第1步：解码字节流并去除 SSE 前缀 "data: "
                    json_str = line.decode('utf-8').strip("data: ")

                    # 第2步：跳过空字符串（SSE 协议中的心跳/空行）
                    if not json_str:
                        logger.info(f"收到空字符串，跳过...")
                        continue

                    # 第3步：校验是否为合法 JSON 格式
                    if json_str.startswith('{') and json_str.endswith('}'):
                        try:
                            data = json.loads(json_str)
                            # 第4步：判断是否为结束标记
                            if data['choices'][0]['finish_reason'] == "stop":
                                logger.info(f"接收JSON数据结束")
                            else:
                                # 第5步：输出当前片段的内容
                                # delta.content 是这一行推送的文本片段
                                logger.info(f"流式输出，响应内容是: {data['choices'][0]['delta']['content']}")
                        except json.JSONDecodeError as e:
                            logger.info(f"JSON解析错误: {e}")
                    else:
                        print(f"无效JSON格式: {json_str}")
    except Exception as e:
        print(f"Error occurred: {e}")

else:
    # ======================================================================
    # 4B：非流式响应处理
    # ======================================================================
    # 非流式模式下，服务端一次性返回完整的 JSON 结果
    # 响应结构：
    #   {"choices":[{"message":{"role":"assistant","content":"完整回复内容"}, "finish_reason":"stop"}]}

    # 发送 POST 请求，等待完整响应
    response = requests.post(url, headers=headers, data=json.dumps(data))

    # 从响应 JSON 中提取助手的回复内容
    # 路径：choices[0].message.content
    content = response.json()['choices'][0]['message']['content']
    logger.info(f"非流式输出，响应内容是: {content}\n")
