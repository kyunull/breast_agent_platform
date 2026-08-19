import { apiClient } from './client'
import type { ModelProfileConnectionTestResponse, Profile, ProfileCreatePayload } from '@/types/api'

export interface ModelProfileConnectionTestPayload {
  provider: 'openai_compatible'
  base_url: string
  model: string
  api_key_ref?: string
  temperature?: number
  top_p?: number
  max_tokens?: number
  timeout?: number
  retries?: number
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
  return (await apiClient.post<ModelProfileConnectionTestResponse>('/api/v1/model-profiles/test', {
    technical_config: payload,
  })).data
}
