import axios from 'axios'
import type { VolunteerRequest, VolunteerPlanResponse } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // 3分钟超时（AI联网搜索可能较慢）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

/**
 * 生成志愿填报方案
 */
export async function generateVolunteerPlan(
  request: VolunteerRequest
): Promise<VolunteerPlanResponse> {
  try {
    const response = await apiClient.post<VolunteerPlanResponse>(
      '/api/volunteer/generate',
      request
    )
    return response.data
  } catch (error: any) {
    console.error('生成志愿方案失败:', error)
    throw new Error(
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      '生成志愿方案失败'
    )
  }
}

/**
 * 获取省份列表
 */
export async function getProvinces(): Promise<{ success: boolean; data: string[] }> {
  try {
    const response = await apiClient.get('/api/volunteer/provinces')
    return response.data
  } catch (error: any) {
    console.error('获取省份列表失败:', error)
    // 返回默认列表作为降级
    return {
      success: false,
      data: [
        '北京', '天津', '上海', '重庆',
        '河北', '山西', '辽宁', '吉林', '黑龙江',
        '江苏', '浙江', '安徽', '福建', '江西', '山东',
        '河南', '湖北', '湖南', '广东', '海南',
        '四川', '贵州', '云南', '陕西', '甘肃', '青海',
        '台湾', '内蒙古', '广西', '西藏', '宁夏', '新疆', '香港', '澳门'
      ]
    }
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

export default apiClient
