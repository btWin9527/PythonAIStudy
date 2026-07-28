<script setup lang="ts">
const emit = defineEmits<{
  (e: 'navigate', tab: string): void
}>()

const tabs = [
  { key: 'home',   label: '🏠 开始使用' },
  { key: 'chat',   label: '💬 智能问答' },
  { key: 'notes',  label: '📝 学习笔记' },
  { key: 'stats',  label: '📊 学习统计' },
]

defineProps<{ activeTab: string }>()
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="app-title">📚 智能文档<br/>问答助手</h1>
    </div>
    <nav class="sidebar-nav">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['nav-btn', { active: activeTab === tab.key }]"
        @click="emit('navigate', tab.key)"
      >
        <span class="nav-icon">{{ tab.label.slice(0, 2) }}</span>
        <span>{{ tab.label.slice(3) }}</span>
      </button>
    </nav>
    <div class="sidebar-footer">
      <p class="footer-text">基于 LangChain + DashScope</p>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
}
.sidebar-header {
  padding: 28px 20px 20px;
}
.app-title {
  color: #f1f5f9;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.5;
  margin: 0;
}
.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
}
.nav-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
  text-align: left;
}
.nav-btn:hover {
  background: rgba(255,255,255,0.06);
  color: #e2e8f0;
}
.nav-btn.active {
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  font-weight: 500;
}
.nav-icon {
  font-size: 18px;
}
.sidebar-footer {
  padding: 16px 20px;
}
.footer-text {
  color: #475569;
  font-size: 11px;
  margin: 0;
}
</style>
