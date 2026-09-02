<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { LoadingOutlined } from '@ant-design/icons-vue'
import { generateVolunteerPlan, getProvinces } from '@/services/api'
import type { VolunteerPlan, VolunteerProfile } from '@/types'
import { SUBJECT_CATEGORY_OPTIONS } from '@/types'

const router = useRouter()

// 表单数据
const form = reactive({
  province: '',
  score: null as number | null,
  targetMajor: '',
  subjectCategory: '' as '' | 'science' | 'arts' | 'art'
})

// 省份列表
const provinces = ref<string[]>([])
const loadingProvinces = ref(false)

// 生成状态
const isGenerating = ref(false)
const generatingStep = ref(0)
const generatingMessage = ref('')

// 生成步骤提示
const generatingSteps = [
  '正在连接AI智能体...',
  '联网搜索近3年分数线数据...',
  '分析院校录取概率...',
  '生成冲/稳/保方案...',
  '正在整理最终结果...'
]

// 分数验证
function validateScore(_rule: any, value: number | null) {
  if (!value) {
    return Promise.reject('请输入高考分数')
  }
  if (value < 100 || value > 750) {
    return Promise.reject('分数必须在100-750之间')
  }
  return Promise.resolve()
}

const formRules = {
  province: [{ required: true, message: '请选择报考省份', trigger: 'change' }],
  score: [{ validator: validateScore, trigger: 'blur' }],
  subjectCategory: [{ required: true, message: '请选择报考类别', trigger: 'change' }]
}

// 加载省份
onMounted(async () => {
  loadingProvinces.value = true
  try {
    const res = await getProvinces()
    provinces.value = res.data || []
  } catch {
    // 降级：硬编码省份列表
    provinces.value = [
      '北京', '天津', '上海', '重庆',
      '河北', '山西', '辽宁', '吉林', '黑龙江',
      '江苏', '浙江', '安徽', '福建', '江西', '山东',
      '河南', '湖北', '湖南', '广东', '海南',
      '四川', '贵州', '云南', '陕西', '甘肃', '青海',
      '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'
    ]
  } finally {
    loadingProvinces.value = false
  }
})

// 启动生成动画
function startGeneratingAnimation() {
  isGenerating.value = true
  generatingStep.value = 0
  generatingMessage.value = generatingSteps[0]

  const timer = setInterval(() => {
    if (generatingStep.value < generatingSteps.length - 1) {
      generatingStep.value++
      generatingMessage.value = generatingSteps[generatingStep.value]
    }
  }, 4000)

  return timer
}

// 停止生成动画
function stopGeneratingAnimation(timer: ReturnType<typeof setInterval> | undefined) {
  isGenerating.value = false
  if (timer) clearInterval(timer)
}

// 获取报考类别中文名
function getSubjectLabel(category: string): string {
  const opt = SUBJECT_CATEGORY_OPTIONS.find(o => o.value === category)
  return opt ? `${opt.label}(${opt.subLabel})` : category
}

// 提交表单
async function handleSubmit() {
  if (!form.province || !form.score || !form.subjectCategory) {
    message.warning('请完整填写省份、分数和报考类别')
    return
  }

  const timer = startGeneratingAnimation()

  try {
    const response = await generateVolunteerPlan({
      province: form.province,
      score: form.score,
      target_major: form.targetMajor.trim(),
      subject_category: form.subjectCategory
    })

    if (!response.success || !response.data) {
      throw new Error(response.message || '生成方案失败')
    }

    // 保存到 sessionStorage
    const plan: VolunteerPlan = response.data
    const profile: VolunteerProfile = {
      province: form.province,
      score: form.score,
      subjectCategory: form.subjectCategory,
      subjectLabel: getSubjectLabel(form.subjectCategory),
      targetMajor: form.targetMajor.trim()
    }

    sessionStorage.setItem('volunteerPlan', JSON.stringify(plan))
    sessionStorage.setItem('volunteerProfile', JSON.stringify(profile))

    stopGeneratingAnimation(timer)
    message.success('志愿方案生成成功！')

    // 跳转到结果页
    setTimeout(() => {
      router.push('/result')
    }, 500)

  } catch (error: any) {
    stopGeneratingAnimation(timer)
    message.error(error.message || '生成志愿方案失败，请稍后重试')
    console.error('生成失败:', error)
  }
}

