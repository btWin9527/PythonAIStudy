/**
 * POI 图片 API
 */
const API_BASE = 'http://localhost:8000'

/** 加载景点图片(多张候选,全局去重) */
export async function loadAttractionPhotos(tripPlan: any): Promise<Record<string, string>> {
  const photos: Record<string, string> = {}
  const loadedUrls = new Set<string>()

  if (!tripPlan) return photos

  const tasks: Promise<void>[] = []

  tripPlan.days.forEach((day: any) => {
    day.attractions.forEach((attraction: any) => {
      const promise = fetch(`${API_BASE}/api/poi/photo?name=${encodeURIComponent(attraction.name)}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data) {
            const candidates: string[] =
              Array.isArray(data.data.photo_urls) && data.data.photo_urls.length > 0
                ? data.data.photo_urls
                : data.data.photo_url ? [data.data.photo_url] : []

            const picked = candidates.find(u => u && !loadedUrls.has(u))
            if (picked) {
              photos[attraction.name] = picked
              loadedUrls.add(picked)
            } else if (candidates.length > 0) {
              photos[attraction.name] = candidates[0]
              loadedUrls.add(candidates[0])
            }
          }
        })
        .catch(err => console.error(`获取${attraction.name}图片失败:`, err))

      tasks.push(promise)
    })
  })

  await Promise.all(tasks)
  return photos
}
