import { apiClient } from './client'
import type { EvidenceResponse, RunResponse, TraceResponse } from '@/types/api'

export async function createRun(payload: { workflow_id: string; version_number?: number; input: Record<string, unknown>; mode: 'sync' | 'async'; model_profile_id?: string }): Promise<RunResponse> {
  return (await apiClient.post<RunResponse>('/api/v1/runs', payload)).data
}

export async function getRun(runId: string): Promise<RunResponse> {
  return (await apiClient.get<RunResponse>(`/api/v1/runs/${runId}`)).data
}

export async function cancelRun(runId: string): Promise<void> {
  await apiClient.post(`/api/v1/runs/${runId}/cancel`)
}

export async function getTraces(runId: string): Promise<TraceResponse[]> {
  return (await apiClient.get<TraceResponse[]>(`/api/v1/runs/${runId}/traces`)).data
}

export async function getEvidence(runId: string, evidenceId: string): Promise<EvidenceResponse> {
  return (await apiClient.get<EvidenceResponse>(`/api/v1/runs/${runId}/evidence/${evidenceId}`)).data
}
