import { apiClient } from './client'
import type { PromptOptimizationResponse } from '@/types/api'

export async function createPromptOptimization(payload: { run_id: string; node_id: string; instruction: string; model_profile_id?: string }): Promise<PromptOptimizationResponse> {
  return (await apiClient.post<PromptOptimizationResponse>('/api/v1/prompt-optimizations', payload)).data
}

export async function getPromptOptimization(id: string): Promise<PromptOptimizationResponse> {
  return (await apiClient.get<PromptOptimizationResponse>(`/api/v1/prompt-optimizations/${id}`)).data
}

export async function applyPromptOptimization(id: string): Promise<PromptOptimizationResponse> {
  return (await apiClient.post<PromptOptimizationResponse>(`/api/v1/prompt-optimizations/${id}/apply`)).data
}
