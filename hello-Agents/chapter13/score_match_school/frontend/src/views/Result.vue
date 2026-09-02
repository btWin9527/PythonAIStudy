<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import type { VolunteerPlan, VolunteerTier, SchoolMajor, VolunteerProfile, FilterState } from '@/types'
import { TIER_CONFIG, SCHOOL_TYPE_OPTIONS, SCHOOL_LEVEL_OPTIONS } from '@/types'
import { exportVolunteerAsImage, exportVolunteerAsPDF } from '@/utils/export'

const router = useRouter()

// 数据
const volunteerPlan = ref<VolunteerPlan | null>(null)
const volunteerProfile = reactive<VolunteerProfile>({
  province: '',
  score: 0,
  subjectCategory: '',
  subjectLabel: '',
  targetMajor: ''
})
const activeTier = ref<string>('chong')
const exportAreaRef = ref<HTMLElement | null>(null)

// 筛选条件
const filter = reactive<FilterState>({
  schoolType: '',
  schoolLevel: '',
  majorKeyword: '',
  minConfidence: 0
})

// ============ 生命周期 ============
onMounted(() => {
  const planData = sessionStorage.getItem('volunteerPlan')
  const profileData = sessionStorage.getItem('volunteerProfile')

  if (planData) {
    try {
      volunteerPlan.value = JSON.parse(planData)
    } catch {
      volunteerPlan.value = null
    }
  }
  if (profileData) {
    try {
      Object.assign(volunteerProfile, JSON.parse(profileData))
    } catch {}
  }
})

// ============ 筛选核心逻辑 ============
function matchSchool(school: SchoolMajor): boolean {
  if (school.confidence < filter.minConfidence) return false
  if (filter.majorKeyword && !school.major_name.includes(filter.majorKeyword)) return false
  if (filter.schoolType && school.school_type !== filter.schoolType) return false
  if (filter.schoolLevel && school.school_level !== filter.schoolLevel) return false
  return true
}

function getFilteredSchools(tier: VolunteerTier): SchoolMajor[] {
  return tier.schools.filter(matchSchool)
}

const filteredTotal = computed(() => {
  if (!volunteerPlan.value) return 0
  return volunteerPlan.value.tiers.reduce(
    (sum, tier) => sum + getFilteredSchools(tier).length, 0
  )
})

function resetFilter() {
  filter.schoolType = ''
  filter.schoolLevel = ''
  filter.majorKeyword = ''
  filter.minConfidence = 0
}

// ============ 辅助方法 ============
function getTierTabLabel(tier: VolunteerTier): string {
  const count = getFilteredSchools(tier).length
  return `${tier.tier_label} (${count})`
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 80) return '#52c41a'
  if (confidence >= 60) return '#1890ff'
  return '#fa8c16'
}

function goBack() {
  router.push('/')
}

// ============ 导出 ============
async function handleExportImage() {
  if (!volunteerPlan.value) return
  await exportVolunteerAsImage(
    volunteerPlan.value,
    volunteerProfile,
    () => message.loading({ content: '正在生成图片...', key: 'export', duration: 0 }),
    () => message.success({ content: '图片导出成功！', key: 'export' }),
    (msg: string) => message.error({ content: msg, key: 'export' })
  )
}

async function handleExportPDF() {
  if (!volunteerPlan.value) return
  await exportVolunteerAsPDF(
    volunteerPlan.value,
    volunteerProfile,
    () => message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 }),
    () => message.success({ content: 'PDF导出成功！', key: 'export' }),
    (msg: string) => message.error({ content: msg, key: 'export' })
  )
}
</script>