// 重置表单
function handleReset() {
  form.province = ''
  form.score = null
  form.targetMajor = ''
  form.subjectCategory = ''
}
</script>

<template>
  <div class="home-page">
    <div class="background-decoration">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>

    <div class="content-wrapper">
      <!-- 头部 -->
      <div class="page-header">
        <h1 class="title">🎓 高考志愿填报助手</h1>
        <p class="subtitle">
          基于AI智能分析 · 联网搜索近3年分数线 · 精准生成冲稳保方案
        </p>
      </div>

      <!-- 表单卡片 -->
      <div class="form-card">
        <!-- 生成中遮罩 -->
        <div v-if="isGenerating" class="generating-overlay">
          <div class="generating-content">
            <LoadingOutlined class="spinner" />
            <h3>{{ generatingMessage }}</h3>
            <div class="step-progress">
              <div
                v-for="(_, index) in generatingSteps"
                :key="index"
                class="step-dot"
                :class="{ active: index <= generatingStep }"
              ></div>
            </div>
            <p class="tip">首次联网搜索可能需要 30-60 秒，请耐心等待...</p>
          </div>
        </div>

        <!-- 表单主体 -->
        <a-form :model="form" layout="vertical" @finish="handleSubmit">
          <!-- 步骤1 标题 -->
          <div class="section-header">
            <span class="step-number">01</span>
            <h2>输入你的高考信息</h2>
            <span class="section-tip">结果附官方原始链接</span>
          </div>

          <a-divider class="section-divider" />

          <!-- 省份选择 -->
          <a-form-item label="报考省份" name="province" :rules="formRules.province">
            <a-select
              v-model:value="form.province"
              size="large"
              placeholder="请选择报考省份"
              :loading="loadingProvinces"
              show-search
              :filter-option="(o: any, v: string) => o.toLowerCase().includes(v.toLowerCase())"
            >
              <a-select-option
                v-for="p in provinces"
                :key="p"
                :value="p"
              >{{ p }}</a-select-option>
            </a-select>
          </a-form-item>

          <!-- 分数输入 -->
          <a-form-item label="高考分数" name="score" :rules="formRules.score">
            <div class="score-input-wrapper">
              <a-input-number
                v-model:value="form.score"
                size="large"
                :min="100"
                :max="750"
                :step="1"
                placeholder="请输入高考分数"
                class="score-input"
              />
              <span class="score-unit">分</span>
            </div>
          </a-form-item>

          <!-- 意向专业 -->
          <a-form-item label="意向专业（可选）" name="targetMajor">
            <a-input
              v-model:value="form.targetMajor"
              size="large"
              placeholder="例如：会计、计算机科学与技术、临床医学...（留空则不限）"
              allow-clear
            />
          </a-form-item>

          <!-- 报考类别 -->
          <a-form-item label="报考类别" name="subjectCategory" :rules="formRules.subjectCategory">
            <div class="category-options">
              <button
                v-for="opt in SUBJECT_CATEGORY_OPTIONS"
                :key="opt.value"
                type="button"
                class="category-btn"
                :class="{ active: form.subjectCategory === opt.value }"
                @click="form.subjectCategory = opt.value"
              >
                <span class="category-label">{{ opt.label }}</span>
                <span class="category-sublabel">{{ opt.subLabel }}</span>
              </button>
            </div>
          </a-form-item>

          <!-- 提交按钮 -->
          <div class="submit-area">
            <a-button
              type="primary"
              size="large"
              html-type="submit"
              class="submit-btn"
              :loading="isGenerating"
              :disabled="isGenerating"
            >
              {{ isGenerating ? 'AI 正在分析中...' : '计算冲、稳、保最佳方案' }}
              <span v-if="!isGenerating" class="submit-arrow">→</span>
            </a-button>
            <a-button
              v-if="!isGenerating && (form.province || form.score || form.targetMajor || form.subjectCategory)"
              size="large"
              class="reset-btn"
              @click="handleReset"
            >
              重置
            </a-button>
          </div>

          <!-- 底部提示 -->
          <div class="form-footer">
            <p>没有官方原始链接的记录，不进入推荐结果</p>
            <div class="feature-tags">
              <span>🤖 AI智能</span>
              <span>🔍 联网搜索</span>
              <span>📊 近3年数据</span>
            </div>
          </div>
        </a-form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 40px 20px;
}

