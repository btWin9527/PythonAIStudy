<script setup lang="ts">
import { ref, nextTick, watch, onMounted, inject } from 'vue'
import { useChat } from '@ai-sdk/vue'
import { api } from '../api'

const chatContainer = ref<HTMLElement | null>(null)
const initStatus = ref('⏳ 正在连接服务器...')

// Token 栏刷新：对话完成后通知 TokenBar
const refreshToken = inject<() => void>('refreshToken', () => {})

// ---- @ai-sdk/vue useChat ----
const {
  messages,
  input,
  handleSubmit,
  isLoading,
  setMessages,
  error,
  reload,
  stop,
} = useChat({
  api: '/api/ai-chat',
  onFinish: () => refreshToken(),   // 对话完成 → 刷新 Token 栏
  onError: (err) => {
    console.error('[useChat]', err)
  },
})

// 自动滚动到底部
watch(messages, () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}, { deep: true })

// 页面加载：初始化 + 恢复历史
onMounted(async () => {
  try {
    const res = await api.init()
    initStatus.value = `✅ ${res.message}${res.document ? ` (文档: ${res.document})` : ''}`
    if (res.history?.length) {
      const msgs: { id: string; role: string; content: string }[] = []
      res.history.forEach((pair: any, idx: number) => {
        msgs.push({
          id: `hist-u-${idx}`,
          role: 'user',
          content: pair.user,
        })
        msgs.push({
          id: `hist-a-${idx}`,
          role: 'assistant',
          content: pair.assistant,
        })
      })
      setMessages(msgs)
    }
  } catch {
    initStatus.value = '❌ 连接服务器失败'
  }
})

// 自定义提交
function onSubmit(e: Event) {
  handleSubmit(e)
}

// 清空
async function handleClear() {
  await api.clearHistory()
  setMessages([])
}

const examples = [
  '有哪些矿山类型？',
  '地下矿山有哪些照片类型？',
  '我之前学过什么内容？',
]
</script>

<template>
  <div class="chat-view">
    <!-- 初始化状态 -->
    <div v-if="initStatus" class="init-banner">{{ initStatus }}</div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-banner">⚠️ {{ error.message }}</div>

    <!-- 对话区域 -->
    <div ref="chatContainer" class="chat-messages">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">💬</div>
        <h3>开始提问</h3>
        <p>向已加载的文档提问，或回顾学习历程</p>
        <div class="examples">
          <button
            v-for="ex in examples"
            :key="ex"
            class="example-chip"
            @click="input = ex; handleSubmit()"
          >{{ ex }}</button>
        </div>
      </div>

      <div
        v-for="msg in messages"
        :key="msg.id"
        :class="['message', msg.role]"
      >
        <div class="message-avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="message-bubble">
          <!-- @ai-sdk/vue 流式光标 -->
          <span
            v-if="msg.role === 'assistant' && isLoading && msg.id === messages[messages.length - 1]?.id"
            class="streaming-cursor"
          ></span>
          <div class="message-text" v-text="msg.content"></div>
        </div>
      </div>

      <div v-if="isLoading" class="streaming-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>

    <!-- 输入区域 -->
    <form class="chat-input-area" @submit="onSubmit">
      <div class="input-row">
        <input
          v-model="input"
          class="chat-input"
          placeholder="输入问题，例如：有什么照片类型？"
          :disabled="isLoading"
        />
        <button
          class="send-btn"
          type="submit"
          :disabled="!input.trim() || isLoading"
        >
          {{ isLoading ? '...' : '发送' }}
        </button>
        <button
          type="button"
          class="clear-btn"
          @click="handleClear"
          :disabled="isLoading"
        >
          清空
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e293b;
}
.init-banner {
  padding: 10px 20px;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  font-size: 13px;
  border-bottom: 1px solid rgba(16, 185, 129, 0.15);
}
.error-banner {
  padding: 10px 20px;
  background: rgba(239, 68, 68, 0.1);
  color: #fca5a5;
  font-size: 13px;
  border-bottom: 1px solid rgba(239, 68, 68, 0.15);
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state h3 { color: #94a3b8; margin: 0 0 6px; font-size: 18px; }
.empty-state p { color: #64748b; margin: 0 0 16px; font-size: 14px; }
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.example-chip {
  padding: 8px 16px;
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 20px;
  color: #a5b4fc;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
  border: none;
  font-family: inherit;
}
.example-chip:hover {
  background: rgba(99, 102, 241, 0.2);
}
.message {
  display: flex;
  gap: 10px;
  max-width: 85%;
}
.message.user {
  margin-left: auto;
  flex-direction: row-reverse;
}
.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: rgba(255,255,255,0.05);
  flex-shrink: 0;
}
.message-bubble {
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.65;
  position: relative;
}
.message.user .message-bubble {
  background: #6366f1;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message.assistant .message-bubble {
  background: #334155;
  color: #e2e8f0;
  border-bottom-left-radius: 4px;
}
.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}
.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: #818cf8;
  margin-right: 2px;
  vertical-align: text-bottom;
  animation: blink 0.8s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.streaming-indicator {
  display: flex;
  gap: 4px;
  padding-left: 46px;
}
.streaming-indicator .dot {
  width: 6px;
  height: 6px;
  background: #64748b;
  border-radius: 50%;
  animation: bounce 1.4s infinite;
}
.streaming-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.streaming-indicator .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}
.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,0.06);
  background: #0f172a;
}
.input-row {
  display: flex;
  gap: 8px;
}
.chat-input {
  flex: 1;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  background: #1e293b;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.chat-input:focus {
  border-color: #6366f1;
}
.chat-input::placeholder {
  color: #475569;
}
.send-btn {
  padding: 12px 24px;
  border-radius: 12px;
  border: none;
  background: #6366f1;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.send-btn:hover:not(:disabled) { background: #4f46e5; }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.clear-btn {
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}
.clear-btn:hover:not(:disabled) { color: #e2e8f0; border-color: rgba(255,255,255,0.15); }
.clear-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