<template>
  <div class="result-page">
    <!-- 头部 -->
    <div class="page-header">
      <a-button class="back-btn" size="large" @click="goBack">← 返回首页</a-button>
      <div class="header-right">
        <a-dropdown>
          <template #overlay>
            <a-menu>
              <a-menu-item key="image" @click="handleExportImage">📷 导出为图片</a-menu-item>
              <a-menu-item key="pdf" @click="handleExportPDF">📄 导出为PDF</a-menu-item>
            </a-menu>
          </template>
          <a-button class="export-btn" size="large">
            📥 导出方案 <DownOutlined />
          </a-button>
        </a-dropdown>
      </div>
    </div>

    <div v-if="volunteerPlan" class="result-content" ref="exportAreaRef">
      <!-- 考生画像 + 策略 -->
      <a-card class="summary-card" :bordered="false">
        <div class="profile-meta">
          <span class="meta-chip province">📍 {{ volunteerProfile.province }}</span>
          <span class="meta-chip score">🎯 {{ volunteerProfile.score }} 分</span>
          <span class="meta-chip category">📚 {{ volunteerProfile.subjectLabel }}</span>
          <span
            v-if="volunteerProfile.targetMajor"
            class="meta-chip major"
          >💼 {{ volunteerProfile.targetMajor }}</span>
        </div>
        <div class="strategy-text">
          <span class="strategy-label">📋 总体策略</span>
          <p>{{ volunteerPlan.summary }}</p>
        </div>
      </a-card>

      <!-- 条件筛选 -->
      <a-card class="filter-card" title="🔍 条件筛选" :bordered="false" size="small">
        <div class="filter-row">
          <div class="filter-item">
            <span class="filter-label">院校类型</span>
            <a-select
              v-model:value="filter.schoolType"
              placeholder="全部"
              allow-clear
              class="filter-select"
            >
              <a-select-option
                v-for="t in SCHOOL_TYPE_OPTIONS"
                :key="t"
                :value="t"
              >{{ t }}</a-select-option>
            </a-select>
          </div>

          <div class="filter-item">
            <span class="filter-label">院校层级</span>
            <a-select
              v-model:value="filter.schoolLevel"
              placeholder="全部"
              allow-clear
              class="filter-select"
            >
              <a-select-option
                v-for="l in SCHOOL_LEVEL_OPTIONS"
                :key="l"
                :value="l"
              >{{ l }}</a-select-option>
            </a-select>
          </div>

          <div class="filter-item">
            <span class="filter-label">专业关键词</span>
            <a-input
              v-model:value="filter.majorKeyword"
              placeholder="搜索专业"
              allow-clear
              class="filter-input"
            >
              <template #prefix>🔎</template>
            </a-input>
          </div>

          <div class="filter-item wide">
            <span class="filter-label">信心度 ≥ {{ filter.minConfidence }}%</span>
            <a-slider
              v-model:value="filter.minConfidence"
              :min="0"
              :max="100"
              :marks="{ 0: '0%', 50: '50%', 100: '100%' }"
              tooltip-placement="bottom"
            />
          </div>
        </div>

        <div class="filter-actions">
          <a-button size="small" @click="resetFilter">重置筛选</a-button>
          <span class="filter-result">共 {{ filteredTotal }} 所院校符合条件</span>
        </div>
      </a-card>

      <!-- 冲/稳/保 Tabs -->
      <a-tabs v-model:activeKey="activeTier" size="large" class="tier-tabs">
        <a-tab-pane
          v-for="tier in volunteerPlan.tiers"
          :key="tier.tier_type"
          :tab="getTierTabLabel(tier)"
        >
          <div class="tier-header">
            <div class="tier-badge" :style="{ background: TIER_CONFIG[tier.tier_type]?.color || '#667eea' }">
              {{ TIER_CONFIG[tier.tier_type]?.icon || '' }} {{ tier.tier_label }}
            </div>
            <span class="tier-desc">{{ tier.description }}</span>
          </div>

          <div class="school-list">
            <div
              v-for="(school, index) in getFilteredSchools(tier)"
              :key="`${tier.tier_type}-${index}-${school.school_name}`"
              class="school-card"
            >
              <div class="school-index" :style="{ borderColor: TIER_CONFIG[tier.tier_type]?.color }">
                {{ index + 1 }}
              </div>
              <div class="school-body">
                <div class="school-main">
                  <h3 class="school-name">{{ school.school_name }}</h3>
                  <div class="school-tags">
                    <span class="tag major">{{ school.major_name }}</span>
                    <span v-if="school.reference_score" class="tag score">
                      参考线 {{ school.reference_score }}
                    </span>
                    <span v-if="school.school_type" class="tag type">{{ school.school_type }}</span>
                    <span v-if="school.school_level" class="tag level">{{ school.school_level }}</span>
                  </div>
                </div>
                <div class="school-reason">💡 {{ school.reason }}</div>
                <!-- 数据来源 -->
                <div
                  v-if="school.reference_sources && school.reference_sources.length > 0"
                  class="school-sources"
                >
                  <div class="sources-toggle" @click="($event.target as HTMLElement).nextElementSibling?.classList.toggle('hidden')">
                    📎 数据来源 ({{ school.reference_sources.length }})
                  </div>
                  <div class="sources-list hidden">
                    <a
                      v-for="(src, i) in school.reference_sources"
                      :key="i"
                      :href="src"
                      target="_blank"
                      rel="noopener"
                      class="source-link"
                    >{{ src }}</a>
                  </div>
                </div>
              </div>
              <div
                class="confidence-badge"
                :style="{ background: getConfidenceColor(school.confidence) }"
              >
                <span class="conf-num">{{ school.confidence }}</span>
                <span class="conf-unit">%</span>
              </div>
            </div>

            <a-empty
              v-if="getFilteredSchools(tier).length === 0"
              description="当前筛选条件下没有符合的院校"
              style="padding: 48px"
            />
          </div>
        </a-tab-pane>
      </a-tabs>

      <!-- 免责声明 -->
      <div v-if="volunteerPlan.disclaimer" class="disclaimer">
        ⚠️ {{ volunteerPlan.disclaimer }}
      </div>
    </div>

    <!-- 空状态 -->
    <a-empty
      v-else
      description="没有找到志愿方案数据"
      style="padding: 80px"
    >
      <a-button type="primary" @click="goBack">返回首页重新生成</a-button>
    </a-empty>
  </div>
