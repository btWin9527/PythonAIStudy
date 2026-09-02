/**
 * 导出工具:图片/PDF
 * 包含旅行计划导出和志愿方案导出两种模式
 */
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import type { VolunteerPlan, VolunteerProfile } from '@/types'

// ============ 通用导出函数 ============

async function captureToCanvas(element: HTMLElement): Promise<HTMLCanvasElement> {
  return html2canvas(element, {
    backgroundColor: '#fff',
    scale: 2,
    logging: false,
    useCORS: true,
    allowTaint: true
  })
}

function triggerDownload(filename: string, canvas: HTMLCanvasElement) {
  const link = document.createElement('a')
  link.download = filename
  link.href = canvas.toDataURL('image/png')
  link.click()
}

function canvasToPDF(canvas: HTMLCanvasElement, filename: string) {
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
  pdf.save(filename)
}

// ============ 志愿方案导出 ============

/** 构建志愿方案导出用的纯HTML（不依赖 Ant Design 组件） */
function buildVolunteerExportHTML(plan: VolunteerPlan, profile: VolunteerProfile): string {
  const tierLabels: Record<string, { label: string; icon: string }> = {
    chong: { label: '冲刺院校', icon: '🎯' },
    wen: { label: '稳妥院校', icon: '✅' },
    bao: { label: '保底院校', icon: '🛡️' }
  }

  const tiersColorMap: Record<string, string> = {
    chong: '#fa8c16',
    wen: '#1890ff',
    bao: '#52c41a'
  }

  const tiersHTML = plan.tiers.map(tier => {
    const color = tiersColorMap[tier.tier_type] || '#667eea'
    const schoolsHTML = tier.schools.map((s, i) => {
      const sourcesHTML = s.reference_sources && s.reference_sources.length > 0
        ? `<div style="margin-top:8px;font-size:11px;color:#888;">
            📎 来源：${s.reference_sources.slice(0, 2).map(src => 
              `<a href="${src}" style="color:#1677ff;text-decoration:none;word-break:break-all;">${src}</a>`
            ).join(' | ')}
            ${s.reference_sources.length > 2 ? ` ...等${s.reference_sources.length}个来源` : ''}
          </div>` : ''

      const tagsHTML = [
        s.school_type ? `<span style="background:#f6ffed;color:#389e0d;padding:1px 6px;border-radius:4px;font-size:11px;margin-left:4px;">${s.school_type}</span>` : '',
        s.school_level ? `<span style="background:#f9f0ff;color:#722ed1;padding:1px 6px;border-radius:4px;font-size:11px;margin-left:4px;">${s.school_level}</span>` : ''
      ].join('')

      return `
        <div style="border:1px solid #e8e8e8;border-radius:8px;padding:14px 16px;margin-bottom:10px;border-left:4px solid ${color};">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="flex:1;">
              <div style="margin-bottom:4px;">
                <span style="background:${color};color:#fff;border-radius:50%;width:22px;height:22px;display:inline-flex;align-items:center;justify-content:center;font-size:12px;margin-right:8px;font-weight:600;">${i + 1}</span>
                <span style="font-size:15px;font-weight:bold;color:#1a1a1a;">${s.school_name}</span>
                <span style="background:#e6f4ff;color:#1677ff;border-radius:4px;padding:2px 8px;font-size:12px;margin-left:6px;">${s.major_name}</span>
                ${tagsHTML}
              </div>
              <div style="font-size:12px;color:#888;margin-bottom:4px;">
                参考线：${s.reference_score ?? '-'}分 ${s.reference_score ? `（考生 ${profile.score} 分，差 ${s.reference_score - profile.score} 分）` : ''}
              </div>
              <div style="color:#555;font-size:13px;line-height:1.5;">💡 ${s.reason}</div>
              ${sourcesHTML}
            </div>
            <div style="min-width:52px;text-align:center;background:${color};color:#fff;border-radius:8px;padding:6px 8px;margin-left:12px;">
              <div style="font-size:18px;font-weight:700;line-height:1;">${s.confidence}</div>
              <div style="font-size:10px;opacity:.85;">信心度</div>
            </div>
          </div>
        </div>
      `
    }).join('')

    return `
      <div style="margin-bottom:24px;">
        <div style="display:flex;align-items:center;margin-bottom:8px;">
          <div style="width:4px;height:24px;background:${color};border-radius:2px;margin-right:12px;"></div>
          <h3 style="color:#1a1a1a;font-size:17px;margin:0;">
            ${tierLabels[tier.tier_type]?.icon || ''} ${tierLabels[tier.tier_type]?.label || tier.tier_label}
            <span style="font-size:13px;color:#999;font-weight:normal;margin-left:8px;">（${tier.schools.length}所）</span>
          </h3>
        </div>
        <p style="color:#888;font-size:13px;margin:0 0 16px 16px;">${tier.description}</p>
        ${schoolsHTML}
      </div>
    `
  }).join('')

  return `
    <div style="width:800px;background:#fff;padding:40px 48px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
      <div style="text-align:center;margin-bottom:32px;border-bottom:2px solid #667eea;padding-bottom:20px;">
        <h1 style="font-size:24px;color:#1a1a1a;margin:0 0 12px;font-weight:700;">🎓 高考志愿填报方案</h1>
        <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;font-size:14px;color:#555;">
          <span>📍 <b>${profile.province}</b></span>
          <span>🎯 <b>${profile.score}</b> 分</span>
          <span>📚 <b>${profile.subjectLabel}</b></span>
          ${profile.targetMajor ? `<span>💼 <b>${profile.targetMajor}</b></span>` : ''}
        </div>
      </div>

      <div style="background:linear-gradient(135deg,#f5f7ff,#f0f2ff);border-left:4px solid #667eea;padding:16px 20px;margin-bottom:28px;border-radius:0 8px 8px 0;">
        <div style="font-weight:600;color:#667eea;margin-bottom:6px;font-size:14px;">📋 总体填报策略</div>
        <p style="color:#444;margin:0;line-height:1.7;font-size:14px;">${plan.summary}</p>
      </div>

      ${tiersHTML}

      <div style="border-top:1px dashed #e8e8e8;padding-top:16px;margin-top:28px;color:#999;font-size:12px;text-align:center;line-height:1.6;">
        ${plan.disclaimer || '以上推荐基于AI分析，仅供参考。实际填报请以各省考试院官方数据为准。'}
      </div>
      <div style="text-align:center;color:#ccc;font-size:11px;margin-top:8px;">
        生成时间：${new Date().toLocaleString('zh-CN')}
      </div>
    </div>
  `
}

