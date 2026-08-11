<template>
  <div class="result-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <a-button class="back-button" size="large" @click="goBack">← 返回首页</a-button>
      <a-space size="middle">
        <a-button v-if="!editMode" @click="toggleEditMode" type="default">✏️ 编辑行程</a-button>
        <a-button v-else @click="saveChanges" type="primary">💾 保存修改</a-button>
        <a-button v-if="editMode" @click="cancelEdit" type="default">❌ 取消编辑</a-button>
        <a-dropdown v-if="!editMode">
          <template #overlay>
            <a-menu>
              <a-menu-item key="image" @click="handleExportImage">📷 导出为图片</a-menu-item>
              <a-menu-item key="pdf" @click="handleExportPDF">📄 导出为PDF</a-menu-item>
            </a-menu>
          </template>
          <a-button type="default">📥 导出行程 <DownOutlined /></a-button>
        </a-dropdown>
      </a-space>
    </div>

    <div v-if="tripPlan" class="content-wrapper">
      <!-- 侧边导航 -->
      <div class="side-nav">
        <a-affix :offset-top="80">
          <a-menu mode="inline" :selected-keys="[activeSection]" @click="scrollToSection">
            <a-menu-item key="overview"><span>📋 行程概览</span></a-menu-item>
            <a-menu-item key="budget" v-if="tripPlan.budget"><span>💰 预算明细</span></a-menu-item>
            <a-menu-item key="map"><span>📍 景点地图</span></a-menu-item>
            <a-sub-menu key="days" title="📅 每日行程">
              <a-menu-item v-for="(day, index) in tripPlan.days" :key="`day-${index}`">
                第{{ day.day_index + 1 }}天
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item key="weather" v-if="tripPlan.weather_info?.length">
              <span>🌤️ 天气信息</span>
            </a-menu-item>
          </a-menu>
        </a-affix>
      </div>

      <!-- 主内容区 -->
      <div class="main-content">
        <div class="top-info-section">
          <TripOverview :tripPlan="tripPlan" />
          <div class="right-map">
            <TripMap
              ref="tripMapRef"
              :tripPlan="tripPlan"
              :editMode="editMode"
              :currentEditDayIndex="currentEditDayIndex"
            />
          </div>
        </div>

        <a-card title="📅 每日行程" :bordered="false" class="days-card">
          <a-collapse v-model:activeKey="activeDays" accordion>
            <TripDayPanel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :day="day"
              :dayIndex="index"
              :editMode="editMode"
              :attractionPhotos="attractionPhotos"
              @moveAttraction="moveAttraction"
              @deleteAttraction="deleteAttraction"
            />
          </a-collapse>
        </a-card>

        <WeatherCard :weatherInfo="tripPlan.weather_info" />
      </div>
    </div>

    <a-empty v-else description="没有找到旅行计划数据">
      <template #image><div style="font-size: 80px;">🗺️</div></template>
      <template #description><span style="color: #999;">暂无旅行计划数据,请先创建行程</span></template>
      <a-button type="primary" @click="goBack">返回首页创建行程</a-button>
    </a-empty>

    <a-back-top :visibility-height="300">
      <div class="back-top-button">↑</div>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import type { TripPlan } from '@/types'

import TripOverview from '@/components/TripOverview.vue'
import TripMap from '@/components/TripMap.vue'
import TripDayPanel from '@/components/TripDayPanel.vue'
import WeatherCard from '@/components/WeatherCard.vue'

import { loadAttractionPhotos } from '@/services/poiApi'
import { captureMapImage, fallbackCaptureMap } from '@/services/mapApi'
import { exportAsImage, exportAsPDF } from '@/utils/export'

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0])
const currentEditDayIndex = ref(0)

onMounted(async () => {
  const data = sessionStorage.getItem('tripPlan')
  if (data) {
    tripPlan.value = JSON.parse(data)
    attractionPhotos.value = await loadAttractionPhotos(tripPlan.value)
  }
})

// ===== 导航 =====
const goBack = () => router.push('/')
const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// ===== 编辑模式 =====
const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info('进入编辑模式:拖动标记修改位置,点击地图空白处新增景点')
}

const saveChanges = () => {
  editMode.value = false
  if (tripPlan.value) sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  message.success('修改已保存')
}

const cancelEdit = () => {
  if (originalPlan.value) tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  editMode.value = false
  message.info('已取消编辑')
}

const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return
  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning('每天至少需要保留一个景点')
    return
  }
  day.attractions.splice(attrIndex, 1)
  message.success('景点已删除')
}

const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return
  const attractions = tripPlan.value.days[dayIndex].attractions
  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

// ===== 导出 =====
const handleExportImage = async () => {
  if (!tripPlan.value) return
  const mapDataURL = await captureMapImage(tripPlan.value) || await fallbackCaptureMap()
  await exportAsImage(
    tripPlan.value,
    mapDataURL,
    (msg) => message.loading({ content: msg, key: 'export', duration: 0 }),
    (msg) => message.success({ content: msg, key: 'export' }),
    (msg) => message.error({ content: msg, key: 'export' })
  )
}

const handleExportPDF = async () => {
  if (!tripPlan.value) return
  const mapDataURL = await captureMapImage(tripPlan.value) || await fallbackCaptureMap()
  await exportAsPDF(
    tripPlan.value,
    mapDataURL,
    (msg) => message.loading({ content: msg, key: 'export', duration: 0 }),
    (msg) => message.success({ content: msg, key: 'export' }),
    (msg) => message.error({ content: msg, key: 'export' })
  )
}
</script>

<style src="../styles/result.css"></style>