</template>

<style scoped>
.result-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
  padding: 24px 20px 60px;
}

.page-header {
  max-width: 1100px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.back-btn {
  border-radius: 10px;
  border-color: #d9d9d9;
}

.back-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.export-btn {
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  font-weight: 500;
}

.result-content {
  max-width: 1100px;
  margin: 0 auto;
}

/* 画像卡 */
.summary-card {
  border-radius: 16px;
  margin-bottom: 20px;
}

.profile-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.meta-chip {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.meta-chip.province { background: #e6f4ff; color: #1677ff; }
.meta-chip.score { background: #fff7e6; color: #d46b08; }
.meta-chip.category { background: #f6ffed; color: #389e0d; }
.meta-chip.major { background: #f9f0ff; color: #722ed1; }

.strategy-label {
  font-weight: 600;
  color: #333;
}

.strategy-text p {
  margin: 8px 0 0;
  color: #555;
  line-height: 1.7;
}

/* 筛选卡 */
.filter-card {
  border-radius: 16px;
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-item {
  flex: 1;
  min-width: 180px;
}

.filter-item.wide {
  flex: 2;
  min-width: 260px;
}

.filter-label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
  font-weight: 500;
}

.filter-select :deep(.ant-select-selector) {
  border-radius: 8px;
}

.filter-input :deep(.ant-input) {
  border-radius: 8px;
}

.filter-actions {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px dashed #e8e8e8;
  padding-top: 12px;
}

.filter-result {
  font-size: 13px;
  color: #667eea;
  font-weight: 600;
}

/* Tabs */
.tier-tabs {
  background: #fff;
  border-radius: 16px;
  padding: 20px 28px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  margin-bottom: 20px;
}

.tier-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.tier-badge {
  padding: 4px 14px;
  border-radius: 20px;
  color: #fff;
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
}

.tier-desc {
  font-size: 13px;
  color: #888;
}

/* 学校卡 */
.school-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.school-card {
  display: flex;
  align-items: stretch;
  gap: 16px;
  padding: 18px 20px;
  background: #fafbfc;
  border-radius: 12px;
  border-left: 4px solid #667eea;
  transition: all 0.2s ease;
}

.school-card:hover {
  background: #f5f7ff;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
}

.school-index {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #666;
  font-size: 15px;
  flex-shrink: 0;
  align-self: center;
}

.school-body {
  flex: 1;
  min-width: 0;
}

.school-main {
  margin-bottom: 10px;
}

.school-name {
  font-size: 17px;
  color: #1a1a1a;
  margin: 0 0 8px;
  font-weight: 600;
}

.school-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tag {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}

.tag.major { background: #e6f4ff; color: #1677ff; }
.tag.score { background: #fff7e6; color: #d46b08; }
.tag.type { background: #f6ffed; color: #389e0d; }
.tag.level { background: #f9f0ff; color: #722ed1; }

.school-reason {
  font-size: 14px;
  color: #555;
  line-height: 1.6;
  margin-bottom: 8px;
}

.school-sources {
  font-size: 12px;
}

.sources-toggle {
  color: #888;
  cursor: pointer;
  font-size: 12px;
  user-select: none;
}

.sources-toggle:hover {
  color: #667eea;
}

.sources-list {
  margin-top: 6px;
  padding-left: 4px;
}

.sources-list.hidden {
  display: none;
}

.source-link {
  display: block;
  color: #1677ff;
  text-decoration: none;
  font-size: 12px;
  margin-bottom: 4px;
  word-break: break-all;
}

.source-link:hover {
  text-decoration: underline;
}

.confidence-badge {
  min-width: 64px;
  border-radius: 12px;
  padding: 6px 10px;
  text-align: center;
  color: #fff;
  flex-shrink: 0;
  align-self: center;
}

.conf-num {
  font-size: 22px;
  font-weight: 700;
  display: block;
  line-height: 1;
}

.conf-unit {
  font-size: 11px;
  opacity: 0.85;
}

/* 免责声明 */
.disclaimer {
  max-width: 1100px;
  margin: 0 auto;
  padding: 16px 24px;
  background: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: 12px;
  color: #ad6800;
  font-size: 13px;
  line-height: 1.7;
}

/* 响应式 */
@media (max-width: 768px) {
  .school-card {
    flex-wrap: wrap;
  }

  .confidence-badge {
    align-self: flex-start;
  }

  .tier-tabs {
    padding: 16px;
  }

  .tier-header {
    flex-wrap: wrap;
  }

  .filter-item {
    min-width: 100%;
  }
}
</style>
