import { apiClient } from './client'
import type { ExtractionConfig } from '@/types/api'

export interface ExtractionPreviewResponse {
  groups: Record<string, Record<string, unknown>>
  missing: Record<string, string[]>
  sufficiency: Record<string, { status: 'sufficient' | 'insufficient'; missing_required: string[]; error_count: number }>
  errors: Record<string, Record<string, string>>
}

export async function previewExtraction(workflowId: string, payload: Record<string, unknown>, config: ExtractionConfig) {
  return (await apiClient.post<ExtractionPreviewResponse>(`/api/v1/workflows/${workflowId}/draft/extraction/preview`, { sample_json: payload, config })).data
}
