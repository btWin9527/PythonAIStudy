/**
 * 地图相关 API
 */
import { collectAttractionCoords, autoZoom } from '@/utils/map'

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000'

/** 调用后端静态地图 API 获取完整地图 PNG dataURL */
export async function captureMapImage(tripPlan: any): Promise<string> {
  if (!tripPlan) return ''

  try {
    const { allAttractions, dayGroups } = collectAttractionCoords(tripPlan)
    if (allAttractions.length === 0) {
      console.warn('[MapCapture] 无景点坐标,跳过')
      return ''
    }

    const lons = allAttractions.map(a => a.lng)
    const lats = allAttractions.map(a => a.lat)
    const centerLng = (Math.min(...lons) + Math.max(...lons)) / 2
    const centerLat = (Math.min(...lats) + Math.max(...lats)) / 2
    const zoom = autoZoom(Math.max(...lons), Math.min(...lons), Math.max(...lats), Math.min(...lats))

    const params = new URLSearchParams()
    params.set('center', `${centerLng.toFixed(6)},${centerLat.toFixed(6)}`)
    params.set('zoom', String(zoom))
    params.set('size', '800*500')
    params.set('markers', JSON.stringify(allAttractions))
    params.set('paths', JSON.stringify(Object.values(dayGroups)))

    const url = `${API_BASE}/api/map/static?${params.toString()}`
    console.log('[MapCapture] 请求静态地图:', url.slice(0, 200), '...')

    const resp = await fetch(url)
    if (!resp.ok) {
      const errText = await resp.text()
      throw new Error(`后端 ${resp.status}: ${errText.slice(0, 200)}`)
    }

    const blob = await resp.blob()
    return await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result || ''))
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  } catch (error) {
    console.error('[MapCapture] 后端静态地图生成失败:', error)
    return ''
  }
}

/** 降级:html2canvas 直接截取地图 DOM */
export async function fallbackCaptureMap(): Promise<string> {
  const mapContainer = document.getElementById('amap-container')
  if (!mapContainer) return ''
  try {
    const { default: html2canvas } = await import('html2canvas')
    const canvas = await html2canvas(mapContainer, {
      backgroundColor: '#ffffff',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })
    return canvas.toDataURL('image/png')
  } catch (e) {
    console.error('[MapCapture] html2canvas 截取地图也失败:', e)
    return ''
  }
}
