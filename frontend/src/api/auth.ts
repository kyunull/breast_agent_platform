import { apiClient } from './client'
import type { LoginCredentials, TokenResponse, User } from '@/types/api'

export async function login(credentials: LoginCredentials): Promise<TokenResponse> {
  return (await apiClient.post<TokenResponse>('/api/v1/auth/login', credentials)).data
}

export async function me(): Promise<User> {
  return (await apiClient.get<User>('/api/v1/me')).data
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/v1/auth/logout')
}
