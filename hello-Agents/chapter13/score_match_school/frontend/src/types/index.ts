/** 志愿填报类型定义 */

// ============ 基础数据类型 ============

export interface SchoolMajor {
  school_name: string
  major_name: string
  confidence: number
  reason: string
  reference_score?: number
  school_type?: string
  school_level?: string
  reference_sources?: string[]
}

export interface VolunteerTier {
  tier_type: 'chong' | 'wen' | 'bao'
  tier_label: string
  description: string
  schools: SchoolMajor[]
}

export interface VolunteerPlan {
  summary: string
  tiers: VolunteerTier[]
  disclaimer?: string
}

export interface VolunteerProfile {
  province: string
  score: number
  subjectCategory: string // science | arts | art
  subjectLabel: string // 显示用：理科/物理类
  targetMajor: string
}

export interface VolunteerPlanResponse {
  success: boolean
  message: string
  data: VolunteerPlan | null
}

// ============ 表单请求类型 ============

export interface VolunteerRequest {
  province: string
  score: number
  target_major: string
  subject_category: 'science' | 'arts' | 'art'
}

// ============ 筛选器类型 ============

export interface FilterState {
  schoolType: string
  schoolLevel: string
  majorKeyword: string
  minConfidence: number
}

// ============ 报考类别配置 ============

export const SUBJECT_CATEGORY_OPTIONS: {
  value: 'science' | 'arts' | 'art'
  label: string
  subLabel: string
}[] = [
  { value: 'science', label: '理科', subLabel: '物理类' },
  { value: 'arts', label: '文科', subLabel: '历史类' },
  { value: 'art', label: '艺术类', subLabel: '艺术类' }
]

// ============ 院校类型选项 ============

export const SCHOOL_TYPE_OPTIONS: string[] = [
  '综合类', '理工类', '财经类', '师范类', '医药类',
  '艺术类', '语言类', '政法类', '农林类', '军事类', '民族类'
]

// ============ 院校层级选项 ============

export const SCHOOL_LEVEL_OPTIONS: string[] = [
  '985', '211', '双一流', '普通本科'
]

// ============ 档位配置 ============

export const TIER_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  chong: { label: '🎯 冲刺', color: '#fa8c16', icon: '🎯' },
  wen: { label: '✅ 稳妥', color: '#1890ff', icon: '✅' },
  bao: { label: '🛡️ 保底', color: '#52c41a', icon: '🛡️' }
}