/** 志愿方案导出图片 */
export async function exportVolunteerAsImage(
  plan: VolunteerPlan,
  profile: VolunteerProfile,
  onLoading: (msg: string) => void,
  onSuccess: (msg: string) => void,
  onError: (msg: string) => void
) {
  try {
    onLoading('正在生成图片...')

    const container = document.createElement('div')
    container.innerHTML = buildVolunteerExportHTML(plan, profile)
    container.style.position = 'absolute'
    container.style.left = '-9999px'
    container.style.top = '0'
    document.body.appendChild(container)

    const canvas = await captureToCanvas(container)
    document.body.removeChild(container)

    const filename = `志愿方案_${profile.province}_${profile.score}分_${Date.now()}.png`
    triggerDownload(filename, canvas)

    onSuccess('图片导出成功!')
  } catch (error: any) {
    console.error('导出图片失败:', error)
    onError(`导出图片失败: ${error.message || '未知错误'}`)
  }
}

/** 志愿方案导出 PDF */
export async function exportVolunteerAsPDF(
  plan: VolunteerPlan,
  profile: VolunteerProfile,
  onLoading: (msg: string) => void,
  onSuccess: (msg: string) => void,
  onError: (msg: string) => void
) {
  try {
    onLoading('正在生成PDF...')

    const container = document.createElement('div')
    container.innerHTML = buildVolunteerExportHTML(plan, profile)
    container.style.position = 'absolute'
    container.style.left = '-9999px'
    container.style.top = '0'
    document.body.appendChild(container)

    const canvas = await captureToCanvas(container)
    document.body.removeChild(container)

    const filename = `志愿方案_${profile.province}_${profile.score}分_${Date.now()}.pdf`
    canvasToPDF(canvas, filename)

    onSuccess('PDF导出成功!')
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    onError(`导出PDF失败: ${error.message || '未知错误'}`)
  }
}
