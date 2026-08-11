/**
 * 导出工具:图片/PDF
 */
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

/** 导出容器样式处理(复制自 DOM 后统一刷样式,确保截图一致) */
function applyExportStyles(container: HTMLElement) {
  // 卡片
  container.querySelectorAll('.ant-card').forEach(card => {
    const el = card as HTMLElement
    el.className = ''
    el.style.cssText = 'background-color:#fff;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,.1);margin-bottom:20px;overflow:hidden'
  })
  // 卡片头部
  container.querySelectorAll('.ant-card-head').forEach(h => {
    const el = h as HTMLElement
    el.style.cssText = 'background-color:#667eea;color:#fff;padding:16px 24px;font-size:18px;font-weight:600'
  })
  // 卡片内容
  container.querySelectorAll('.ant-card-body').forEach(b => {
    (b as HTMLElement).style.cssText = 'background-color:#fff;padding:24px'
  })
  // 酒店卡片
  container.querySelectorAll('.hotel-card').forEach(card => {
    (card as HTMLElement).style.backgroundColor = '#e3f2fd'
    const head = card.querySelector('.ant-card-head') as HTMLElement
    if (head) head.style.backgroundColor = '#1976d2'
  })
  // 天气卡片
  container.querySelectorAll('.weather-card').forEach(card => {
    (card as HTMLElement).style.backgroundColor = '#e0f7fa'
  })
  // 预算总计
  const budgetTotal = container.querySelector('.budget-total') as HTMLElement
  if (budgetTotal) {
    budgetTotal.style.cssText = 'background-color:#667eea;color:#fff;padding:20px;border-radius:12px;margin-bottom:20px'
  }
  // 预算项
  container.querySelectorAll('.budget-item').forEach(item => {
    (item as HTMLElement).style.cssText = 'background-color:#f5f7fa;padding:16px;border-radius:8px;margin-bottom:12px'
  })
}

/** 导出为图片 */
export async function exportAsImage(
  tripPlan: any,
  mapDataURL: string,
  onLoading: (msg: string) => void,
  onSuccess: (msg: string) => void,
  onError: (msg: string) => void
) {
  try {
    onLoading('正在生成图片...')

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) throw new Error('未找到内容元素')

    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f5f7fa'
    exportContainer.style.padding = '20px'
    exportContainer.innerHTML = element.innerHTML

    // 嵌入地图截图
    if (mapDataURL) {
      const mapEl = exportContainer.querySelector('#amap-container') as HTMLElement
      if (mapEl) {
        mapEl.innerHTML = `<img src="${mapDataURL}" style="width:100%;height:500px;object-fit:cover;display:block;" />`
        mapEl.style.height = '500px'
      }
    }

    applyExportStyles(exportContainer)

    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f5f7fa',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })
    document.body.removeChild(exportContainer)

    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.city}_${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()

    onSuccess('图片导出成功!')
  } catch (error: any) {
    console.error('导出图片失败:', error)
    onError(`导出图片失败: ${error.message}`)
  }
}

/** 导出为 PDF */
export async function exportAsPDF(
  tripPlan: any,
  mapDataURL: string,
  onLoading: (msg: string) => void,
  onSuccess: (msg: string) => void,
  onError: (msg: string) => void
) {
  try {
    onLoading('正在生成PDF...')

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) throw new Error('未找到内容元素')

    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f5f7fa'
    exportContainer.style.padding = '20px'
    exportContainer.innerHTML = element.innerHTML

    if (mapDataURL) {
      const mapEl = exportContainer.querySelector('#amap-container') as HTMLElement
      if (mapEl) {
        mapEl.innerHTML = `<img src="${mapDataURL}" style="width:100%;height:500px;object-fit:cover;display:block;" />`
        mapEl.style.height = '500px'
      }
    }

    applyExportStyles(exportContainer)

    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f5f7fa',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })
    document.body.removeChild(exportContainer)

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const imgWidth = 210
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    let heightLeft = imgHeight
    let position = 0
    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297
    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }
    pdf.save(`旅行计划_${tripPlan.city}_${Date.now()}.pdf`)

    onSuccess('PDF导出成功!')
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    onError(`导出PDF失败: ${error.message}`)
  }
}
