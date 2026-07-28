/* ======================== API 客户端 ======================== */

const BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

// ---- SSE 流式读取 ----
export async function* streamChat(question: string): AsyncGenerator<string> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const data = JSON.parse(line.slice(6))
        if (data.type === 'delta' && data.text) {
          yield data.text
        }
      } catch {
        // 跳过非 JSON 行
      }
    }
  }
}

// ---- REST API ----
export const api = {
  init: () => request<InitResponse>('/init'),

  token: () => request<TokenInfo>('/token'),

  uploadPdf: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE}/upload-pdf`, { method: 'POST', body: form })
    return res.json()
  },

  addNote: (content: string, concept?: string) =>
    request<{ success: boolean }>('/add-note', {
      method: 'POST',
      body: JSON.stringify({ content, concept }),
    }),

  stats: () => request<Record<string, any>>('/stats'),

  report: () => request<Record<string, any>>('/report'),

  history: () => request<{ history: ChatPair[] }>('/history'),

  clearHistory: () =>
    request<{ success: boolean }>('/clear-history', { method: 'POST' }),
}

// ---- 类型 ----
export interface TokenInfo {
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  remaining: number
  calls: number
}

export interface ChatPair {
  user: string
  assistant: string
}

export interface InitResponse {
  success: boolean
  message: string
  document: string
  history: ChatPair[]
  token_usage: TokenInfo
}
