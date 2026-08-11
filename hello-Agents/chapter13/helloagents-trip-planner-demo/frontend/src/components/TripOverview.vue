<template>
  <div class="left-info">
    <a-card id="overview" :title="`${tripPlan.city}旅行计划`" :bordered="false" class="overview-card">
      <div class="overview-content">
        <div class="info-item">
          <span class="info-label">📅 日期:</span>
          <span class="info-value">{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">💡 建议:</span>
          <span class="info-value">{{ tripPlan.overall_suggestions }}</span>
        </div>
      </div>
    </a-card>

    <a-card v-if="tripPlan.budget" id="budget" title="💰 预算明细" :bordered="false" class="budget-card">
      <div class="budget-grid">
        <div class="budget-item">
          <div class="budget-label">景点门票</div>
          <div class="budget-value">¥{{ tripPlan.budget.total_attractions }}</div>
        </div>
        <div class="budget-item">
          <div class="budget-label">酒店住宿</div>
          <div class="budget-value">¥{{ tripPlan.budget.total_hotels }}</div>
        </div>
        <div class="budget-item">
          <div class="budget-label">餐饮费用</div>
          <div class="budget-value">¥{{ tripPlan.budget.total_meals }}</div>
        </div>
        <div class="budget-item">
          <div class="budget-label">交通费用</div>
          <div class="budget-value">¥{{ tripPlan.budget.total_transportation }}</div>
        </div>
      </div>
      <div class="budget-total">
        <span class="total-label">预估总费用</span>
        <span class="total-value">¥{{ tripPlan.budget.total }}</span>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import type { TripPlan } from '@/types'

defineProps<{
  tripPlan: TripPlan
}>()
</script>

<style scoped>
.left-info { flex: 0 0 400px; display: flex; flex-direction: column; gap: 20px; }
.overview-card { height: fit-content; }
.overview-content { display: flex; flex-direction: column; gap: 12px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 14px; font-weight: 600; color: #666; }
.info-value { font-size: 15px; color: #333; line-height: 1.6; }
.budget-card { height: fit-content; }
.budget-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 16px; }
.budget-item { text-align: center; padding: 12px; background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); border-radius: 8px; border: 1px solid #e8e8e8; }
.budget-label { font-size: 13px; color: #666; margin-bottom: 8px; }
.budget-value { font-size: 20px; font-weight: 700; color: #1890ff; }
.budget-total { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; color: white; }
.total-label { font-size: 16px; font-weight: 600; }
.total-value { font-size: 28px; font-weight: 700; }
</style>
