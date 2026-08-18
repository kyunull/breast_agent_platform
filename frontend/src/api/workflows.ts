import { apiClient } from './client'
import type { DraftResponse, PublishedVersion, WorkflowSummary } from '@/types/api'

export async function listWorkflows(): Promise<WorkflowSummary[]> {
  return (await apiClient.get<WorkflowSummary[]>('/api/v1/workflows')).data
}

export async function createWorkflow(payload: { name: string; description?: string }): Promise<WorkflowSummary> {
  return (await apiClient.post<WorkflowSummary>('/api/v1/workflows', payload)).data
}

export async function getDraft(workflowId: string): Promise<DraftResponse> {
  return (await apiClient.get<DraftResponse>(`/api/v1/workflows/${workflowId}/draft`)).data
}

export async function patchDraft(workflowId: string, payload: Partial<Pick<DraftResponse, 'name' | 'description' | 'graph' | 'extraction' | 'metadata' | 'template_refs'>>): Promise<DraftResponse> {
  return (await apiClient.patch<DraftResponse>(`/api/v1/workflows/${workflowId}/draft`, payload)).data
}

export async function publishWorkflow(workflowId: string): Promise<PublishedVersion> {
  return (await apiClient.post<PublishedVersion>(`/api/v1/workflows/${workflowId}/publish`)).data
}

export async function listVersions(workflowId: string): Promise<PublishedVersion[]> {
  return (await apiClient.get<PublishedVersion[]>(`/api/v1/workflows/${workflowId}/versions`)).data
}
