import axios from 'axios'

export const TOKEN_KEY = 'breast-agent-token'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      sessionStorage.removeItem(TOKEN_KEY)
    }
    return Promise.reject(error)
  },
)

export function getApiError(error: unknown): { code: string; message: string; detail?: Record<string, unknown> } {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return { code: 'request_failed', message: detail }
    if (detail && typeof detail === 'object') {
      return {
        code: String(detail.code ?? 'request_failed'),
        message: String(detail.message ?? '请求失败，请稍后重试。'),
        detail,
      }
    }
    return { code: `http_${error.response?.status ?? 'unknown'}`, message: '请求失败，请检查服务连接。' }
  }
  return { code: 'unknown_error', message: '发生未知错误，请稍后重试。' }
}
