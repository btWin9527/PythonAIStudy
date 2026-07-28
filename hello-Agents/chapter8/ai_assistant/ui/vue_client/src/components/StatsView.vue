<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'

const stats = ref<Record<string, any>>({})
const reportMsg = ref('')
const loading = ref(false)

async function fetchStats() {
  loading.value = true
  try {
    stats.value = await api.stats()
  } catch {
    stats.value = {}
  } finally {
    loading.value = false
  }
}

async function generateReport() {
  reportMsg.value = '⏳ 生成中...'
  try {
    const report = await api.report()
    reportMsg.value = `✅ 报告已生成${report.report_file ? ` (${report.report_file})` : ''}`
  } catch (e: any) {
    reportMsg.value = `❌ ${e.message}`
  }
}

onMounted(fetchStats)
</script>

<template>
  <div class="stats-view">
    <div class="page-header">
      <h2>📊 学习统计</h2>
      <p>查看学习进度和统计信息</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="(value, key) in stats" :key="key">
        <div class="stat-label">{{ key }}</div>
        <div class="stat-value">{{ value }}</div>
      </div>
    </div>
    <p v-if="loading" class="loading-msg">加载中...</p>

    <!-- 报告区域 -->
    <div class="report-section">
      <button class="report-btn" @click="generateReport">生成学习报告</button>
      <div v-if="reportMsg" class="report-msg">{{ reportMsg }}</div>
    </div>
  </div>
</template>

<style scoped>
.stats-view {
  padding: 32px;
  height: 100%;
  overflow-y: auto;
  background: #1e293b;
}
.page-header h2 {
  margin: 0 0 4px;
  color: #f1f5f9;
  font-size: 22px;
}
.page-header p {
  margin: 0 0 24px;
  color: #64748b;
  font-size: 14px;
}
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  max-width: 800px;
}
.stat-card {
  padding: 18px;
  border-radius: 12px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.06);
}
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 6px;
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #e2e8f0;
  font-variant-numeric: tabular-nums;
}
.loading-msg {
  color: #64748b;
  font-size: 14px;
  margin-top: 16px;
}
.report-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.report-btn {
  padding: 12px 28px;
  border-radius: 10px;
  border: none;
  background: #6366f1;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.report-btn:hover { background: #4f46e5; }
.report-msg {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  font-size: 13px;
  max-width: 600px;
}
</style>
