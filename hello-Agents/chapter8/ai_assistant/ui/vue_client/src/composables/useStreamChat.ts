/**
 * 流式聊天 Composable（打字机效果）
 *
 * - 基于 SSE + ReadableStream 实现
 * - 支持逐字/逐块渲染的打字机效果
 * - 替代 @ai-sdk/vue 的 useChat，提供更精细的 UI 控制
 *
 * 如果安装了 @ai-sdk/vue，可以替换为：
 *   import { useChat } from '@ai-sdk/vue'
 *   const { messages, input, handleSubmit, isLoading } = useChat({
 *     api: '/api/chat',
 *   })
 */

import { ref, computed } from 'vue'
import { streamChat } from '../api'

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

export function useStreamChat() {
  const messages = ref<Message[]>([])
  const isStreaming = ref(false)
  const currentStreamContent = ref('')

  const isLoading = computed(() => isStreaming.value)

  /** 发送消息并流式接收回复 */
  async function sendMessage(question: string) {
    if (!question.trim() || isStreaming.value) return

    // 添加用户消息
    messages.value.push({ role: 'user', content: question })

    // 添加空的 assistant 消息占位
    messages.value.push({ role: 'assistant', content: '' })
    const assistantIdx = messages.value.length - 1

    isStreaming.value = true
    currentStreamContent.value = ''

    try {
      for await (const chunk of streamChat(question)) {
        currentStreamContent.value += chunk
        messages.value[assistantIdx].content = currentStreamContent.value
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '未知错误'
      messages.value[assistantIdx].content = `❌ 请求失败: ${msg}`
    } finally {
      isStreaming.value = false
    }
  }

  /** 从接口加载历史消息 */
  function loadHistory(history: { user: string; assistant: string }[]) {
    for (const pair of history) {
      messages.value.push({ role: 'user', content: pair.user })
      messages.value.push({ role: 'assistant', content: pair.assistant })
    }
  }

  /** 清空消息 */
  function clear() {
    messages.value = []
    currentStreamContent.value = ''
  }

  return {
    messages,
    isStreaming,
    isLoading,
    currentStreamContent,
    sendMessage,
    loadHistory,
    clear,
  }
}