.background-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.1;
}

.shape-1 {
  width: 400px;
  height: 400px;
  background: #fff;
  top: -100px;
  right: -100px;
}

.shape-2 {
  width: 300px;
  height: 300px;
  background: #fff;
  bottom: -80px;
  left: -80px;
}

.shape-3 {
  width: 200px;
  height: 200px;
  background: #fff;
  top: 50%;
  left: 10%;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 600px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.title {
  font-size: 36px;
  color: #fff;
  margin: 0 0 10px;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.85);
  margin: 0;
}

.form-card {
  background: #fff;
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  position: relative;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.step-number {
  font-size: 22px;
  font-weight: 600;
  color: #667eea;
  opacity: 0.8;
}

.section-header h2 {
  font-size: 22px;
  color: #1a1a1a;
  margin: 0;
  flex: 1;
}

.section-tip {
  font-size: 13px;
  color: #999;
}

.section-divider {
  margin: 16px 0 24px;
}

/* 分数输入 */
.score-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.score-input :deep(.ant-input-number) {
  width: 100%;
  border: 2px solid #667eea !important;
  border-radius: 8px;
}

.score-unit {
  position: absolute;
  right: 16px;
  color: #999;
  font-size: 14px;
}

/* 报考类别按钮组 */
.category-options {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.category-btn {
  flex: 1;
  min-width: 120px;
  padding: 16px 20px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  background: #fafafa;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-family: inherit;
}

.category-btn:hover {
  border-color: #667eea;
  background: #f5f6ff;
}

.category-btn.active {
  border-color: #667eea;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.category-label {
  font-size: 18px;
  font-weight: 600;
}

.category-sublabel {
  font-size: 13px;
  opacity: 0.7;
}

.category-btn.active .category-sublabel {
  opacity: 0.85;
}

/* 提交按钮 */
.submit-area {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

.submit-btn {
  flex: 1;
  height: 52px;
  font-size: 17px;
  font-weight: 600;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.submit-btn:hover {
  opacity: 0.95;
  transform: translateY(-1px);
}

.submit-arrow {
  margin-left: 6px;
}

.reset-btn {
  height: 52px;
  border-radius: 12px;
}

/* 表单底部 */
.form-footer {
  margin-top: 24px;
  text-align: center;
}

.form-footer p {
  font-size: 13px;
  color: #bbb;
  margin: 0 0 12px;
}

.feature-tags {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.feature-tags span {
  font-size: 12px;
  color: #888;
  background: #f5f5f5;
  padding: 4px 12px;
  border-radius: 12px;
}

/* 生成中遮罩 */
.generating-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 20px;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.generating-content {
  text-align: center;
  padding: 40px;
}

.spinner {
  font-size: 48px;
  color: #667eea;
  margin-bottom: 24px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.generating-content h3 {
  font-size: 18px;
  color: #333;
  margin: 0 0 20px;
}

.step-progress {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}

.step-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #e8e8e8;
  transition: all 0.3s ease;
}

.step-dot.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transform: scale(1.2);
}

.tip {
  font-size: 13px;
  color: #999;
  margin: 0;
}

/* 响应式 */
@media (max-width: 640px) {
  .home-page {
    padding: 20px 12px;
  }

  .form-card {
    padding: 28px 20px;
  }

  .title {
    font-size: 28px;
  }

  .category-btn {
    min-width: 100px;
    padding: 12px 16px;
  }
}
</style>
