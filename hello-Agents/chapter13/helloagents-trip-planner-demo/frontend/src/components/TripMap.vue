<template>
  <a-card id="map" title="📍 景点地图" :bordered="false" class="map-card">
    <div id="amap-container" class="amap-container"></div>
  </a-card>
</template>

<script setup lang="ts">
import { onMounted, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import type { TripPlan } from '@/types'

const props = defineProps<{
  tripPlan: TripPlan | null
  editMode: boolean
  currentEditDayIndex: number
}>()

const emit = defineEmits<{
  mapReady: [mapInstance: any, markers: any[], amapSDK: any]
}>()

let map: any = null
let allMarkers: any[] = []
let allPolylines: any[] = []
let mapEditHandler: any = null

onMounted(async () => {
  await initMap()
})

watch(() => props.editMode, (val) => {
  if (val) enableMapEdit()
  else disableMapEdit()
})

// ===== 初始化 =====
async function initMap() {
  try {
    const jsApiKey = (import.meta as any).env.VITE_AMAP_WEB_JS_KEY
    const securityJsCode = (import.meta as any).env.VITE_AMAP_SECURITY_JS_CODE

    if (!jsApiKey) { message.error('未配置 VITE_AMAP_WEB_JS_KEY'); return }

    if (securityJsCode) {
      ;(window as any)._AMapSecurityConfig = { securityJsCode }
    }

    const AMap = await AMapLoader.load({
      key: jsApiKey,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })

    const container = document.getElementById('amap-container')
    if (!container) throw new Error('地图容器不存在')
    if (container.clientWidth === 0 || container.clientHeight === 0) {
      await new Promise(resolve => setTimeout(resolve, 200))
    }

    map = new AMap.Map(container, {
      zoom: 12,
      center: [112.55086, 37.89028],
      viewMode: '2D',
      resizeEnable: true
    })

    addAttractionMarkers(AMap)

    setTimeout(() => { if (map) map.resize() }, 200)

    emit('mapReady', map, allMarkers, AMap)
    message.success('地图加载成功')
  } catch (error) {
    console.error('地图加载失败:', error)
    message.error('地图加载失败')
  }
}

// ===== 标记 =====
function addAttractionMarkers(AMap: any) {
  if (!props.tripPlan) return

  allMarkers = []
  const allAttractions: any[] = []

  props.tripPlan.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction: any, attrIndex: number) => {
      if (attraction.location?.longitude && attraction.location?.latitude) {
        allAttractions.push({ ...attraction, dayIndex, attrIndex })
      }
    })
  })

  allAttractions.forEach((attraction: any, index: number) => {
    const isEdit = props.editMode
    const labelColor = isEdit ? '#FF9800' : '#4CAF50'
    const labelText = `${index + 1}${isEdit ? '✎' : ''}`
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      draggable: isEdit,
      label: {
        content: `<div style="background: ${labelColor}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">${labelText}</div>`,
        offset: new AMap.Pixel(0, -30)
      }
    })
    ;(marker as any)._attractionRef = attraction

    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding: 10px;">
          <h4 style="margin:0 0 8px 0;">${attraction.name}</h4>
          <p style="margin:4px 0;"><strong>地址:</strong> ${attraction.address}</p>
          <p style="margin:4px 0;"><strong>游览时长:</strong> ${attraction.visit_duration}分钟</p>
          <p style="margin:4px 0;"><strong>描述:</strong> ${attraction.description}</p>
          <p style="margin:4px 0;color:#1890ff;"><strong>第${attraction.dayIndex + 1}天 景点${attraction.attrIndex + 1}</strong></p>
          ${isEdit ? '<p style="margin:4px 0;color:#FF5722;"><strong>拖动标记可修改位置</strong></p>' : ''}
        </div>`,
      offset: new AMap.Pixel(0, -30)
    })

    marker.on('click', () => infoWindow.open(map, marker.getPosition()))
    marker.on('dragend', () => {
      const pos = marker.getPosition()
      attraction.location.longitude = pos.lng
      attraction.location.latitude = pos.lat
      redrawRoutes(AMap)
    })

    allMarkers.push(marker)
  })

  map.add(allMarkers)
  if (allAttractions.length > 0) map.setFitView(allMarkers, false, [60, 60, 60, 60])
  drawRoutes(AMap, allAttractions)
}

function redrawRoutes(AMap: any) {
  allPolylines.forEach(p => map.remove(p))
  allPolylines = []

  const allAttractions: any[] = []
  props.tripPlan?.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction: any, attrIndex: number) => {
      if (attraction.location?.longitude && attraction.location?.latitude) {
        allAttractions.push({ ...attraction, dayIndex, attrIndex })
      }
    })
  })
  drawRoutes(AMap, allAttractions)
}

// ===== 路线 =====
function drawRoutes(AMap: any, attractions: any[]) {
  if (attractions.length < 2) return

  const dayGroups: Record<number, any[]> = {}
  attractions.forEach(attr => {
    if (!dayGroups[attr.dayIndex]) dayGroups[attr.dayIndex] = []
    dayGroups[attr.dayIndex].push(attr)
  })

  Object.values(dayGroups).forEach((dayAttrs: any[]) => {
    if (dayAttrs.length < 2) return
    const path = dayAttrs.map(a => [a.location.longitude, a.location.latitude])
    const polyline = new AMap.Polyline({
      path,
      strokeColor: '#1890ff',
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeStyle: 'solid',
      showDir: true
    })
    map.add(polyline)
    allPolylines.push(polyline)
  })
}

// ===== 编辑模式 =====
function enableMapEdit() {
  if (!map) return
  const Pixel = (window as any).AMap?.Pixel
  allMarkers.forEach((m, i) => {
    m.setDraggable(true)
    m.setLabel({
      content: `<div style="background:#FF9800;color:white;padding:4px 8px;border-radius:4px;font-size:12px;">${i + 1}✎</div>`,
      offset: Pixel ? new Pixel(0, -30) : undefined
    })
  })

  mapEditHandler = (e: any) => {
    if (!props.tripPlan || !props.editMode) return
    if (e.target?._attractionRef) return

    const day = props.tripPlan.days[props.currentEditDayIndex]
    if (!day) return

    const pos = e.lnglat
    const newAttr = {
      name: `新景点${day.attractions.length + 1}`,
      address: '手动标记',
      location: { longitude: pos.lng, latitude: pos.lat },
      visit_duration: 60,
      description: '手动新增景点',
      category: '自定义',
      rating: null,
      photos: [],
      poi_id: '',
      image_url: null,
      ticket_price: 0
    }
    day.attractions.push(newAttr)
    message.success(`已在地图添加「${newAttr.name}」到第${props.currentEditDayIndex + 1}天`)

    const AMap = (window as any).AMap
    if (AMap) {
      allMarkers.forEach(m => map.remove(m))
      addAttractionMarkers(AMap)
    }
  }
  map.on('click', mapEditHandler)
}

function disableMapEdit() {
  if (!map) return
  if (mapEditHandler) { map.off('click', mapEditHandler); mapEditHandler = null }
  const Pixel = (window as any).AMap?.Pixel
  allMarkers.forEach((m, i) => {
    m.setDraggable(false)
    m.setLabel({
      content: `<div style="background:#4CAF50;color:white;padding:4px 8px;border-radius:4px;font-size:12px;">${i + 1}</div>`,
      offset: Pixel ? new Pixel(0, -30) : undefined
    })
  })
}
</script>

<style scoped>
.map-card { height: 100%; min-height: 500px; }
.amap-container { width: 100%; height: 500px; min-height: 500px; }
.map-card :deep(.ant-card-body) { height: calc(100% - 57px); padding: 0; }
</style>
