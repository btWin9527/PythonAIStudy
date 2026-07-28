<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api'

const initStatus = ref('⏳ 正在初始化助手...')
const pdfFile = ref<File | null>(null)
const uploadStatus = ref('')
const uploading = ref(false)
const document = ref('')

onMounted(async () => {
  try {
    const res = await api.init()
    initStatus.value = `✅ 助手已就绪`
    document.value = res.document || ''
  } catch {
    initStatus.value = '❌ 初始化失败'
  }
})

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  pdfFile.value = input.files?.[0] || null
}

async function uploadPdf() {
  if (!pdfFile.value) {
    uploadStatus.value = '❌ 请选择 PDF 文件'
    return
  }
  uploading.value = true
  uploadStatus.value = '⏳ 上传并加载中...'
  try {
    const res = await api.uploadPdf(pdfFile.value)
    if (res.success) {
      uploadStatus.value = `✅ ${res.message}`
      document.value = res.document || pdfFile.value.name
    } else {
      uploadStatus.value = `❌ ${res.message}`
    }
  } catch (e: any) {
    uploadStatus.value = `❌ ${e.message}`
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="home-view">
    <div class="page-header">
      <h2>🏠 开始使用</h2>
    </div>

    <div class="status-card">
      <div class="status-icon">✅</div>
      <div>
        <div class="status-title">助手状态</div>
        <div class="status-text">{{ initStatus }}</div>
      </div>
    </div>

    <div class="status-card" v-if="document">
      <div class="status-icon">📄</div>
      <div>
        <div class="status-title">当前文档</div>
        <div class="status-text">{{ document }}</div>
      </div>
    </div>

    <div class="upload-section">
      <h3>📄 上传 PDF 文档</h3>
      <p class="hint">页面加载后会自动初始化并加载默认文档，也可手动上传 PDF 替换。</p>
      <div class="upload-row">
        <input
          type="file"
          accept=".pdf"
          @change="onFileChange"
          class="file-input"
        />
        <button class="upload-btn" @click="uploadPdf" :disabled="!pdfFile || uploading">
          {{ uploading ? '加载中...' : '加载文档' }}
        </button>
      </div>
      <div v-if="uploadStatus" class="upload-status">{{ uploadStatus }}</div>
    </div>

    <div class="info-grid">
      <div class="info-card">
        <div class="info-icon">💡</div>
        <h4>智能问答</h4>
        <p>基于 RAG 技术，向文档提问获取精准回答</p>
      </div>
      <div class="info-card">
        <div class="info-icon">📝</div>
        <h4>学习笔记</h4>
        <p>记录学习心得，系统自动关联相关概念</p>
      </div>
      <div class="info-card">
        <div class="info-icon">🧠</div>
        <h4>学习回顾</h4>
        <p>输入"我之前学过什么"即可回顾学习历程</p>
      </div>
      <div class="info-card">
        <div class="info-icon">📊</div>
        <h4>学习报告</h4>
        <p>自动生成学习报告，统计 Token 用量</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  padding: 32px;
  height: 100%;
  overflow-y: auto;
  background: #1e293b;
}
.page-header h2 {
  margin: 0 0 20px;
  color: #f1f5f9;
  font-size: 22px;
}
.status-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border-radius: 12px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 12px;
  max-width: 500px;
}
.status-icon { font-size: 24px; }
.status-title {
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 2px;
}
.status-text {
  color: #e2e8f0;
  font-size: 14px;
}
.upload-section {
  max-width: 500px;
  margin-top: 24px;
  padding: 20px;
  border-radius: 12px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.06);
}
.upload-section h3 {
  margin: 0 0 6px;
  color: #f1f5f9;
  font-size: 16px;
}
.hint {
  color: #64748b;
  font-size: 13px;
  margin: 0 0 16px;
}
.upload-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.file-input {
  color: #94a3b8;
  font-size: 13px;
}
.upload-btn {
  padding: 10px 20px;
  border-radius: 10px;
  border: none;
  background: #6366f1;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.upload-btn:hover:not(:disabled) { background: #4f46e5; }
.upload-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.upload-status {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  font-size: 13px;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  max-width: 800px;
  margin-top: 32px;
}
.info-card {
  padding: 20px;
  border-radius: 12px;
  background: #0f172a;
  border: 1px solid rgba(255,255,255,0.06);
}
.info-icon { font-size: 24px; margin-bottom: 8px; }
.info-card h4 {
  margin: 0 0 6px;
  color: #f1f5f9;
  font-size: 15px;
}
.info-card p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
}
</style>
