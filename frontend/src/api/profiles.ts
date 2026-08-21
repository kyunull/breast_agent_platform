import { apiClient } from './client'
import type { EvidenceResponse, ModelProfileConnectionTestResponse, Profile, ProfileCreatePayload } from '@/types/api'

export interface ModelProfileConnectionTestPayload {
  provider: 'openai_compatible'
  base_url: string
  model: string
  api_key?: string
  profile_id?: string
  temperature?: number
  top_p?: number
  max_tokens?: number
  timeout?: number
  retries?: number
}

export interface KnowledgePreviewPayload {
  knowledge_profile_id: string
  query: string
  guideline_ids: string[]
  version_ids: string[]
  language: string
}

export interface KnowledgePreviewResponse {
  evidence: EvidenceResponse[]
}

export async function listModelProfiles(): Promise<Profile[]> {
  return (await apiClient.get<Profile[]>('/api/v1/model-profiles')).data
}

export async function listKnowledgeProfiles(): Promise<Profile[]> {
  return (await apiClient.get<Profile[]>('/api/v1/knowledge-profiles')).data
}

export async function createModelProfile(payload: ProfileCreatePayload): Promise<Profile> {
  return (await apiClient.post<Profile>('/api/v1/model-profiles', payload)).data
}

export async function createKnowledgeProfile(payload: ProfileCreatePayload): Promise<Profile> {
  return (await apiClient.post<Profile>('/api/v1/knowledge-profiles', payload)).data
}

export async function patchModelProfile(id: string, payload: Partial<ProfileCreatePayload>): Promise<Profile> {
  return (await apiClient.patch<Profile>(`/api/v1/model-profiles/${id}`, payload)).data
}

export async function patchKnowledgeProfile(id: string, payload: Partial<ProfileCreatePayload>): Promise<Profile> {
  return (await apiClient.patch<Profile>(`/api/v1/knowledge-profiles/${id}`, payload)).data
}

export async function testModelProfile(payload: ModelProfileConnectionTestPayload): Promise<ModelProfileConnectionTestResponse> {
  const { api_key, profile_id, ...technical_config } = payload
  return (await apiClient.post<ModelProfileConnectionTestResponse>('/api/v1/model-profiles/test', { technical_config, api_key, profile_id })).data
}

export async function previewKnowledge(payload: KnowledgePreviewPayload): Promise<KnowledgePreviewResponse> {
  return (await apiClient.post<KnowledgePreviewResponse>('/api/v1/knowledge/retrieve/preview', payload)).data
}
