<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'

const noteContent = ref('')
const concept = ref('')
const status = ref('')
const saving = ref(false)

async function handleSave() {
  if (!noteContent.value.trim()) {
    status.value = '❌ 笔记内容不能为空'
    return
  }
  saving.value = true
  try {
    await api.addNote(noteContent.value, concept.value || undefined)
    status.value = `✅ 笔记已保存: ${noteContent.value.slice(0, 50)}...`
    noteContent.value = ''
    concept.value = ''
  } catch (e: any) {
    status.value = `❌ ${e.message}`
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="notes-view">
    <div class="page-header">
      <h2>📝 学习笔记</h2>
      <p>记录学习心得和重要概念</p>
    </div>

    <div class="notes-form">
      <div class="form-group">
        <label>笔记内容</label>
        <textarea
          v-model="noteContent"
          placeholder="输入你的学习笔记..."
          rows="4"
        ></textarea>
      </div>
      <div class="form-group">
        <label>相关概念（可选）</label>
        <input
          v-model="concept"
          placeholder="例如：露天矿山, 尾矿库"
        />
      </div>
      <button class="save-btn" @click="handleSave" :disabled="saving">
        {{ saving ? '保存中...' : '保存笔记' }}
      </button>
      <div v-if="status" class="status-msg">{{ status }}</div>
    </div>
  </div>
</template>

<style scoped>
.notes-view {
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
.notes-form {
  max-width: 600px;
}
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
}
.form-group textarea,
.form-group input {
  width: 100%;
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  background: #0f172a;
  color: #e2e8f0;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}
.form-group textarea {
  resize: vertical;
  font-family: inherit;
}
.form-group textarea:focus,
.form-group input:focus {
  border-color: #6366f1;
}
.save-btn {
  padding: 12px 28px;
  border-radius: 10px;
  border: none;
  background: #6366f1;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}
.save-btn:hover:not(:disabled) { background: #4f46e5; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.status-msg {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  font-size: 13px;
}
</style>
