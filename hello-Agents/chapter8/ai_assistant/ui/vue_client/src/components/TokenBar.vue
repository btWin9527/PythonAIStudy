<script setup lang="ts">
import { ref, onMounted, inject, watch } from 'vue'
import type { Ref } from 'vue'
import { api, type TokenInfo } from '../api'

const token = ref<TokenInfo | null>(null)

async function refreshToken() {
  try {
    token.value = await api.token()
  } catch {
    token.value = null
  }
}

// 页面加载时获取一次
onMounted(refreshToken)

// 对话完成后由 ChatView 触发刷新（无需轮询）
const refreshSignal = inject<Ref<number>>('refreshTokenSignal', ref(0))
watch(refreshSignal, () => {
  if (refreshSignal.value > 0) refreshToken()
})
</script>

<template>
  <div class="token-bar">
    <template v-if="token">
      <span class="token-item">
        <span class="label">模型</span>
        <span class="value highlight">{{ token.model }}</span>
      </span>
      <span class="token-divider">|</span>
      <span class="token-item">
        <span class="label">剩余</span>
        <span class="value">{{ token.remaining.toLocaleString() }}</span>
      </span>
      <span class="token-divider">|</span>
      <span class="token-item">
        <span class="label">输入</span>
        <span class="value">{{ token.prompt_tokens.toLocaleString() }}</span>
      </span>
      <span class="token-item">
        <span class="label">输出</span>
        <span class="value">{{ token.completion_tokens.toLocaleString() }}</span>
      </span>
      <span class="token-divider">|</span>
      <span class="token-item">
        <span class="label">调用</span>
        <span class="value">{{ token.calls }} 次</span>
      </span>
    </template>
    <span v-else class="loading">⏳ 连接中...</span>
  </div>
</template>

<style scoped>
.token-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 24px;
  background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
  color: #e0e7ff;
  font-size: 13px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.token-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.label {
  color: #a5b4fc;
  font-size: 11px;
}
.value {
  color: #e0e7ff;
  font-variant-numeric: tabular-nums;
}
.value.highlight {
  color: #c4b5fd;
  font-weight: 600;
}
.token-divider {
  color: rgba(255,255,255,0.15);
}
.loading {
  color: #a5b4fc;
}
</style>
