<template>
  <a-collapse-panel :key="dayIndex" :id="`day-${dayIndex}`">
    <template #header>
      <div class="day-header">
        <span class="day-title">第{{ day.day_index + 1 }}天</span>
        <span class="day-date">{{ day.date }}</span>
      </div>
    </template>

    <div class="day-info">
      <div class="info-row">
        <span class="label">📝 行程描述:</span>
        <span class="value">{{ day.description }}</span>
      </div>
      <div class="info-row">
        <span class="label">🚗 交通方式:</span>
        <span class="value">{{ day.transportation }}</span>
      </div>
      <div class="info-row">
        <span class="label">🏨 住宿:</span>
        <span class="value">{{ day.accommodation }}</span>
      </div>
    </div>

    <a-divider orientation="left">🎯 景点安排</a-divider>
    <a-list :data-source="day.attractions" :grid="{ gutter: 16, column: 2 }">
      <template #renderItem="{ item, index }">
        <a-list-item>
          <AttractionCard
            :item="item"
            :index="index"
            :editMode="editMode"
            :isLast="index === day.attractions.length - 1"
            :imageSrc="getImage(item.name, index)"
            @moveUp="$emit('moveAttraction', day.day_index, index, 'up')"
            @moveDown="$emit('moveAttraction', day.day_index, index, 'down')"
            @delete="$emit('deleteAttraction', day.day_index, index)"
          />
        </a-list-item>
      </template>
    </a-list>

    <a-divider v-if="day.hotel" orientation="left">🏨 住宿推荐</a-divider>
    <a-card v-if="day.hotel" size="small" class="hotel-card">
      <template #title><span class="hotel-title">{{ day.hotel.name }}</span></template>
      <a-descriptions :column="2" size="small">
        <a-descriptions-item label="地址">{{ day.hotel.address }}</a-descriptions-item>
        <a-descriptions-item label="类型">{{ day.hotel.type }}</a-descriptions-item>
        <a-descriptions-item label="价格范围">{{ day.hotel.price_range }}</a-descriptions-item>
        <a-descriptions-item label="评分">{{ day.hotel.rating }}⭐</a-descriptions-item>
        <a-descriptions-item label="距离" :span="2">{{ day.hotel.distance }}</a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-divider orientation="left">🍽️ 餐饮安排</a-divider>
    <a-descriptions :column="1" bordered size="small">
      <a-descriptions-item v-for="meal in day.meals" :key="meal.type" :label="mealLabel(meal.type)">
        {{ meal.name }}<span v-if="meal.description"> - {{ meal.description }}</span>
      </a-descriptions-item>
    </a-descriptions>
  </a-collapse-panel>
</template>

<script setup lang="ts">
import AttractionCard from './AttractionCard.vue'
import { createPlaceholderImage } from '@/utils/image'
import { getMealLabel } from '@/utils/map'

const props = defineProps<{
  day: any
  dayIndex: number
  editMode: boolean
  attractionPhotos: Record<string, string>
}>()

defineEmits<{
  moveAttraction: [dayIndex: number, attrIndex: number, direction: 'up' | 'down']
  deleteAttraction: [dayIndex: number, attrIndex: number]
}>()

function getImage(name: string, index: number): string {
  return props.attractionPhotos[name] || createPlaceholderImage(name, index)
}

function mealLabel(type: string): string {
  return getMealLabel(type)
}
</script>

<style scoped>
.day-header { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.day-title { font-size: 18px; font-weight: 600; color: #333; }
.day-date { font-size: 14px; color: #999; }
.day-info { margin-bottom: 20px; padding: 16px; background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%); border-radius: 8px; border: 1px solid #e8e8e8; }
.info-row { display: flex; gap: 12px; margin-bottom: 8px; }
.info-row:last-child { margin-bottom: 0; }
.info-row .label { font-weight: 600; color: #666; min-width: 100px; }
.info-row .value { color: #333; flex: 1; }
.hotel-card { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border: none !important; }
.hotel-card :deep(.ant-card-head) { background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%); }
.hotel-title { color: white !important; font-weight: 600; }
</style>
