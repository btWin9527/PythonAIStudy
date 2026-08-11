/**
 * 地图工具函数
 */

/** 收集所有景点的经纬度坐标 */
export function collectAttractionCoords(tripPlan: any) {
  const allAttractions: Array<{ lng: number; lat: number; name: string; label: string }> = []
  const dayGroups: Record<number, Array<{ lng: number; lat: number }>> = {}

  tripPlan.days.forEach((day: any, dayIdx: number) => {
    day.attractions.forEach((att: any) => {
      const loc = att.location
      if (loc && loc.longitude && loc.latitude) {
        allAttractions.push({ lng: loc.longitude, lat: loc.latitude, name: att.name, label: String(dayIdx + 1) })
        if (!dayGroups[dayIdx]) dayGroups[dayIdx] = []
        dayGroups[dayIdx].push({ lng: loc.longitude, lat: loc.latitude })
      }
    })
  })

  return { allAttractions, dayGroups }
}

/** 根据经纬度范围自动计算合适的 zoom 级别 */
export function autoZoom(maxLon: number, minLon: number, maxLat: number, minLat: number): number {
  const maxSpan = Math.max(maxLon - minLon, maxLat - minLat)
  if (maxSpan > 2) return 7
  if (maxSpan > 0.5) return 9
  if (maxSpan > 0.2) return 11
  if (maxSpan > 0.1) return 12
  if (maxSpan > 0.04) return 13
  if (maxSpan > 0.02) return 14
  return 15
}

/** 餐食类型中文映射 */
export function getMealLabel(type: string): string {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}
